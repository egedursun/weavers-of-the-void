from types import SimpleNamespace
from typing import cast

from aerona.catalog.good_builtins import BUILT_IN_GOODS, SEED_STOCK
from aerona.catalog.life.forecasting import METHOD_COST_PCT, METHOD_STRENGTH_PCT, NEEDS
from aerona.catalog.life.limit_ways import LIMIT_WAYS
from aerona.catalog.money import FORM_BACKINGS, MONEY_FORMS
from aerona.catalog.movement import CAVE_WAYS
from aerona.catalog.nature_kinds50 import LOCAL_CAUSES, SPACE_WEATHER
from aerona.catalog.strata import STRATA
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.cuisine import FLAVOURS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import GoodKindRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.domain.enums.body_systems import BodySystem, LimitWay
from aerona.domain.enums.economy import CommodityKind, MoneyBacking, MoneyForm
from aerona.domain.enums.environment import MovementMode, TerrainKind
from aerona.domain.enums.forecasting import WeatherAim, WeatherWorkMethod
from aerona.domain.enums.geology import UndergroundStratum
from aerona.domain.enums.kinds import GoodCategory, IngredientRole
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.records import FactUnit, InstrumentKind, RumourDistortion, StepAction, StepState
from aerona.domain.enums.water import LocalClimateCause
from aerona.engine.body.tolerance import Ground, excess
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import role_in
from aerona.engine.economy.money_forms_w52 import backing_of
from aerona.engine.forecasting.works import aim_for
from aerona.engine.lore.tellings import COUNTED_UNITS
from aerona.engine.military.duels import Bout, Fighter, drafts
from aerona.rules.registry import Rules

RULES = Rules()
CTX = cast(TickContext, SimpleNamespace(rules=RULES))


def test_new_good_categories_hold_built_in_goods_and_seed_is_held_back() -> None:
    placed = {good.category for good in BUILT_IN_GOODS.values()}
    assert {GoodCategory.PREPARED_FOOD, GoodCategory.FERTILISER, GoodCategory.RESIN_AND_GUM} <= placed
    assert CommodityKind.GRAIN in SEED_STOCK and RULES.goods.seed_reserve_pct == 15 and RULES.goods.fertiliser_yield_pct == 20


def test_money_forms_carry_their_own_backing() -> None:
    assert {MoneyForm.BILL_OF_EXCHANGE, MoneyForm.WAREHOUSE_RECEIPT, MoneyForm.LAND_SCRIP} <= set(MONEY_FORMS)
    assert backing_of(MoneyForm.LAND_SCRIP, False) is MoneyBacking.LAND
    assert backing_of(MoneyForm.LABOUR_HOURS, False) is MoneyBacking.LABOUR
    assert backing_of(MoneyForm.COIN, True) is MoneyBacking.METAL
    assert FORM_BACKINGS[MoneyForm.WAREHOUSE_RECEIPT] is MoneyBacking.COMMODITY


def test_sour_dishes_use_fruit_as_their_acid() -> None:
    fruit = GoodKindRow(category=GoodCategory.FRUIT)
    herbs = GoodKindRow(category=GoodCategory.SEASONING)
    assert role_in(RULES, fruit, {"sour": 80}) is IngredientRole.ACID
    assert role_in(RULES, fruit, {"sour": 10}) is IngredientRole.GARNISH
    assert role_in(RULES, herbs, {"pungent": 90}) is IngredientRole.AROMA
    assert {"astringent", "rich"} <= set(FLAVOURS)


def test_duels_record_taunts_and_pleas_as_words() -> None:
    first, second = EntityRow(id=1, name="A"), EntityRow(id=2, name="B")
    bout = Bout(
        winner=Fighter(first, 1.0, 10, 0, 1, 50, 50),
        loser=Fighter(second, 1.0, 10, 0, 1, 50, 50),
        end=DuelEnd.YIELD,
        context=DuelContext.HONOUR,
        exchanges=0,
    )
    steps = drafts(bout)
    assert steps[0].action is StepAction.INSULT and steps[0].instrument_kind is InstrumentKind.WORD
    assert (2, StepState.FRIGHTENED) in steps[0].states
    assert steps[-1].action is StepAction.PLEAD


def test_rumours_inflate_counts_by_their_rule() -> None:
    assert FactUnit.PEOPLE in COUNTED_UNITS and RULES.rumours.inflate_pct == 20
    row = RumourDistortionRow(distortion=RumourDistortion.COUNT_INFLATED, fact_key="dead", told_number=120.0)
    assert row.distortion is RumourDistortion.COUNT_INFLATED


def test_weather_works_call_snow_and_wind_and_each_method_has_its_cost() -> None:
    assert aim_for(CTX, -RULES.forecasting.weather_work_shift, False, snowless=True) is WeatherAim.SNOW
    assert aim_for(CTX, 0, False, harbour=True) is WeatherAim.WIND
    assert set(METHOD_COST_PCT) == set(METHOD_STRENGTH_PCT) == set(NEEDS) == set(WeatherWorkMethod)


def test_local_climates_and_space_weather_widen() -> None:
    assert LOCAL_CAUSES[LocalClimateCause.ICE_FIELD].heat < 0 and LOCAL_CAUSES[LocalClimateCause.WETLAND].sickens
    assert "meteor_shower" in {kind.value for kind in SPACE_WEATHER}


def test_new_tolerances_strain_a_body_and_ways_past_ease_it() -> None:
    row = BodySystemRow(system=BodySystem.NERVES, present=True, air_need=0, gravity_max=100, cold_min=0, heat_max=100, toxin_tolerance=100)
    row.radiation_max, row.light_min, row.humidity_range = 20, 40, 100
    assert excess(row, Ground(50, 50, 50, 0, radiation=70, light=50, humidity=50)) == 50
    assert excess(row, Ground(50, 50, 50, 0, radiation=0, light=10, humidity=50)) == 30
    assert set(LIMIT_WAYS) == set(LimitWay) and all(spec.ease(RULES) > 0 for spec in LIMIT_WAYS.values())


def test_strata_name_eleven_layers_with_their_ways_and_ground() -> None:
    assert next(iter(STRATA)) is UndergroundStratum.PERMAFROST_LAYER and list(STRATA)[-1] is UndergroundStratum.DEEP_UNDERWORLD
    assert STRATA[UndergroundStratum.UNDER_OCEAN].terrain is TerrainKind.SEA
    assert STRATA[UndergroundStratum.CAVERN_LOWER].modes == CAVE_WAYS and MovementMode.BURROWING not in CAVE_WAYS
    assert not STRATA[UndergroundStratum.FAULT_ZONE].dwellable
