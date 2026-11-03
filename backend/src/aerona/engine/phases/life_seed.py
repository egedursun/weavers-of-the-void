from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import PeopleStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import stat

NATIVE_PEOPLE_SUBTYPE = "native people"
NATIVE_SPECIES_SUBTYPE = "native creature"


def fertility_of(ctx: TickContext, region: EntityRow) -> int:
    value = stat(region, "fertility")
    return value if value is not None else ctx.rules.society.default_stat


async def fertile_regions(ctx: TickContext, world: WorldRow) -> list[EntityRow]:
    minimum = ctx.rules.deep_life.life_min_fertility
    regions = [region for region in await canon(ctx.session, [EntityType.REGION], world.id) if not region.is_water and fertility_of(ctx, region) >= minimum]
    return sorted(regions, key=lambda region: (-fertility_of(ctx, region), region.id))


async def empty_for(ctx: TickContext, world: WorldRow) -> int:
    last_people: int | None = await ctx.session.scalar(
        select(func.max(EntityRow.end_epoch)).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.PEOPLE)
    )
    since = last_people if last_people is not None else world.created_epoch
    return max(0, ctx.epoch - since)


async def native_people(ctx: TickContext, world: WorldRow, region: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(f"native_people.{world.id}")

    def rolled() -> int:
        return clamp_int(life.native_people_stat + rng.die(life.native_people_stat_die), 0, PERCENT)

    people = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=f"Natives of {region.name}",
            body=(
                f"In {world.name}, on the lands of {region.name}, a people no one created appeared: "
                "they were born of the earth itself, of the long patience of water and light."
            ),
            stats=PeopleStats(
                population=life.native_people_population + rng.die(life.native_people_population_die),
                martiality=rolled(),
                magic=rolled(),
                craft=rolled(),
                piety=clamp_int(life.native_people_piety + rng.die(life.native_people_piety_die), 0, PERCENT),
            ),
            power=life.native_people_power,
            location_id=region.id,
            world_id=world.id,
            subtype=NATIVE_PEOPLE_SUBTYPE,
            flags=(EntityFlag.NATIVE,),
        ),
    )
    await note(ctx, f"A people appeared of its own accord in {world.name} ({region.name}).", key="life.native_people", ids=[people.id, region.id])
    await bind_language_and_faith(ctx, people)
    ctx.count("native_peoples")
    return people


async def native_species(ctx: TickContext, world: WorldRow, region: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(f"native_species.{world.id}")
    species = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SPECIES,
            name=f"Creatures of {region.name}",
            body=f"The first species stirred on the lands of {region.name} in {world.name}.",
            stats=SpeciesStats(
                hp=life.native_species_hp + rng.die(life.native_species_hp_die),
                strength=clamp_int(life.native_species_strength + rng.die(life.native_species_strength_die), 0, PERCENT),
                agility=clamp_int(life.native_species_agility + rng.die(life.native_species_agility_die), 0, PERCENT),
                intelligence=clamp_int(life.native_species_intelligence + rng.die(life.native_species_intelligence_die), 0, PERCENT),
                danger=clamp_int(life.native_species_danger + rng.die(life.native_species_danger_die), 0, PERCENT),
            ),
            power=life.native_species_power,
            location_id=region.id,
            world_id=world.id,
            subtype=NATIVE_SPECIES_SUBTYPE,
            flags=(EntityFlag.NATIVE,),
        ),
    )
    await note(ctx, f"The first species appeared in {world.name}.", key="life.native_species", ids=[species.id, region.id])
    ctx.count("native_species")
    return species


@reads("region.fertility")
@reads("region.fertility")
async def life_seed(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        regions = await fertile_regions(ctx, world)
        if not regions:
            continue
        top = regions[: rules.deep_life.life_region_pick]
        has_people = bool(await canon(ctx.session, [EntityType.PEOPLE], world.id))
        guarantee = rules.empty_world.native_guarantee_epochs
        if not has_people and (rng.chance(rules.deep_world.native_people_chance) or (guarantee > 0 and await empty_for(ctx, world) >= guarantee)):
            await native_people(ctx, world, rng.pick(top))
        if not await canon(ctx.session, [EntityType.SPECIES], world.id) and rng.chance(rules.deep_world.native_species_chance):
            await native_species(ctx, world, rng.pick(top))


async def seed_life(ctx: TickContext, world_id: int, people: bool) -> EntityRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    regions = await fertile_regions(ctx, world) or [region for region in await canon(ctx.session, [EntityType.REGION], world.id) if not region.is_water]
    if not regions:
        raise NotFoundError(f"{world.name} has no land where life could take hold.")
    region = ctx.rng(f"seed_life.{world.id}").pick(regions[: ctx.rules.deep_life.life_region_pick])
    return await native_people(ctx, world, region) if people else await native_species(ctx, world, region)


PHASES = (Phase("life_seed", life_seed),)
