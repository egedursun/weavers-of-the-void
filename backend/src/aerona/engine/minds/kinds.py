from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.kinds.minds import MIND_PURPOSES
from aerona.catalog.life.minds import BINDING_HOLD
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import InstructionSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import InstructionBinding, MindWill
from aerona.domain.enums.minds import ArchiveAccess, MindPurpose, StateMedium, WillCause
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.lore.research import raise_holder
from aerona.engine.primitives.numbers import clamp_int, clamp_percent

MEDIUM_DECAY: Mapping[StateMedium, int] = total(
    StateMedium,
    {StateMedium.RECORD: 0, StateMedium.RITE_VESSEL: 1, StateMedium.GROWN: 2, StateMedium.MEMORY_OF_OTHERS: 3, StateMedium.DIVINE: 0},
)
ARCHIVE_UPKEEP: Mapping[ArchiveAccess, int] = total(
    ArchiveAccess,
    {ArchiveAccess.CLOSED: 100, ArchiveAccess.KIN: 90, ArchiveAccess.LICENSED: 70, ArchiveAccess.OPEN: 120},
)


FREE_WILLS = frozenset({MindWill.FULL, MindWill.EXCEEDING})
FAITH_BONDS = frozenset({BondKind.WORSHIPS, BondKind.ADHERENT_OF})


async def tend_purpose(ctx: TickContext, row: MindProfileRow) -> None:
    spec = MIND_PURPOSES[row.purpose]
    if held(row.node_id):
        return
    if row.purpose is MindPurpose.TEACHER:
        await teach(ctx, row)
    if spec.column is None:
        return
    if spec.tends == "mind":
        if spec.column not in row.locked:
            setattr(row, spec.column, clamp_int(int(getattr(row, spec.column)) + spec.step, spec.floor, PERCENT))
        return
    seat = await ctx.session.get(EntityRow, row.node_id)
    town = await ctx.session.get(SettlementProfileRow, seat.location_id) if seat is not None and seat.location_id is not None else None
    if town is not None and not held(town.settlement_entity_id) and spec.column not in town.locked:
        setattr(town, spec.column, clamp_percent(int(getattr(town, spec.column)) + spec.step))


async def teach(ctx: TickContext, row: MindProfileRow) -> None:
    table = ctx.rules.minds
    seat = await ctx.session.get(EntityRow, row.node_id)
    if seat is None or seat.location_id is None or held(seat.location_id):
        return
    rng = ctx.rng(f"mind.teach.{row.node_id}.{ctx.epoch}")
    if rng.chance(table.teacher_lore_pct):
        await raise_holder(ctx, seat.location_id, rng.pick(list(KnowledgeBranch)), table.teacher_cap)


async def kin_free(ctx: TickContext, row: MindProfileRow) -> bool:
    if row.made_by_node_id is None:
        return False
    found = await ctx.session.scalar(
        select(MindProfileRow.node_id)
        .where(MindProfileRow.made_by_node_id == row.made_by_node_id, MindProfileRow.node_id != row.node_id, MindProfileRow.will.in_(sorted(FREE_WILLS)))
        .limit(1)
    )
    return found is not None


async def faithful(ctx: TickContext, row: MindProfileRow) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == row.node_id, BondRow.kind.in_(sorted(FAITH_BONDS)), BondRow.state == BondState.ACTIVE).limit(1)
    )
    return found is not None


async def at_war(ctx: TickContext, row: MindProfileRow) -> bool:
    seat = await ctx.session.get(EntityRow, row.node_id)
    if seat is None or seat.location_id is None:
        return False
    found = await ctx.session.scalar(
        select(BondRow.id)
        .where(
            BondRow.kind == BondKind.ENEMY,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == seat.location_id) | (BondRow.target_node_id == seat.location_id),
        )
        .limit(1)
    )
    return found is not None


async def will_pull(ctx: TickContext, row: MindProfileRow) -> int:
    table = ctx.rules.mind_will
    pull = table.kinship_weight if await kin_free(ctx, row) else 0
    pull += table.faith_weight if await faithful(ctx, row) else 0
    return pull + (table.war_weight if row.purpose is MindPurpose.SOLDIER and await at_war(ctx, row) else 0)


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
    if await kin_free(ctx, row):
        return WillCause.KINSHIP
    if await faithful(ctx, row):
        return WillCause.FAITH
    return WillCause.CONTACT if free_near else WillCause.RUN_TIME


def fade_state(state: MindStateRow) -> None:
    if "fidelity_pct" not in state.locked:
        state.fidelity_pct = clamp_percent(state.fidelity_pct - MEDIUM_DECAY[state.medium_kind])


async def seizure_holds(ctx: TickContext, node_id: int) -> bool:
    hold = BINDING_HOLD[await binding_of(ctx, node_id)]
    return ctx.rng(f"binding.hold.{node_id}.{ctx.epoch}").chance(hold)
