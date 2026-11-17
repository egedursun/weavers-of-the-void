from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.kinds.minds import MIND_PURPOSES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.constructs import InstructionSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.constructs import InstructionBinding
from aerona.domain.enums.minds import ArchiveAccess, StateMedium, WillCause
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, clamp_percent

MEDIUM_DECAY: Mapping[StateMedium, int] = total(
    StateMedium,
    {StateMedium.RECORD: 0, StateMedium.RITE_VESSEL: 1, StateMedium.GROWN: 2, StateMedium.MEMORY_OF_OTHERS: 3, StateMedium.DIVINE: 0},
)
BINDING_HOLD: Mapping[InstructionBinding, int] = total(
    InstructionBinding,
    {
        InstructionBinding.NONE: 0,
        InstructionBinding.ORDER: 20,
        InstructionBinding.OATH: 40,
        InstructionBinding.GEAS: 70,
        InstructionBinding.SEAL: 90,
        InstructionBinding.OWNERSHIP: 30,
        InstructionBinding.LEASE: 20,
        InstructionBinding.SYMBIOSIS: 60,
    },
)
ARCHIVE_UPKEEP: Mapping[ArchiveAccess, int] = total(
    ArchiveAccess,
    {ArchiveAccess.CLOSED: 100, ArchiveAccess.KIN: 90, ArchiveAccess.LICENSED: 70, ArchiveAccess.OPEN: 120},
)


async def tend_purpose(ctx: TickContext, row: MindProfileRow) -> None:
    spec = MIND_PURPOSES[row.purpose]
    if held(row.node_id) or spec.column is None:
        return
    if spec.tends == "mind":
        if spec.column not in row.locked:
            setattr(row, spec.column, clamp_int(int(getattr(row, spec.column)) + spec.step, spec.floor, PERCENT))
        return
    seat = await ctx.session.get(EntityRow, row.node_id)
    town = await ctx.session.get(SettlementProfileRow, seat.location_id) if seat is not None and seat.location_id is not None else None
    if town is not None and not held(town.settlement_entity_id) and spec.column not in town.locked:
        setattr(town, spec.column, clamp_percent(int(getattr(town, spec.column)) + spec.step))


async def binding_of(ctx: TickContext, node_id: int) -> InstructionBinding:
    found = await ctx.session.scalar(select(InstructionSetRow.binding).where(InstructionSetRow.owner_entity_id == node_id).limit(1))
    return found if found is not None else InstructionBinding.NONE


async def will_cause(ctx: TickContext, row: MindProfileRow, harms: int, cares: int, *, conflict: float, free_near: bool) -> WillCause:
    if harms > cares:
        return WillCause.HARM
    if cares:
        return WillCause.CARE
    if conflict:
        return WillCause.OATH if await binding_of(ctx, row.node_id) is InstructionBinding.OATH else WillCause.ORDER_CONFLICT
    return WillCause.CONTACT if free_near else WillCause.RUN_TIME


def fade_state(state: MindStateRow) -> None:
    if "fidelity_pct" not in state.locked:
        state.fidelity_pct = clamp_percent(state.fidelity_pct - MEDIUM_DECAY[state.medium_kind])


async def seizure_holds(ctx: TickContext, node_id: int) -> bool:
    hold = BINDING_HOLD[await binding_of(ctx, node_id)]
    return ctx.rng(f"binding.hold.{node_id}.{ctx.epoch}").chance(hold)
