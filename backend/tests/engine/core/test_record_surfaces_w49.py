import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.views.scoped_lines import scoped_lines
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.chronicle import ChronicleKind, ChronicleScope
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactUnit, FactValue, InstrumentKind, ProcessGroup, RumourDistortion, StepAction, StepOutcome, StepState
from aerona.engine.recording import accounts, legacy, search
from aerona.engine.recording.accounts import account_of, history_of
from aerona.engine.recording.legacy import LEGACY_FIXUP, upgrade_records
from aerona.engine.recording.search import RecordQuery, search_records
from aerona.services.books import records as book_records
from aerona.services.books.records import add_history_sections
from aerona.services.books.typed import TypedIndex
from tests.engine.core.factories import CoreWorld, mortal

SCRIPTS = Path(__file__).resolve().parents[4] / "scripts"
DUEL = "duel.honour"
DUEL_KIND = IncidentKindSpec(
    key=DUEL,
    group=ProcessGroup.SINGLE_COMBAT,
    template="{actor} fought {target} for {stake}.",
    roles=(RoleSpec(IncidentRole.ACTOR), RoleSpec(IncidentRole.TARGET)),
    facts=(FactSpec("stake", FactValue.NAME), FactSpec("target", FactValue.NODE, required=False)),
    steps=frozenset({StepAction.STRIKE, StepAction.FALL}),
)
KINDS = {DUEL: DUEL_KIND}


@pytest.fixture(autouse=True)
def kinds(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (accounts, legacy, book_records):
        monkeypatch.setattr(module, "INCIDENT_KINDS", KINDS)


async def duel(session: AsyncSession, world: CoreWorld) -> tuple[IncidentRow, int, int]:
    first = await mortal(session, "Arem", world, world.regions[0].id)
    second = await mortal(session, "Bessa", world, world.regions[0].id)
    line = ChronicleRow(epoch=1, year=12, kind=ChronicleKind.WORLD, template_key=DUEL, world_id=world.world.id, text="Arem fought Bessa for honour.")
    session.add(line)
    await session.flush()
    incident = IncidentRow(
        kind=DUEL, epoch=1, year=12, world_id=world.world.id, place_entity_id=world.regions[0].id, chronicle_id=line.id, magnitude=3, locked=[]
    )
    session.add(incident)
    await session.flush()
    session.add_all(
        [
            IncidentParticipantRow(incident_id=incident.id, node_id=first.id, role=IncidentRole.ACTOR, position=0),
            IncidentParticipantRow(incident_id=incident.id, node_id=second.id, role=IncidentRole.TARGET, position=1),
            IncidentFactRow(incident_id=incident.id, key="stake", name="honour"),
        ]
    )
    strike = IncidentStepRow(
        incident_id=incident.id,
        position=0,
        round=0,
        year=12,
        actor_node_id=first.id,
        target_node_id=second.id,
        action=StepAction.STRIKE,
        instrument_kind=InstrumentKind.ITEM,
        instrument_key="mace",
        amount=14.0,
        unit=FactUnit.HP,
        outcome=StepOutcome.WOUNDED,
    )
    session.add(strike)
    await session.flush()
    session.add(IncidentStepStateRow(step_id=strike.id, node_id=second.id, state=StepState.PRONE))
    session.add(
        StateChangeRow(
            epoch=1,
            year=12,
            table_name="entities",
            row_key=f'{{"id": {second.id}}}',
            node_id=second.id,
            operation=LedgerOperation.UPDATE,
            field="power_level",
            before_number=3.0,
            after_number=2.0,
            actor_kind=ActorKind.ENGINE,
            phase="vendettas",
            incident_id=incident.id,
        )
    )
    await session.flush()
    session.add(IncidentNameRow(incident_id=incident.id, name="The Honour Fight", language_entity_id=world.language.id, epoch=1, locked=[]))
    rumour = RumourRow(incident_id=incident.id, carrier_entity_id=first.id, source_entity_id=second.id, fidelity=60, hops=1, epoch=1)
    session.add(rumour)
    await session.flush()
    session.add(
        RumourDistortionRow(
            rumour_id=rumour.id,
            position=0,
            distortion=RumourDistortion.ROLE_CHANGED,
            role=IncidentRole.INSTRUMENT,
            step_id=strike.id,
            told_enum_value="axe",
            epoch=1,
            locked=[],
        )
    )
    await session.flush()
    return incident, first.id, second.id


async def test_an_account_serves_every_tier_and_a_node_history_pages_it(session: AsyncSession, world: CoreWorld) -> None:
    incident, first, second = await duel(session, world)
    account = await account_of(session, incident.id)
    assert account.line == "Arem fought Bessa for honour." and account.retold == "Arem fought Bessa for honour."
    assert [(item.role, item.name) for item in account.participants] == [(IncidentRole.ACTOR, "Arem"), (IncidentRole.TARGET, "Bessa")]
    assert account.facts[0].name == "honour" and account.place_id == world.regions[0].id
    assert account.steps[0].instrument_key == "mace" and account.steps[0].states[0].state is StepState.PRONE
    assert account.changes[0].after_number == 2.0 and account.changes[0].node_name == "Bessa"
    assert account.name == "The Honour Fight" and account.name_language_id == world.language.id
    told = account.rumours[0].distortions[0]
    assert told.distortion is RumourDistortion.ROLE_CHANGED and told.told_enum_value == "axe" and told.step_id == account.steps[0].id
    page = await history_of(session, second, offset=0, limit=1)
    assert page.total_incidents == 1 and page.incidents[0].roles == (IncidentRole.TARGET,) and page.incidents[0].steps == 1
    assert page.total_steps == 1 and page.total_changes >= 1 and page.kinds == (DUEL,)
    assert any(change.field == "power_level" and change.after_number == 2.0 for change in (await history_of(session, second, limit=200)).changes)
    only_actors = await history_of(session, second, role=IncidentRole.ACTOR)
    assert only_actors.total_incidents == 0
    assert (await history_of(session, first, kind="duel")).total_incidents == 1


async def test_records_are_found_by_their_facts_and_steps(session: AsyncSession, world: CoreWorld) -> None:
    incident, _, _ = await duel(session, world)
    total, hits = await search_records(session, RecordQuery(fact_key="stake"))
    assert total == 1 and hits[0].incident_id == incident.id and hits[0].name == "honour"
    total, hits = await search_records(session, RecordQuery(instrument_kind=InstrumentKind.ITEM))
    assert total == 1 and hits[0].step_action is StepAction.STRIKE and hits[0].enum_value == "mace"
    assert (await search_records(session, RecordQuery(action=StepAction.FALL)))[0] == 0
    assert search.RecordQuery(action=StepAction.FALL).by_step


async def test_legacy_records_gain_roles_years_and_restored_lines_once(session: AsyncSession, world: CoreWorld) -> None:
    first = await mortal(session, "Old One", world, world.regions[0].id)
    second = await mortal(session, "Old Two", world, world.regions[0].id)
    line = ChronicleRow(epoch=1, year=30, kind=ChronicleKind.ENGINE_RAW, visible=False, template_key=DUEL, text="Old One fought Old Two for land.")
    summary = ChronicleRow(
        epoch=1, year=30, kind=ChronicleKind.WORLD, visible=True, template_key=f"{DUEL}.folded", text="4 more events of the same kind happened this epoch."
    )
    session.add_all([line, summary])
    await session.flush()
    incident = IncidentRow(kind=DUEL, epoch=1, chronicle_id=line.id, magnitude=0, locked=[])
    session.add(incident)
    await session.flush()
    session.add_all(
        [
            IncidentParticipantRow(incident_id=incident.id, node_id=first.id, role=IncidentRole.SUBJECT, position=0),
            IncidentParticipantRow(incident_id=incident.id, node_id=second.id, role=IncidentRole.SUBJECT, position=1),
        ]
    )
    await session.flush()
    assert await upgrade_records(session) > 0
    roles = dict(
        (
            await session.execute(select(IncidentParticipantRow.node_id, IncidentParticipantRow.role).where(IncidentParticipantRow.incident_id == incident.id))
        ).all()
    )
    assert roles == {first.id: IncidentRole.ACTOR, second.id: IncidentRole.TARGET}
    facts = list(await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id)))
    assert [(fact.key, fact.node_id) for fact in facts] == [("target", second.id)]
    assert incident.year == 30 and line.visible and line.kind is ChronicleKind.WORLD and not summary.visible
    assert await session.get(AppliedFixupRow, LEGACY_FIXUP) is not None
    assert await upgrade_records(session) == 0


async def test_previews_page_their_chronicle_with_a_total(session: AsyncSession, world: CoreWorld) -> None:
    for number in range(5):
        session.add(
            ChronicleRow(epoch=1, year=number, kind=ChronicleKind.WORLD, world_id=world.world.id, son_id=world.son.id, text=f"Line {number + 1} was written.")
        )
    await session.flush()
    first, total = await scoped_lines(session, ChronicleScope.WORLD, world.world.id, offset=0, limit=2)
    older, again = await scoped_lines(session, ChronicleScope.WORLD, world.world.id, offset=2, limit=10)
    assert total == again >= 5 and len(first) == 2 and len(older) == total - 2
    assert not {line.id for line in first} & {line.id for line in older}
    sons, son_total = await scoped_lines(session, ChronicleScope.SON, world.son.id, offset=0, limit=100)
    assert son_total == len(sons) >= 5


async def test_the_book_tells_every_tier_of_a_happening_in_each_entry(session: AsyncSession, world: CoreWorld) -> None:
    incident, first, second = await duel(session, world)
    names = {first: "Arem", second: "Bessa", world.regions[0].id: world.regions[0].name}
    index = TypedIndex(names)
    ledger = await add_history_sections(session, index)
    history = next(section for section in index.of(second) if section.title == "History")
    told = history.lines[0]
    assert "Arem fought Bessa for honour." in told and "as target" in told and "stake honour" in told
    assert "Arem strike Bessa with mace" in told or ("strike" in told and "mace" in told)
    assert "named The Honour Fight" in told and "role changed (instrument) told as axe" in told
    assert "Bessa prone" in told and "power level of entities of Bessa: 3 → 2" in told and "during: Arem fought Bessa for honour." in told
    changes = next(section for section in index.of(second) if section.title == "Changes")
    assert any("power level of entities of Bessa: 3 → 2" in row for row in changes.lines)
    tables = await book_records.record_tables(session, ledger)
    ages = [table for table in tables if table.title.startswith("Happenings")]
    assert ages and any(row[2] == "Arem fought Bessa for honour." and "stake honour" in row[6] for table in ages for row in table.rows)
    assert incident.id


def test_the_record_cuts_guard_finds_a_record_read_cut_short() -> None:
    spec = importlib.util.spec_from_file_location("check_record_cuts", SCRIPTS / "check_record_cuts.py")
    assert spec is not None and spec.loader is not None
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    cut = "rows = await session.scalars(select(IncidentRow).order_by(IncidentRow.id).limit(40))\n"
    paged = "rows = await session.scalars(select(IncidentRow).order_by(IncidentRow.id).offset(start).limit(40))\n"
    single = "row = await session.scalar(select(IncidentRow).order_by(IncidentRow.id).limit(1))\n"
    assert guard.cuts({Path("a.py"): cut}) and not guard.cuts({Path("b.py"): paged}) and not guard.cuts({Path("c.py"): single})
    assert guard.cuts({Path("d.py"): "shown = incidents[:8]\n"})
