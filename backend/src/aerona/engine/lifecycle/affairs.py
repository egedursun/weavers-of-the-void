from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Select, or_, select

from aerona.catalog.affairs import OUTLIVES
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cycles import GiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import IdeaRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.communication import DispatchState
from aerona.domain.enums.cycles import GiftState
from aerona.domain.enums.entity import ENDED_STATUSES
from aerona.domain.enums.gathering import GatheringStatus
from aerona.domain.enums.lifecycle_affairs import AffairKind
from aerona.domain.enums.mind import IdeaState
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.statecraft import MandateState
from aerona.domain.enums.war import HeroQuestStatus
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import recording


@dataclass(frozen=True)
class Affair:
    kind: AffairKind
    row: type[Any]
    holder: str
    state: str
    active: tuple[StrEnum, ...]
    ended: StrEnum


AFFAIRS: tuple[Affair, ...] = (
    Affair(AffairKind.IDEA, IdeaRow, "holder_node_id", "state", (IdeaState.INCUBATING,), IdeaState.LAPSED),
    Affair(AffairKind.QUEST, HeroQuestRow, "hero_entity_id", "status", (HeroQuestStatus.ACTIVE,), HeroQuestStatus.DIED),
    Affair(AffairKind.GATHERING, GatheringRow, "host_node_id", "status", (GatheringStatus.PLANNED,), GatheringStatus.CANCELLED),
    Affair(AffairKind.GIFT, GiftRow, "giver_node_id", "state", (GiftState.OPEN,), GiftState.LAPSED),
    Affair(AffairKind.GIFT, GiftRow, "receiver_node_id", "state", (GiftState.OPEN,), GiftState.LAPSED),
    Affair(AffairKind.MANDATE, MandateRow, "polity_entity_id", "state", (MandateState.ACTIVE,), MandateState.FAILED),
    Affair(AffairKind.MESSAGE, MessageRow, "recipient_node_id", "state", (DispatchState.UNDER_WAY,), DispatchState.LOST),
)

ENDING = [kind for kind, outlives in OUTLIVES.items() if not outlives]


@dataclass
class AffairTally:
    affairs: int = 0
    ties: int = 0
    holders: int = 0


def ended() -> Select[int]:
    return select(EntityRow.id).where(EntityRow.status.in_(sorted(ENDED_STATUSES)))


async def open_affairs(ctx: TickContext) -> dict[int, list[tuple[object, str, object]]]:
    found: dict[int, list[tuple[object, str, object]]] = defaultdict(list)
    for affair in AFFAIRS:
        holder = getattr(affair.row, affair.holder)
        rows = await ctx.session.scalars(
            select(affair.row).where(holder.in_(ended()), getattr(affair.row, affair.state).in_(list(affair.active))).order_by(holder)
        )
        for row in rows:
            found[int(getattr(row, affair.holder))].append((row, affair.state, affair.ended))
    return found


async def open_ties(ctx: TickContext) -> dict[int, list[BondRow]]:
    gone = set(await ctx.session.scalars(ended()))
    statement = select(BondRow).where(
        BondRow.state == BondState.ACTIVE, BondRow.kind.in_(ENDING), or_(BondRow.source_node_id.in_(ended()), BondRow.target_node_id.in_(ended()))
    )
    found: dict[int, list[BondRow]] = defaultdict(list)
    for tie in await ctx.session.scalars(statement.order_by(BondRow.id)):
        found[tie.source_node_id if tie.source_node_id in gone else tie.target_node_id].append(tie)
    return found


async def close_affairs(ctx: TickContext, tally: AffairTally) -> None:
    bonds = BondRepository(ctx.session)
    affairs_of = await open_affairs(ctx)
    ties_of = await open_ties(ctx)
    for holder in sorted(set(affairs_of) | set(ties_of)):
        if held(holder):
            continue
        affairs = affairs_of.get(holder, [])
        ties = [tie for tie in ties_of.get(holder, []) if not held(tie.source_node_id, tie.target_node_id)]
        if not affairs and not ties:
            continue
        async with recording(ctx, "lifecycle.affairs_closed", participants=[holder]):
            for row, state, closed in affairs:
                setattr(row, state, closed)
            for tie in ties:
                await bonds.deactivate(tie, ctx.epoch, "the end of one bound by it")
            await record(ctx, "lifecycle.affairs_closed", roles={IncidentRole.SUBJECT: holder}, facts={"affairs": len(affairs), "ties": len(ties)})
        tally.affairs += len(affairs)
        tally.ties += len(ties)
        tally.holders += 1
    await ctx.session.flush()
