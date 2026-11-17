import re
from enum import StrEnum
from pathlib import Path

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, InstrumentKind, RumourDistortion, StepAction, StepLocus, StepOutcome, StepState, WitnessMode
from aerona.engine.recording.render import indexed, render_incident

BACKEND = Path(__file__).resolve().parents[2] / "src" / "aerona"
FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src"
PRODUCERS = ("engine", "services", "agents", "tools", "epoch")
DECLARED_STEPS = re.compile(r"steps=(?:frozenset\()?[({][^)}]*[)}]\)?")
RECORD_ENUMS: tuple[type[StrEnum], ...] = (StepAction, StepOutcome, StepState, InstrumentKind, StepLocus, FactUnit, WitnessMode, RumourDistortion)


def sample(fact: FactSpec) -> object:
    if fact.value is FactValue.NUMBER:
        return 2
    if fact.value is FactValue.ENUM:
        return next(iter(fact.enum)) if fact.enum is not None else "value"
    return f"the {fact.key.replace('_', ' ')}"


def told(spec: IncidentKindSpec) -> str:
    needed = indexed(spec.template)
    names = {role.role: [f"the {role.role.value} {count + 1}" for count in range(max(1, needed.get(role.role.value, 1)))] for role in spec.roles}
    facts = {fact.key: [sample(fact)] if fact.many else sample(fact) for fact in spec.facts}
    return render_incident(spec, names, facts)


def written_members(enum: type[StrEnum], texts: list[str]) -> set[str]:
    found: set[str] = set()
    for text in texts:
        aliases = {enum.__name__} | set(re.findall(rf"\b{enum.__name__} as (\w+)", text))
        for alias in aliases:
            found |= set(re.findall(rf"\b{alias}\.([A-Z_]+)\b", text))
    return found


def undeclared(path: Path, enum: type[StrEnum]) -> str:
    text = path.read_text()
    if enum is FactUnit or "incident_kinds" not in path.parts:
        return text
    for name in set(re.findall(r"steps=([A-Z][A-Z_]+)\b", text)):
        text = re.sub(rf"^{name} = frozenset\(.*?^\)", "", text, flags=re.MULTILINE | re.DOTALL)
    return DECLARED_STEPS.sub("", text)


def producer_texts(enum: type[StrEnum]) -> list[str]:
    folders = [BACKEND / folder for folder in PRODUCERS]
    return [path.read_text() for folder in folders for path in sorted(folder.rglob("*.py"))] + [
        undeclared(path, enum) for path in sorted((BACKEND / "catalog").rglob("*.py"))
    ]


def frontend_text() -> str:
    return "\n".join(path.read_text() for path in sorted(FRONTEND.rglob("*.ts*")) if "generated" not in path.parts)


def test_a_kind_renders_from_its_roles_and_facts() -> None:
    spec = IncidentKindSpec("sample.kind", next(iter(INCIDENT_KINDS.values())).group, "{actor} gave {count:coin|coins} to {receiver}.")
    assert render_incident(spec, {IncidentRole.ACTOR: ["Ama"], IncidentRole.RECEIVER: ["Bel", "Cor"]}, {"count": 1}) == "Ama gave 1 coin to Bel and Cor."


def test_every_told_kind_renders_from_sample_facts() -> None:
    broken = []
    for key, spec in INCIDENT_KINDS.items():
        if not spec.told or spec.draft:
            continue
        try:
            text = told(spec)
        except (KeyError, IndexError, ValueError) as error:
            broken.append(f"{key}: {error}")
            continue
        if not text.strip():
            broken.append(f"{key}: renders an empty line")
    assert broken == []


def test_no_kind_is_left_a_generated_draft() -> None:
    drafts = sorted(key for key, spec in INCIDENT_KINDS.items() if spec.draft)
    assert drafts == []


def test_every_record_enum_value_is_produced_by_the_engine_and_read_by_a_screen() -> None:
    shown = frontend_text()
    unused = [
        f"{enum.__name__}.{member.name}"
        for enum in RECORD_ENUMS
        for written in [written_members(enum, producer_texts(enum))]
        for member in enum
        if member.name not in written or not re.search(rf"\b{member.value}\b", shown)
    ]
    assert unused == []


def test_a_kind_that_names_two_of_a_role_needs_both_and_reads_without_a_lost_one() -> None:
    spec = INCIDENT_KINDS["divine.syncretism"]
    assert indexed(spec.template) == {"subject": 2}
    whole = render_incident(spec, {IncidentRole.SUBJECT: ["Ama", "Bel"], IncidentRole.ACTOR: ["Cor"]}, {})
    assert whole == "Ama came to hold Cor and Bel as one."
    assert render_incident(spec, {IncidentRole.SUBJECT: ["Ama"], IncidentRole.ACTOR: ["Cor"]}, {}) == "Ama came to hold Cor and as one."
