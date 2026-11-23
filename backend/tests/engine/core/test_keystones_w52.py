from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import CatchGroundRow
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.evolution import KeystoneRole
from aerona.engine.ecology.keystones import dispersal, hold_reef_fish, reef_shield, unchecked_grazers
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, range_of

RULES = Rules()


def test_seven_keystone_roles_and_losing_a_disperser_slows_the_forest_while_a_reef_breaks_waves() -> None:
    assert len(KeystoneRole) == 7
    assert dispersal(RULES, None) == 1.0 == dispersal(RULES, {KeystoneRole.SEED_DISPERSER: 60})
    assert dispersal(RULES, {KeystoneRole.SEED_DISPERSER: 0}) == 1 - RULES.keystones.disperser_succession_pct / 100
    assert reef_shield(RULES, {KeystoneRole.REEF_BUILDER: 100}) == 1 - RULES.keystones.reef_wave_cut_pct / 100
    assert reef_shield(RULES, None) == 1.0


async def test_without_a_regulator_grazers_multiply(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    deer = await kind(session, world, "Bramble Deer", region, 50, diet=Diet.HERBIVORE)
    wolf = await kind(session, world, "Grey Stalker", region, 50, diet=Diet.CARNIVORE)
    await unchecked_grazers(await manual_context(session, "keystones", tuned_rules(keystones={"regulator_grazer_rise_pct": 100})), region.id)
    assert (await range_of(session, deer, region)).abundance == 55
    assert (await range_of(session, wolf, region)).abundance == 50


async def test_a_living_reef_keeps_its_fish_and_a_dead_one_lets_them_go(session: AsyncSession, world: CoreWorld) -> None:
    reefed, bare = world.regions[0], world.regions[1]
    fish = await kind(session, world, "Reef Snapper", reefed, 50)
    stray = await kind(session, world, "Bare Snapper", bare, 50)
    session.add(
        CatchGroundRow(
            source_entity_id=fish.id, region_entity_id=reefed.id, ground=CatchGround.SHORE_GATHERING, gear=Gear.NETS, first_stock=100, stock=5, locked=[]
        )
    )
    lost = CatchGroundRow(
        source_entity_id=stray.id, region_entity_id=bare.id, ground=CatchGround.SHORE_GATHERING, gear=Gear.NETS, first_stock=100, stock=50, locked=[]
    )
    session.add(lost)
    await session.flush()
    ctx = await manual_context(session, "keystones", tuned_rules(keystones={"reef_fish_pct": 40}))
    await hold_reef_fish(ctx, reefed.id, 100)
    await hold_reef_fish(ctx, bare.id, 0)
    kept = await session.get(CatchGroundRow, (fish.id, reefed.id))
    assert kept is not None and kept.stock == 40
    assert lost.stock == 46
