from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cosmography import BEING_MODEL, EMBODIED, PHENOMENON_MODEL, SCOPE_SPREAD, SENSE_REACH
from aerona.catalog.life.environment import WORLD_SOIL
from aerona.catalog.preservation import PRESERVATION
from aerona.catalog.soils import SOILS
from aerona.catalog.travel import TRAVEL_MODEL, medium_of
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmography import PhenomenonProfileRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.cosmography import BeingKind, PhenomenonCause, PhenomenonKind, PhenomenonPersistence, PhenomenonScope
from aerona.domain.enums.economy import CommodityKind, CurrencyIssuer, MoneyForm, TradeMode
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.travel import JourneyEventKind, TravelMedium, TravelMethod
from aerona.domain.enums.urban import CargoClass, PreservationMethod
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import PeopleStats, SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos import control
from aerona.engine.cosmos.phenomena import phenomena_cycles, spread
from aerona.engine.economy.cargo import spoilage
from aerona.engine.economy.control_depth import MoneyShape, NewCoin, check_money, create_currency, reshape_currency
from aerona.engine.economy.convoys import preservation_for
from aerona.engine.economy.money import strain
from aerona.engine.phases.travel import MEDIUM_EVENTS
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import set_stats
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, tick, tuned


def test_every_travel_method_has_a_medium_and_the_engine_reads_it() -> None:
    assert set(TRAVEL_MODEL) == set(TravelMethod)
    assert medium_of(TravelMethod.DEATH_CURRENT) is TravelMedium.DEATH
    assert MEDIUM_EVENTS[medium_of(TravelMethod.CARRIED_WITHIN)] is JourneyEventKind.NOT_RELEASED
    assert MEDIUM_EVENTS[medium_of(TravelMethod.DREAM_JOURNEY)] is JourneyEventKind.DREAM_NOT_RETURNED


async def test_a_phenomenon_bound_to_a_place_never_spreads(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Stillfield", cosmos.home.id)
    body = await control.new_phenomenon(ctx, PhenomenonKind.TIME_DISTORTION, region.id, 100, PhenomenonCause.DIVINE)
    profile = await ctx.session.get(PhenomenonProfileRow, body.id)
    assert profile is not None and PHENOMENON_MODEL[profile.kind].scope is PhenomenonScope.PLACE
    assert SCOPE_SPREAD[PhenomenonScope.PLACE] == 0
    assert await spread(ctx, cast(RegionAtlas, None), body, profile, []) == 0


async def test_a_passing_phenomenon_fades_faster_than_a_lasting_one(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Wideheath", cosmos.home.id)
    passing = await control.new_phenomenon(ctx, PhenomenonKind.POWER_SURGE, region.id, 50, PhenomenonCause.DIVINE)
    lasting = await control.new_phenomenon(ctx, PhenomenonKind.LASTING_STORM, region.id, 50, PhenomenonCause.DIVINE)
    for body in (passing, lasting):
        profile = await ctx.session.get(PhenomenonProfileRow, body.id)
        assert profile is not None
        profile.growth = 0
    await phenomena_cycles(ctx)
    passing_profile = await ctx.session.get(PhenomenonProfileRow, passing.id)
    lasting_profile = await ctx.session.get(PhenomenonProfileRow, lasting.id)
    assert passing_profile is not None and lasting_profile is not None
    assert PHENOMENON_MODEL[PhenomenonKind.POWER_SURGE].persistence is PhenomenonPersistence.PASSING
    assert passing_profile.intensity < lasting_profile.intensity


async def test_a_permanent_phenomenon_outlasts_its_intensity_until_fully_warded(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Heavyfold", cosmos.home.id)
    body = await control.new_phenomenon(ctx, PhenomenonKind.GRAVITY_ANOMALY, region.id, 1, PhenomenonCause.DIVINE)
    profile = await ctx.session.get(PhenomenonProfileRow, body.id)
    assert profile is not None
    profile.growth = -5
    profile.containment = 0
    await phenomena_cycles(ctx)
    await ctx.session.refresh(body)
    assert body.status.value == "canon"
    profile.containment = 100
    await phenomena_cycles(ctx)
    await ctx.session.refresh(body)
    assert body.status.value != "canon"


def test_every_being_has_a_substrate_and_a_sense_that_shape_its_reach() -> None:
    assert set(BEING_MODEL) == set(BeingKind)
    assert BEING_MODEL[BeingKind.VOID_KEEPER].substrate not in EMBODIED
    assert SENSE_REACH[BEING_MODEL[BeingKind.TIME_TRAVELLER].sense] < SENSE_REACH[BEING_MODEL[BeingKind.PLANAR_NATIVE].sense]
    assert BEING_MODEL[BeingKind.SWARM_INTELLIGENCE].substrate is MindSeat.BODIES


def test_every_preservation_method_spares_its_own_share_of_spoilage(rules: Rules) -> None:
    fresh = spoilage(rules, CargoClass.PERISHABLE, TradeMode.ROAD, PreservationMethod.NONE)
    for method, spec in PRESERVATION.items():
        kept = spoilage(rules, CargoClass.PERISHABLE, TradeMode.ROAD, method)
        assert kept == pytest.approx(fresh * (1 - spec.keeping(rules) / 100)), method
    assert spoilage(rules, CargoClass.PERISHABLE, TradeMode.ROAD, PreservationMethod.FREEZING) < spoilage(
        rules, CargoClass.PERISHABLE, TradeMode.ROAD, PreservationMethod.DRYING
    )


async def test_a_convoy_keeps_its_goods_by_what_its_owner_knows(ctx: TickContext, cosmos: Cosmos) -> None:
    owner = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    cargo = {CommodityKind.GRAIN.value: 10}
    assert await preservation_for(ctx, owner.id, {}, TradeMode.SEA) is PreservationMethod.NONE
    assert await preservation_for(ctx, owner.id, cargo, TradeMode.SEA) is PreservationMethod.CURING
    assert await preservation_for(ctx, owner.id, cargo, TradeMode.ROAD) is PreservationMethod.NONE


async def coin_issuer(ctx: TickContext, cosmos: Cosmos) -> int:
    town = await make_entity(ctx.session, "Coinhold", EntityType.SETTLEMENT, SettlementStats(population=500), world_id=cosmos.home.id)
    return town.id


async def test_only_coin_and_commodity_money_are_made_of_metal(ctx: TickContext, cosmos: Cosmos) -> None:
    issuer = await coin_issuer(ctx, cosmos)
    with pytest.raises(ValidationFailedError):
        check_money(MoneyForm.PAPER, MaterialKind.SILVER)
    with pytest.raises(ValidationFailedError):
        check_money(MoneyForm.COIN, None)
    notes = await create_currency(ctx, NewCoin(issuer_id=issuer, name="Notes", metal=None, purity=100, trust=60, supply=0, form=MoneyForm.PAPER))
    assert notes.metal is None and notes.form is MoneyForm.PAPER and notes.issuer_kind is CurrencyIssuer.COMMUNITY
    coin = await create_currency(
        ctx,
        NewCoin(
            issuer_id=issuer,
            name="Penny",
            metal=MaterialKind.SILVER,
            purity=90,
            trust=70,
            supply=0,
        ),
    )
    await reshape_currency(ctx, coin, MoneyShape(form=MoneyForm.LEDGER))
    assert coin.form is MoneyForm.LEDGER and coin.metal is None


async def test_money_not_made_of_metal_is_issued_counterfeited_and_broken_into(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "money", counterfeit_chance=100, intrusion_chance=100))
    issuer = await coin_issuer(ctx, cosmos)
    town = await session.get(EntityRow, issuer)
    assert town is not None
    paper = await create_currency(ctx, NewCoin(issuer_id=issuer, name="Notes", metal=None, purity=100, trust=0, supply=1000, form=MoneyForm.PAPER))
    await strain(ctx, paper, town)
    assert paper.supply == 1000 + ctx.rules.money.issue_units
    network = CurrencyRow(issuer_entity_id=issuer, name="Bits", metal=None, purity=100, supply=1000, trust=50, minted_epoch=0, form=MoneyForm.NETWORK)
    session.add(network)
    await strain(ctx, network, town)
    assert network.supply < 1000 + ctx.rules.money.issue_units
    notes = [
        CurrencyRow(id=900 + index, issuer_entity_id=issuer, name="Notes", metal=None, purity=100, supply=0, trust=10, minted_epoch=0, form=MoneyForm.PAPER)
        for index in range(10)
    ]
    for row in notes:
        await strain(ctx, row, town)
    assert any(row.trust < 10 for row in notes)
    set_stats(town, population=5000)
    await strain(ctx, paper, town)
    assert paper.supply == 1000 + 6 * ctx.rules.money.issue_units


def test_every_soil_has_a_fertility_and_the_new_soils_are_reached(rules: Rules) -> None:
    assert set(SOILS) == set(SoilKind)
    reached = set(WORLD_SOIL.values())
    for soil in (SoilKind.LATERITE, SoilKind.PERMAFROST, SoilKind.REGOLITH, SoilKind.ARTIFICIAL):
        assert soil in reached
        assert 0 <= SOILS[soil].fertility(rules) <= 100
    assert WORLD_SOIL[WorldType.ICE] is SoilKind.PERMAFROST
