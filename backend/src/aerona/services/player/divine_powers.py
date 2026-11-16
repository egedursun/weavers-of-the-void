from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.divine_powers import DIVINE_POWER_FIELDS, DivinePowerRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.domain import Domain
from aerona.engine.divine.grammar import pay, wield
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

CAP = 100


class DivinePowerCreate(Command):
    holder_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    verb: DivineVerb = DivineVerb.BLESS
    object: DivineObject = DivineObject.STAT
    object_key: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    scope: DivineScope = DivineScope.COMMUNITY
    mode: DivineMode = DivineMode.PASSIVE
    cost: DivineCost = DivineCost.ESSENCE
    cost_amount: int = Field(default=5, ge=0, le=1000)
    cooldown: int = Field(default=0, ge=0, le=100)
    strength: int = Field(default=20, ge=0, le=CAP)
    domains: list[Domain] = Field(default_factory=list, max_length=12)


class DivinePowerTarget(Command):
    power_id: int


class DivinePowerEdit(Edited):
    power_id: int
    hold: bool = True


class DivinePowerDomains(Command):
    power_id: int
    domains: list[Domain] = Field(default_factory=list, max_length=12)


class DivinePowerUse(Command):
    power_id: int
    target_id: int | None = None


async def power_of(scope: PlayerScope, power_id: int) -> DivinePowerRow:
    row = await (await scope.context("divine_power")).session.get(DivinePowerRow, power_id)
    if row is None:
        raise NotFoundError("No such divine power.")
    return row


@player_action("divine_power:create", ActionKind.EDIT_RECORD)
async def power_create(scope: PlayerScope, command: DivinePowerCreate) -> Effect:
    ctx = await scope.context("divine_power_create")
    if await ctx.session.get(NodeRow, command.holder_id) is None:
        raise NotFoundError("There is no one there to hold the power.")
    row = DivinePowerRow(holder_node_id=command.holder_id, name=command.name, verb=command.verb, object=command.object, scope=command.scope)
    row.object_key, row.mode, row.cost, row.cost_amount = command.object_key, command.mode, command.cost, command.cost_amount
    row.cooldown, row.strength, row.domains = command.cooldown, command.strength, [domain.value for domain in command.domains]
    row.granted_epoch, row.locked = ctx.epoch, []
    ctx.session.add(row)
    await ctx.session.flush()
    return Effect(f"{command.name} is granted.", command.holder_id, values={"power_id": row.id})


@player_action("divine_power:edit", ActionKind.EDIT_RECORD)
async def power_edit(scope: PlayerScope, command: DivinePowerEdit) -> Effect:
    row = await power_of(scope, command.power_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(DIVINE_POWER_FIELDS))
    return Effect(f"{row.name}: {', '.join(changed) or 'nothing'} set.", row.holder_node_id)


@player_action("divine_power:delete", ActionKind.EDIT_RECORD)
async def power_delete(scope: PlayerScope, command: DivinePowerTarget) -> Effect:
    ctx = await scope.context("divine_power_delete")
    row = await power_of(scope, command.power_id)
    await ctx.session.delete(row)
    return Effect(f"{row.name} is taken away.", row.holder_node_id)


@player_action("divine_power:domains", ActionKind.EDIT_RECORD)
async def power_domains(scope: PlayerScope, command: DivinePowerDomains) -> Effect:
    row = await power_of(scope, command.power_id)
    row.domains = list(dict.fromkeys(domain.value for domain in command.domains))
    if "domains" not in row.locked:
        row.locked = [*row.locked, "domains"]
    return Effect(f"{row.name} draws on {several(len(row.domains), 'domain', 'domains')}.", row.holder_node_id)


@player_action("divine_power:use", ActionKind.EDIT_RECORD)
async def power_use(scope: PlayerScope, command: DivinePowerUse) -> Effect:
    ctx = await scope.context("divine_power_use")
    row = await power_of(scope, command.power_id)
    if row.last_used_epoch is not None and ctx.epoch - row.last_used_epoch < row.cooldown:
        raise ValidationFailedError(f"{row.name} is not ready again until epoch {row.last_used_epoch + row.cooldown}.")
    if not await pay(ctx, row):
        raise ValidationFailedError(f"{row.name} costs more than its holder can give.")
    touched = await wield(ctx, row, command.target_id)
    return Effect(f"{row.name} acted on {touched} at once.", row.holder_node_id, values={"touched": touched})
