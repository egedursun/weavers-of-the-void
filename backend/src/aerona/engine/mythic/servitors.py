from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.divine import SERVITOR_ORIGINS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import an, spoken
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, SpiritProfileRow
from aerona.db.tables.lore import FolkBeliefRow
from aerona.db.tables.mythic import ServitorRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import AfterlifeState, SpiritAlignment, StratumActivity, StratumValence
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mythic import ServitorOrigin, ServitorRole
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, god_of, living_gods
from aerona.engine.divine.wounds import betrayed
from aerona.engine.faith.book import patron_node
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

SERVITOR_POWER = 3


UNREWARDED = frozenset({StratumValence.PUNISHMENT})


@dataclass
class ServitorTally:
    raised: int = 0
    fallen: int = 0
    judged: int = 0
    served: int = 0


async def make_servitor(
    ctx: TickContext,
    god_id: int,
    *,
    name: str,
    role: ServitorRole,
    post_id: int | None,
    world_id: int | None,
    origin: ServitorOrigin = ServitorOrigin.MADE,
) -> ServitorRow:
    spirit = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.SPIRIT,
            stats=SpiritStats(strength=PERCENT // 2),
            body=f"{an(spoken(role), capital=True)} in the service of its god.",
            power=SERVITOR_POWER,
            world_id=world_id,
            location_id=post_id,
            pending=False,
        ),
    )
    son = await ctx.session.get(SonRow, god_id)
    ctx.session.add(
        SpiritProfileRow(
            spirit_entity_id=spirit.id,
            alignment=SpiritAlignment.GUARDIAN,
            state=AfterlifeState.WANDERING,
            patron_son_id=son.id if son is not None else None,
            locked=[],
        )
    )
    return await enrol(ctx, spirit.id, god_id, role=role, post_id=post_id, origin=origin)


async def enrol(
    ctx: TickContext, spirit_id: int, god_id: int, *, role: ServitorRole, post_id: int | None, origin: ServitorOrigin, former_god_id: int | None = None
) -> ServitorRow:
    row = await ctx.session.get(ServitorRow, spirit_id)
    if row is None:
        row = ServitorRow(spirit_entity_id=spirit_id, god_node_id=god_id, locked=[])
        ctx.session.add(row)
    spec = SERVITOR_ORIGINS[origin]
    row.god_node_id, row.role, row.post_entity_id, row.origin = god_id, role, post_id, origin
    row.former_god_node_id = former_god_id if spec.names_former_god else None
    row.loyalty = spec.loyalty(ctx.rules) if spec.loyalty is not None else ctx.rules.servitors.fall_at + PERCENT // 2
    row.since_epoch = ctx.epoch
    await ctx.session.flush()
    await record(
        ctx,
        "servitor.joined",
        roles={IncidentRole.SUBJECT: spirit_id, IncidentRole.PATRON: god_id, IncidentRole.ORIGIN: row.former_god_node_id},
        facts={"origin": origin, "origin_label": spec.label},
        kind=ChronicleKind.WORLD,
    )
    return row


async def bind_summoned(ctx: TickContext, spirit_id: int, god_id: int | None) -> ServitorRow | None:
    if god_id is None:
        return None
    return await enrol(ctx, spirit_id, god_id, role=ServitorRole.MESSENGER, post_id=None, origin=ServitorOrigin.SUMMONED)


async def standing_of(ctx: TickContext, god_id: int) -> int:
    mean = await ctx.session.scalar(select(func.avg(DivineStandingRow.awe)).where(DivineStandingRow.god_node_id == god_id))
    return round_half_up(float(mean or 0))


async def new_master(ctx: TickContext, god: God | None, stream: str) -> int | None:
    if god is not None:
        mine = set(domains_of(god))
        rivals = [other.id for other in await living_gods(ctx.session) if other.id != god.id and mine & set(domains_of(other))]
        if rivals:
            return int(ctx.rng(stream).pick(sorted(rivals)))
    outer = await canon(ctx.session, [EntityType.OUTER_BEING])
    return outer[0].id if outer else None


async def fall(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    chance = table.fall_pct * (table.defected_fall_pct / PERCENT if row.origin is ServitorOrigin.DEFECTED else 1)
    if row.loyalty >= table.fall_at or "god_node_id" in row.locked or not ctx.rng(f"servitor.fall.{row.spirit_entity_id}.{ctx.epoch}").chance(chance):
        return
    master = await new_master(ctx, await god_of(ctx.session, row.god_node_id), f"servitor.master.{row.spirit_entity_id}")
    if master is None:
        return
    old = row.god_node_id
    row.god_node_id, row.fallen_to_node_id, row.loyalty = master, master, table.defected_loyalty
    if "origin" not in row.locked:
        row.origin, row.former_god_node_id = ServitorOrigin.DEFECTED, old
    await betrayed(ctx, old, row.spirit_entity_id)
    profile = await ctx.session.get(SpiritProfileRow, row.spirit_entity_id)
    if profile is not None and "alignment" not in profile.locked:
        profile.alignment = SpiritAlignment.VENGEFUL
    tally.fallen += 1
    await record(ctx, "mythic.servitor_fell", roles={IncidentRole.SUBJECT: [row.spirit_entity_id, old, master]}, kind=ChronicleKind.WORLD)


Duty = Callable[[TickContext, ServitorRow, ServitorTally], Awaitable[None]]


DUTIES: Handlers[ServitorRole, Duty] = Handlers(ServitorRole)


@DUTIES.on(ServitorRole.JUDGE)
async def judge(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    son = await ctx.session.get(SonRow, row.god_node_id)
    if son is None:
        return
    for spirit in await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.patron_son_id == son.id)):
        if not held(spirit.spirit_entity_id) and "veneration" not in spirit.locked:
            spirit.veneration = clamp_int(spirit.veneration + ctx.rules.servitors.judge_veneration, 0, PERCENT)
            tally.judged += 1


async def standings(ctx: TickContext, god_id: int) -> list[DivineStandingRow]:
    rows = await ctx.session.scalars(select(DivineStandingRow).where(DivineStandingRow.god_node_id == god_id).order_by(DivineStandingRow.community_entity_id))
    return [row for row in rows if not held(row.community_entity_id)]


@DUTIES.on(ServitorRole.MESSENGER)
@DUTIES.on(ServitorRole.GUARD)
@DUTIES.on(ServitorRole.HOST)
@DUTIES.on(ServitorRole.SPY)
async def stand_by(_ctx: TickContext, _row: ServitorRow, _tally: ServitorTally) -> None:
    return None


@DUTIES.on(ServitorRole.AGENT)
async def act_as_agent(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    post = await ctx.session.get(EntityRow, row.post_entity_id) if row.post_entity_id is not None else None
    if post is not None and post.status is EntityStatus.CANON and not held(post.id):
        shift_stat(post, "prosperity", ctx.rules.servitors.agent_prosperity, 0, high=PERCENT)
        tally.served += 1


@DUTIES.on(ServitorRole.AVENGER)
async def avenge(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    for standing in await standings(ctx, row.god_node_id):
        if standing.love < table.avenger_scorn and "fear" not in standing.locked:
            standing.fear = clamp_int(standing.fear + table.avenger_fear, 0, PERCENT)
            tally.served += 1


@DUTIES.on(ServitorRole.GUIDE_OF_SOULS)
async def guide_souls(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    son = await ctx.session.get(SonRow, row.god_node_id)
    if son is None:
        return
    stratum = await ctx.session.scalar(
        select(AfterlifeStratumRow).where(AfterlifeStratumRow.son_id == son.id, AfterlifeStratumRow.closed.is_(False)).order_by(AfterlifeStratumRow.id).limit(1)
    )
    if stratum is None:
        return
    for spirit in await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.patron_son_id == son.id, SpiritProfileRow.stratum_id.is_(None))):
        if not held(spirit.spirit_entity_id) and "stratum_id" not in spirit.locked:
            spirit.stratum_id = stratum.id
            stratum.population += 1
            tally.served += 1


@DUTIES.on(ServitorRole.WORSHIPPER)
async def worship(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    for standing in await standings(ctx, row.god_node_id):
        if standing.love >= ctx.rules.servitors.avenger_scorn and "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + ctx.rules.servitors.worshipper_awe, 0, PERCENT)
            tally.served += 1


@DUTIES.on(ServitorRole.WARDEN)
async def ward(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    town = await ctx.session.get(SettlementProfileRow, row.post_entity_id) if row.post_entity_id is not None else None
    if town is None or held(town.settlement_entity_id):
        return
    cut = ctx.rules.servitors.warden_order
    if "crime" not in town.locked:
        town.crime = clamp_int(town.crime - cut, 0, PERCENT)
    if "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest - cut, 0, PERCENT)
    tally.served += 1


@DUTIES.on(ServitorRole.SCRIBE)
async def keep_accounts(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    tellers = set(await ctx.session.scalars(select(FolkBeliefRow.people_entity_id).where(FolkBeliefRow.god_node_id == row.god_node_id)))
    for standing in await standings(ctx, row.god_node_id):
        community = await ctx.session.get(EntityRow, standing.community_entity_id)
        people = await people_of(ctx.session, community) if community is not None else None
        if people is not None and people.id in tellers and "love" not in standing.locked:
            standing.love = clamp_int(standing.love + ctx.rules.servitors.scribe_love, 0, PERCENT)
            tally.served += 1


@DUTIES.on(ServitorRole.HEALER)
async def tend_sick(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    town = await ctx.session.get(SettlementProfileRow, row.post_entity_id) if row.post_entity_id is not None else None
    if town is None or held(town.settlement_entity_id):
        return
    table = ctx.rules.servitors
    if "sanitation" not in town.locked:
        town.sanitation = clamp_int(town.sanitation + table.healer_health, 0, PERCENT)
    if "siege_disease" not in town.locked:
        town.siege_disease = clamp_int(town.siege_disease - table.healer_health, 0, PERCENT)
    tally.served += 1


@DUTIES.on(ServitorRole.TEACHER)
async def teach_town(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    place = await ctx.session.get(EntityRow, row.post_entity_id) if row.post_entity_id is not None else None
    people = await people_of(ctx.session, place) if place is not None else None
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is None or held(culture.people_entity_id) or "literacy" in culture.locked:
        return
    culture.literacy = clamp_int(culture.literacy + ctx.rules.servitors.teacher_learning, 0, PERCENT)
    tally.served += 1


DUTIES.seal()


async def raise_saints(ctx: TickContext, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    serving = set(await ctx.session.scalars(select(ServitorRow.spirit_entity_id)))
    saints = select(EntityRow.id).where(EntityRow.mortal_role == MortalRole.SAINT)
    for spirit in list(await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id.in_(saints)))):
        if spirit.spirit_entity_id in serving or held(spirit.spirit_entity_id) or spirit.origin_mortal_id is None:
            continue
        stratum = await ctx.session.get(AfterlifeStratumRow, spirit.stratum_id) if spirit.stratum_id is not None else None
        if stratum is not None and (stratum.valence in UNREWARDED or stratum.activity is StratumActivity.DISSOLUTION):
            continue
        mortal = await ctx.session.get(EntityRow, spirit.origin_mortal_id)
        home = await patron_node(ctx.session, mortal.location_id) if mortal is not None and mortal.location_id is not None else None
        god = (stratum.son_id if stratum is not None else None) or spirit.patron_son_id or home
        if god is None or not ctx.rng(f"servitor.raise.{spirit.spirit_entity_id}.{ctx.epoch}").chance(table.raise_pct):
            continue
        await enrol(ctx, spirit.spirit_entity_id, god, role=ServitorRole.JUDGE, post_id=None, origin=ServitorOrigin.RAISED)
        tally.raised += 1


async def raise_offspring(ctx: TickContext, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    serving = set(await ctx.session.scalars(select(ServitorRow.spirit_entity_id)))
    children = select(EntityRow.id).where(EntityRow.creator_son_id.is_not(None), EntityRow.entity_type == EntityType.MORTAL)
    for spirit in list(
        await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id.in_(children)).order_by(SpiritProfileRow.spirit_entity_id))
    ):
        if spirit.spirit_entity_id in serving or held(spirit.spirit_entity_id) or spirit.origin_mortal_id is None:
            continue
        child = await ctx.session.get(EntityRow, spirit.origin_mortal_id)
        parent = await ctx.session.get(SonRow, child.creator_son_id) if child is not None and child.creator_son_id is not None else None
        if parent is None or held(parent.id) or not ctx.rng(f"servitor.born.{spirit.spirit_entity_id}.{ctx.epoch}").chance(table.born_rise_pct):
            continue
        await enrol(ctx, spirit.spirit_entity_id, parent.id, role=ServitorRole.GUARD, post_id=None, origin=ServitorOrigin.BORN)
        tally.raised += 1


async def raise_heroes(ctx: TickContext, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    serving = set(await ctx.session.scalars(select(ServitorRow.spirit_entity_id)))
    heroes = select(EntityRow.id).where(EntityRow.mortal_role == MortalRole.HERO)
    rows = await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id.in_(heroes)).order_by(SpiritProfileRow.spirit_entity_id))
    for spirit in list(rows):
        if spirit.spirit_entity_id in serving or held(spirit.spirit_entity_id) or spirit.patron_son_id is None or held(spirit.patron_son_id):
            continue
        if not ctx.rng(f"servitor.ascend.{spirit.spirit_entity_id}.{ctx.epoch}").chance(table.raise_pct):
            continue
        await enrol(ctx, spirit.spirit_entity_id, spirit.patron_son_id, role=ServitorRole.MESSENGER, post_id=None, origin=ServitorOrigin.ASCENDED)
        tally.raised += 1


async def bargained_servant(ctx: TickContext, god_id: int) -> ServitorRow | None:
    serving = select(ServitorRow.spirit_entity_id)
    spirit = await ctx.session.scalar(
        select(SpiritProfileRow.spirit_entity_id)
        .where(SpiritProfileRow.state == AfterlifeState.WANDERING, SpiritProfileRow.spirit_entity_id.not_in(serving))
        .order_by(SpiritProfileRow.spirit_entity_id)
        .limit(1)
    )
    if spirit is None or held(spirit, god_id):
        return None
    return await enrol(ctx, spirit, god_id, role=ServitorRole.GUARD, post_id=None, origin=ServitorOrigin.BARGAINED)


async def tend_servitors(ctx: TickContext, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    await raise_saints(ctx, tally)
    await raise_heroes(ctx, tally)
    await raise_offspring(ctx, tally)
    for row in list(await ctx.session.scalars(select(ServitorRow).order_by(ServitorRow.spirit_entity_id))):
        spirit = await ctx.session.get(EntityRow, row.spirit_entity_id)
        if spirit is None or spirit.status is not EntityStatus.CANON or held(row.spirit_entity_id, row.god_node_id):
            continue
        if "loyalty" not in row.locked:
            aim = await standing_of(ctx, row.god_node_id)
            step = table.loyalty_drift if aim > row.loyalty else -table.loyalty_drift if aim < row.loyalty else 0
            row.loyalty = clamp_int(row.loyalty + step, 0, PERCENT)
        await DUTIES[row.role](ctx, row, tally)
        await fall(ctx, row, tally)
    await ctx.session.flush()


async def turned_back(ctx: TickContext, place_ids: list[int | None], stream: str) -> bool:
    wanted = [place for place in place_ids if place is not None]
    if not wanted:
        return False
    guard = await ctx.session.scalar(
        select(ServitorRow.spirit_entity_id).where(ServitorRow.role == ServitorRole.GUARD, ServitorRow.post_entity_id.in_(wanted)).limit(1)
    )
    return guard is not None and ctx.rng(stream).chance(ctx.rules.servitors.guard_pct)


async def host_of(session: AsyncSession, rules: Rules, god_id: int) -> int:
    count = await session.scalar(select(func.count()).select_from(ServitorRow).where(ServitorRow.god_node_id == god_id, ServitorRow.role == ServitorRole.HOST))
    return int(count or 0) * rules.servitors.host_strength


async def shake_host(ctx: TickContext, god_id: int) -> int:
    shaken = 0
    for row in await ctx.session.scalars(select(ServitorRow).where(ServitorRow.god_node_id == god_id, ServitorRow.role == ServitorRole.HOST)):
        if "loyalty" not in row.locked and not held(row.spirit_entity_id):
            row.loyalty = clamp_int(row.loyalty - ctx.rules.servitors.defeat_loyalty, 0, PERCENT)
            shaken += 1
    return shaken


def wear(rules: Rules, row: ServitorRow) -> None:
    if "loyalty" not in row.locked:
        row.loyalty = clamp_int(row.loyalty - rules.servitors.command_loyalty, 0, PERCENT)


async def herald_bonus(session: AsyncSession, rules: Rules, god_id: int) -> int:
    count = await session.scalar(
        select(func.count()).select_from(ServitorRow).where(ServitorRow.god_node_id == god_id, ServitorRow.role == ServitorRole.MESSENGER)
    )
    return min(rules.servitors.herald_max_pct, int(count or 0) * rules.servitors.herald_dream_pct)
