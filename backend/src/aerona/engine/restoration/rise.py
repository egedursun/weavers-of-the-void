from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, LawJurisdictionRow, LawProfileRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.restoration import OPEN_STAGES, RestorationBasis, RestorationFailure, RestorationStage
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.control import split
from aerona.engine.polity.formation import found_polity, refresh_realms, set_ruler
from aerona.engine.polity.laws import enact
from aerona.engine.polity.titles import de_jure_lands
from aerona.engine.primitives.mirrors import close_legacy, first_sight
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect, living_entity, remove_flag
from aerona.engine.reckoning.book import ReckoningTally
from aerona.engine.reckoning.opening import choose, open_reckoning, victims_pressure
from aerona.engine.recording.record import record

LEGACY_FIXUP = "restoration.legacy_pretenders"
CLAIM_FAMILY = "restoration.claim"
STABILITY_FLOOR = 0
TRACE_MEMORY = 10
B = RestorationBasis
BASIS_LEGITIMACY = total(RestorationBasis, {B.BLOODLINE: 10, B.FAITH: 15, B.LAW: 5, B.MEMORY: 5, B.FOREIGN_BACKING: 0})
FOREIGN_HOLD = 20


@dataclass
class RestorationTally:
    begun: int = 0
    rising: int = 0
    restored: int = 0
    failed: int = 0
    faded: int = 0


def bases_of(row: RestorationRow) -> set[RestorationBasis]:
    known = {item.value: item for item in RestorationBasis}
    return {known[value] for value in row.bases or [] if value in known}


async def open_for(ctx: TickContext, fallen_id: int) -> RestorationRow | None:
    query = select(RestorationRow).where(RestorationRow.fallen_polity_id == fallen_id, RestorationRow.stage.in_(sorted(OPEN_STAGES)))
    return await ctx.session.scalar(query.order_by(RestorationRow.id).limit(1))


async def old_lands(ctx: TickContext, fallen_id: int) -> list[int]:
    lands: set[int] = set()
    for title in await ctx.session.scalars(select(TitleProfileRow.title_entity_id).where(TitleProfileRow.polity_entity_id == fallen_id)):
        lands |= await de_jure_lands(ctx, title)
    profile = await ctx.session.get(PolityProfileRow, fallen_id)
    if profile is not None and profile.core_entity_id is not None:
        lands.add(profile.core_entity_id)
    return sorted(lands)


async def remembered(ctx: TickContext, fallen_id: int) -> int:
    accounts = len(list(await ctx.session.scalars(select(AccountRow.id).where(AccountRow.subject_node_id == fallen_id))))
    claims = len(list(await ctx.session.scalars(select(ClaimRow.id).where(ClaimRow.polity_entity_id == fallen_id, ClaimRow.ended_epoch.is_(None)))))
    titles = len(list(await ctx.session.scalars(select(TitleProfileRow.title_entity_id).where(TitleProfileRow.polity_entity_id == fallen_id))))
    return clamp_int((accounts + claims + titles) * TRACE_MEMORY, 0, PERCENT)


async def raise_movement(
    ctx: TickContext, fallen: EntityRow, *, claimant: int | None, bases: list[RestorationBasis], territories: list[int], tally: RestorationTally
) -> RestorationRow:
    found = await open_for(ctx, fallen.id)
    if found is not None:
        if found.stage is RestorationStage.MEMORY and "stage" not in (found.locked or []):
            found.stage = RestorationStage.MOVEMENT
        return found
    row = RestorationRow(
        fallen_polity_id=fallen.id,
        claimant_node_id=claimant,
        territories=sorted(set(territories)) or await old_lands(ctx, fallen.id),
        bases=sorted({basis.value for basis in bases}),
        stage=RestorationStage.MOVEMENT,
        memory=clamp_int(await remembered(ctx, fallen.id) + ctx.rules.restoration.basis_memory * len(set(bases)), 0, PERCENT),
        begun_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.begun += 1
    await record(
        ctx,
        "polity.restoration_begun",
        roles={IncidentRole.SUBJECT: fallen.id, IncidentRole.ACTOR: claimant},
        facts={"bases": ", ".join(spoken(basis) for basis in bases) or "memory", "memory": row.memory},
    )
    return row


async def grievance(ctx: TickContext, towns: list[int]) -> int:
    unrest = [row.unrest for row in await ctx.session.scalars(select(SettlementProfileRow).where(SettlementProfileRow.settlement_entity_id.in_(towns)))]
    return sum(unrest) // len(unrest) if unrest else 0


async def realms_holding(ctx: TickContext, towns: list[int]) -> dict[int, list[int]]:
    held_by: dict[int, list[int]] = {}
    for member in await ctx.session.scalars(
        select(PolityMemberRow).where(PolityMemberRow.member_entity_id.in_(towns)).order_by(PolityMemberRow.member_entity_id)
    ):
        held_by.setdefault(member.polity_entity_id, []).append(member.member_entity_id)
    return held_by


async def resisted(ctx: TickContext, row: RestorationRow) -> bool:
    steady = ctx.rules.restoration.resistance_stability + (FOREIGN_HOLD if RestorationBasis.FOREIGN_BACKING in bases_of(row) else 0)
    for realm_id in await realms_holding(ctx, list(row.territories or [])):
        profile = await ctx.session.get(PolityProfileRow, realm_id)
        if profile is not None and profile.stability >= steady:
            return True
    return False


async def fail(ctx: TickContext, row: RestorationRow, why: RestorationFailure, tally: RestorationTally) -> None:
    row.stage, row.ended_epoch = RestorationStage.FAILED, ctx.epoch
    tally.failed += 1
    await record(
        ctx, "polity.restoration_failed", roles={IncidentRole.SUBJECT: row.fallen_polity_id, IncidentRole.ACTOR: row.claimant_node_id}, facts={"why": why}
    )


async def take_back(ctx: TickContext, row: RestorationRow, fallen: EntityRow, profile: PolityProfileRow) -> int:
    old = await ctx.session.get(PolityProfileRow, fallen.id)
    if old is not None:
        profile.emblem, profile.government = dict(old.emblem or {}), old.government
    laws = (
        select(LawProfileRow)
        .join(LawJurisdictionRow, LawJurisdictionRow.law_entity_id == LawProfileRow.law_entity_id)
        .where(LawJurisdictionRow.node_entity_id == fallen.id)
    )
    taken = 0
    for law in list(await ctx.session.scalars(laws.order_by(LawProfileRow.law_entity_id)))[: ctx.rules.restoration.old_law_cap]:
        realm = await ctx.session.get(EntityRow, profile.polity_entity_id)
        if realm is not None:
            await enact(ctx, realm, law.kind, dict(law.params or {}))
            taken += 1
    bases = bases_of(row)
    loss = ctx.rules.restoration.old_law_stability_loss // (2 if RestorationBasis.LAW in bases else 1)
    if "stability" not in (profile.locked or []):
        profile.stability = clamp_int(profile.stability - taken * loss, STABILITY_FLOOR, PERCENT)
    if "legitimacy" not in (profile.locked or []):
        profile.legitimacy = clamp_int(profile.legitimacy + sum(BASIS_LEGITIMACY[basis] for basis in bases), 0, PERCENT)
    return taken


async def carry_rights(ctx: TickContext, fallen_id: int, restored_id: int, ruler: int | None) -> None:
    for claim in await ctx.session.scalars(
        select(ClaimRow).where(ClaimRow.polity_entity_id == fallen_id, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.id)
    ):
        if "polity_entity_id" not in (claim.locked or []):
            claim.polity_entity_id = restored_id
    for title in await ctx.session.scalars(
        select(TitleProfileRow).where(TitleProfileRow.polity_entity_id == fallen_id).order_by(TitleProfileRow.title_entity_id)
    ):
        if "polity_entity_id" not in (title.locked or []):
            title.polity_entity_id = restored_id
            title.holder_node_id = ruler if ruler is not None else title.holder_node_id


async def restore(ctx: TickContext, row: RestorationRow, tally: RestorationTally) -> EntityRow | None:
    fallen = await ctx.session.get(EntityRow, row.fallen_polity_id)
    towns = [town for town in [await living_entity(ctx.session, node) for node in row.territories or []] if town is not None and not held(town.id)]
    if fallen is None or not towns:
        await fail(ctx, row, RestorationFailure.NO_LANDS, tally)
        return None
    holders = sorted((await realms_holding(ctx, [town.id for town in towns])).items())
    for realm_id, members in holders:
        if not held(realm_id):
            await split(ctx, realm_id, members)
    book = await RealmBook.load(ctx.session)
    realm = await found_polity(ctx, book, towns[0], told=False)
    for town in towns[1:]:
        await remove_flag(ctx.session, town.id, EntityFlag.INDEPENDENT)
        await connect(ctx.session, towns[0].id, town.id, BondKind.RULES, ctx.epoch, description=f"taken back for {fallen.name}")
    realm.entity.name = fallen.name
    claimant = await living_entity(ctx.session, row.claimant_node_id) if row.claimant_node_id is not None else None
    ruler = claimant.id if claimant is not None and claimant.entity_type is EntityType.MORTAL else None
    if ruler is not None:
        set_ruler(ctx, realm, ruler, f"restored to the throne of {fallen.name}")
    laws = await take_back(ctx, row, fallen, realm.profile)
    await carry_rights(ctx, fallen.id, realm.entity.id, ruler)
    await connect(ctx.session, realm.entity.id, fallen.id, BondKind.DESCENDS_FROM, ctx.epoch, description="restored the old realm")
    await refresh_realms(ctx, book)
    row.stage, row.restored_polity_id, row.ended_epoch = RestorationStage.RESTORED, realm.entity.id, ctx.epoch
    tally.restored += 1
    for realm_id, _members in holders:
        if not held(realm_id) and ctx.rng(f"restoration.reckoning.{row.id}.{realm_id}").chance(ctx.rules.reckoning.open_chance_pct):
            measures = await choose(ctx, ruler, realm.profile, await victims_pressure(ctx, realm.entity.id))
            await open_reckoning(ctx, realm.entity, realm_id, measures, by=ruler, fallen_epoch=ctx.epoch, tally=ReckoningTally())
    await record(
        ctx,
        "polity.restored",
        roles={IncidentRole.PREDECESSOR: fallen.id, IncidentRole.SUCCESSOR: realm.entity.id, IncidentRole.ACTOR: row.claimant_node_id},
        facts={"lands": len(towns), "laws": laws},
    )
    return realm.entity


async def advance(ctx: TickContext, row: RestorationRow, tally: RestorationTally) -> RestorationStage:
    table = ctx.rules.restoration
    if row.stage is RestorationStage.MEMORY:
        if await grievance(ctx, list(row.territories or [])) >= table.movement_grievance_threshold:
            row.stage = RestorationStage.MOVEMENT
    elif row.stage is RestorationStage.MOVEMENT:
        if row.memory >= table.rising_memory and ctx.rng(f"restoration.rise.{row.id}.{ctx.epoch}").chance(table.rising_chance_pct):
            row.stage = RestorationStage.RISING
            tally.rising += 1
            await record(
                ctx,
                "polity.restoration_rising",
                roles={IncidentRole.SUBJECT: row.fallen_polity_id, IncidentRole.ACTOR: row.claimant_node_id},
                facts={"memory": row.memory},
            )
    elif row.stage is RestorationStage.RISING:
        if await resisted(ctx, row):
            await fail(ctx, row, RestorationFailure.PUT_DOWN, tally)
        else:
            await restore(ctx, row, tally)
    return row.stage


async def tend_restorations(ctx: TickContext) -> RestorationTally:
    tally = RestorationTally()
    await press_claims(ctx, tally)
    await memories(ctx, tally)
    for row in list(await ctx.session.scalars(select(RestorationRow).where(RestorationRow.stage.in_(sorted(OPEN_STAGES))).order_by(RestorationRow.id))):
        if held(row.fallen_polity_id) or "stage" in (row.locked or []):
            continue
        if row.stage is not RestorationStage.RISING and "memory" not in (row.locked or []):
            decay = ctx.rules.restoration.memory_decay_per_epoch // (2 if RestorationBasis.MEMORY in bases_of(row) else 1)
            row.memory = clamp_int(row.memory - decay, 0, PERCENT)
            if not row.memory:
                tally.faded += 1
                await fail(ctx, row, RestorationFailure.MEMORY_FADED, tally)
                continue
        await advance(ctx, row, tally)
    return tally


async def memories(ctx: TickContext, tally: RestorationTally) -> None:
    table = ctx.rules.restoration
    fallen = select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status != EntityStatus.CANON).order_by(EntityRow.id)
    for polity in list(await ctx.session.scalars(fallen)):
        if held(polity.id) or await open_for(ctx, polity.id) is not None or await remembered(ctx, polity.id) == 0:
            continue
        lands = await old_lands(ctx, polity.id)
        if lands and await grievance(ctx, lands) >= table.movement_grievance_threshold:
            await raise_movement(ctx, polity, claimant=None, bases=[RestorationBasis.MEMORY], territories=lands, tally=tally)


async def press_claims(ctx: TickContext, tally: RestorationTally) -> None:
    made = 0
    query = select(ClaimRow).where(ClaimRow.pressed.is_(True), ClaimRow.ended_epoch.is_(None), ClaimRow.title_entity_id.is_not(None)).order_by(ClaimRow.id)
    for claim in list(await ctx.session.scalars(query)):
        fallen = await ctx.session.get(EntityRow, claim.polity_entity_id)
        if fallen is None or fallen.status is EntityStatus.CANON or held(fallen.id) or not await first_sight(ctx.session, CLAIM_FAMILY, claim.id):
            continue
        begun = select(RestorationRow.id).where(RestorationRow.fallen_polity_id == fallen.id, RestorationRow.claimant_node_id == claim.claimant_entity_id)
        if await open_for(ctx, fallen.id) is not None or await ctx.session.scalar(begun.limit(1)) is not None:
            continue
        await raise_movement(ctx, fallen, claimant=claim.claimant_entity_id, bases=[RestorationBasis.BLOODLINE], territories=[], tally=tally)
        made += 1
    await close_legacy(ctx.session, LEGACY_FIXUP, {"restorations": made})
    await ctx.session.flush()
