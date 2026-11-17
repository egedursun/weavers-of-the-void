from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds import g12_knowledge, g16_peoples
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentTermRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis, ValuePole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.mind.values import note_shift
from aerona.engine.phases.civilization import lend
from aerona.engine.regime.control import found_school
from tests.engine.core.factories import CoreWorld, entity, mortal


async def latest(session: AsyncSession, key: str) -> IncidentRow:
    found = await session.scalar(select(IncidentRow).where(IncidentRow.kind == key).order_by(IncidentRow.id.desc()).limit(1))
    assert found is not None
    return found


async def roles_of(session: AsyncSession, incident_id: int) -> dict[IncidentRole, set[int]]:
    found: dict[IncidentRole, set[int]] = {}
    for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident_id)):
        found.setdefault(row.role, set()).add(row.node_id)
    return found


async def facts_of(session: AsyncSession, incident_id: int) -> dict[str, IncidentFactRow]:
    return {row.key: row for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id))}


def test_every_kind_of_knowledge_and_peoples_is_a_real_kind_with_typed_facts() -> None:
    kinds = [*g12_knowledge.KINDS, *g16_peoples.KINDS]
    assert kinds and not [spec.key for spec in kinds if spec.draft]
    assert not [(spec.key, fact.key) for spec in kinds for fact in spec.facts if fact.value.value == "number" and fact.unit is None]
    assert not [spec.key for spec in kinds if spec.told and not spec.template]


async def test_a_school_founded_by_a_master_names_the_teacher_and_the_school(ctx: TickContext, world: CoreWorld) -> None:
    master = await mortal(ctx.session, "Ilen", world, world.regions[0].id)
    school = await found_school(ctx, master.id, "Ilen's Hall", None)
    incident = await latest(ctx.session, "schools.founded")
    assert (await roles_of(ctx.session, incident.id))[IncidentRole.TEACHER] == {master.id}
    facts = await facts_of(ctx.session, incident.id)
    assert facts["school"].name == school.name and facts["disciples"].number == 0


async def test_a_shift_of_values_keeps_the_axis_the_pole_and_the_numbers(ctx: TickContext, world: CoreWorld) -> None:
    mark = ctx.rules.culture_drift.notable_value
    await note_shift(ctx, world.people, {ValueAxis.MERCY: mark - 1}, {ValueAxis.MERCY: mark + 1})
    incident = await latest(ctx.session, "culture.shift")
    facts = await facts_of(ctx.session, incident.id)
    assert facts["axis"].enum_value == ValueAxis.MERCY.value and facts["pole"].enum_value == ValuePole.HIGH.value
    assert facts["before"].number == mark - 1 and facts["after"].number == mark + 1
    terms = list(await ctx.session.scalars(select(IncidentTermRow).where(IncidentTermRow.incident_id == incident.id)))
    assert [term.term for term in terms] == ["rules.culture_drift.notable_value"]


async def test_a_loan_names_lender_and_borrower_and_keeps_the_amount_and_term(ctx: TickContext, world: CoreWorld) -> None:
    borrower = await entity(ctx.session, "Arhet", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    text = await lend(ctx, world.people, borrower, 10)
    incident = await latest(ctx.session, "civilization.loan")
    roles = await roles_of(ctx.session, incident.id)
    assert roles[IncidentRole.LENDER] == {world.people.id} and roles[IncidentRole.BORROWER] == {borrower.id}
    facts = await facts_of(ctx.session, incident.id)
    assert facts["amount"].number is not None and facts["due_epoch"].number == ctx.epoch + ctx.rules.civilization.loan_term
    assert world.people.name in text and borrower.name in text
