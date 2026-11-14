from pydantic import Field

from aerona.catalog.dangers import DANGERS, MEMORY_LABELS
from aerona.core.errors import NotFoundError
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.region import DangerSource, RegionMemoryKind
from aerona.engine.environment import region_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

TITLE_MAX = 200


class CreateDanger(Command):
    region_id: int
    source: DangerSource
    strength: int = Field(ge=0, le=100)
    hold: bool = True


class EditDanger(Command):
    danger_id: int
    strength: int | None = Field(default=None, ge=0, le=100)
    hold: bool | None = None


class DangerTarget(Command):
    danger_id: int


class Sanctify(Command):
    region_id: int
    sacredness: int | None = Field(default=None, ge=0, le=100)
    hold: bool = True


class AddMemory(Command):
    region_id: int
    kind: RegionMemoryKind
    magnitude: int = Field(ge=0, le=100)
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    hold: bool = True


class EditMemory(Command):
    memory_id: int
    kind: RegionMemoryKind | None = None
    magnitude: int | None = Field(default=None, ge=0, le=100)
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    hold: bool | None = None


class MemoryTarget(Command):
    memory_id: int


class SetKnowledge(Command):
    polity_id: int
    region_id: int
    level: int = Field(ge=0, le=100)
    hold: bool = True


class KnowledgeTarget(Command):
    polity_id: int
    region_id: int


class RedirectRiver(Command):
    from_region_id: int
    to_region_id: int


async def _name(scope: PlayerScope, entity_id: int) -> str:
    found = await scope.session.get(EntityRow, entity_id)
    if found is None:
        raise NotFoundError("No such record.")
    return found.name


@player_action("region:danger_create", ActionKind.OTHER)
async def create_danger(scope: PlayerScope, command: CreateDanger) -> Effect:
    row = await region_control.set_danger(
        scope.session, scope.rules, command.region_id, command.source, command.strength, epoch=await scope.epoch(), held=command.hold
    )
    held = " and held there" if command.hold else ""
    label = DANGERS[command.source].label.lower()
    return Effect(f"{await _name(scope, row.region_entity_id)} now suffers {label} at strength {row.strength}{held}.", target_node_id=row.region_entity_id)


@player_action("region:danger_edit", ActionKind.OTHER)
async def edit_danger(scope: PlayerScope, command: EditDanger) -> Effect:
    row = await region_control.edit_danger(
        scope.session, scope.rules, command.danger_id, strength=command.strength, held=command.hold, epoch=await scope.epoch()
    )
    state = ", held" if row.held else ""
    label = DANGERS[row.source].label
    return Effect(f"{label} in {await _name(scope, row.region_entity_id)} now stand at {row.strength}{state}.", target_node_id=row.region_entity_id)


@player_action("region:danger_release", ActionKind.OTHER)
async def release_danger(scope: PlayerScope, command: DangerTarget) -> Effect:
    row = await region_control.release_danger(scope.session, scope.rules, command.danger_id)
    label = DANGERS[row.source].label
    return Effect(f"{label} in {await _name(scope, row.region_entity_id)} follow the land again.", target_node_id=row.region_entity_id)


@player_action("region:danger_delete", ActionKind.OTHER)
async def delete_danger(scope: PlayerScope, command: DangerTarget) -> Effect:
    row = await region_control.delete_danger(scope.session, scope.rules, command.danger_id)
    label = DANGERS[row.source].label
    return Effect(
        f"{label} are driven from {await _name(scope, row.region_entity_id)}; if the land still breeds them they will return.",
        target_node_id=row.region_entity_id,
    )


@player_action("region:sanctify", ActionKind.OTHER)
async def sanctify(scope: PlayerScope, command: Sanctify) -> Effect:
    ground = await region_control.sanctify(scope.session, scope.rules, command.region_id, command.sacredness, held=command.hold)
    held = " and held" if command.hold else ""
    return Effect(f"{await _name(scope, ground.entity_id)} is sanctified: its sacredness is {ground.sacredness}{held}.", target_node_id=ground.entity_id)


@player_action("region:memory_add", ActionKind.OTHER)
async def add_memory(scope: PlayerScope, command: AddMemory) -> Effect:
    row = await region_control.add_memory(
        scope.session, command.region_id, command.kind, command.magnitude, command.title, epoch=await scope.epoch(), held=command.hold
    )
    return Effect(
        f"{await _name(scope, row.region_entity_id)} now remembers {row.title} ({MEMORY_LABELS[row.kind].lower()}, {row.magnitude}).",
        target_node_id=row.region_entity_id,
    )


@player_action("region:memory_edit", ActionKind.OTHER)
async def edit_memory(scope: PlayerScope, command: EditMemory) -> Effect:
    edit = region_control.MemoryEdit(kind=command.kind, magnitude=command.magnitude, title=command.title, held=command.hold)
    row = await region_control.edit_memory(scope.session, command.memory_id, edit)
    return Effect(f"The memory of {row.title} in {await _name(scope, row.region_entity_id)} is reshaped.", target_node_id=row.region_entity_id)


@player_action("region:memory_delete", ActionKind.OTHER)
async def delete_memory(scope: PlayerScope, command: MemoryTarget) -> Effect:
    row = await region_control.delete_memory(scope.session, command.memory_id)
    return Effect(f"{await _name(scope, row.region_entity_id)} forgets {row.title}.", target_node_id=row.region_entity_id)


@player_action("region:knowledge_set", ActionKind.OTHER)
async def set_knowledge(scope: PlayerScope, command: SetKnowledge) -> Effect:
    row = await region_control.set_knowledge(scope.session, command.polity_id, command.region_id, command.level, held=command.hold, epoch=await scope.epoch())
    polity, region = await _name(scope, row.polity_entity_id), await _name(scope, row.region_entity_id)
    if row.level == 0:
        return Effect(f"{polity} has lost every map of {region}.", target_node_id=row.region_entity_id)
    return Effect(f"{polity} now knows {region} at {row.level}.", target_node_id=row.region_entity_id)


@player_action("region:knowledge_release", ActionKind.OTHER)
async def release_knowledge(scope: PlayerScope, command: KnowledgeTarget) -> Effect:
    row = await region_control.release_knowledge(scope.session, command.polity_id, command.region_id)
    polity, region = await _name(scope, row.polity_entity_id), await _name(scope, row.region_entity_id)
    return Effect(f"What {polity} knows of {region} follows its explorers again.", target_node_id=row.region_entity_id)


@player_action("region:river_redirect", ActionKind.OTHER)
async def redirect_river(scope: PlayerScope, command: RedirectRiver) -> Effect:
    moved = await region_control.redirect_river(scope.session, scope.rules, command.from_region_id, command.to_region_id, epoch=await scope.epoch())
    source, target = await _name(scope, command.from_region_id), await _name(scope, command.to_region_id)
    river = moved.river.value.replace("_", " ")
    tail = f"; {several(moved.dried, 'place', 'places')} went dry and {moved.watered} found water" if moved.dried or moved.watered else ""
    return Effect(f"The {river} of {source} now runs through {target}{tail}.", target_node_id=command.to_region_id)
