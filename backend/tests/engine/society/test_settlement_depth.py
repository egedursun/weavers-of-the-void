from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.economy import TradeFlowRow, WorkshopRow
from aerona.db.tables.settlement import DistrictDesignRow, DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictHarm, DistrictKind, SizeTier
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.military.siege import gate_factor, wall_defence
from aerona.engine.phases.settlement_life import settlement_life
from aerona.engine.polity.offices import wanted_offices
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.settlement import control
from aerona.engine.settlement.book import TIER_ORDER, town_of
from aerona.engine.settlement.districts import (
    admin_parts,
    damage_districts,
    effects_of,
    material_factor,
    office_tier,
    parameters_of,
    wound_district,
)
from aerona.engine.settlement.life import ambient_heat, capacities, endure_siege, flammable_share, invest, logistics_waste, self_igniting
from aerona.engine.settlement.storage import settlement_store, storage_index, storage_room
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, people, settlement

RULES = Rules()


def district(kind: DistrictKind, level: int = 1, *, material: BuildMaterial = BuildMaterial.TIMBER, design_id: int | None = None) -> DistrictRow:
    return DistrictRow(id=None, settlement_entity_id=1, kind=kind, level=level, condition=100, material=material, built_epoch=0, design_id=design_id, locked=[])


def test_base_parameters_give_every_district_kind_its_effect() -> None:
    effects = effects_of(
        RULES,
        [
            district(DistrictKind.PALACE),
            district(DistrictKind.NECROPOLIS, 2),
            district(DistrictKind.FOREIGN_QUARTER),
            district(DistrictKind.HARBOUR, 3),
            district(DistrictKind.TEMPLE_QUARTER),
            district(DistrictKind.SLUMS),
            district(DistrictKind.CITADEL),
            district(DistrictKind.MARKET),
            district(DistrictKind.CRAFT_QUARTER),
            district(DistrictKind.FARMLAND),
        ],
        {},
    )
    table = RULES.districts
    assert effects.order == table.palace_order
    assert effects.admin_pct == table.admin_palace_pct
    assert effects.sanitation == 2 * table.necropolis_sanitation - RULES.sanitation.slum_loss
    assert effects.piety_floor == 2 * table.necropolis_piety_floor + table.temple_quarter_piety_floor
    assert effects.harbour == 3 * RULES.urban.harbour_per_level
    assert effects.investment_pct == table.foreign_quarter_investment_pct
    assert effects.tension_relief_pct == table.foreign_quarter_tension_pct
    assert effects.policing == RULES.crime.citadel_policing
    assert effects.food_store == 2 * RULES.urban.granary_per_level
    assert effects.goods_store == 2 * table.warehouse_per_level
    assert effects.housing == 13 * RULES.urban.housing_per_level


def test_a_design_overrides_only_the_parameters_it_names() -> None:
    design = DistrictDesignRow(id=7, world_id=1, name="Bazaar", base_kind=DistrictKind.MARKET, food_store=None, goods_store=900, order=3)
    found = parameters_of(RULES, DistrictKind.MARKET, design)
    assert found["goods_store"] == 900
    assert found["order"] == 3
    assert found["food_store"] == RULES.urban.granary_per_level
    effects = effects_of(RULES, [district(DistrictKind.MARKET, 2, design_id=7)], {7: design})
    assert effects.goods_store == 1800
    assert effects.order == 6


def test_a_held_district_keeps_its_condition_and_level() -> None:
    held = district(DistrictKind.MARKET, 2)
    held.locked = ["condition"]
    assert not wound_district(held, 60)
    assert held.condition == 100
    open_district = district(DistrictKind.MARKET, 1)
    open_district.condition = 30
    assert wound_district(open_district, 40)
    level_held = district(DistrictKind.MARKET, 1)
    level_held.condition = 10
    level_held.locked = ["level"]
    assert not wound_district(level_held, 40)
    assert level_held.level == 1


def test_material_branches_every_harm() -> None:
    table = RULES.districts
    assert material_factor(RULES, DistrictHarm.FLOOD, BuildMaterial.TIMBER) > material_factor(RULES, DistrictHarm.FLOOD, BuildMaterial.STONE)
    assert material_factor(RULES, DistrictHarm.STORM, BuildMaterial.TIMBER) > material_factor(RULES, DistrictHarm.STORM, BuildMaterial.STONE)
    assert material_factor(RULES, DistrictHarm.EARTHQUAKE, BuildMaterial.STONE) == table.stone_quake_pct / 100
    assert material_factor(RULES, DistrictHarm.SACK, BuildMaterial.TIMBER) == table.timber_sack_pct / 100
    assert material_factor(RULES, DistrictHarm.DROUGHT, BuildMaterial.STONE) == 1.0


def test_administrative_reach_adds_literacy_scribes_writing_and_palace() -> None:
    parts = admin_parts(RULES, literacy=50, scribe_share=5.0, writing=2, palace_pct=10)
    taxation = RULES.taxation
    table = RULES.districts
    assert parts.base == taxation.admin_base_pct
    assert parts.literacy == round(50 * taxation.admin_per_literacy_pct / 100)
    assert parts.scribes == round(5 * table.admin_per_scribe_pct / 100)
    assert parts.writing == 2 * table.admin_per_writing_pct
    assert parts.total == parts.base + parts.literacy + parts.scribes + parts.writing + 10


def test_stone_walls_and_towers_hold_better_and_gates_weaken_them() -> None:
    ctx = cast(Any, SimpleNamespace(rules=RULES))
    siege = SiegeRow(walls_level=3, breaches=0)
    stone = SettlementInfrastructureRow(walls_level=3, walls_material=BuildMaterial.STONE, towers=4, gates=1, locked=[])
    timber = SettlementInfrastructureRow(walls_level=3, walls_material=BuildMaterial.TIMBER, towers=0, gates=3, locked=[])
    assert wall_defence(ctx, siege, stone) > wall_defence(ctx, siege) > wall_defence(ctx, siege, timber)
    assert gate_factor(ctx, timber) > gate_factor(ctx, stone)
    assert gate_factor(ctx, timber) == pytest.approx(1 + 2 * RULES.districts.gate_breach_pct / 100)


def test_storage_room_adds_absolute_capacity_to_household_stores() -> None:
    need = 1000
    assert storage_room(RULES, 0, need) == RULES.economy.storage_base_index * need // RULES.economy.supply_index_epoch
    assert storage_room(RULES, 500, need) == storage_room(RULES, 0, need) + 500
    assert storage_index(RULES, 1000, need) == RULES.economy.storage_base_index + 100
    store = WorkshopRow(kind=WorkshopKind.GRANARY, level=2)
    parts = settlement_store(RULES, 4000, store, Commodity.FOOD)
    assert parts.total == 4000 + 2 * RULES.districts.granary_workshop_store


def test_office_tiers_gate_council_and_governors() -> None:
    assert office_tier(RULES, OfficeKind.SPYMASTER) == RULES.districts.spymaster_tier
    assert office_tier(RULES, OfficeKind.RULER) == 0
    atlas = SimpleNamespace(top_region=lambda entity_id: 100 if entity_id == 1 else None, communities_in=lambda region: {100: [1], 200: [2], 300: [3]}[region])
    book = cast(Any, SimpleNamespace(atlas=atlas))
    territory = {region: SimpleNamespace(province=None) for region in (100, 200, 300)}
    realm = cast(Any, SimpleNamespace(profile=SimpleNamespace(tier=RULES.realm_tiers.provinces, capital_entity_id=1), territory=territory))
    towns = {
        1: SettlementProfileRow(size_tier=SizeTier.VILLAGE),
        2: SettlementProfileRow(size_tier=SizeTier.TOWN),
        3: SettlementProfileRow(size_tier=SizeTier.HAMLET),
    }
    wanted = wanted_offices(book, realm, [], RULES, cast(Any, towns))
    kinds = {kind for kind, _, _ in wanted}
    assert OfficeKind.MARSHAL in kinds and OfficeKind.CHANCELLOR in kinds
    assert OfficeKind.SPYMASTER not in kinds and OfficeKind.TREASURER not in kinds
    assert (OfficeKind.GOVERNOR, 200, None) in wanted
    assert (OfficeKind.GOVERNOR, 300, None) not in wanted


async def test_a_flood_wrecks_low_timber_districts_more_than_stone(realm: Realm) -> None:
    town = await settlement(realm, "Lowmere", population=4000)
    session = realm.session
    timber = DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.FARMLAND, level=2, condition=100, material=BuildMaterial.TIMBER, built_epoch=1)
    stone = DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.HARBOUR, level=2, condition=100, material=BuildMaterial.STONE, built_epoch=1)
    citadel = DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.CITADEL, level=1, condition=100, material=BuildMaterial.STONE, built_epoch=1)
    session.add_all([timber, stone, citadel])
    await session.flush()
    struck = await damage_districts(context(session), town, DistrictHarm.FLOOD, 1.0)
    assert struck == 2
    assert timber.condition < stone.condition < 100
    assert citadel.condition == 100
    assert "settlement.district_flood" in await chronicle_keys(session)


async def test_settlement_life_unifies_storage_markets_and_admin(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Harrowgate", population=6000)
    session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.GRANARY, level=2, built_epoch=1))
    session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.MARKET, level=2, built_epoch=1))
    await session.flush()
    ctx = context(session)
    await town_of(ctx, town, await KnowledgeMap.load(session))
    await settlement_life(ctx)
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id)))
    market_levels = sum(row.level for row in districts if row.kind is DistrictKind.MARKET)
    assert market_levels >= 1
    infrastructure = await session.get(SettlementInfrastructureRow, town.id)
    assert infrastructure is not None
    farm_levels = sum(row.level for row in districts if row.kind in (DistrictKind.FARMLAND, DistrictKind.MARKET))
    assert infrastructure.granary_capacity == farm_levels * RULES.urban.granary_per_level + 2 * RULES.districts.granary_workshop_store
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None
    assert profile.admin_capacity >= RULES.taxation.admin_base_pct


async def test_a_market_district_opens_a_market_workshop(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Fairstead", population=2500)
    ctx = context(session)
    built = await control.build_district(ctx, town.id, DistrictKind.MARKET, material=BuildMaterial.TIMBER, son_id=None)
    workshop = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == town.id, WorkshopRow.kind == WorkshopKind.MARKET))
    assert workshop is not None
    markets = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id, DistrictRow.kind == DistrictKind.MARKET)))
    for row in markets:
        await control.raze_district(ctx, row.id)
    assert built.kind is DistrictKind.MARKET
    gone = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == town.id, WorkshopRow.kind == WorkshopKind.MARKET))
    assert gone is None


async def test_held_settlement_fields_survive_the_engine(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Keepwell", population=5000)
    ctx = context(session)
    await control.edit_settlement(ctx, town.id, {"granary_capacity": 12345, "admin_capacity": 140, "militia": 77, "rationing": True}, release=[])
    await settlement_life(ctx)
    infrastructure = await session.get(SettlementInfrastructureRow, town.id)
    profile = await session.get(SettlementProfileRow, town.id)
    assert infrastructure is not None and profile is not None
    assert infrastructure.granary_capacity == 12345
    assert profile.admin_capacity == 140
    assert profile.militia == 77
    assert profile.rationing is True
    await control.edit_settlement(ctx, town.id, {}, release=["admin_capacity", "militia"])
    assert "admin_capacity" not in profile.locked and "militia" not in profile.locked
    with pytest.raises(ValidationFailedError):
        await control.edit_settlement(ctx, town.id, {}, release=["nonsense"])


async def test_district_kind_design_and_holds_are_editable(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Designport", population=4000)
    ctx = context(session)
    design = await control.create_design(
        ctx, realm.world.id, "Lantern Quay", DistrictKind.HARBOUR, {"harbour": 900, "order": 2}, description="A lit quay.", son_id=None
    )
    built = await control.build_district(ctx, town.id, None, material=BuildMaterial.STONE, son_id=None, design_id=design.id)
    assert built.kind is DistrictKind.HARBOUR and built.design_id == design.id
    edited = await control.edit_district(ctx, built.id, control.DistrictChange(condition=40, kind=DistrictKind.PALACE))
    assert edited.kind is DistrictKind.PALACE and edited.design_id is None and "condition" in edited.locked
    released = await control.edit_district(ctx, built.id, control.DistrictChange(release=("condition",)))
    assert "condition" not in released.locked
    await control.edit_district(ctx, built.id, control.DistrictChange(design_id=design.id))
    reworked = await control.edit_design(ctx, design.id, control.DesignChange(values={"harbour": None}, base_kind=DistrictKind.MARKET))
    assert reworked.harbour is None
    assert built.kind is DistrictKind.MARKET
    await control.delete_design(ctx, design.id)
    assert built.design_id is None
    with pytest.raises(ValidationFailedError):
        await control.create_design(ctx, realm.world.id, "Bad", DistrictKind.MARKET, {"flying": 3}, description=None, son_id=None)


async def test_foreigners_can_be_set_and_held(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Crossways", population=4000)
    folk = await people(realm, "Wayfolk")
    ctx = context(session)
    found = await control.set_foreigners(ctx, town.id, {folk.id: 20})
    assert found.profile.foreigners == {str(folk.id): 20}
    assert "foreigners" in found.profile.locked
    with pytest.raises(ValidationFailedError):
        await control.set_foreigners(ctx, town.id, {town.id: 10})


async def test_owners_profits_fill_the_investment_pool_and_a_hold_keeps_it(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Coinmoor", population=3000)
    partner = await settlement(realm, "Saltreach", population=2000)
    ctx = context(session)
    built = await town_of(ctx, town, await KnowledgeMap.load(session))
    session.add(
        TradeFlowRow(
            route_entity_id=town.id, epoch=ctx.epoch, commodity=CommodityKind.GRAIN, from_entity_id=town.id, to_entity_id=partner.id, volume=10, value=500
        )
    )
    await session.flush()
    before = built.profile.investment_pool
    profit = await invest(ctx, built)
    assert profit >= 500 * RULES.urban.investment_pct // 100
    assert built.profile.investment_pool == before + profit
    built.profile.locked = ["investment_pool"]
    held = built.profile.investment_pool
    await invest(ctx, built)
    assert built.profile.investment_pool == held


async def test_roads_raise_hauling_and_hauling_short_of_the_people_wastes_production(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Sprawl", population=20000)
    ctx = context(session)
    knowledge = await KnowledgeMap.load(session)
    built = await town_of(ctx, town, knowledge)
    built.infrastructure.roads = 0
    await capacities(ctx, built, knowledge)
    unpaved = built.profile.hauling_capacity
    built.infrastructure.roads = 5
    await capacities(ctx, built, knowledge)
    assert built.profile.hauling_capacity >= unpaved
    built.profile.size_tier = TIER_ORDER[-1]
    built.profile.hauling_capacity = 0
    starved = logistics_waste(RULES, built)
    assert starved == RULES.urban.waste_pct / 100
    built.profile.hauling_capacity = 20000
    assert logistics_waste(RULES, built) == 0 < starved


async def test_a_starving_merciless_town_abandons_its_old_and_a_merciful_one_does_not(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Frostgate", population=5000)
    session.add(
        CohortRow(
            community_entity_id=town.id, age_band=AgeBand.ELDER, sex=Sex.FEMALE, social_class=SocialClass.FARMER, condition=CohortCondition.NONE, count=600
        )
    )
    await session.flush()
    ctx = context(session)
    built = await town_of(ctx, town, await KnowledgeMap.load(session))
    await endure_siege(ctx, built, {ValueAxis.MERCY: 60})
    assert built.profile.rationing
    assert town.stats.population == 5000
    await endure_siege(ctx, built, {ValueAxis.MERCY: -80})
    assert town.stats.population == 5000 - 600 * RULES.urban.abandon_pct // 100
    assert "settlement.abandoned" in await chronicle_keys(session)


async def test_fire_reads_ignition_points_and_a_lava_worlds_heat_lights_timber(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Cinderhold", population=3000)
    ctx = context(session)
    built = await town_of(ctx, town, await KnowledgeMap.load(session))
    built.districts = [district(DistrictKind.FARMLAND, 2), district(DistrictKind.MARKET, 2, material=BuildMaterial.STONE)]
    assert flammable_share(built) == 0.5
    mild = SimpleNamespace(temperature=RULES.environment.temperature_ordinary)
    lava = SimpleNamespace(temperature=RULES.environment.temperature_lava)
    assert ambient_heat(RULES, cast(Any, mild)) == 0
    assert ambient_heat(RULES, cast(Any, lava)) > 0
    assert not self_igniting(RULES, built, cast(Any, mild))
    assert self_igniting(RULES, built, cast(Any, lava))
    built.districts = [district(DistrictKind.MARKET, 2, material=BuildMaterial.STONE)]
    assert not self_igniting(RULES, built, cast(Any, lava))
