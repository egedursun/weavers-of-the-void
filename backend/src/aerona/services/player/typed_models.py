from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.anatomy import ATTACK_FIELDS, CreatureAttackRow
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.dimension_aspects import ASPECT_FIELDS, DimensionAspectRow
from aerona.db.tables.horror import HORROR_FIELDS, HorrorEventRow
from aerona.db.tables.lore import LegendaryQuestRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement
from aerona.domain.enums.ecology import AttackDelivery, AttackEffect, AttackRange
from aerona.engine.cosmos.aspects import aspect_row
from aerona.engine.powers.control import edit_fields
from aerona.engine.storyteller.pace import storyteller_of
from aerona.engine.storyteller.palette import BY_KEY
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

QUEST_FIELDS = {"aim", "target_kind", "obstacle", "reward", "scale"}
WEIGHT_MAX = 1000


class HorrorEdit(Edited):
    horror_id: int
    hold: bool = True


class HorrorTarget(Command):
    horror_id: int


class AttackMake(Command):
    node_id: int
    delivery: AttackDelivery = AttackDelivery.TOUCH
    effect: AttackEffect = AttackEffect.FORCE
    range: AttackRange = AttackRange.NEAR
    recharge: int = Field(default=0, ge=0, le=100)
    permanent: bool = False


class AttackEdit(Edited):
    attack_id: int
    hold: bool = True


class AttackTarget(Command):
    attack_id: int


class AspectMake(Command):
    dimension_id: int
    form: SpellForm | None = None
    element: DimensionElement | None = None
    strength: int = Field(default=50, ge=0, le=100)


class AspectEdit(Edited):
    aspect_id: int
    hold: bool = True


class AspectTarget(Command):
    aspect_id: int


class LegendaryQuestEdit(Edited):
    thread_id: int
    hold: bool = True


class HeroQuestEdit(Edited):
    quest_id: int
    hold: bool = True


class PaletteSet(Command):
    world_id: int
    key: str
    weight_pct: int | None = Field(default=None, ge=0, le=WEIGHT_MAX)
    release: bool = False


async def horror_of(scope: PlayerScope, horror_id: int) -> HorrorEventRow:
    row = await scope.session.get(HorrorEventRow, horror_id)
    if row is None:
        raise NotFoundError("No such horror.")
    return row


@player_action("horror_event:edit", ActionKind.EDIT_RECORD)
async def horror_edit(scope: PlayerScope, command: HorrorEdit) -> Effect:
    row = await horror_of(scope, command.horror_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(HORROR_FIELDS))
    return Effect(f"The horror: {', '.join(changed) or 'nothing'} set.", row.world_id)


@player_action("horror_event:delete", ActionKind.EDIT_RECORD)
async def horror_delete(scope: PlayerScope, command: HorrorTarget) -> Effect:
    row = await horror_of(scope, command.horror_id)
    await scope.session.delete(row)
    return Effect("The horror is gone from the world.", row.world_id)


@player_action("creature_attack:create", ActionKind.EDIT_RECORD)
async def attack_create(scope: PlayerScope, command: AttackMake) -> Effect:
    if await scope.session.get(NodeRow, command.node_id) is None:
        raise NotFoundError("No such creature.")
    row = CreatureAttackRow(
        node_id=command.node_id, delivery=command.delivery, effect=command.effect, range=command.range, recharge=command.recharge, permanent=command.permanent
    )
    row.locked = []
    scope.session.add(row)
    await scope.session.flush()
    return Effect("It has a new attack.", command.node_id, values={"attack_id": row.id})


async def attack_of(scope: PlayerScope, attack_id: int) -> CreatureAttackRow:
    row = await scope.session.get(CreatureAttackRow, attack_id)
    if row is None:
        raise NotFoundError("No such attack.")
    return row


@player_action("creature_attack:edit", ActionKind.EDIT_RECORD)
async def attack_edit(scope: PlayerScope, command: AttackEdit) -> Effect:
    row = await attack_of(scope, command.attack_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(ATTACK_FIELDS))
    return Effect(f"The attack: {', '.join(changed) or 'nothing'} set.", row.node_id)


@player_action("creature_attack:delete", ActionKind.EDIT_RECORD)
async def attack_delete(scope: PlayerScope, command: AttackTarget) -> Effect:
    row = await attack_of(scope, command.attack_id)
    await scope.session.delete(row)
    return Effect("The attack is taken from it.", row.node_id)


@player_action("dimension_aspect:create", ActionKind.EDIT_RECORD)
async def aspect_create(scope: PlayerScope, command: AspectMake) -> Effect:
    if await scope.session.get(DimensionRow, command.dimension_id) is None:
        raise NotFoundError("No such dimension.")
    if (command.form is None) == (command.element is None):
        raise ValidationFailedError("An aspect is either a form or a matter, never both or neither.")
    row = aspect_row(command.dimension_id, strength=command.strength, form=command.form, element=command.element)
    scope.session.add(row)
    await scope.session.flush()
    return Effect("The dimension takes on a new aspect.", command.dimension_id, values={"aspect_id": row.id})


async def aspect_of(scope: PlayerScope, aspect_id: int) -> DimensionAspectRow:
    row = await scope.session.get(DimensionAspectRow, aspect_id)
    if row is None:
        raise NotFoundError("No such aspect.")
    return row


@player_action("dimension_aspect:edit", ActionKind.EDIT_RECORD)
async def aspect_edit(scope: PlayerScope, command: AspectEdit) -> Effect:
    row = await aspect_of(scope, command.aspect_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(ASPECT_FIELDS))
    if (row.form is None) == (row.element is None):
        raise ValidationFailedError("An aspect is either a form or a matter, never both or neither.")
    return Effect(f"The aspect: {', '.join(changed) or 'nothing'} set.", row.dimension_id)


@player_action("dimension_aspect:delete", ActionKind.EDIT_RECORD)
async def aspect_delete(scope: PlayerScope, command: AspectTarget) -> Effect:
    row = await aspect_of(scope, command.aspect_id)
    await scope.session.delete(row)
    return Effect("The aspect fades from the dimension.", row.dimension_id)


@player_action("legendary_quest:edit", ActionKind.EDIT_RECORD)
async def legendary_edit(scope: PlayerScope, command: LegendaryQuestEdit) -> Effect:
    row = await scope.session.get(LegendaryQuestRow, command.thread_id)
    if row is None:
        raise NotFoundError("No such legendary quest.")
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, QUEST_FIELDS)
    return Effect(f"The legendary quest: {', '.join(changed) or 'nothing'} set.")


@player_action("hero_quest:edit", ActionKind.EDIT_RECORD)
async def hero_quest_edit(scope: PlayerScope, command: HeroQuestEdit) -> Effect:
    row = await scope.session.get(HeroQuestRow, command.quest_id)
    if row is None:
        raise NotFoundError("No such quest.")
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, QUEST_FIELDS)
    return Effect(f"The quest: {', '.join(changed) or 'nothing'} set.", row.hero_entity_id)


@player_action("storyteller:palette", ActionKind.EDIT_RECORD)
async def palette_set(scope: PlayerScope, command: PaletteSet) -> Effect:
    if command.key not in BY_KEY:
        raise ValidationFailedError("No such event in the storyteller's palette.")
    row = await storyteller_of(await scope.context("storyteller_palette"), command.world_id)
    palette = dict(row.palette or {})
    if command.release:
        row.locked = [field for field in (row.locked or []) if field != "palette"]
        return Effect("The storyteller weighs its palette again.", command.world_id)
    if command.weight_pct is None:
        raise ValidationFailedError("Give a weight or release the palette.")
    palette[command.key] = command.weight_pct
    row.palette = palette
    row.locked = sorted({*(row.locked or []), "palette"})
    return Effect(f"The storyteller weighs {command.key.replace('_', ' ')} at {command.weight_pct}%.", command.world_id)
