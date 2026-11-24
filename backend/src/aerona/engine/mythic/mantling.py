from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.mythic import SKILL_DOMAINS
from aerona.constants.units import PERCENT
from aerona.db.repositories.notifications import NotificationDraft, NotificationRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import DivineStandingRow, GodGoalRow
from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import CosmicOfficeRow, MantlingRow
from aerona.db.tables.renown import ReputationRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory
from aerona.domain.enums.divine import GoalState, GodGoalKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mythic import MantlingState, OfficeChoice
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.transform import TransformKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, living_gods
from aerona.engine.faith.book import patron_node
from aerona.engine.gods.deification import deify
from aerona.engine.mythic.heroquests import renown_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.recording.record import record


@dataclass
class MantleTally:
    walking: int = 0
    ascended: int = 0
    blocked: int = 0


@dataclass(frozen=True)
class Replacement:
    old: SonRow
    domains: tuple[Domain, Domain]
    claims: tuple[tuple[int, int], ...]
    worshippers: tuple[int, ...]


async def deeds_in(ctx: TickContext, mortal_id: int, domains: set[Domain]) -> int:
    rows = await ctx.session.execute(
        select(ReputationRow.skill, ReputationRow.value).where(
            ReputationRow.subject_node_id == mortal_id,
            ReputationRow.skill.is_not(None),
            ReputationRow.heard_epoch >= ctx.epoch - ctx.rules.mantling.deed_window,
        )
    )
    value = ctx.rules.mantling.deed_value
    return sum(int(amount) // value for skill, amount in rows if skill is not None and SKILL_DOMAINS[skill] & domains)


async def worship_of(ctx: TickContext, mortal_id: int) -> int:
    count = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.target_node_id == mortal_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    return int(count or 0)


async def path_of(ctx: TickContext, mortal: EntityRow) -> tuple[God, int] | None:
    patron = await patron_node(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    best: tuple[God, int] | None = None
    for god in await living_gods(ctx.session):
        deeds = await deeds_in(ctx, mortal.id, set(domains_of(god)))
        if deeds and (best is None or (deeds, god.id == patron) > (best[1], best[0].id == patron)):
            best = (god, deeds)
    return best


def progress_of(ctx: TickContext, mortal: EntityRow, deeds: int, worship: int, renown: int) -> int:
    table = ctx.rules.mantling
    parts = (
        min(1.0, deeds / max(1, table.deeds_min)),
        min(1.0, worship / max(1, table.worship_min)),
        min(1.0, renown / max(1, table.renown_min)),
        min(1.0, mortal.power_level / max(1, table.power_min)),
    )
    return clamp_int(sum(parts) / len(parts) * PERCENT, 0, PERCENT)


async def goal_set(ctx: TickContext, kind: GodGoalKind, mortal_id: int) -> list[int]:
    rows = await ctx.session.scalars(
        select(GodGoalRow.god_node_id).where(GodGoalRow.kind == kind, GodGoalRow.target_node_id == mortal_id, GodGoalRow.state == GoalState.ACTIVE)
    )
    return list(rows)


async def tell_player(ctx: TickContext, mortal: EntityRow, row: MantlingRow) -> None:
    if row.notified:
        return
    row.notified = True
    await NotificationRepository(ctx.session).add(
        NotificationDraft(
            category=NotificationCategory.ASCENSION,
            title=f"{mortal.name} walks a god's path",
            body="This mortal now meets the conditions to ascend; block, pin or let Fate decide.",
            epoch=ctx.epoch,
            target_node_id=mortal.id,
        )
    )


async def ascend(ctx: TickContext, mortal: EntityRow, row: MantlingRow) -> SonRow | None:
    creator = await ctx.session.scalar(select(CreatorRow).limit(1))
    if creator is None:
        return None
    deification = await deify(ctx, creator, mortal, TransformKind.MANTLING)
    await carry_cults(ctx, mortal.id, deification.son.id)
    row.state = MantlingState.ASCENDED
    await record(ctx, "mythic.mantled", roles={IncidentRole.SUBJECT: mortal.id}, kind=ChronicleKind.ASCENSION)
    return deification.son


async def contested(ctx: TickContext, mortal: EntityRow, row: MantlingRow) -> bool:
    if row.god_node_id is None:
        return False
    rival = await ctx.session.scalar(
        select(MantlingRow)
        .where(MantlingRow.god_node_id == row.god_node_id, MantlingRow.mortal_entity_id != mortal.id, MantlingRow.progress >= PERCENT)
        .order_by(MantlingRow.mortal_entity_id)
        .limit(1)
    )
    if rival is None:
        return False
    for claim in (row, rival):
        if "state" not in claim.locked:
            claim.state = MantlingState.CONTESTED
    roles = {IncidentRole.ACTOR: mortal.id, IncidentRole.OPPONENT: rival.mortal_entity_id, IncidentRole.TARGET: row.god_node_id}
    await record(ctx, "mantle.contested", roles=roles)
    return True


async def weigh(ctx: TickContext, mortal: EntityRow, tally: MantleTally) -> None:
    table = ctx.rules.mantling
    path = await path_of(ctx, mortal)
    if path is None:
        return
    god, deeds = path
    row = await ctx.session.get(MantlingRow, mortal.id)
    if row is None:
        row = MantlingRow(
            mortal_entity_id=mortal.id, god_node_id=god.id, state=MantlingState.WALKING, blocked=False, notified=False, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    if row.state is not MantlingState.WALKING:
        return
    if deeds >= table.deeds_min:
        await gather_cult(ctx, mortal)
    worship, renown = await worship_of(ctx, mortal.id), await renown_of(ctx, mortal.id)
    for key, value in (("god_node_id", god.id), ("deeds", deeds), ("worship", worship), ("progress", progress_of(ctx, mortal, deeds, worship, renown))):
        if key not in row.locked:
            setattr(row, key, value)
    tally.walking += 1
    if row.progress < PERCENT:
        return
    await tell_player(ctx, mortal, row)
    rng = ctx.rng(f"mantling.{mortal.id}.{ctx.epoch}")
    if (row.god_node_id is not None and await goal_set(ctx, GodGoalKind.PREVENT_MANTLING, mortal.id)) and rng.chance(table.oppose_pct):
        row.state = MantlingState.BLOCKED
        tally.blocked += 1
        return
    if await contested(ctx, mortal, row):
        return
    sponsors = await goal_set(ctx, GodGoalKind.SPONSOR_MANTLING, mortal.id)
    if row.blocked or not rng.chance(table.fate_pct + (table.sponsor_pct if sponsors else 0)):
        return
    if await ascend(ctx, mortal, row) is not None:
        tally.ascended += 1


async def carry_cults(ctx: TickContext, mortal_id: int, son_id: int) -> None:
    cults = await ctx.session.scalars(
        select(BondRow).where(BondRow.target_node_id == mortal_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    )
    for bond in list(cults):
        bond.state = BondState.PAST
        await connect(ctx.session, bond.source_node_id, son_id, BondKind.WORSHIPS, ctx.epoch, description="followed the mortal it venerated into godhood")


async def gather_cult(ctx: TickContext, mortal: EntityRow) -> int | None:
    table = ctx.rules.mantling
    if await worship_of(ctx, mortal.id) >= table.worship_min or not ctx.rng(f"mantling.cult.{mortal.id}.{ctx.epoch}").chance(table.cult_pct):
        return None
    admirers = await ctx.session.scalars(
        select(ReputationRow.community_node_id)
        .where(ReputationRow.subject_node_id == mortal.id, ReputationRow.value >= table.cult_reputation)
        .order_by(ReputationRow.value.desc(), ReputationRow.community_node_id)
    )
    for community_id in dict.fromkeys(admirers):
        worships = await ctx.session.scalar(
            select(BondRow.id).where(BondRow.source_node_id == community_id, BondRow.target_node_id == mortal.id, BondRow.kind == BondKind.WORSHIPS)
        )
        if worships is not None or held(community_id) or await patron_node(ctx.session, community_id) is None:
            continue
        await connect(ctx.session, community_id, mortal.id, BondKind.WORSHIPS, ctx.epoch, description="venerates one who walks a god's path")
        await record(ctx, "mythic.hero_cult", roles={IncidentRole.SUBJECT: [mortal.id, community_id]}, kind=ChronicleKind.WORLD)
        return community_id
    return None


async def mantle_world(ctx: TickContext, tally: MantleTally) -> None:
    table = ctx.rules.mantling
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if held(mortal.id) or await renown_of(ctx, mortal.id) < table.renown_min // 2:
            continue
        await weigh(ctx, mortal, tally)
    await ctx.session.flush()


async def weak(ctx: TickContext, son: SonRow) -> bool:
    table = ctx.rules.mantling
    total = int(
        await ctx.session.scalar(select(func.count()).select_from(BondRow).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)) or 0
    )
    mine = int(
        await ctx.session.scalar(
            select(func.count())
            .select_from(BondRow)
            .where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        )
        or 0
    )
    awe = float(await ctx.session.scalar(select(func.avg(DivineStandingRow.awe)).where(DivineStandingRow.god_node_id == son.id)) or 0)
    share = mine * PERCENT / total if total else 0
    return son.existence < table.weak_existence_max and share < table.weak_faith_share_max and awe < table.weak_standing_max


async def overwhelming(ctx: TickContext, mortal: EntityRow, son: SonRow) -> bool:
    table = ctx.rules.mantling
    row = await ctx.session.get(MantlingRow, mortal.id)
    if row is None or row.god_node_id != son.id or row.blocked:
        return False
    renown, worship = await renown_of(ctx, mortal.id), await worship_of(ctx, mortal.id)
    might = (son.strength + son.will) / 2 + son.level
    return (
        renown >= table.renown_min
        and worship >= table.worship_min
        and mortal.power_level >= table.power_min
        and row.deeds >= table.deeds_min
        and mortal.power_level * PERCENT // 10 >= might * (1 + table.power_margin_pct / PERCENT)
    )


async def replacement_for(ctx: TickContext, mortal: EntityRow, son: SonRow) -> Replacement | None:
    if son.status is SonStatus.DEAD or held(mortal.id, son.id) or not await weak(ctx, son) or not await overwhelming(ctx, mortal, son):
        return None
    claims = tuple((row.region_entity_id, row.strength) for row in await ctx.session.scalars(select(DominionRow).where(DominionRow.god_node_id == son.id)))
    worshippers = tuple(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        )
    )
    return Replacement(son, (son.domain_primary, son.domain_secondary), claims, worshippers)


async def replace(ctx: TickContext, mortal: EntityRow, plan: Replacement) -> SonRow | None:
    table = ctx.rules.mantling
    if mortal.status is not EntityStatus.CANON or not ctx.rng(f"mantling.replace.{mortal.id}").chance(table.fate_pct):
        return None
    row = await ctx.session.get(MantlingRow, mortal.id)
    creator = await ctx.session.scalar(select(CreatorRow).limit(1))
    if row is None or creator is None:
        return None
    son = (await deify(ctx, creator, mortal, TransformKind.MANTLING)).son
    await carry_cults(ctx, mortal.id, son.id)
    son.domain_primary, son.domain_secondary = plan.domains
    for region, strength in plan.claims:
        ctx.session.add(DominionRow(god_node_id=son.id, region_entity_id=region, strength=strength, epoch=ctx.epoch, locked=[]))
    kept = round_half_up(len(plan.worshippers) * table.inherit_worship_pct / PERCENT)
    for follower in plan.worshippers[:kept]:
        await connect(ctx.session, follower, son.id, BondKind.WORSHIPS, ctx.epoch, description="followed the one who took its god's place")
    for office in await ctx.session.scalars(select(CosmicOfficeRow).where(CosmicOfficeRow.holder_node_id == plan.old.id)):
        office.holder_node_id, office.chosen_by, office.since_epoch = son.id, OfficeChoice.MANTLING, ctx.epoch
    row.state = MantlingState.REPLACED
    await record(ctx, "mythic.replaced", roles={IncidentRole.SUBJECT: [mortal.id, plan.old.id]}, kind=ChronicleKind.ASCENSION, son_id=son.id)
    return son
