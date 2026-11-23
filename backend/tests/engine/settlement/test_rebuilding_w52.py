from aerona.catalog.rebuilding import REBUILD_CAUSES, REBUILD_PLANS
from aerona.db.tables.agrarian import PreparednessRow, ReconstructionRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.domain.enums.agrarian import PreparednessKind, RebuildCause, RebuildPlan
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.agrarian.rebuilding_ways import abandon_town, learn, relocate
from aerona.engine.agrarian.ruin import ruin_towns_in
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, settlement, tuned

RULES = Rules()
CERTAIN = tuned(rebuilding={f"{cause.value}_lesson_pct": 100 for cause in RebuildCause})


def test_eight_causes_and_four_ways_each_with_their_lesson() -> None:
    assert len(RebuildCause) == 8 and set(REBUILD_CAUSES) == set(RebuildCause)
    assert REBUILD_CAUSES[RebuildCause.SEA_WAVE].lesson is PreparednessKind.SEAWALL
    assert REBUILD_CAUSES[RebuildCause.LANDSLIDE].technique is Technique.TERRACING
    assert REBUILD_PLANS[RebuildPlan.RELOCATED].moves and not REBUILD_PLANS[RebuildPlan.ABANDONED].builds


async def test_a_sea_wave_ruins_the_towns_of_its_coast_and_they_learn(realm: Realm) -> None:
    town = await settlement(realm, "Harbour", population=1500)
    ctx = context(realm.session, CERTAIN)
    assert await ruin_towns_in(ctx, realm.region.id, RebuildCause.SEA_WAVE) >= 1
    row = ReconstructionRow(settlement_entity_id=town.id, cause=RebuildCause.LANDSLIDE, started_epoch=1, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    await learn(ctx, row, town)
    assert await realm.session.get(PreparednessRow, (town.id, PreparednessKind.WARNING_NETWORK)) is not None
    assert await realm.session.get(HolderTechniqueRow, (town.id, Technique.TERRACING)) is not None


async def test_a_relocated_town_moves_and_leaves_a_ruin(realm: Realm) -> None:
    town = await settlement(realm, "Lowtown", population=900)
    row = ReconstructionRow(
        settlement_entity_id=town.id, cause=RebuildCause.SEA_WAVE, plan=RebuildPlan.RELOCATED, site_entity_id=realm.far_region.id, locked=[]
    )
    realm.session.add(row)
    await realm.session.flush()
    await relocate(context(realm.session, RULES), row, town)
    assert town.location_id == realm.far_region.id
    assert "settlement.relocated" in await chronicle_keys(realm.session)


async def test_an_abandoned_town_sends_its_people_away_as_displaced(realm: Realm) -> None:
    town = await settlement(realm, "Ashfall", population=600)
    host = await settlement(realm, "Shelter", population=1000)
    row = ReconstructionRow(settlement_entity_id=town.id, cause=RebuildCause.ERUPTION, plan=RebuildPlan.ABANDONED, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    await abandon_town(context(realm.session, RULES), row, town)
    assert town.status is not EntityStatus.CANON and row.finished_epoch is not None
    assert stat(host, "population") == 1600
    assert "settlement.left_after_ruin" in await chronicle_keys(realm.session)
