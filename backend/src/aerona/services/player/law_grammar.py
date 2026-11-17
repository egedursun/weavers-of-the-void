from pydantic import Field

from aerona.catalog.law_grammar import Grammar
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.law_grammar import EXCEPTION_FIELDS, THEORY_FIELDS, LawExceptionRow, LawTheoryRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawExceptionKind, LawOperator, LawTarget
from aerona.engine.divine.law_grammar import set_grammar
from aerona.engine.powers.control import edit_fields
from aerona.engine.primitives.queries import living_entity
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NEEDS_NODE = frozenset({LawExceptionKind.PERSON, LawExceptionKind.LINE, LawExceptionKind.PEOPLE, LawExceptionKind.PLACE})


class GrammarSet(Command):
    law_id: int
    target: LawTarget
    operator: LawOperator
    key: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    value: int = Field(default=100, ge=0, le=1000)
    condition: LawCondition = LawCondition.ALWAYS
    until_epoch: int | None = Field(default=None, ge=0)


class ExceptionMake(Command):
    law_id: int
    kind: LawExceptionKind
    node_id: int | None = None
    entity_type: EntityType | None = None


class ExceptionEdit(Edited):
    exception_id: int
    hold: bool = True


class ExceptionTarget(Command):
    exception_id: int


class TheoryMake(Command):
    law_id: int
    holder_id: int
    believed_operator: LawOperator = LawOperator.SET
    believed_value: int = Field(default=100, ge=0, le=1000)


class TheoryEdit(Edited):
    theory_id: int
    hold: bool = True


class TheoryTarget(Command):
    theory_id: int


async def law_entity(scope: PlayerScope, law_id: int) -> None:
    law = await living_entity(scope.session, law_id)
    if law is None or law.entity_type is not EntityType.NATURAL_LAW:
        raise NotFoundError("No such living natural law.")


@player_action("law_grammar:set", ActionKind.EDIT_RECORD)
async def grammar_set(scope: PlayerScope, command: GrammarSet) -> Effect:
    ctx = await scope.context("law_grammar_set")
    law = await living_entity(ctx.session, command.law_id)
    if law is None or law.entity_type is not EntityType.NATURAL_LAW:
        raise NotFoundError("No such living natural law.")
    grammar = Grammar(command.target, command.operator, command.key.strip(), command.value)
    await set_grammar(ctx, law, grammar, command.condition, command.until_epoch, hold=True)
    return Effect(f"{law.name} now {spoken(command.operator)}s {command.key.strip()}.", law.id)


@player_action("law_exception:create", ActionKind.EDIT_RECORD)
async def exception_create(scope: PlayerScope, command: ExceptionMake) -> Effect:
    await law_entity(scope, command.law_id)
    if command.kind in NEEDS_NODE and (command.node_id is None or await scope.session.get(NodeRow, command.node_id) is None):
        raise ValidationFailedError("Name who or what the law spares.")
    if command.kind is LawExceptionKind.KIND and command.entity_type is None:
        raise ValidationFailedError("Name the kind of thing the law spares.")
    row = LawExceptionRow(law_entity_id=command.law_id, kind=command.kind, node_id=command.node_id, entity_type=command.entity_type, locked=[])
    scope.session.add(row)
    await scope.session.flush()
    return Effect("The law now spares them.", command.law_id, values={"exception_id": row.id})


async def exception_of(scope: PlayerScope, exception_id: int) -> LawExceptionRow:
    row = await scope.session.get(LawExceptionRow, exception_id)
    if row is None:
        raise NotFoundError("No such exception to a law.")
    return row


@player_action("law_exception:edit", ActionKind.EDIT_RECORD)
async def exception_edit(scope: PlayerScope, command: ExceptionEdit) -> Effect:
    row = await exception_of(scope, command.exception_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(EXCEPTION_FIELDS))
    return Effect(f"The exception: {', '.join(changed) or 'nothing'} set.", row.law_entity_id)


@player_action("law_exception:delete", ActionKind.EDIT_RECORD)
async def exception_delete(scope: PlayerScope, command: ExceptionTarget) -> Effect:
    row = await exception_of(scope, command.exception_id)
    await scope.session.delete(row)
    return Effect("The law spares them no longer.", row.law_entity_id)


@player_action("law_theory:create", ActionKind.EDIT_RECORD)
async def theory_create(scope: PlayerScope, command: TheoryMake) -> Effect:
    await law_entity(scope, command.law_id)
    if await scope.session.get(NodeRow, command.holder_id) is None:
        raise NotFoundError("No such holder for the theory.")
    ctx = await scope.context("law_theory_create")
    row = LawTheoryRow(
        holder_node_id=command.holder_id, law_entity_id=command.law_id, believed_operator=command.believed_operator, believed_value=command.believed_value
    )
    row.updated_epoch, row.locked = ctx.epoch, ["believed_operator", "believed_value"]
    ctx.session.add(row)
    await ctx.session.flush()
    return Effect("They now hold a theory of the law.", command.holder_id, values={"theory_id": row.id})


async def theory_of(scope: PlayerScope, theory_id: int) -> LawTheoryRow:
    row = await scope.session.get(LawTheoryRow, theory_id)
    if row is None:
        raise NotFoundError("No such theory of a law.")
    return row


@player_action("law_theory:edit", ActionKind.EDIT_RECORD)
async def theory_edit(scope: PlayerScope, command: TheoryEdit) -> Effect:
    row = await theory_of(scope, command.theory_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(THEORY_FIELDS))
    return Effect(f"The theory: {', '.join(changed) or 'nothing'} set.", row.holder_node_id)


@player_action("law_theory:delete", ActionKind.EDIT_RECORD)
async def theory_delete(scope: PlayerScope, command: TheoryTarget) -> Effect:
    row = await theory_of(scope, command.theory_id)
    await scope.session.delete(row)
    return Effect("The theory is forgotten.", row.holder_node_id)
