from sqlalchemy import select

from aerona.catalog.laws import LAW_PARAMS
from aerona.catalog.methods import METHODS, POLLUTANTS
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.industry import MethodKind, Pollutant
from aerona.domain.enums.polity import LawKind
from aerona.engine.industry.pollution import PollutionTally, sky_factor, tend_pollution
from aerona.engine.industry.sky import irradiate
from aerona.rules.registry import Rules
from tests.engine.industry.test_industry import loaded
from tests.engine.society.factories import Realm, context, settlement


def test_six_pollutants_each_with_recovery_and_harm_rules() -> None:
    table = Rules().pollution
    assert len(POLLUTANTS) == 6 and all(hasattr(table, spec.recover_rule) and hasattr(table, spec.harm_rule) for spec in POLLUTANTS.values())
    assert METHODS[MethodKind.STEAM_HAMMER].pollution(Pollutant.NOISE) > 0 and METHODS[MethodKind.HAND_JOINERY].pollution(Pollutant.NOISE) == 0
    assert "pollutant" in LAW_PARAMS[LawKind.ENVIRONMENT_LAW]


async def test_a_crowded_town_raises_noise_and_rising_pollution_is_told(realm: Realm) -> None:
    ctx = context(realm.session)
    await settlement(realm, "Clamourford", population=200000)
    await realm.session.flush()
    book = await loaded(realm)
    await tend_pollution(ctx, book, PollutionTally())
    row = book.pollution[realm.region.id]
    assert row.noise > 0
    told = await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "pollution.rose"))
    assert told is not None


async def test_light_dims_the_sky_and_fallout_irradiates_the_land(realm: Realm) -> None:
    ctx = context(realm.session)
    assert await irradiate(realm.session, realm.region.id, 40, ctx.epoch) == 40
    row = await realm.session.get(RegionPollutionRow, realm.region.id)
    assert row is not None and row.radiation == 40
    row.light = 100
    assert sky_factor(ctx.rules, row) < 1
