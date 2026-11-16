from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.core.total import total
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
from aerona.domain.enums.mythic import ServitorOrigin, ServitorRole
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, god_of, living_gods
from aerona.engine.faith.book import patron_node
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat
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
            body=f"{an(role.value.replace('_', ' '), capital=True)} in the service of its god.",
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


async def enrol(ctx: TickContext, spirit_id: int, god_id: int, *, role: ServitorRole, post_id: int | None, origin: ServitorOrigin) -> ServitorRow:
    row = await ctx.session.get(ServitorRow, spirit_id)
    if row is None:
        row = ServitorRow(spirit_entity_id=spirit_id, god_node_id=god_id, locked=[])
        ctx.session.add(row)
    row.god_node_id, row.role, row.post_entity_id, row.origin = god_id, role, post_id, origin
    row.loyalty, row.since_epoch = ctx.rules.servitors.fall_at + PERCENT // 2, ctx.epoch
    await ctx.session.flush()
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
    if row.loyalty >= table.fall_at or "god_node_id" in row.locked or not ctx.rng(f"servitor.fall.{row.spirit_entity_id}.{ctx.epoch}").chance(table.fall_pct):
        return
    master = await new_master(ctx, await god_of(ctx.session, row.god_node_id), f"servitor.master.{row.spirit_entity_id}")
    if master is None:
        return
    old = row.god_node_id
    row.god_node_id, row.fallen_to_node_id, row.loyalty = master, master, PERCENT // 2
    profile = await ctx.session.get(SpiritProfileRow, row.spirit_entity_id)
    if profile is not None and "alignment" not in profile.locked:
        profile.alignment = SpiritAlignment.VENGEFUL
    tally.fallen += 1
    await note(
        ctx,
        "A servitor fell from its god and took another master.",
        key="mythic.servitor_fell",
        ids=[row.spirit_entity_id, old, master],
        kind=ChronicleKind.WORLD,
    )


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


async def stand_by(_ctx: TickContext, _row: ServitorRow, _tally: ServitorTally) -> None:
    return None


async def act_as_agent(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    post = await ctx.session.get(EntityRow, row.post_entity_id) if row.post_entity_id is not None else None
    if post is not None and post.status is EntityStatus.CANON and not held(post.id):
        shift_stat(post, "prosperity", ctx.rules.servitors.agent_prosperity, 0, high=PERCENT)
        tally.served += 1


async def avenge(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    for standing in await standings(ctx, row.god_node_id):
        if standing.love < table.avenger_scorn and "fear" not in standing.locked:
            standing.fear = clamp_int(standing.fear + table.avenger_fear, 0, PERCENT)
            tally.served += 1


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


async def worship(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    for standing in await standings(ctx, row.god_node_id):
        if standing.love >= ctx.rules.servitors.avenger_scorn and "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + ctx.rules.servitors.worshipper_awe, 0, PERCENT)
            tally.served += 1


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


async def keep_accounts(ctx: TickContext, row: ServitorRow, tally: ServitorTally) -> None:
    tellers = set(await ctx.session.scalars(select(FolkBeliefRow.people_entity_id).where(FolkBeliefRow.god_node_id == row.god_node_id)))
    for standing in await standings(ctx, row.god_node_id):
        community = await ctx.session.get(EntityRow, standing.community_entity_id)
        people = await people_of(ctx.session, community) if community is not None else None
        if people is not None and people.id in tellers and "love" not in standing.locked:
            standing.love = clamp_int(standing.love + ctx.rules.servitors.scribe_love, 0, PERCENT)
            tally.served += 1


Duty = Callable[[TickContext, ServitorRow, ServitorTally], Awaitable[None]]
DUTIES: Mapping[ServitorRole, Duty] = total(
    ServitorRole,
    {
        ServitorRole.MESSENGER: stand_by,
        ServitorRole.GUARD: stand_by,
        ServitorRole.JUDGE: judge,
        ServitorRole.HOST: stand_by,
        ServitorRole.SPY: stand_by,
        ServitorRole.AGENT: act_as_agent,
        ServitorRole.AVENGER: avenge,
        ServitorRole.GUIDE_OF_SOULS: guide_souls,
        ServitorRole.WORSHIPPER: worship,
        ServitorRole.WARDEN: ward,
        ServitorRole.SCRIBE: keep_accounts,
    },
)


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


async def tend_servitors(ctx: TickContext, tally: ServitorTally) -> None:
    table = ctx.rules.servitors
    await raise_saints(ctx, tally)
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
