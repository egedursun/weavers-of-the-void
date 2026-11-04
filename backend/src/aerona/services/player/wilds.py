from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.ecology import SpeciesUse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.engine.ecology import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | str | bool | dict[str, int] | list[int] | None]


class EditSpecies(Command):
    species_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class EditRange(Command):
    species_id: int
    region_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class MoveRange(Command):
    species_id: int
    source_id: int
    target_id: int


class DropRange(Command):
    species_id: int
    region_id: int


class SpeciesYield(Command):
    species_id: int
    product: str
    commodity: CommodityKind | None = None
    material: MaterialKind | None = None
    rate: int


class Use(Command):
    species_id: int
    use: SpeciesUse
    held: bool = True


class Host(Command):
    species_id: int
    disease_id: int
    carried: bool = True
    immune: bool = False


class Sacred(Command):
    species_id: int
    son_id: int | None = None


class Domesticate(Command):
    species_id: int
    community_id: int


class EditHerd(Command):
    community_id: int
    species_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class EditBeast(Command):
    beast_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class Rouse(Command):
    beast_id: int
    awake: bool


class Bind(Command):
    beast_id: int
    node_id: int | None = None
    tamed: bool = False


class Lair(Command):
    beast_id: int
    place_id: int


class Spawn(Command):
    species_id: int


@player_action("species:edit", ActionKind.EDIT_RECORD)
async def edit_species(scope: PlayerScope, command: EditSpecies) -> Effect:
    await control.edit_species(await scope.context("species_edit"), command.species_id, command.values, release=command.release)
    return Effect("The kind is reshaped.", command.species_id)


@player_action("species:range", ActionKind.EDIT_RECORD)
async def edit_range(scope: PlayerScope, command: EditRange) -> Effect:
    row = await control.edit_range(await scope.context("species_range"), command.species_id, command.region_id, command.values, release=command.release)
    return Effect(f"It ranges there at {row.abundance}.", command.species_id)


@player_action("species:move_range", ActionKind.OTHER)
async def move_range(scope: PlayerScope, command: MoveRange) -> Effect:
    row = await control.move_range(await scope.context("species_move"), command.species_id, command.source_id, command.target_id)
    return Effect(f"The herds move; there they number {row.abundance}.", command.species_id)


@player_action("species:drop_range", ActionKind.OTHER)
async def drop_range(scope: PlayerScope, command: DropRange) -> Effect:
    await control.drop_range(await scope.context("species_drop"), command.species_id, command.region_id)
    return Effect("It is gone from that land.", command.species_id)


@player_action("species:yield", ActionKind.EDIT_RECORD)
async def set_yield(scope: PlayerScope, command: SpeciesYield) -> Effect:
    ctx = await scope.context("species_yield")
    row = await control.set_yield(ctx, command.species_id, command.product, commodity=command.commodity, material=command.material, rate=command.rate)
    return Effect(f"It yields {row.rate} {row.product}." if row is not None else f"It yields no {command.product}.", command.species_id)


@player_action("species:use", ActionKind.EDIT_RECORD)
async def set_use(scope: PlayerScope, command: Use) -> Effect:
    row = await control.set_use(await scope.context("species_use"), command.species_id, command.use, held=command.held)
    label = command.use.value.replace("_", " ")
    return Effect(f"It serves for {label}." if row is not None else f"It no longer serves for {label}.", command.species_id)


@player_action("species:host", ActionKind.EDIT_RECORD)
async def set_host(scope: PlayerScope, command: Host) -> Effect:
    row = await control.set_host(await scope.context("species_host"), command.species_id, command.disease_id, carried=command.carried, immune=command.immune)
    return Effect("It carries the sickness." if row is not None and not row.immune else "It is free of that sickness.", command.species_id)


@player_action("species:sacred", ActionKind.EDIT_RECORD)
async def make_sacred(scope: PlayerScope, command: Sacred) -> Effect:
    await control.make_sacred(await scope.context("species_sacred"), command.species_id, command.son_id)
    return Effect("The kind is holy." if command.son_id is not None else "The kind is no longer holy.", command.species_id)


@player_action("species:domesticate", ActionKind.OTHER)
async def domesticate(scope: PlayerScope, command: Domesticate) -> Effect:
    child = await control.domesticate_now(await scope.context("species_domesticate"), command.species_id, command.community_id)
    return Effect(f"{child.name} is bred.", child.id, created_ids=(child.id,))


@player_action("herd:edit", ActionKind.EDIT_RECORD)
async def edit_herd(scope: PlayerScope, command: EditHerd) -> Effect:
    row = await control.edit_herd(await scope.context("herd_edit"), command.community_id, command.species_id, command.values, release=command.release)
    return Effect(f"The herd numbers {row.head}.", command.community_id)


@player_action("beast:edit", ActionKind.EDIT_RECORD)
async def edit_beast(scope: PlayerScope, command: EditBeast) -> Effect:
    await control.edit_beast(await scope.context("beast_edit"), command.beast_id, command.values, release=command.release)
    return Effect("The beast is changed.", command.beast_id)


@player_action("beast:rouse", ActionKind.OTHER)
async def rouse(scope: PlayerScope, command: Rouse) -> Effect:
    await control.rouse(await scope.context("beast_rouse"), command.beast_id, awake=command.awake)
    return Effect("The beast wakes, hungry." if command.awake else "The beast sleeps.", command.beast_id)


@player_action("beast:bind", ActionKind.OTHER)
async def bind(scope: PlayerScope, command: Bind) -> Effect:
    await control.bind_beast(await scope.context("beast_bind"), command.beast_id, command.node_id, tamed=command.tamed)
    return Effect("The beast is bound." if command.node_id is not None else "The beast is loosed.", command.beast_id)


@player_action("beast:lair", ActionKind.OTHER)
async def shift_lair(scope: PlayerScope, command: Lair) -> Effect:
    await control.shift_lair(await scope.context("beast_lair"), command.beast_id, command.place_id)
    return Effect("The beast makes a new lair.", command.beast_id)


@player_action("beast:spawn", ActionKind.OTHER)
async def spawn(scope: PlayerScope, command: Spawn) -> Effect:
    beast = await control.spawn_beast(await scope.context("beast_spawn"), command.species_id)
    return Effect(f"{beast.name} rises.", beast.id, created_ids=(beast.id,))
