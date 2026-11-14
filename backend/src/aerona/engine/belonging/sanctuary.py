from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import SanctuaryLawRow, SanctuaryRow
from aerona.db.tables.collective import SocialNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import DefectionRow, OutlawRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind, SanctuaryState
from aerona.domain.enums.collective import NormSituation
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.mind import EthicalStance, MemoryKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.belonging.refuge import OPEN_STATES, refuge_of
from aerona.engine.body.afflictions import desecration_curse
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import ruler_id
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.purse import give_coin, receive_coin, take_coin
from aerona.engine.law.prisons import imprison
from aerona.engine.mind.hooks import desecrated
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.services.community_relations import change_relation

HOLY = (StructureKind.TEMPLE, StructureKind.SHRINE, StructureKind.MONASTERY)
WELCOMING = frozenset({EthicalStance.REQUIRED, EthicalStance.ADMIRABLE})


@dataclass
class SanctuaryTally:
    sought: int = 0
    asylums: int = 0
    paid: int = 0
    bargained: int = 0
    besieged: int = 0
    violated: int = 0
    surrendered: int = 0


@dataclass(frozen=True)
class Fugitive:
    mortal: EntityRow
    kind: FugitiveKind
    pursuer: int | None


async def restricted(ctx: TickContext, polity: int | None) -> bool:
    law = await ctx.session.get(SanctuaryLawRow, polity) if polity is not None else None
    return law is not None and law.restricted


async def temple_in(ctx: TickContext, town: int) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.location_id == town, EntityRow.status == EntityStatus.CANON, StructureProfileRow.kind.in_(list(HOLY)))
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def welcoming(ctx: TickContext, town: EntityRow) -> bool:
    folk = await people_of(ctx.session, town)
    holders = [town.id, *([folk.id] if folk is not None else [])]
    stances = await ctx.session.scalars(
        select(SocialNormRow.stance).where(SocialNormRow.holder_entity_id.in_(holders), SocialNormRow.situation == NormSituation.HOSPITALITY)
    )
    return any(stance in WELCOMING for stance in stances)


async def host_for(ctx: TickContext, fugitive: Fugitive) -> tuple[EntityRow, SanctuaryKind] | None:
    town = await ctx.session.get(EntityRow, fugitive.mortal.location_id) if fugitive.mortal.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        return None
    temple = await temple_in(ctx, town.id)
    if temple is not None and not await restricted(ctx, await realm_of(ctx.session, town.id)) and not held(temple.id):
        return temple, SanctuaryKind.TEMPLE
    if await welcoming(ctx, town) and not held(town.id):
        return town, SanctuaryKind.HOSPITALITY
    return None


async def fugitives(ctx: TickContext) -> list[Fugitive]:
    found: dict[int, Fugitive] = {}
    for row in await ctx.session.scalars(select(OutlawRow).order_by(OutlawRow.mortal_entity_id)):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is not None:
            found.setdefault(mortal.id, Fugitive(mortal, FugitiveKind.OUTLAW, row.polity_entity_id))
    for case in await ctx.session.scalars(
        select(CrimeCaseRow).where(CrimeCaseRow.stage != CaseStage.CLOSED, CrimeCaseRow.accused_entity_id.is_not(None)).order_by(CrimeCaseRow.id)
    ):
        mortal = await living_entity(ctx.session, case.accused_entity_id)
        if mortal is not None:
            found.setdefault(mortal.id, Fugitive(mortal, FugitiveKind.ACCUSED, case.polity_entity_id))
    return [item for _, item in sorted(found.items())]


async def shelter(ctx: TickContext, fugitive: Fugitive, host: EntityRow, kind: SanctuaryKind) -> SanctuaryRow:
    row = SanctuaryRow(
        fugitive_entity_id=fugitive.mortal.id,
        host_entity_id=host.id,
        kind=kind,
        fugitive_kind=fugitive.kind,
        pursuer_entity_id=fugitive.pursuer,
        fee=ctx.rules.sanctuary.fee,
        granted_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def seek(ctx: TickContext, tally: SanctuaryTally) -> None:
    for fugitive in await fugitives(ctx):
        if held(fugitive.mortal.id) or await refuge_of(ctx.session, fugitive.mortal.id) is not None:
            continue
        if not ctx.rng(seed_of("sanctuary.seek", fugitive.mortal.id, ctx.epoch)).chance(ctx.rules.sanctuary.seek_chance):
            continue
        found = await host_for(ctx, fugitive)
        if found is None:
            continue
        await shelter(ctx, fugitive, *found)
        tally.sought += 1
        await note(ctx, f"{fugitive.mortal.name} claimed sanctuary in {found[0].name}.", key="sanctuary.claimed", ids=[fugitive.mortal.id, found[0].id])


async def asylums(ctx: TickContext, tally: SanctuaryTally) -> None:
    for row in await ctx.session.scalars(select(DefectionRow).where(DefectionRow.to_entity_id.is_not(None)).order_by(DefectionRow.id)):
        defector = await living_entity(ctx.session, row.defector_entity_id)
        host = await living_entity(ctx.session, row.to_entity_id)
        if defector is None or host is None or held(defector.id, host.id) or await refuge_of(ctx.session, defector.id) is not None:
            continue
        known = await ctx.session.scalar(select(SanctuaryRow.id).where(SanctuaryRow.fugitive_entity_id == defector.id, SanctuaryRow.host_entity_id == host.id))
        if known is not None:
            continue
        await shelter(ctx, Fugitive(defector, FugitiveKind.DEFECTOR, row.from_entity_id), host, SanctuaryKind.ASYLUM)
        if row.from_entity_id is not None and not held(row.from_entity_id):
            await change_relation(
                ctx, row.from_entity_id, host.id, -ctx.rules.sanctuary.asylum_relation, MemoryKind.ILL_WILL, note=f"gave asylum to {defector.name}"
            )
        tally.asylums += 1


async def hand_over(ctx: TickContext, row: SanctuaryRow, state: SanctuaryState) -> None:
    row.state = state
    fugitive = await living_entity(ctx.session, row.fugitive_entity_id)
    if fugitive is not None:
        await imprison(ctx, fugitive)


async def violate(ctx: TickContext, row: SanctuaryRow, host: EntityRow, pursuer: EntityRow, tally: SanctuaryTally) -> None:
    await hand_over(ctx, row, SanctuaryState.VIOLATED)
    ruler = await ruler_id(ctx, pursuer.id) if pursuer.entity_type is EntityType.POLITY else pursuer.id
    if ruler is not None and not held(ruler):
        await add_infamy(ctx.session, ruler, ctx.rules.sanctuary.infamy, ctx.epoch, rules=ctx.rules)
        if row.kind is SanctuaryKind.TEMPLE:
            await desecration_curse(ctx, host, ruler)
    await desecrated(ctx, host.id, pursuer.id, note="broke the sanctuary")
    tally.violated += 1
    await note(ctx, f"{pursuer.name} broke the sanctuary of {host.name}.", key="sanctuary.violated", ids=[pursuer.id, host.id])


async def pay_host(ctx: TickContext, host: EntityRow, amount: int) -> None:
    keeper = await ctx.session.scalar(select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == host.id).limit(1))
    doctrine = await ctx.session.get(CultDoctrineRow, keeper) if keeper is not None else None
    if doctrine is None or "treasury" in doctrine.locked:
        await give_coin(ctx.session, ctx.rules, host, amount)
        return
    doctrine.treasury += amount
    cult = await ctx.session.get(EntityRow, keeper)
    if cult is not None and not held(cult.id):
        shift_stat(cult, "influence", ctx.rules.sanctuary.cult_influence, default=0)


async def split_fee(ctx: TickContext, row: SanctuaryRow, host: EntityRow) -> None:
    realm = await realm_of(ctx.session, host.location_id or host.id)
    law = await ctx.session.get(SanctuaryLawRow, realm) if realm is not None else None
    levy = round_half_up(row.fee * law.fee_pct / PERCENT) if law is not None else 0
    polity = await ctx.session.get(EntityRow, realm) if levy and realm is not None else None
    if polity is not None:
        await receive_coin(ctx.session, ctx.rules, polity, levy)
    await pay_host(ctx, host, row.fee - (levy if polity is not None else 0))


async def pursue(ctx: TickContext, row: SanctuaryRow, tally: SanctuaryTally) -> None:
    table = ctx.rules.sanctuary
    host = await living_entity(ctx.session, row.host_entity_id)
    fugitive = await living_entity(ctx.session, row.fugitive_entity_id)
    if host is None or fugitive is None:
        row.state = SanctuaryState.ENDED
        return
    if row.fee and await take_coin(ctx.session, ctx.rules, fugitive, row.fee):
        await split_fee(ctx, row, host)
        tally.paid += 1
    pursuer = await living_entity(ctx.session, row.pursuer_entity_id) if row.pursuer_entity_id is not None else None
    if pursuer is None or held(pursuer.id) or "state" in row.locked:
        return
    if row.state is SanctuaryState.NEGOTIATING:
        if await take_coin(ctx.session, ctx.rules, pursuer, table.ransom):
            await pay_host(ctx, host, table.ransom)
            await hand_over(ctx, row, SanctuaryState.ENDED)
            tally.bargained += 1
        return
    if row.state is SanctuaryState.BESIEGED:
        row.siege_epochs += 1
        if row.siege_epochs >= table.surrender_epochs:
            await hand_over(ctx, row, SanctuaryState.ENDED)
            tally.surrendered += 1
        return
    roll = ctx.rng(seed_of("sanctuary.pursue", row.id, ctx.epoch))
    if roll.chance(table.violate_chance):
        await violate(ctx, row, host, pursuer, tally)
    elif roll.chance(table.negotiate_chance):
        row.state = SanctuaryState.NEGOTIATING
    elif roll.chance(table.besiege_chance):
        row.state = SanctuaryState.BESIEGED
        tally.besieged += 1


async def keep_sanctuaries(ctx: TickContext, tally: SanctuaryTally) -> None:
    await seek(ctx, tally)
    await asylums(ctx, tally)
    for row in list(await ctx.session.scalars(select(SanctuaryRow).where(SanctuaryRow.state.in_(OPEN_STATES)).order_by(SanctuaryRow.id))):
        if held(row.fugitive_entity_id, row.host_entity_id):
            continue
        await pursue(ctx, row, tally)
    await ctx.session.flush()
