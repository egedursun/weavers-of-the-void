from typing import Annotated

from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import BeastTemper, Diet, FoodLink, SizeClass, Sociality, SpeciesUse, YieldProduct
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats, SpeciesStats
from aerona.engine.ecology import control
from aerona.engine.ecology.profiles import SpeciesSpec
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | str | bool | dict[str, int] | list[int] | None]
Percent = Annotated[int, Field(ge=0, le=100)]
LINK_WORDS = {FoodLink.PINNED: "now hunts", FoodLink.BARRED: "may never hunt", FoodLink.DERIVED: "hunts as nature wills"}


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
    world_material_id: int | None = None
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
    release: bool = False


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


class CreateSpecies(Command):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    description: Annotated[str, Field(max_length=SHORT_TEXT_MAX_LENGTH)] = ""
    region_id: int
    body_plan: BodyPlan
    size_class: SizeClass
    diet: Diet
    sociality: Sociality | None = None
    nocturnal: bool | None = None
    migratory: bool | None = None
    products: list[YieldProduct] = Field(default_factory=list)
    traits: list[CreatureTrait] = Field(default_factory=list)
    hp: Annotated[int, Field(ge=1)] | None = None
    strength: Percent | None = None
    agility: Percent | None = None
    intelligence: Percent | None = None
    danger: Percent | None = None
    might: Percent | None = None
    abundance: Percent | None = None
    power: Annotated[int, Field(ge=1, le=10)] = 2


class CreateBeast(Command):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    description: Annotated[str, Field(max_length=SHORT_TEXT_MAX_LENGTH)] = ""
    species_id: int | None = None
    lair_id: int | None = None
    world_id: int | None = None
    size_class: SizeClass | None = None
    temper: BeastTemper | None = None
    hp: Annotated[int, Field(ge=1)] | None = None
    strength: Percent | None = None
    agility: Percent | None = None
    danger: Percent | None = None
    cunning: Percent | None = None
    renown: Percent | None = None
    terror: Percent | None = None
    endurance: Percent | None = None
    perception: Percent | None = None
    willpower: Percent | None = None
    intelligence: Percent | None = None
    power: Annotated[int, Field(ge=1, le=10)] = 3


class Slay(Command):
    beast_id: int
    slayer_id: int | None = None


class HerdTarget(Command):
    community_id: int
    species_id: int


class Prey(Command):
    hunter_id: int
    prey_id: int
    link: FoodLink


class Totem(Command):
    people_id: int
    species_id: int | None = None


class Treasure(Command):
    beast_id: int
    item_id: int
    into_hoard: bool = True
    receiver_id: int | None = None


class NewUseKind(Command):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    base_use: SpeciesUse
    output_pct: Annotated[int, Field(ge=0, le=1000)] = 100
    description: Annotated[str, Field(max_length=SHORT_TEXT_MAX_LENGTH)] | None = None


class EditUseKind(Command):
    kind_id: int
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class UseKindTarget(Command):
    kind_id: int


class CustomUse(Command):
    species_id: int
    kind_id: int
    held: bool = True


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
    row = await control.set_yield(
        ctx,
        command.species_id,
        command.product,
        commodity=command.commodity,
        material=command.material,
        rate=command.rate,
        world_material_id=command.world_material_id,
    )
    return Effect(f"It yields {row.rate} {row.product}." if row is not None else f"It yields no {command.product}.", command.species_id)


@player_action("species:use", ActionKind.EDIT_RECORD)
async def set_use(scope: PlayerScope, command: Use) -> Effect:
    row = await control.set_use(await scope.context("species_use"), command.species_id, command.use, held=command.held)
    label = command.use.value.replace("_", " ")
    return Effect(f"It serves for {label}." if row is not None else f"It no longer serves for {label}.", command.species_id)


@player_action("species:host", ActionKind.EDIT_RECORD)
async def set_host(scope: PlayerScope, command: Host) -> Effect:
    row = await control.set_host(
        await scope.context("species_host"), command.species_id, command.disease_id, carried=command.carried, immune=command.immune, release=command.release
    )
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


@player_action("species:create", ActionKind.CREATE_ENTITY)
async def create_species(scope: PlayerScope, command: CreateSpecies) -> Effect:
    draft = control.NewSpecies(
        name=command.name.strip(),
        description=command.description.strip() or f"A kind of {command.size_class.value} {command.diet.value} the Creator set loose.",
        region_id=command.region_id,
        spec=SpeciesSpec(
            body_plan=command.body_plan,
            size_class=command.size_class,
            diet=command.diet,
            sociality=command.sociality,
            nocturnal=command.nocturnal,
            migratory=command.migratory,
            products=tuple(dict.fromkeys(command.products)),
        ),
        stats=SpeciesStats(
            hp=command.hp,
            strength=command.strength,
            agility=command.agility,
            intelligence=command.intelligence,
            danger=command.danger,
            might=command.might,
            abundance=command.abundance,
        ),
        power=command.power,
        traits=tuple(command.traits),
        abundance=command.abundance,
    )
    species = await control.create_species(await scope.context("species_create"), draft)
    return Effect(f"{species.name} walks the land.", species.id, created_ids=(species.id,))


@player_action("beast:create", ActionKind.CREATE_ENTITY)
async def create_beast(scope: PlayerScope, command: CreateBeast) -> Effect:
    abilities = {key: value for key in ("endurance", "perception", "willpower", "intelligence") if (value := getattr(command, key)) is not None}
    draft = control.NewBeast(
        name=command.name.strip(),
        description=command.description.strip() or "A beast the Creator called forth.",
        stats=BeastStats(
            hp=command.hp,
            strength=command.strength,
            agility=command.agility,
            danger=command.danger,
            cunning=command.cunning,
            renown=command.renown,
            terror=command.terror,
        ),
        species_id=command.species_id,
        lair_id=command.lair_id,
        size_class=command.size_class,
        temper=command.temper,
        power=command.power,
        abilities=abilities,
    )
    beast = await control.create_beast(await scope.context("beast_create"), draft, world_id=command.world_id)
    return Effect(f"{beast.name} rises.", beast.id, created_ids=(beast.id,))


@player_action("beast:slay", ActionKind.DESTROY)
async def slay(scope: PlayerScope, command: Slay) -> Effect:
    told = await control.slay_beast(await scope.context("beast_slay"), command.beast_id, command.slayer_id)
    return Effect(f"{told}.", command.beast_id)


@player_action("herd:drop", ActionKind.DESTROY)
async def drop_herd(scope: PlayerScope, command: HerdTarget) -> Effect:
    await control.drop_herd(await scope.context("herd_drop"), command.community_id, command.species_id)
    return Effect("The herd is scattered.", command.community_id)


@player_action("species:prey", ActionKind.EDIT_RECORD)
async def set_prey(scope: PlayerScope, command: Prey) -> Effect:
    await control.set_prey(await scope.context("species_prey"), command.hunter_id, command.prey_id, command.link)
    return Effect(f"It {LINK_WORDS[command.link]} that kind.", command.hunter_id)


@player_action("people:totem", ActionKind.EDIT_RECORD)
async def set_totem(scope: PlayerScope, command: Totem) -> Effect:
    tradition = await control.set_totem(await scope.context("people_totem"), command.people_id, command.species_id)
    created = (tradition.id,) if tradition is not None else ()
    return Effect("The people take a new emblem." if tradition is not None else "The people set their emblem aside.", command.people_id, created_ids=created)


@player_action("beast:treasure", ActionKind.EDIT_RECORD)
async def move_treasure(scope: PlayerScope, command: Treasure) -> Effect:
    item = await control.move_treasure(
        await scope.context("beast_treasure"), command.beast_id, command.item_id, into_hoard=command.into_hoard, receiver_id=command.receiver_id
    )
    return Effect(f"{item.name} {'lies in the hoard' if command.into_hoard else 'leaves the hoard'}.", command.beast_id)


@player_action("use_kind:create", ActionKind.CREATE_ENTITY)
async def create_use_kind(scope: PlayerScope, command: NewUseKind) -> Effect:
    row = await control.create_use_kind(await scope.context("use_kind_create"), command.name, command.base_use, command.output_pct, command.description)
    return Effect(f"A new way of keeping beasts: {row.name}.", values={"kind_id": row.id})


@player_action("use_kind:edit", ActionKind.EDIT_RECORD)
async def edit_use_kind(scope: PlayerScope, command: EditUseKind) -> Effect:
    row = await control.edit_use_kind(await scope.context("use_kind_edit"), command.kind_id, command.values, release=command.release)
    return Effect(f"{row.name} is reshaped.", values={"kind_id": row.id})


@player_action("use_kind:drop", ActionKind.DESTROY)
async def drop_use_kind(scope: PlayerScope, command: UseKindTarget) -> Effect:
    await control.drop_use_kind(await scope.context("use_kind_drop"), command.kind_id)
    return Effect("That way of keeping beasts is forgotten.", values={"kind_id": command.kind_id})


@player_action("species:custom_use", ActionKind.EDIT_RECORD)
async def set_custom_use(scope: PlayerScope, command: CustomUse) -> Effect:
    row = await control.set_custom_use(await scope.context("species_custom_use"), command.species_id, command.kind_id, held=command.held)
    return Effect("It is kept that way." if row is not None else "It is no longer kept that way.", command.species_id)
