from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import SOCIALITIES
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityTraitRow
from aerona.domain.enums.ecology import Diet, Sociality
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.ecology.living_ways import keep_living_ways
from aerona.engine.ecology.profiles import sociality_of
from aerona.engine.ecology.ranges import nesting_gain
from aerona.engine.ecology.w52_life import SOCIAL_FIXUP, backfill_social
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, land, range_of, told


def test_eight_social_forms_and_every_one_can_arise_from_a_kind_s_nature() -> None:
    assert len(SOCIALITIES) == len(Sociality) == 8
    reached = {
        sociality_of(Diet.HERBIVORE, {CreatureTrait.HIVE_MIND}, None),
        sociality_of(Diet.CARNIVORE, {CreatureTrait.PACK_HUNTER}, None),
        sociality_of(Diet.HERBIVORE, {CreatureTrait.SWARM_BREEDER}, None),
        sociality_of(Diet.PISCIVORE, {CreatureTrait.FLYING}, None),
        sociality_of(Diet.HERBIVORE, set(), None),
        sociality_of(Diet.CARNIVORE, set(), None),
        sociality_of(Diet.HERBIVORE, {CreatureTrait.LONG_LIVED}, None),
        sociality_of(Diet.CARNIVORE, {CreatureTrait.FLYING}, None),
    }
    assert reached == set(Sociality)


async def test_a_swarm_strips_the_harvest_and_moves_into_the_next_land(session: AsyncSession, world: CoreWorld) -> None:
    here, next_land = world.regions[0], world.regions[1]
    ground = await land(session, world, here, harvest_pct=100)
    swarm = await kind(session, world, "Cloud Locust", here, 80, sociality=Sociality.SWARM)
    tally = await keep_living_ways(await manual_context(session, "ecology", tuned_rules(species_forms={"swarm_crop_harm": 50, "swarm_move": 1})), set())
    assert ground.harvest_pct == 60 and tally.swarmed == 1
    assert (await session.get(SpeciesRangeRow, (swarm.id, next_land.id))) is not None
    assert await told(session, "life.swarm_struck")


async def test_a_large_colony_holds_and_nesting_grounds_give_a_richer_catch(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    colony = await kind(session, world, "Cliff Gannet", region, 60, sociality=Sociality.COLONY)
    loner = await kind(session, world, "Lone Heron", region, 60, sociality=Sociality.SOLITARY)
    ctx = await manual_context(session, "ecology", tuned_rules(species_forms={"colony_harvest_pct": 40}))
    await keep_living_ways(ctx, set())
    assert (await range_of(session, colony, region)).abundance == 60
    assert await nesting_gain(ctx, colony.id) == 1.4 and await nesting_gain(ctx, loner.id) == 1.0


async def test_swarm_breeders_of_the_old_record_become_swarms_once(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    breeder = await kind(session, world, "Old Locust", region, 40, sociality=Sociality.HERD)
    held_kind = await kind(session, world, "Held Locust", region, 40, sociality=Sociality.HERD, locked=["sociality"])
    session.add_all(
        [EntityTraitRow(entity_id=breeder.id, trait=CreatureTrait.SWARM_BREEDER), EntityTraitRow(entity_id=held_kind.id, trait=CreatureTrait.SWARM_BREEDER)]
    )
    await session.flush()
    ctx = await manual_context(session, "ecology")
    assert await backfill_social(ctx) == 1
    first, second = await session.get(SpeciesProfileRow, breeder.id), await session.get(SpeciesProfileRow, held_kind.id)
    assert first is not None and first.sociality is Sociality.SWARM
    assert second is not None and second.sociality is Sociality.HERD
    assert await session.get(AppliedFixupRow, SOCIAL_FIXUP) is not None and await backfill_social(ctx) == 0
