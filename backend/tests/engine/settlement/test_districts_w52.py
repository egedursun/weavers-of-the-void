from sqlalchemy import select

from aerona.catalog.urban import DENSITY_RULE
from aerona.catalog.zones import ZONE_OF_DISTRICT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.districts import base_parameters
from aerona.engine.settlement.quarter_levels import quarter_levels
from aerona.engine.settlement.quarters import backfill_camps, keep_quarters
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, settlement

RULES = Rules()


def displaced(town_id: int, count: int) -> CohortRow:
    return CohortRow(
        community_entity_id=town_id,
        age_band=AgeBand.ADULT,
        sex_kind=SexKind.BEARER,
        social_class=SocialClass.FARMER,
        condition=CohortCondition.DISPLACED,
        count=count,
        generation_epoch=0,
    )


def test_twenty_four_district_kinds_with_their_own_effects() -> None:
    assert len(DistrictKind) == 27 and set(DENSITY_RULE) == set(DistrictKind) and set(ZONE_OF_DISTRICT) == set(DistrictKind)
    assert base_parameters(RULES, DistrictKind.CAMP)["sanitation"] < 0 < base_parameters(RULES, DistrictKind.LAZARETTO)["sanitation"]


async def test_the_displaced_get_a_camp_that_settles_into_slums(realm: Realm) -> None:
    town = await settlement(realm, "Refuge", population=2000)
    realm.session.add(displaced(town.id, 400))
    await realm.session.flush()
    ctx = context(realm.session, RULES, epoch=3)
    assert await backfill_camps(ctx) == 1
    assert await backfill_camps(ctx) == 0
    camp = await realm.session.scalar(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id, DistrictRow.kind == DistrictKind.CAMP))
    assert camp is not None
    later = context(realm.session, RULES, epoch=3 + RULES.districts.epochs(RULES.districts.camp_settle_years))
    built = await town_of(later, town, await KnowledgeMap.load(realm.session))
    assert await keep_quarters(later, built) >= 1
    assert camp.kind is DistrictKind.SLUMS
    assert "district.settled" in await chronicle_keys(realm.session)
    assert (await quarter_levels(realm.session, DistrictKind.SLUMS)).get(town.id, 0) >= 1
