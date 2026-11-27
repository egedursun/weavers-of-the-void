import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.settle_modes import SETTLE_MODES
from aerona.catalog.units import UNITS
from aerona.catalog.war_grounds import WAR_GROUNDS
from aerona.catalog.world_views import WORLD_VIEWS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand, TerrainKind
from aerona.domain.enums.military import UnitFamily
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_view import SettleMode, WarTerrain
from aerona.engine.context import TickContext
from aerona.engine.environment.battleground import war_ground
from aerona.engine.military.battle import Field, Stack, battle_width, fights_here
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from aerona.engine.settlement.control import edit_settlement
from aerona.engine.settlement.modes import ModeTally, choose_mode, defence_pct, exposure_pct, keep_modes
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, settlement, tuned_rules

RULES = Rules()


async def at(session: AsyncSession, epoch: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "settle_modes", rules=tuned_rules())


async def folk_of_body(session: AsyncSession, world: CoreWorld, plan: BodyPlan) -> None:
    session.add(
        PeopleBiologyRow(
            people_entity_id=world.people.id,
            maturity_years=15,
            adult_years=40,
            elder_years=60,
            fertility_pct=100,
            acclimatised=TemperatureBand.TEMPERATE,
            staple=CommodityKind.GRAIN,
            body_plan=plan,
            traits=[],
            locked=[],
        )
    )
    await session.flush()


async def ground(session: AsyncSession, world: CoreWorld, terrain: TerrainKind, cover: int) -> None:
    await environment_survey(await manual_context(session, "environment", rules=tuned_rules()))
    region = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert region is not None
    region.dominant_terrain = terrain
    region.forest_cover = cover
    await session.flush()


async def town_of_folk(session: AsyncSession, world: CoreWorld, name: str = "Holdfast") -> EntityRow:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    return town


@pytest.mark.parametrize(
    "case",
    [
        (BodyPlan.AQUATIC, TerrainKind.SEA, 0, SettleMode.SUBMERGED),
        (BodyPlan.AQUATIC, TerrainKind.PLAIN, 0, SettleMode.GROUND),
        (BodyPlan.INSECTOID, TerrainKind.PLAIN, 0, SettleMode.BURROW),
        (BodyPlan.INSECTOID, TerrainKind.MARSH, 0, SettleMode.STILT),
        (BodyPlan.ARBOREAL, TerrainKind.JUNGLE, 80, SettleMode.CANOPY),
        (BodyPlan.ARBOREAL, TerrainKind.JUNGLE, 10, SettleMode.GROUND),
        (BodyPlan.HUMANOID, TerrainKind.FOREST, 90, SettleMode.GROUND),
    ],
)
async def test_a_settlement_takes_the_way_of_settling_its_bodies_and_ground_allow(
    session: AsyncSession, world: CoreWorld, case: tuple[BodyPlan, TerrainKind, int, SettleMode]
) -> None:
    plan, terrain, cover, expected = case
    await folk_of_body(session, world, plan)
    await ground(session, world, terrain, cover)
    town = await town_of_folk(session, world)
    assert await choose_mode(session, RULES, town) is expected


def test_every_way_of_settling_and_ground_of_war_has_its_rules_and_the_new_worlds_their_grounds() -> None:
    for mode in SettleMode:
        assert SETTLE_MODES[mode].label and defence_pct(RULES, mode) > 0 and exposure_pct(RULES, mode) > 0
    assert defence_pct(RULES, SettleMode.SUBMERGED) > defence_pct(RULES, SettleMode.GROUND) > 0
    assert exposure_pct(RULES, SettleMode.BURROW) < exposure_pct(RULES, SettleMode.GROUND) < exposure_pct(RULES, SettleMode.CANOPY)
    assert WORLD_VIEWS[WorldType.VOID_POCKET].war is WarTerrain.SPACE
    assert WORLD_VIEWS[WorldType.CHTHONIAN].war is WarTerrain.UNDERGROUND
    assert WORLD_VIEWS[WorldType.ICE_SHELL].war is WarTerrain.UNDER_WATER


async def test_a_canopy_town_comes_down_with_its_forest_and_a_held_unfit_way_breeds_unrest(session: AsyncSession, world: CoreWorld) -> None:
    await folk_of_body(session, world, BodyPlan.ARBOREAL)
    await ground(session, world, TerrainKind.JUNGLE, 10)
    canopy = await town_of_folk(session, world, "Highbough")
    drowned = await town_of_folk(session, world, "Lowmere")
    session.add(SettlementProfileRow(settlement_entity_id=canopy.id, size_tier=SizeTier.TOWN, settle_mode=SettleMode.CANOPY, locked=[], foreigners={}))
    session.add(
        SettlementProfileRow(
            settlement_entity_id=drowned.id, size_tier=SizeTier.TOWN, settle_mode=SettleMode.SUBMERGED, unrest=0, locked=["settle_mode"], foreigners={}
        )
    )
    await session.flush()
    before = stat_or(canopy, "population", 0)
    ctx = await at(session, 2)
    tally = ModeTally()
    await keep_modes(ctx, tally)
    fallen = await session.get(SettlementProfileRow, canopy.id)
    unfit = await session.get(SettlementProfileRow, drowned.id)
    assert fallen is not None and fallen.settle_mode is SettleMode.GROUND and stat_or(canopy, "population", 0) < before and tally.fell == 1
    assert unfit is not None and unfit.settle_mode is SettleMode.SUBMERGED and unfit.unrest == ctx.rules.settle_modes.unfit_unrest and tally.unfit >= 1
    kinds = set(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.like("settle_modes.%"))))
    assert kinds == {"settle_modes.canopy_fell", "settle_modes.unfit"}


async def test_the_god_sets_and_holds_a_settlement_way_of_settling(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of_folk(session, world)
    ctx = await at(session, 2)
    found = await edit_settlement(ctx, town.id, {"settle_mode": "burrow"}, release=[])
    assert found.profile.settle_mode is SettleMode.BURROW and "settle_mode" in found.profile.locked


def stack_of(family: UnitFamily) -> Stack:
    kind = next(kind for kind, spec in UNITS.items() if spec.family is family)
    return Stack(row=ArmyUnitRow(army_entity_id=1, kind=kind, count=100, locked=[]), spec=UNITS[kind], start=100)


def test_each_ground_of_war_forms_its_own_front_and_bars_those_who_cannot_fight_there() -> None:
    land = battle_width(RULES, Field(TerrainKind.MOUNTAINS, None, False), False)
    space = battle_width(RULES, Field(TerrainKind.MOUNTAINS, None, False, ground=WarTerrain.SPACE), False)
    tunnels = battle_width(RULES, Field(TerrainKind.MOUNTAINS, None, False, ground=WarTerrain.UNDERGROUND), False)
    assert space > land > tunnels > 0
    assert WAR_GROUNDS[WarTerrain.UNDERGROUND].blind and WAR_GROUNDS[WarTerrain.UNDER_WATER].three_dimensional
    sky = Field(TerrainKind.PLAIN, None, False, ground=WarTerrain.SKY)
    assert fights_here(stack_of(UnitFamily.AIR), sky) and not fights_here(stack_of(UnitFamily.INFANTRY), sky)
    assert fights_here(stack_of(UnitFamily.INFANTRY), Field(TerrainKind.PLAIN, None, False))
    assert war_ground(WarTerrain.LAND, TerrainKind.UNDERGROUND) is WarTerrain.UNDERGROUND
    assert war_ground(WarTerrain.SKY, TerrainKind.PLAIN) is WarTerrain.SKY
