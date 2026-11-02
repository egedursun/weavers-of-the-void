from aerona.agents.bard import without_rejected
from aerona.agents.chronicle_audit import ChronicleText, audit, repair, review, weight
from aerona.agents.context.chronicle_facts import EpochFacts, epoch_facts, son_ref
from aerona.agents.context.scope import load_scope
from aerona.agents.runtime import AgentRuntime
from aerona.db.repositories.entities import EntityRepository
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.domain.enums.chronicle import ChronicleAuditKind, ChronicleKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.models.records import ChronicleCountClaim, ChronicleCoverage, ChronicleCreditClaim, ChronicleOutcomeClaim
from aerona.prompts.contexts.chronicler import ContestKind, FactActor, FactEvent, FactOutcome
from aerona.prompts.schemas.fate import ChronicleCoverageOutput, ChronicleFixOutput
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld

CREATOR_ID = 1
VESAELON = 10
AERON = 11
ORRIN = 20
ILEMAT = 30
ESVARIN = 31


def sample_facts() -> EpochFacts:
    creator = FactActor(ref="creator", id=CREATOR_ID, name="Haevaron", deeds=["drew essence (5 times)"], deed_count=5)
    facts = EpochFacts(epoch=4, creator=creator, rejected={99: "Ehremisael Salt Well"})
    facts.sons = [
        FactActor(ref=son_ref(VESAELON), id=VESAELON, name="Vesaelon", deeds=["healed the Orrin"], deed_count=3),
        FactActor(ref=son_ref(AERON), id=AERON, name="Aeron", deeds=["raised a tower"], deed_count=1),
    ]
    facts.outcomes = [FactOutcome(ref="war-1", kind=ContestKind.WAR, contest="Salt War", winner_id=ILEMAT, winner="Ilemat", loser_id=ESVARIN, loser="Esvarin")]
    facts.events = [FactEvent(ref="event-7", category="disaster", text="A flood drowned the lowlands")]
    facts.counts = {"creator": 5, son_ref(VESAELON): 3, son_ref(AERON): 1, "event-7": 1}
    facts.names = {"creator": ["Haevaron"], son_ref(VESAELON): ["Vesaelon"], son_ref(AERON): ["Aeron"], "event-7": ["Lowmere"], "war-1": ["Ilemat", "Esvarin"]}
    facts.deed_owner = {ORRIN: VESAELON}
    facts.record_names = {ORRIN: "Orrin"}
    facts.actor_deeds = {CREATOR_ID: 5, VESAELON: 3, AERON: 1}
    facts.actor_names = {CREATOR_ID: "Haevaron", VESAELON: "Vesaelon", AERON: "Aeron", ILEMAT: "Ilemat", ESVARIN: "Esvarin"}
    return facts


def test_audit_finds_every_kind_and_repairs_by_rule() -> None:
    rules = Rules()
    facts = sample_facts()
    narrative = (
        "Vesaelon walked among the Orrin and the sick rose from their mats of reed. "
        "The Ehremisael Salt Well was dug by night. "
        "Haevaron was silent all through the age, while the Salt War raged on."
    )
    duplicate = "Vesaelon walked among the Orrin and the sick rose from their mats of reed."
    text = ChronicleText(narrative, {2: f"{duplicate} The rivers of the south kept their old course."})
    coverage = ChronicleCoverage(
        covered=(son_ref(VESAELON), "war-1"),
        outcomes=(ChronicleOutcomeClaim(ref="war-1", winner_id=ESVARIN),),
        credits=(ChronicleCreditClaim(entity_id=ORRIN, actor_id=CREATOR_ID),),
        idle_actor_ids=(CREATOR_ID,),
        counts=(ChronicleCountClaim(ref="creator", value=2),),
    )
    findings = audit(facts, text, coverage, set(), rules)
    kinds = {item.kind for item in findings}
    assert kinds == {
        ChronicleAuditKind.REJECTED_MENTIONED,
        ChronicleAuditKind.SON_SKIPPED,
        ChronicleAuditKind.EVENT_SKIPPED,
        ChronicleAuditKind.WINNER_AS_LOSER,
        ChronicleAuditKind.ACTIVE_AS_SILENT,
        ChronicleAuditKind.DEED_MISCREDITED,
        ChronicleAuditKind.NUMBER_CONTRADICTION,
    }
    skipped = next(item for item in findings if item.kind is ChronicleAuditKind.SON_SKIPPED)
    assert skipped.name == "Aeron"
    repaired, changed = repair(text, findings, rules)
    assert "Salt Well" not in repaired.narrative
    assert duplicate not in repaired.sections[2]
    assert changed == 2
    remaining = audit(facts, repaired, ChronicleCoverage(covered=coverage.covered), set(), rules)
    assert ChronicleAuditKind.REJECTED_MENTIONED not in {item.kind for item in remaining}
    assert weight(remaining, rules) < weight(findings, rules)


def test_names_count_as_coverage_without_structured_output() -> None:
    rules = Rules()
    facts = sample_facts()
    text = ChronicleText("Vesaelon and Aeron argued while Haevaron watched; the waters rose over Lowmere's fields.")
    assert audit(facts, text, ChronicleCoverage(), set(), rules) == []


async def test_review_keeps_a_rewrite_only_when_findings_shrink(
    database: Database, rules: Rules, world: AgentWorld, runtime: AgentRuntime, model: FakeModel
) -> None:
    son = world.core.son
    async with database.write() as session:
        epoch = (await load_scope(session, rules)).epoch
        rejected = await session.get(EntityRow, world.pending.id)
        assert rejected is not None
        await EntityRepository(session).set_status(rejected, EntityStatus.REJECTED, epoch, "rejected")
        deed = ChronicleRow(epoch=epoch, kind=ChronicleKind.CREATION, text=f"{son.name} shaped the Orrin Folk.", son_id=son.id)
        tainted = ChronicleRow(epoch=epoch, kind=ChronicleKind.CULTURE, text="The Unnamed Tale spread among the hills.")
        session.add_all([deed, tainted])
        await session.flush()
        session.add(ChronicleEntityRow(chronicle_id=tainted.id, entity_id=rejected.id, position=0))
    async with database.read() as session:
        facts = await epoch_facts(await load_scope(session, rules), epoch)
    son_fact = next(item for item in facts.sons if item.id == son.id)
    assert son_fact.deed_count == 1
    assert world.creation.id in {record.id for record in son_fact.records}
    assert rejected.id in facts.rejected
    corrected = f"{son.name} shaped the Orrin Folk in the salt hills, and their songs carried across the age."
    model.script(ChronicleFixOutput, ChronicleFixOutput(narrative=corrected, coverage=ChronicleCoverageOutput(covered=[son_ref(son.id)])))
    text = ChronicleText("The Unnamed Tale spread among the hills. The hills were quiet.")
    repaired, report = await review(runtime, epoch, text, ChronicleCoverage())
    assert report.found >= 2
    assert report.rewritten
    assert repaired.narrative == corrected
    assert not [item for item in report.remaining if item.kind is ChronicleAuditKind.REJECTED_MENTIONED]


def test_historian_view_drops_sentences_about_rejected_records() -> None:
    text = "We dug the Ehremisael Salt Well at dawn. Our songs rose over the dunes."
    assert without_rejected(text, ["Ehremisael Salt Well"], 4) == "Our songs rose over the dunes."
    assert without_rejected("Only the dunes remember.", ["Ehremisael Salt Well"], 4) == "Only the dunes remember."
