from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import AccountRow
from aerona.db.tables.concealment import HiddenTruthRow, PublicKnowledgeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.domain.enums.concealment import HiddenTruthKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import CoupCause, DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.reckoning import CaseOutcome, MeasureStage, ReckoningMeasure
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.manual import manual_context
from aerona.engine.reckoning.book import ReckoningTally
from aerona.engine.reckoning.opening import after_coups, apply_legacy, choose, open_reckoning
from aerona.engine.reckoning.tend import tend_reckoning
from aerona.engine.recording.record import record
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def fallen_realm(session: AsyncSession, world: CoreWorld, *, stability: int = 60) -> tuple[EntityRow, EntityRow, EntityRow, OfficeRow]:
    capital = await settlement(session, "Fallholm", world, world.regions[0], population=4000)
    realm = await entity(session, "The Turned Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    profile = PolityProfileRow(
        polity_entity_id=realm.id,
        government=next(iter(GovernmentKind)),
        decision_rule=next(iter(DecisionRule)),
        core_entity_id=capital.id,
        capital_entity_id=capital.id,
        administration=50,
        treasury=1000,
        stability=stability,
    )
    session.add(profile)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=capital.id))
    fallen = await mortal(session, "Old Varric", world, capital.id)
    servant = await mortal(session, "Merel Sand", world, capital.id)
    office = OfficeRow(
        polity_entity_id=realm.id, kind=OfficeKind.MARSHAL, holder_entity_id=servant.id, appointed_by_entity_id=fallen.id, since_epoch=0, powers=[]
    )
    session.add(office)
    await session.flush()
    return realm, fallen, servant, office


async def test_a_coup_opens_a_reckoning_whose_measures_follow_the_realm(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "coup", tuned_rules(reckoning={"open_chance_pct": 100}))
    realm, fallen, _servant, _office = await fallen_realm(session, world, stability=10)
    usurper = await mortal(session, "Iron Kesh", world, None)
    await record(
        ctx,
        "polity.coup",
        roles={IncidentRole.ACTOR: usurper.id, IncidentRole.TARGET: realm.id, IncidentRole.PREDECESSOR: fallen.id},
        facts={"cause": CoupCause.MARSHAL, "infamy": 0},
    )
    tally = ReckoningTally()
    await after_coups(ctx, tally)
    row = await session.scalar(select(ReckoningRow))
    assert tally.opened == 1 and row is not None and row.fallen_node_id == fallen.id and row.opened_by_node_id == usurper.id
    measures = {measure.measure for measure in await session.scalars(select(ReckoningMeasureRow))}
    assert measures == {ReckoningMeasure.AMNESTY}


async def test_a_tribunal_convicts_a_servant_the_record_names_and_bars_cost_administration(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "tribunal", tuned_rules(reckoning={"convict_pct": 100, "measure_years": 1, "harsh_from": 200}))
    realm, fallen, servant, office = await fallen_realm(session, world)
    tally = ReckoningTally()
    row = await open_reckoning(ctx, realm, fallen.id, [(ReckoningMeasure.OFFICE_BAR, 80)], by=None, fallen_epoch=ctx.epoch, tally=tally)
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    await tend_reckoning(ctx, row, tally)
    case = await session.scalar(select(ReckoningCaseRow).where(ReckoningCaseRow.accused_node_id == servant.id))
    assert case is not None and case.outcome is CaseOutcome.BARRED and office.holder_entity_id is None
    assert profile.administration == 50 and row.closed_epoch == ctx.epoch


async def test_an_amnesty_pardons_eases_the_servants_and_stirs_the_victims(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, fallen, servant, office = await fallen_realm(session, world)
    tally = ReckoningTally()
    row = await open_reckoning(ctx, realm, fallen.id, [(ReckoningMeasure.AMNESTY, 80)], by=None, fallen_epoch=ctx.epoch, tally=tally)
    before_resistance, before_pressure = row.resistance, row.victims_pressure
    await tend_reckoning(ctx, row, tally)
    case = await session.scalar(select(ReckoningCaseRow).where(ReckoningCaseRow.accused_node_id == servant.id))
    assert case is not None and case.outcome is CaseOutcome.PARDONED and office.holder_entity_id == servant.id
    assert row.resistance <= before_resistance and row.victims_pressure > before_pressure


async def test_an_inquiry_writes_the_account_and_opened_records_reveal_the_fallen_secrets(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, fallen, _servant, _office = await fallen_realm(session, world)
    truth = HiddenTruthRow(title="the hidden treasury", subject_node_id=fallen.id, kind=next(iter(HiddenTruthKind)), locked=[])
    session.add(truth)
    await session.flush()
    tally = ReckoningTally()
    row = await open_reckoning(
        ctx, realm, fallen.id, [(ReckoningMeasure.TRUTH_INQUIRY, 90), (ReckoningMeasure.RECORD_OPENING, 70)], by=None, fallen_epoch=ctx.epoch, tally=tally
    )
    await tend_reckoning(ctx, row, tally)
    account = await session.scalar(select(AccountRow).where(AccountRow.subject_node_id == fallen.id))
    known = await session.scalar(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth.id))
    assert tally.inquiries == 1 and account is not None and known is not None and known.know_pct == 70


async def test_a_harsh_reckoning_drives_the_old_servants_to_revolt(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(
        session, "harsh", tuned_rules(reckoning={"harsh_revolt_chance_pct": 100, "harsh_from": 100, "convict_pct": 0, "measure_years": 150})
    )
    realm, fallen, _servant, _office = await fallen_realm(session, world)
    tally = ReckoningTally()
    row = await open_reckoning(ctx, realm, fallen.id, [(ReckoningMeasure.TRIBUNAL, 100)], by=None, fallen_epoch=ctx.epoch, tally=tally)
    await tend_reckoning(ctx, row, tally)
    rebels = await session.scalar(select(FactionProfileRow).where(FactionProfileRow.kind == FactionKind.REBELS))
    assert tally.revolts == 1 and rebels is not None


async def test_a_recorded_purge_becomes_a_closed_reckoning_with_its_victims_as_cases(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, fallen, _servant, _office = await fallen_realm(session, world)
    purge = CollectionRow(kind=CollectionKind.PURGE, name="the purge of the crown", world_id=world.world.id, start_epoch=0, end_epoch=0)
    session.add(purge)
    await session.flush()
    session.add_all(
        [
            CollectionMemberRow(collection_id=purge.id, node_id=realm.id, role=CollectionRole.LEADER),
            CollectionMemberRow(collection_id=purge.id, node_id=fallen.id, role=CollectionRole.VICTIM),
        ]
    )
    await session.flush()
    tally = ReckoningTally()
    await apply_legacy(ctx, tally)
    row = await session.scalar(select(ReckoningRow))
    case = await session.scalar(select(ReckoningCaseRow))
    assert row is not None and row.closed_epoch == 0 and case is not None and case.accused_node_id == fallen.id
    measure = await session.scalar(select(ReckoningMeasureRow))
    assert measure is not None and measure.stage is MeasureStage.DONE


async def test_a_weak_realm_reckons_by_amnesty_and_pressed_victims_get_repair(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _realm, _fallen, _servant, _office = await fallen_realm(session, world, stability=10)
    profile = await session.scalar(select(PolityProfileRow))
    assert profile is not None
    chosen = dict(await choose(ctx, None, profile, 80))
    assert ReckoningMeasure.AMNESTY in chosen and ReckoningMeasure.REPARATION_TO_VICTIMS in chosen and ReckoningMeasure.MEMORIAL in chosen
