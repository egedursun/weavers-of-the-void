from pydantic import Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.council_order import (
    PROCEDURE_FIELDS,
    SEAT_FIELDS,
    VIOLATION_FIELDS,
    CouncilProcedureRow,
    CouncilViolationRow,
    DivineSeatRow,
)
from aerona.db.tables.divine import CouncilRulingRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import CouncilRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import CouncilCaller
from aerona.domain.enums.divine import CouncilSeat, EscalationStep
from aerona.domain.models.records import CouncilMinutes
from aerona.engine.divine.council_order import PENALTIES, procedure_of
from aerona.engine.powers.control import edit_fields
from aerona.services.player import guards
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class ProcedureEdit(Edited):
    hold: bool = True


class ProcedureReset(Command):
    pass


class SeatSet(Command):
    god_id: int
    seat: CouncilSeat = CouncilSeat.INVITED


class SeatEdit(Edited):
    god_id: int
    hold: bool = True


class SeatTarget(Command):
    god_id: int


class ViolationMake(Command):
    ruling_id: int
    violator_id: int
    step: EscalationStep = EscalationStep.CENSURE


class ViolationEdit(Edited):
    violation_id: int
    hold: bool = True


class ViolationTarget(Command):
    violation_id: int


class VetoTarget(Command):
    ruling_id: int


@player_action("council_procedure:edit", ActionKind.EDIT_RECORD)
async def procedure_edit(scope: PlayerScope, command: ProcedureEdit) -> Effect:
    row = await procedure_of(await scope.context("council_procedure_edit"))
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(PROCEDURE_FIELDS))
    return Effect(f"How the council decides: {', '.join(changed) or 'nothing'} set.")


@player_action("council_procedure:reset", ActionKind.EDIT_RECORD)
async def procedure_reset(scope: PlayerScope, command: ProcedureReset) -> Effect:
    rows = list(await scope.session.scalars(select(CouncilProcedureRow)))
    for row in rows:
        await scope.session.delete(row)
    return Effect("The council's procedure is struck; it returns to the rules of the world at the next epoch.")


async def a_god(scope: PlayerScope, god_id: int) -> None:
    if await scope.session.get(SonRow, god_id) is None and await scope.session.get(ForeignGodRow, god_id) is None:
        raise NotFoundError("No such god.")


@player_action("divine_seat:set", ActionKind.EDIT_RECORD)
async def seat_set(scope: PlayerScope, command: SeatSet) -> Effect:
    await a_god(scope, command.god_id)
    ctx = await scope.context("divine_seat_set")
    row = await ctx.session.get(DivineSeatRow, command.god_id)
    if row is None:
        row = DivineSeatRow(god_node_id=command.god_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.seat, row.excluded_until = command.seat, None
    return Effect("The god takes a seat on the council.", command.god_id)


async def seat_of(scope: PlayerScope, god_id: int) -> DivineSeatRow:
    row = await scope.session.get(DivineSeatRow, god_id)
    if row is None:
        raise NotFoundError("This god holds no seat on the council.")
    return row


@player_action("divine_seat:edit", ActionKind.EDIT_RECORD)
async def seat_edit(scope: PlayerScope, command: SeatEdit) -> Effect:
    row = await seat_of(scope, command.god_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(SEAT_FIELDS))
    return Effect(f"The seat: {', '.join(changed) or 'nothing'} set.", command.god_id)


@player_action("divine_seat:delete", ActionKind.EDIT_RECORD)
async def seat_delete(scope: PlayerScope, command: SeatTarget) -> Effect:
    row = await seat_of(scope, command.god_id)
    await scope.session.delete(row)
    return Effect("The god's seat on the council is taken away.", command.god_id)


@player_action("council_violation:create", ActionKind.EDIT_RECORD)
async def violation_create(scope: PlayerScope, command: ViolationMake) -> Effect:
    if await scope.session.get(CouncilRulingRow, command.ruling_id) is None:
        raise NotFoundError("No such ruling.")
    await a_god(scope, command.violator_id)
    ctx = await scope.context("council_violation_create")
    row = CouncilViolationRow(ruling_id=command.ruling_id, violator_node_id=command.violator_id, epoch=ctx.epoch, step=command.step, locked=[])
    ctx.session.add(row)
    await PENALTIES[command.step](ctx, command.violator_id)
    await ctx.session.flush()
    return Effect(f"The god answers for breaking the ruling: {spoken(command.step)}.", command.violator_id, values={"violation_id": row.id})


async def violation_of(scope: PlayerScope, violation_id: int) -> CouncilViolationRow:
    row = await scope.session.get(CouncilViolationRow, violation_id)
    if row is None:
        raise NotFoundError("No such breach of a ruling.")
    return row


@player_action("council_violation:edit", ActionKind.EDIT_RECORD)
async def violation_edit(scope: PlayerScope, command: ViolationEdit) -> Effect:
    row = await violation_of(scope, command.violation_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(VIOLATION_FIELDS))
    return Effect(f"The breach: {', '.join(changed) or 'nothing'} set.", row.violator_node_id)


@player_action("council_violation:delete", ActionKind.EDIT_RECORD)
async def violation_delete(scope: PlayerScope, command: ViolationTarget) -> Effect:
    row = await violation_of(scope, command.violation_id)
    await scope.session.delete(row)
    return Effect("The breach is struck from the record.", row.violator_node_id)


class CouncilRecordMake(Command):
    topic: str = Field(min_length=1, max_length=400)
    passed: bool = False
    epoch: int | None = Field(default=None, ge=1)


class CouncilRecordEdit(Command):
    council_id: int
    topic: str | None = Field(default=None, min_length=1, max_length=400)
    passed: bool | None = None


class CouncilRecordTarget(Command):
    council_id: int


async def council_of(scope: PlayerScope, council_id: int) -> CouncilRow:
    row = await scope.session.get(CouncilRow, council_id)
    if row is None:
        raise NotFoundError("No such council on record.")
    return row


@player_action("council_record:create", ActionKind.EDIT_RECORD)
async def council_record_create(scope: PlayerScope, command: CouncilRecordMake) -> Effect:
    present = await scope.epoch()
    epoch = command.epoch or present
    if epoch > present:
        raise ValidationFailedError("A council cannot be set down ahead of the present epoch.")
    row = CouncilRow(
        epoch=epoch,
        topic=command.topic,
        minutes=CouncilMinutes(topic=command.topic, convened_by=CouncilCaller.CREATOR, passed=command.passed),
        passed=command.passed,
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect("A council of the gods is set down in the record.", values={"council_id": row.id})


@player_action("council_record:edit", ActionKind.EDIT_RECORD)
async def council_record_edit(scope: PlayerScope, command: CouncilRecordEdit) -> Effect:
    row = await council_of(scope, command.council_id)
    topic = command.topic if command.topic is not None else row.topic
    passed = command.passed if command.passed is not None else row.passed
    row.topic, row.passed = topic, passed
    row.minutes = row.minutes.model_copy(update={"topic": topic, "passed": passed})
    return Effect("The council's record is set so.", values={"council_id": row.id})


@player_action("council_record:delete", ActionKind.EDIT_RECORD)
async def council_record_delete(scope: PlayerScope, command: CouncilRecordTarget) -> Effect:
    row = await council_of(scope, command.council_id)
    await scope.session.delete(row)
    return Effect("The council is struck from the record.")


@player_action("council:veto", ActionKind.EDIT_RECORD)
async def veto(scope: PlayerScope, command: VetoTarget) -> Effect:
    ctx = await scope.context("council_veto")
    procedure = await procedure_of(ctx)
    if not procedure.creator_veto:
        raise ValidationFailedError("The council's rules give the Creator no veto.")
    ruling = await ctx.session.get(CouncilRulingRow, command.ruling_id)
    if ruling is None or not ruling.active:
        raise NotFoundError("No ruling in force to veto.")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.council.veto_attention, "council.veto_attention")
    ruling.active, ruling.note = False, "vetoed by the Creator"
    later = await ctx.session.scalars(select(CouncilViolationRow).where(CouncilViolationRow.ruling_id == ruling.id))
    for row in list(later):
        await ctx.session.delete(row)
    return Effect("The Creator vetoed the council's ruling.", ruling.target_node_id, essence_spent=spent)
