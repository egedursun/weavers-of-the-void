from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionPolarity
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import divine_of
from aerona.engine.divine.prayer_window import judged_in_run
from aerona.engine.gods.reputation import event_polarity
from aerona.engine.gods.worship import creator_node_id
from aerona.engine.primitives.numbers import clamp_int

AXES = ("awe", "love", "fear", "neglect")


@dataclass
class Tally:
    answered: int = 0
    unanswered: int = 0
    kind: int = 0
    stern: int = 0


@dataclass
class StandingBook:
    tallies: dict[tuple[int, int], Tally] = field(default_factory=lambda: defaultdict(Tally))


async def community_of(ctx: TickContext, node_id: int) -> int | None:
    row = await ctx.session.get(EntityRow, node_id)
    if row is None:
        return None
    if row.entity_type in COMMUNITY_TYPES:
        return row.id
    place = await ctx.session.get(EntityRow, row.location_id) if row.location_id is not None else None
    return place.id if place is not None and place.entity_type in COMMUNITY_TYPES else None


async def tally_epoch(ctx: TickContext, gods: set[int]) -> StandingBook:
    book = StandingBook()
    prayers = await ctx.session.scalars(
        select(MessageRow).where(judged_in_run(ctx.epoch), MessageRow.intent != MessageIntent.CHAT, MessageRow.recipient_node_id.in_(list(gods)))
    )
    for prayer in prayers:
        community = await community_of(ctx, prayer.sender_node_id)
        if community is None:
            continue
        tally = book.tallies[(community, prayer.recipient_node_id)]
        if prayer.answered:
            tally.answered += 1
        else:
            tally.unanswered += 1
    acts = await ctx.session.scalars(
        select(ActionRecordRow).where(
            ActionRecordRow.epoch == ctx.epoch, ActionRecordRow.actor_node_id.in_(list(gods)), ActionRecordRow.target_node_id.is_not(None)
        )
    )
    for act in acts:
        community = await community_of(ctx, act.target_node_id) if act.target_node_id is not None else None
        if community is None or act.actor_node_id is None:
            continue
        polarity = event_polarity(act.kind)
        tally = book.tallies[(community, act.actor_node_id)]
        if polarity is ActionPolarity.BENEVOLENT:
            tally.kind += 1
        elif polarity is ActionPolarity.STERN:
            tally.stern += 1
    return book


async def standing_row(ctx: TickContext, community_id: int, god_id: int) -> DivineStandingRow:
    row = await ctx.session.get(DivineStandingRow, (community_id, god_id))
    if row is None:
        row = DivineStandingRow(community_entity_id=community_id, god_node_id=god_id, awe=0, love=0, fear=0, neglect=0, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


def temper(god: object) -> tuple[float, float]:
    if isinstance(god, SonRow):
        return 1 + god.mercy / PERCENT, 1 + god.wrath / PERCENT
    return 1.0, 1.0


async def present(ctx: TickContext, god: object, community: EntityRow) -> bool:
    if isinstance(god, SonRow):
        return god.current_world_id == community.world_id
    world = getattr(god, "world_id", None)
    return world is None or world == community.world_id


def moved(current: int, gain: float, decay_pct: int) -> int:
    return clamp_int(current * (PERCENT - decay_pct) / PERCENT + gain, 0, PERCENT)


async def tend_standing(ctx: TickContext) -> int:
    table = ctx.rules.divine_standing
    creator = await creator_node_id(ctx.session)
    pairs: set[tuple[int, int]] = set()
    worship = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        )
    )
    for community_id, god_id in worship:
        pairs.add((community_id, god_id))
    known = await ctx.session.execute(select(DivineStandingRow.community_entity_id, DivineStandingRow.god_node_id))
    pairs |= {(community_id, god_id) for community_id, god_id in known}
    if creator is not None:
        communities = await ctx.session.scalars(
            select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
        )
        pairs |= {(community_id, creator) for community_id in communities}
    gods = {god_id for _, god_id in pairs}
    tallies = (await tally_epoch(ctx, gods)).tallies
    tended = 0
    for community_id, god_id in sorted(pairs):
        if held(community_id, god_id):
            continue
        community = await ctx.session.get(EntityRow, community_id)
        god = await divine_of(ctx.session, god_id)
        if community is None or god is None or community.status is not EntityStatus.CANON:
            continue
        row = await standing_row(ctx, community_id, god_id)
        tally = tallies.get((community_id, god_id), Tally())
        mercy, wrath = temper(god)
        here = await present(ctx, god, community)
        gains = {
            "awe": (tally.kind + tally.stern) * table.act_awe + (table.presence_awe if here else 0),
            "love": (tally.answered * table.answer_love + tally.kind * table.kind_love) * mercy,
            "fear": tally.stern * table.stern_fear * wrath,
            "neglect": tally.unanswered * table.unanswered_neglect
            + (0 if here or god_id == creator else table.absence_neglect)
            - tally.answered * table.answer_relief,
        }
        for axis in AXES:
            if axis not in row.locked:
                setattr(row, axis, moved(getattr(row, axis), gains[axis], table.decay_pct))
        row.epoch = ctx.epoch
        tended += 1
    await ctx.session.flush()
    return tended


async def standing_of(ctx: TickContext, god_id: int) -> list[DivineStandingRow]:
    statement = select(DivineStandingRow).where(DivineStandingRow.god_node_id == god_id).order_by(DivineStandingRow.community_entity_id)
    return list(await ctx.session.scalars(statement))


async def mean_neglect(ctx: TickContext, god_id: int) -> float:
    rows = await standing_of(ctx, god_id)
    return sum(row.neglect for row in rows) / len(rows) if rows else 0.0


async def standing_of_pair(ctx: TickContext, community_id: int, god_id: int) -> DivineStandingRow | None:
    return await ctx.session.get(DivineStandingRow, (community_id, god_id))


async def neglect_of(ctx: TickContext, community_id: int, god_id: int) -> int:
    row = await ctx.session.get(DivineStandingRow, (community_id, god_id))
    return row.neglect if row is not None else 0
