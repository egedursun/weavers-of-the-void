from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.labour import REASONS
from aerona.catalog.law_areas import LAW_AREAS
from aerona.catalog.life.polity import DEFAULT_POWERS, TASKS
from aerona.catalog.means import LIFTS, LOCKS
from aerona.catalog.needs import SHORTFALLS
from aerona.catalog.rebuilding import REBUILD_CAUSES, REBUILD_PLANS
from aerona.catalog.relief import RELIEF_KINDS
from aerona.catalog.urban import FINE_HOMES, HOUSING_ORDER, RACKETS_OF
from aerona.catalog.zones import RING_OF_ZONE, ZONE_OF_DISTRICT
from aerona.db.kind_concepts.society import BUILT_IN_ORGANISATIONS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.urban import DistrictServiceRow
from aerona.domain.enums.agrarian import AidKind, PreparednessKind, RebuildCause, RebuildPlan
from aerona.domain.enums.customs import ReliefKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.means import LockKind, WaterLift
from aerona.domain.enums.polity import LawArea, LawKind, OfficeKind, OfficePower
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.society_depth import LabourReason, ShortfallEffect
from aerona.domain.enums.society_kinds import OrganisationPurpose
from aerona.domain.enums.statecraft import CouncilTask, MandateKind, MandateState
from aerona.domain.enums.urban import HousingLevel, RacketKind, UrbanService, ZoneKind
from aerona.engine.context import TickContext
from aerona.engine.polity.mandates import keep_quarantine
from aerona.engine.primitives.manual import manual_context
from aerona.engine.urban.coverage import derive
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int = 3) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "deepening_4", rules=tuned_rules())


def test_debt_and_kin_duty_set_work_and_learning_and_justice_can_be_wanting() -> None:
    assert not REASONS[LabourReason.DEBT].chosen and not REASONS[LabourReason.KIN_DUTY].chosen
    assert {ShortfallEffect.LEARNING, ShortfallEffect.JUSTICE} <= set(SHORTFALLS)


def test_new_quarters_sit_in_their_zones_and_housing_runs_from_shack_to_palace() -> None:
    assert ZONE_OF_DISTRICT[DistrictKind.CARAVAN_QUARTER] is ZoneKind.COMMERCIAL
    assert ZONE_OF_DISTRICT[DistrictKind.PILGRIM_QUARTER] is ZoneKind.CIVIC
    assert ZoneKind.PORT in RING_OF_ZONE
    assert HOUSING_ORDER[0] is HousingLevel.SHACK and HOUSING_ORDER[-1] is HousingLevel.PALACE
    assert HousingLevel.PALACE in FINE_HOMES


def test_lighting_comes_from_power_and_pest_control_from_sanitation() -> None:
    rules = Rules()
    rows = {(1, service): DistrictServiceRow(district_id=1, service=service, coverage=0, locked=[]) for service in UrbanService}
    rows[(1, UrbanService.POWER)].coverage = 80
    rows[(1, UrbanService.SANITATION)].coverage = 50
    derive(rules, 1, rows)
    assert rows[(1, UrbanService.LIGHTING)].coverage == 80 * rules.coverage.lighting_from_power_pct // 100
    assert rows[(1, UrbanService.PEST_CONTROL)].coverage == 50 * rules.coverage.pest_control_from_sanitation_pct // 100


def test_sinkholes_and_plague_teach_their_lessons_and_a_town_can_be_restored() -> None:
    assert REBUILD_CAUSES[RebuildCause.SINKHOLE].lesson is PreparednessKind.QUAKE_BUILDING
    assert REBUILD_CAUSES[RebuildCause.PLAGUE].lesson is PreparednessKind.IMMUNISATION_PLAN
    assert REBUILD_PLANS[RebuildPlan.RESTORED].builds and not REBUILD_PLANS[RebuildPlan.RESTORED].moves
    assert RELIEF_KINDS[ReliefKind.PUBLIC_KITCHEN].eases_poverty and RELIEF_KINDS[ReliefKind.SHELTER].eases_poverty
    assert AidKind.TRANSPORT.value == "transport"


def test_a_living_lock_needs_living_craft_and_an_animal_wheel_lifts_water() -> None:
    assert LOCKS[LockKind.LIVING].opened_by == () and not LOCKS[LockKind.LIVING].picked
    assert LIFTS[WaterLift.ANIMAL_WHEEL].capacity > LIFTS[WaterLift.SHADUF].capacity


def test_fences_and_coiners_are_crime_organisations_with_rackets_of_their_own() -> None:
    for kind in (FactionKind.FENCE_NETWORK, FactionKind.COUNTERFEITING_RING):
        assert BUILT_IN_ORGANISATIONS[kind].category is OrganisationPurpose.CRIME
        assert RacketKind.FORGERY in RACKETS_OF[kind]
    assert RacketKind.POACHING in RACKETS_OF[FactionKind.BANDITS]


def test_the_censor_counts_people_and_family_and_environment_law_hold_their_kinds() -> None:
    assert DEFAULT_POWERS[OfficeKind.CENSOR] == (OfficePower.CENSUS,)
    assert TASKS[OfficeKind.WARDEN] is CouncilTask.SECURE_BORDERS
    assert LAW_AREAS[LawKind.MARRIAGE_LAW] is LawArea.FAMILY
    assert LAW_AREAS[LawKind.ENVIRONMENT_LAW] is LawArea.ENVIRONMENT


async def test_a_quarantine_cleans_a_town_and_costs_it_trade(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    town = await settlement(session, "Shut Gates", world, world.regions[0])
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, sanitation=20, locked=[], foreigners={})
    session.add(profile)
    await session.flush()
    before = profile.sanitation
    row = MandateRow(
        polity_entity_id=town.id, kind=MandateKind.QUARANTINE, settlement_entity_id=town.id, issued_epoch=3, until_epoch=4, state=MandateState.ACTIVE, locked=[]
    )
    await keep_quarantine(ctx, row)
    assert profile.sanitation == before + ctx.rules.mandates.quarantine_health
