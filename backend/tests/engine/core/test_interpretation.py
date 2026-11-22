from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.interpretation import InterpretationFault, InterpretedEvent
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.models.entity_stats import LanguageStats, TreatyStats
from aerona.engine.interpretation.tend import tend_interpretations
from aerona.engine.interpretation.work import interpret, reach_of, slant_of
from aerona.engine.mortal.standing import shift_standing, standing_of
from aerona.engine.polity.accords import Clause, read_through
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.community_relations import relation
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def tongue(session: AsyncSession, world: CoreWorld, name: str) -> EntityRow:
    language = await entity(session, name, EntityType.LANGUAGE, LanguageStats(spread=20, complexity=40, sacredness=0), world_id=world.world.id)
    await language_profile(session, language, None)
    return language


async def renown(session: AsyncSession, reader: EntityRow) -> int:
    return await standing_of(session, reader, "renown") or 0


async def two_peoples(session: AsyncSession, world: CoreWorld, skill: int = 80) -> tuple[EntityRow, EntityRow, EntityRow]:
    first = await settlement(session, "Eastmouth", world, world.regions[0])
    second = await settlement(session, "Westmouth", world, world.regions[1])
    await bond(session, first.id, (await tongue(session, world, "Eastern")).id, BondKind.SPEAKS)
    await bond(session, second.id, (await tongue(session, world, "Western")).id, BondKind.SPEAKS)
    reader = await mortal(session, "Ivo Ternan", world, first.id)
    session.add(SkillRow(holder_node_id=reader.id, skill=SkillKind.LANGUAGES, level=skill, peak=skill, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return first, second, reader


async def test_a_faithful_interpreter_carries_words_between_tongues_and_gains_standing(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "faithful", tuned_rules(interpreters={"fault_base_pct": 0, "fault_per_distance_pct": 0}))
    first, second, reader = await two_peoples(session, world)
    before = await renown(session, reader)
    row = await interpret(ctx, InterpretedEvent.PARLEY, first.id, second.id)
    assert row is not None and row.interpreter_node_id == reader.id and row.fault is InterpretationFault.NONE and 0 < row.fidelity <= 80
    assert await renown(session, reader) > before


async def test_an_error_changes_a_clause_and_its_coming_to_light_mends_it_and_leaves_grievance(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(interpreters={"fault_base_pct": 100, "fault_per_distance_pct": 100, "slant_loyalty_threshold": 100, "fault_found_pct": 100})
    ctx = await manual_context(session, "error", rules)
    first, second, _reader = await two_peoples(session, world)
    row = await interpret(ctx, InterpretedEvent.TREATY, first.id, second.id)
    assert row is not None and row.fault not in {InterpretationFault.NONE, InterpretationFault.SLANTED}
    clause = read_through(ctx, Clause(ClauseKind.TRIBUTE, first.id, second.id, {"amount": 40}), row)
    assert clause.params["amount"] != 40 and clause.params["interpretation"] == row.id
    treaty = await entity(session, "The Mouth Accord", EntityType.TREATY, TreatyStats(), world_id=world.world.id)
    stored = TreatyClauseRow(
        treaty_entity_id=treaty.id, kind=clause.kind, obligor_node_id=first.id, beneficiary_node_id=second.id, params=clause.params, locked=[]
    )
    session.add(stored)
    await session.flush()
    trust = await relation(session, ctx.rules, first.id, second.id)
    tally = await tend_interpretations(ctx)
    assert tally.found == 1 and tally.mended == 1 and row.found
    assert stored.params == {"amount": 40}
    assert await relation(session, ctx.rules, first.id, second.id) < trust
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "tongue.fault_found")) is not None


async def test_a_loyal_interpreter_slants_toward_its_own_side_and_loses_standing_when_found(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(interpreters={"fault_base_pct": 100, "fault_per_distance_pct": 100, "slant_loyalty_threshold": 0, "fault_found_pct": 100})
    ctx = await manual_context(session, "slant", rules)
    first, second, reader = await two_peoples(session, world)
    row = await interpret(ctx, InterpretedEvent.TRADE, first.id, second.id)
    assert row is not None and row.fault is InterpretationFault.SLANTED and row.favoured_party_id == first.id
    owed = read_through(ctx, Clause(ClauseKind.TRIBUTE, second.id, first.id, {"amount": 40}), row)
    assert owed.params["amount"] == 80
    await shift_standing(session, reader, "renown", 20, ctx.epoch)
    before = await renown(session, reader)
    await tend_interpretations(ctx)
    assert await renown(session, reader) < before
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "tongue.slanted")) is not None


async def test_no_interpretation_without_an_interpreter_or_between_one_tongue(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "none", tuned_rules())
    first, second, _reader = await two_peoples(session, world, skill=5)
    assert await interpret(ctx, InterpretedEvent.SERMON, first.id, second.id) is None
    assert await interpret(ctx, InterpretedEvent.SERMON, first.id, first.id) is None


async def test_a_recurring_exchange_keeps_one_reading_whose_error_lasts_until_found_and_narrows_trade(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(interpreters={"fault_base_pct": 100, "fault_per_distance_pct": 100, "slant_loyalty_threshold": 100})
    ctx = await manual_context(session, "trade", rules)
    first, second, _reader = await two_peoples(session, world)
    row = await interpret(ctx, InterpretedEvent.TRADE, first.id, second.id)
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch += 1
    later = await manual_context(session, "trade", rules)
    assert row is not None and await interpret(later, InterpretedEvent.TRADE, first.id, second.id) is row
    assert row.epoch == ctx.epoch and reach_of(ctx, row) < 1
    assert slant_of(row, first.id, second.id) == 0
    assert len(list(await session.scalars(select(InterpretationRow)))) == 1


async def test_a_skilled_interpreter_with_no_regard_for_either_side_errs_but_never_slants(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(interpreters={"fault_base_pct": 100, "fault_per_distance_pct": 100, "slant_loyalty_threshold": 40})
    ctx = await manual_context(session, "unslanted", rules)
    first, second, _reader = await two_peoples(session, world, skill=100)
    row = await interpret(ctx, InterpretedEvent.TRADE, first.id, second.id)
    assert row is not None and row.fault is not InterpretationFault.SLANTED and row.favoured_party_id is None
