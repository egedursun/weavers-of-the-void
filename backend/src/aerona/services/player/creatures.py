from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.phases.creatures import (
    cross_species,
    cull_species,
    force_mutation,
    force_people_split,
    introduce_species,
    order_feeding,
    place_megafauna_trail,
    spare_prey,
)
from aerona.engine.phases.life_seed import seed_life
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

CULL_REASON = "culled by the Creator"


class Feeding(Command):
    species_id: int
    soul_id: int | None = None


class SpeciesTarget(Command):
    species_id: int


class PeopleTarget(Command):
    people_id: int


class Chimera(Command):
    first_id: int
    second_id: int
    weaver_id: int | None = None


class Cull(Command):
    species_id: int
    reason: str = ""


class LifeSeed(Command):
    world_id: int
    people: bool = False


class Introduction(Command):
    species_id: int
    region_id: int


@player_action("species:feed", ActionKind.ORDER_FEEDING)
async def feed(scope: PlayerScope, command: Feeding) -> Effect:
    soul = await order_feeding(scope.session, scope.rules, command.species_id, command.soul_id)
    return Effect(f"The soul of {soul.name} was swallowed.", command.species_id, values={"soul_id": soul.id})


@player_action("species:mutate", ActionKind.MUTATE_SPECIES)
async def mutate(scope: PlayerScope, command: SpeciesTarget) -> Effect:
    mutated = await force_mutation(scope.session, scope.rules, command.species_id)
    created = (mutated.id,) if mutated.id != command.species_id else ()
    return Effect(f"{mutated.name} changed.", mutated.id, created_ids=created)


@player_action("people:split", ActionKind.SPLIT_PEOPLE)
async def split(scope: PlayerScope, command: PeopleTarget) -> Effect:
    offshoot = await force_people_split(scope.session, scope.rules, command.people_id)
    return Effect(f"{offshoot.name} split away.", offshoot.id, created_ids=(offshoot.id,))


@player_action("species:chimera", ActionKind.WEAVE_CHIMERA)
async def chimera(scope: PlayerScope, command: Chimera) -> Effect:
    woven = await cross_species(scope.session, scope.rules, command.first_id, command.second_id, command.weaver_id)
    return Effect(f"{woven.name} was made.", woven.id, created_ids=(woven.id,))


@player_action("species:trail", ActionKind.MEGAFAUNA_TRAIL)
async def trail(scope: PlayerScope, command: SpeciesTarget) -> Effect:
    path = await place_megafauna_trail(scope.session, scope.rules, command.species_id)
    if path is None:
        raise ValidationFailedError("This species leaves no trail across the land.")
    return Effect(f"{path.name} marks its passage.", path.id, created_ids=(path.id,))


@player_action("species:cull", ActionKind.DESTROY)
async def cull(scope: PlayerScope, command: Cull) -> Effect:
    culled = await cull_species(scope.session, scope.rules, command.species_id, command.reason.strip() or CULL_REASON)
    return Effect(f"{culled.name} was culled.", culled.id)


@player_action("species:spare_prey", ActionKind.SPARE_PREY)
async def spare(scope: PlayerScope, command: SpeciesTarget) -> Effect:
    species = guards.of_types(await guards.canon_entity(scope.session, command.species_id), (EntityType.SPECIES,), "Only a species can be spared.")
    closed = await spare_prey(scope.session, species.id, await scope.epoch())
    if not closed:
        raise ValidationFailedError(f"Nothing hunts {species.name}.")
    return Effect(f"{several(closed, 'hunter', 'hunters')} of {species.name} were turned away.", species.id, values={"hunts_closed": closed})


@player_action("species:introduce", ActionKind.INTRODUCE_SPECIES)
async def introduce(scope: PlayerScope, command: Introduction) -> Effect:
    carried = await introduce_species(scope.session, scope.rules, command.species_id, command.region_id)
    return Effect(f"{carried.name} was carried to a new land.", carried.id, created_ids=(carried.id,))


@player_action("species:seed", ActionKind.CREATE_ENTITY)
async def seed(scope: PlayerScope, command: LifeSeed) -> Effect:
    born = await seed_life(await scope.context("seed_life"), command.world_id, command.people)
    return Effect(f"{born.name} took root by the Creator's hand.", born.id, created_ids=(born.id,))
