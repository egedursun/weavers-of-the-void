from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow, OccupationRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.tables.polity import LawJurisdictionRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.tables.reckoning import ReckoningRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.occupation_regimes import CollaborationFate, CollaborationKind, OccupationEnding, OccupationMeasure, OccupationRule
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.military.occupation import occupation_tax
from aerona.engine.occupation_regime.book import RegimeTally
from aerona.engine.occupation_regime.collaborators import join, tend_collaborators
from aerona.engine.occupation_regime.effects import partisan_share
from aerona.engine.occupation_regime.measures import impose
from aerona.engine.occupation_regime.rule import govern, set_rule
from aerona.engine.occupation_regime.tend import tend_regimes
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.engine.reckoning.book import servants
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def realm(session: AsyncSession, world: CoreWorld, name: str, core: EntityRow) -> EntityRow:
    polity = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=core.id, treasury=1000))
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=core.id))
    await session.flush()
    return polity


async def occupied(session: AsyncSession, world: CoreWorld, *, control: int = 50) -> tuple[OccupationRow, EntityRow, EntityRow, EntityRow]:
    town = await settlement(session, "Heldtown", world, world.regions[0], population=4000)
    seat = await settlement(session, "Marchseat", world, world.regions[1], population=4000)
    owner = await realm(session, world, "The Held Crown", town)
    occupier = await realm(session, world, "The Marching Crown", seat)
    row = OccupationRow(region_entity_id=world.regions[0].id, occupier_entity_id=occupier.id, since_epoch=0, control=control, resistance=50, locked=[])
    session.add(row)
    await session.flush()
    return row, town, owner, occupier


async def regime_of(session: AsyncSession) -> OccupationRegimeRow:
    regime: OccupationRegimeRow | None = await session.scalar(select(OccupationRegimeRow))
    assert regime is not None
    return regime


async def test_an_occupation_gains_a_military_regime_that_sets_the_occupiers_share_of_taxes(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row, _town, owner, occupier = await occupied(session, world)
    tally = await tend_regimes(ctx)
    regime = await regime_of(session)
    assert tally.founded == 1 and regime.rule is OccupationRule.MILITARY and regime.owner_polity_id == owner.id and regime.occupier_entity_id == occupier.id
    regime.tax_pct = 20
    assert await occupation_tax(ctx, 1000, row) == 1000 * 20 // 100 * row.control // 100


async def test_civil_rule_extends_the_occupiers_laws_and_liberation_lifts_them_and_judges_collaborators(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "liberate", tuned_rules(reckoning={"open_chance_pct": 100}))
    row, town, owner, occupier = await occupied(session, world)
    law = await enact(ctx, occupier, LawKind.SERFDOM, {})
    await tend_regimes(ctx)
    regime = await regime_of(session)
    tally = RegimeTally()
    assert await set_rule(ctx, regime, OccupationRule.CIVIL_BY_OCCUPIER, tally)
    assert await session.get(LawJurisdictionRow, (law.id, town.id)) is not None and regime.imposed_laws == [law.id]
    servant = await mortal(session, "Tamsin Orl", world, town.id)
    service = await join(ctx, regime, servant.id, CollaborationKind.ADMINISTRATION, tally)
    assert regime.administrators == [servant.id]
    await session.delete(row)
    await session.flush()
    await tend_regimes(ctx)
    assert regime.ending is OccupationEnding.LIBERATED and service.fate is CollaborationFate.ENDED
    assert await session.get(LawJurisdictionRow, (law.id, town.id)) is None
    reckoning = await session.scalar(select(ReckoningRow).where(ReckoningRow.polity_entity_id == owner.id))
    assert reckoning is not None and reckoning.fallen_node_id == occupier.id
    assert servant.id in {holder.id for holder, _office in await servants(session, reckoning)}


async def test_measures_cut_partisans_raise_resistance_are_remembered_and_deport_people(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row, town, _owner, occupier = await occupied(session, world)
    await tend_regimes(ctx)
    regime = await regime_of(session)
    tally = RegimeTally()
    before = row.resistance
    await impose(ctx, regime, OccupationMeasure.HOSTAGES, 100, tally)
    assert await partisan_share(session, ctx.rules, regime.region_entity_id) < 1 and row.resistance > before
    memory = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == town.id, MemoryRow.subject_node_id == occupier.id))
    assert memory is not None and memory.magnitude < 0
    people = stat(town, "population") or 0
    await impose(ctx, regime, OccupationMeasure.DEPORTATION, 100, tally)
    captives = await session.scalar(select(CaptiveCohortRow).where(CaptiveCohortRow.origin_entity_id == town.id))
    assert captives is not None and captives.captor_entity_id == occupier.id and (stat(town, "population") or 0) == people - captives.count


async def test_informers_cut_the_raids_and_an_exposed_collaborator_is_killed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "exposed", tuned_rules(occupation={"exposure_kill_pct": 100}))
    _row, town, _owner, _occupier = await occupied(session, world)
    await tend_regimes(ctx)
    regime = await regime_of(session)
    tally = RegimeTally()
    informer = await mortal(session, "Vell Darro", world, town.id)
    service = await join(ctx, regime, informer.id, CollaborationKind.INFORMING, tally)
    assert await partisan_share(session, ctx.rules, regime.region_entity_id) < 1
    service.exposure = 100
    await tend_collaborators(ctx, regime, 100, tally)
    assert service.fate is CollaborationFate.KILLED and informer.status is not EntityStatus.CANON and tally.killed == 1


async def test_annexation_takes_the_land_into_the_occupiers_realm_with_settlers(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row, town, _owner, occupier = await occupied(session, world, control=95)
    await tend_regimes(ctx)
    regime = await regime_of(session)
    tally = RegimeTally()
    await set_rule(ctx, regime, OccupationRule.ANNEXATION, tally)
    await govern(ctx, regime, tally)
    assert regime.ending is OccupationEnding.ANNEXED and regime.settlers > 0 and tally.annexed == 1
    profile = await session.get(PolityProfileRow, occupier.id)
    assert profile is not None
    rules = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.target_node_id == town.id, BondRow.state == BondState.ACTIVE))
    assert rules is not None and rules.source_node_id == profile.core_entity_id
    assert await session.get(OccupationRow, row.region_entity_id) is None
    assert await session.scalar(select(CollaborationRow.id)) is None


async def test_a_peace_that_cedes_the_occupied_land_to_the_occupier_ends_the_regime_as_an_annexation_not_a_liberation(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    row, _town, _owner, occupier = await occupied(session, world)
    await tend_regimes(ctx)
    regime = await regime_of(session)
    session.add(PolityTerritoryRow(polity_entity_id=occupier.id, region_entity_id=row.region_entity_id, control=row.control))
    await session.delete(row)
    await session.flush()
    tally = await tend_regimes(ctx)
    assert regime.ending is OccupationEnding.ANNEXED and tally.annexed == 1 and tally.liberated == 0
    assert await session.scalar(select(ReckoningRow)) is None
