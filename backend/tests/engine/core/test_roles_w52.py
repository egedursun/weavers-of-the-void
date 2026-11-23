from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import HerdRow, SpeciesUseRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.domain.enums.ecology import AnimalRole, DomesticationStage, HerdTraining
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.gathering import GatheringKind, GatheringStatus
from aerona.engine.communication.post import send
from aerona.engine.crafts.catch import trap_factors
from aerona.engine.ecology.living_ways import animal_roles
from aerona.engine.ecology.w52_life import backfill_hunting_role
from aerona.engine.economy.stocks import holdings
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules
from tests.engine.core.living_kinds import kind, told


async def keep(session: AsyncSession, town_id: int, species_id: int, role: AnimalRole, head: int = 10) -> None:
    session.add(SpeciesUseRow(species_entity_id=species_id, use=role))
    session.add(HerdRow(community_entity_id=town_id, species_entity_id=species_id, head=head, stage=DomesticationStage.DOMESTICATED, locked=[]))
    await session.flush()


async def test_medicine_animals_yield_remedies_and_sport_animals_raise_a_gathering(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    town = await settlement(session, "Bowl Town", world, region)
    leech = await kind(session, world, "Healing Leech", region, 30)
    hound = await kind(session, world, "Racing Hound", region, 30)
    await keep(session, town.id, leech.id, AnimalRole.MEDICINE)
    await keep(session, town.id, hound.id, AnimalRole.SPORT)
    ctx = await manual_context(session, "ecology", tuned_rules(species_roles={"medicine_yield": 7, "sport_draw": 15}))
    gathering = GatheringRow(
        host_node_id=town.id, kind=GatheringKind.FEAST, status=GatheringStatus.HELD, place_entity_id=town.id, epoch=ctx.epoch, prestige=20, locked=[]
    )
    session.add(gathering)
    await session.flush()
    await animal_roles(ctx)
    await session.flush()
    assert (await holdings(session, town.id)).get(CommodityKind.MEDICINE, 0) == 7
    assert gathering.prestige == 35 and await told(session, "life.contest_held")


async def test_hunting_animals_raise_the_catch_of_grounds_that_need_them(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    town = await settlement(session, "Kennel Town", world, region)
    game = await kind(session, world, "Field Hare", region, 60)
    hound = await kind(session, world, "Tracking Hound", region, 20)
    session.add(
        CatchGroundRow(
            source_entity_id=game.id, region_entity_id=region.id, ground=CatchGround.GAME_HUNT, gear=Gear.HUNTING_ANIMALS, first_stock=100, stock=100, locked=[]
        )
    )
    await session.flush()
    rules = tuned_rules(species_roles={"hunting_catch_pct": 50})
    without = (await trap_factors(session, rules))[(game.id, region.id)]
    await keep(session, town.id, hound.id, AnimalRole.HUNTING)
    with_hounds = (await trap_factors(session, rules))[(game.id, region.id)]
    assert without == 0.0 and with_hounds > 0


async def test_kinds_trained_to_hunt_in_the_old_record_gain_the_hunting_role_once(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    town = await settlement(session, "Old Kennels", world, region)
    hound = await kind(session, world, "Old Hound", region, 20)
    session.add(
        HerdRow(
            community_entity_id=town.id, species_entity_id=hound.id, head=5, stage=DomesticationStage.DOMESTICATED, training=HerdTraining.HUNTING, locked=[]
        )
    )
    await session.flush()
    ctx = await manual_context(session, "ecology")
    assert await backfill_hunting_role(ctx) == 1
    assert await session.get(SpeciesUseRow, (hound.id, AnimalRole.HUNTING)) is not None
    assert await backfill_hunting_role(ctx) == 0


async def test_messenger_animals_speed_a_letter_and_may_lose_it_on_the_way(session: AsyncSession, world: CoreWorld) -> None:
    region, far = world.regions[0], world.regions[-1]
    home = await settlement(session, "Loft Town", world, region)
    other = await settlement(session, "Far Town", world, far)
    bird = await kind(session, world, "Carrier Kind", region, 30)
    plain_ctx = await manual_context(session, "post", tuned_rules(species_roles={"messenger_intercept_pct": 0}))
    slow = await send(plain_ctx, home.id, other.id, DispatchContent.PROPOSAL, Medium.LETTER)
    await keep(session, home.id, bird.id, AnimalRole.MESSENGER)
    fast = await send(plain_ctx, home.id, other.id, DispatchContent.PROPOSAL, Medium.LETTER)
    assert slow is not None and fast is not None and slow.arrival_epoch is not None and fast.arrival_epoch is not None
    assert fast.arrival_epoch <= slow.arrival_epoch and fast.state is DispatchState.UNDER_WAY
    caught_ctx = await manual_context(session, "post", tuned_rules(species_roles={"messenger_intercept_pct": 100}))
    caught = await send(caught_ctx, home.id, other.id, DispatchContent.PROPOSAL, Medium.LETTER)
    assert caught is not None and caught.state is DispatchState.INTERCEPTED
    assert await told(session, "life.message_carried")
