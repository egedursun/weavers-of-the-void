from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.constructs import CommandToken, OrderCondition, OrderKind, OrderTime
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.material import MaterialKind
from aerona.engine.constructs import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

MANY = 1_000_000
PRIORITIES = 100


class ConstructDraft(Command):
    maker_id: int
    material: MaterialKind | None = None
    source: MagicSource | None = None
    token: CommandToken | None = None
    name: str | None = Field(default=None, max_length=120)


class ConstructTarget(Command):
    construct_id: int


class ConstructSoul(Command):
    construct_id: int
    spirit_id: int | None = None


class ConstructEdit(Edited):
    construct_id: int


class RulesDraft(Command):
    owner_id: int
    token: CommandToken = CommandToken.WORD
    token_id: int | None = None
    holder_id: int | None = None


class RulesTarget(Command):
    set_id: int


class RulesEdit(Edited):
    set_id: int


class OrderDraft(Command):
    set_id: int
    kind: OrderKind = OrderKind.GUARD
    target_id: int | None = None
    priority: int = Field(default=1, ge=0, le=PRIORITIES)
    condition: OrderCondition = OrderCondition.ALWAYS
    until_epoch: int | None = Field(default=None, ge=0)
    times: OrderTime | None = None


class OrderTarget(Command):
    order_id: int


class OrderEdit(Edited):
    order_id: int


class RemadeDraft(Command):
    mortal_id: int


class RemadeEdit(Edited):
    mortal_id: int


class ContractDraft(Command):
    town_id: int
    beast_id: int
    bounty: int = Field(default=30, ge=0, le=MANY)


class ContractTarget(Command):
    contract_id: int


class ContractHunter(Command):
    contract_id: int
    hunter_id: int


class ContractEdit(Edited):
    contract_id: int


class SignDraft(Command):
    mortal_id: int


class SignEdit(Edited):
    mortal_id: int


@player_action("construct:create", ActionKind.EDIT_RECORD)
async def construct_create(scope: PlayerScope, command: ConstructDraft) -> Effect:
    row = await control.build_construct(
        await scope.context("construct_create"), command.maker_id, material=command.material, source=command.source, token=command.token, name=command.name
    )
    return Effect("The maker gives a body motion and orders.", command.maker_id, created_ids=(row.entity_id,))


@player_action("construct:ensoul", ActionKind.EDIT_RECORD)
async def construct_ensoul(scope: PlayerScope, command: ConstructSoul) -> Effect:
    await control.ensoul(await scope.context("construct_ensoul"), command.construct_id, command.spirit_id)
    return Effect("A soul is bound into the construct." if command.spirit_id is not None else "The construct holds no soul.", command.construct_id)


@player_action("construct:unmake", ActionKind.EDIT_RECORD)
async def construct_unmake(scope: PlayerScope, command: ConstructTarget) -> Effect:
    await control.unmake_construct(await scope.context("construct_unmake"), command.construct_id)
    return Effect("The construct is stilled for good.", command.construct_id)


@player_action("construct:edit", ActionKind.EDIT_RECORD)
async def construct_edit(scope: PlayerScope, command: ConstructEdit) -> Effect:
    await control.edit_record(await scope.context("construct_edit"), "construct", command.construct_id, command.values, command.release)
    return Effect("The construct is set so.", command.construct_id)


@player_action("construct:delete", ActionKind.EDIT_RECORD)
async def construct_delete(scope: PlayerScope, command: ConstructTarget) -> Effect:
    await control.delete_record(await scope.context("construct_delete"), "construct", command.construct_id)
    return Effect("The body is a construct no more.", command.construct_id)


@player_action("instruction_set:create", ActionKind.EDIT_RECORD)
async def instruction_set_create(scope: PlayerScope, command: RulesDraft) -> Effect:
    row = await control.write_rules(await scope.context("instruction_set_create"), command.owner_id, command.token, command.token_id, command.holder_id)
    return Effect("The orders are bound to a command token.", command.owner_id, values={"set_id": row.id})


@player_action("instruction_set:resolve", ActionKind.EDIT_RECORD)
async def instruction_set_resolve(scope: PlayerScope, command: RulesTarget) -> Effect:
    row = await control.refresh_holder(await scope.context("instruction_set_resolve"), command.set_id)
    return Effect("The orders answer whoever holds the token now.", row.owner_entity_id)


@player_action("instruction_set:edit", ActionKind.EDIT_RECORD)
async def instruction_set_edit(scope: PlayerScope, command: RulesEdit) -> Effect:
    row = await control.edit_record(await scope.context("instruction_set_edit"), "instruction_set", command.set_id, command.values, command.release)
    return Effect("The instruction set is set so.", getattr(row, "owner_entity_id", None))


@player_action("instruction_set:delete", ActionKind.EDIT_RECORD)
async def instruction_set_delete(scope: PlayerScope, command: RulesTarget) -> Effect:
    await control.delete_record(await scope.context("instruction_set_delete"), "instruction_set", command.set_id)
    return Effect("The orders and their token are struck away.")


@player_action("instruction_order:create", ActionKind.EDIT_RECORD)
async def instruction_order_create(scope: PlayerScope, command: OrderDraft) -> Effect:
    row = await control.give_order(
        await scope.context("instruction_order_create"),
        command.set_id,
        command.kind,
        target_id=command.target_id,
        priority=command.priority,
        condition=command.condition,
        until_epoch=command.until_epoch,
        times=command.times,
    )
    return Effect("A new order is written.", command.target_id, values={"order_id": row.id})


@player_action("instruction_order:edit", ActionKind.EDIT_RECORD)
async def instruction_order_edit(scope: PlayerScope, command: OrderEdit) -> Effect:
    row = await control.edit_record(await scope.context("instruction_order_edit"), "instruction_order", command.order_id, command.values, command.release)
    return Effect("The order is set so.", getattr(row, "target_node_id", None))


@player_action("instruction_order:delete", ActionKind.EDIT_RECORD)
async def instruction_order_delete(scope: PlayerScope, command: OrderTarget) -> Effect:
    await control.delete_record(await scope.context("instruction_order_delete"), "instruction_order", command.order_id)
    return Effect("The order is struck out.")


@player_action("remade:create", ActionKind.EDIT_RECORD)
async def remade_create(scope: PlayerScope, command: RemadeDraft) -> Effect:
    await control.remake_mortal(await scope.context("remade_create"), command.mortal_id)
    return Effect("The mortal is remade in body.", command.mortal_id)


@player_action("remade:edit", ActionKind.EDIT_RECORD)
async def remade_edit(scope: PlayerScope, command: RemadeEdit) -> Effect:
    await control.edit_record(await scope.context("remade_edit"), "remade", command.mortal_id, command.values, command.release)
    return Effect("The remade mortal is set so.", command.mortal_id)


@player_action("remade:delete", ActionKind.EDIT_RECORD)
async def remade_delete(scope: PlayerScope, command: RemadeDraft) -> Effect:
    await control.delete_record(await scope.context("remade_delete"), "remade", command.mortal_id)
    return Effect("The mortal is remade no longer.", command.mortal_id)


@player_action("monster_contract:create", ActionKind.EDIT_RECORD)
async def monster_contract_create(scope: PlayerScope, command: ContractDraft) -> Effect:
    row = await control.post_contract(await scope.context("monster_contract_create"), command.town_id, command.beast_id, command.bounty)
    return Effect("A bounty is posted on the beast.", command.beast_id, values={"contract_id": row.id})


@player_action("monster_contract:assign", ActionKind.EDIT_RECORD)
async def monster_contract_assign(scope: PlayerScope, command: ContractHunter) -> Effect:
    await control.assign_hunter(await scope.context("monster_contract_assign"), command.contract_id, command.hunter_id)
    return Effect("The hunter takes the contract.", command.hunter_id)


@player_action("monster_contract:edit", ActionKind.EDIT_RECORD)
async def monster_contract_edit(scope: PlayerScope, command: ContractEdit) -> Effect:
    row = await control.edit_record(await scope.context("monster_contract_edit"), "monster_contract", command.contract_id, command.values, command.release)
    return Effect("The contract is set so.", getattr(row, "beast_entity_id", None))


@player_action("monster_contract:delete", ActionKind.EDIT_RECORD)
async def monster_contract_delete(scope: PlayerScope, command: ContractTarget) -> Effect:
    await control.delete_record(await scope.context("monster_contract_delete"), "monster_contract", command.contract_id)
    return Effect("The contract is torn up.")


@player_action("birth_sign:create", ActionKind.EDIT_RECORD)
async def birth_sign_create(scope: PlayerScope, command: SignDraft) -> Effect:
    row = await control.cast_sign(await scope.context("birth_sign_create"), command.mortal_id)
    return Effect("The dreaded sign is read for the mortal." if row.dreaded else "The sign of the mortal's birth is read.", command.mortal_id)


@player_action("birth_sign:edit", ActionKind.EDIT_RECORD)
async def birth_sign_edit(scope: PlayerScope, command: SignEdit) -> Effect:
    await control.edit_record(await scope.context("birth_sign_edit"), "birth_sign", command.mortal_id, command.values, command.release)
    return Effect("The birth sign is set so.", command.mortal_id)


@player_action("birth_sign:delete", ActionKind.EDIT_RECORD)
async def birth_sign_delete(scope: PlayerScope, command: SignDraft) -> Effect:
    await control.delete_record(await scope.context("birth_sign_delete"), "birth_sign", command.mortal_id)
    return Effect("The mortal's birth sign is forgotten.", command.mortal_id)
