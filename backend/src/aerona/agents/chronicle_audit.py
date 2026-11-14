import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.chronicle_facts import EpochFacts, epoch_facts
from aerona.agents.context.chronicler import living_world_items
from aerona.agents.context.scope import load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import sanitize, sentences
from aerona.core.grammar import several
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.chronicle import HEAVY_AUDIT_KINDS, ChronicleAuditKind
from aerona.domain.models.records import (
    ChronicleAuditFinding,
    ChronicleAuditReport,
    ChronicleCountClaim,
    ChronicleCoverage,
    ChronicleCreditClaim,
    ChronicleOutcomeClaim,
)
from aerona.language.similarity import normalize_name
from aerona.prompts import PromptId
from aerona.prompts.contexts.chronicler import AuditFindingItem, ChroniclerAuditFixContext, ChroniclerSystemContext
from aerona.prompts.contexts.common import WorldItem
from aerona.prompts.schemas.fate import ChronicleCoverageOutput, ChronicleFixOutput
from aerona.rules.registry import Rules

PARAGRAPHS = re.compile(r"\n")
EXTRA_BLANK_LINES = re.compile(r"\n{3,}")
WORD_SPLIT = re.compile(r"\s+")


@dataclass
class ChronicleText:
    narrative: str
    sections: dict[int, str] = field(default_factory=dict)

    def parts(self) -> list[tuple[int | None, str]]:
        return [(None, self.narrative), *self.sections.items()]

    def whole(self) -> str:
        return "\n".join(text for _, text in self.parts() if text)


def coverage_from(output: ChronicleCoverageOutput) -> ChronicleCoverage:
    return ChronicleCoverage(
        covered=tuple(output.covered),
        entity_ids=tuple(output.entity_ids),
        outcomes=tuple(ChronicleOutcomeClaim(ref=claim.ref, winner_id=claim.winner_id) for claim in output.outcomes),
        credits=tuple(ChronicleCreditClaim(entity_id=claim.entity_id, actor_id=claim.actor_id) for claim in output.credits),
        idle_actor_ids=tuple(output.idle_actor_ids),
        counts=tuple(ChronicleCountClaim(ref=claim.ref, value=claim.value) for claim in output.counts),
    )


def first_word(name: str) -> str:
    return normalize_name(WORD_SPLIT.split(name.strip())[0]) if name.strip() else ""


def mentioned(text: str, name: str, min_letters: int, distinct_first: bool = True) -> bool:
    haystack = normalize_name(text)
    needle = normalize_name(name)
    if not needle:
        return False
    if re.search(rf"(?<!\w){re.escape(needle)}", haystack) is not None:
        return True
    head = first_word(name)
    if not distinct_first or len(head) < min_letters:
        return False
    return re.search(rf"(?<!\w){re.escape(head)}", haystack) is not None


def finding(kind: ChronicleAuditKind, **values: object) -> ChronicleAuditFinding:
    return ChronicleAuditFinding.model_validate({"kind": kind, **values})


def rejected_findings(facts: EpochFacts, text: ChronicleText, coverage: ChronicleCoverage, taken_heads: set[str], rules: Rules) -> list[ChronicleAuditFinding]:
    minimum = rules.chronicle_audit.name_min_letters
    found: list[ChronicleAuditFinding] = []
    spotted: set[int] = set()
    for entity_id, name in facts.rejected.items():
        distinct = len(WORD_SPLIT.split(name.strip())) > 1 and first_word(name) not in taken_heads
        for world_id, part in text.parts():
            for sentence in sentences(part):
                if mentioned(sentence, name, minimum, distinct):
                    spotted.add(entity_id)
                    found.append(finding(ChronicleAuditKind.REJECTED_MENTIONED, name=name, sentence=sentence, world_id=world_id))
    for entity_id in coverage.entity_ids:
        if entity_id in facts.rejected and entity_id not in spotted:
            found.append(finding(ChronicleAuditKind.REJECTED_MENTIONED, name=facts.rejected[entity_id]))
    return found


def coverage_findings(facts: EpochFacts, text: ChronicleText, coverage: ChronicleCoverage, rules: Rules) -> list[ChronicleAuditFinding]:
    minimum = rules.chronicle_audit.name_min_letters
    whole = text.whole()
    covered = set(coverage.covered)
    reported = bool(covered)

    def told(ref: str) -> bool:
        return ref in covered or any(mentioned(whole, name, minimum) for name in facts.names.get(ref, []))

    found: list[ChronicleAuditFinding] = []
    for son in facts.sons:
        if not told(son.ref):
            found.append(
                finding(ChronicleAuditKind.SON_SKIPPED, ref=son.ref, name=son.name, detail="; ".join(son.deeds) or None, world_id=facts.world_of.get(son.ref))
            )
    for event in facts.events:
        if not told(event.ref) and (reported or facts.names.get(event.ref)):
            found.append(finding(ChronicleAuditKind.EVENT_SKIPPED, ref=event.ref, detail=event.text, world_id=facts.world_of.get(event.ref)))
    for verdict in facts.verdicts:
        if not told(verdict.ref) and (reported or facts.names.get(verdict.ref)):
            found.append(finding(ChronicleAuditKind.VERDICT_SKIPPED, ref=verdict.ref, detail=verdict.text))
    return found


def claim_findings(facts: EpochFacts, coverage: ChronicleCoverage, rules: Rules) -> list[ChronicleAuditFinding]:
    found: list[ChronicleAuditFinding] = []
    contests = {outcome.ref: outcome for outcome in facts.outcomes}
    for claim in coverage.outcomes:
        outcome = contests.get(claim.ref)
        if outcome is not None and claim.winner_id != outcome.winner_id:
            stated = facts.actor_names.get(claim.winner_id, str(claim.winner_id))
            found.append(
                finding(
                    ChronicleAuditKind.WINNER_AS_LOSER,
                    ref=claim.ref,
                    name=outcome.winner,
                    detail=outcome.contest or outcome.kind.value,
                    stated=stated,
                    actual=outcome.winner,
                )
            )
    for actor_id in dict.fromkeys(coverage.idle_actor_ids):
        deeds = facts.actor_deeds.get(actor_id, 0)
        if deeds >= rules.chronicle_audit.silent_min_deeds:
            found.append(finding(ChronicleAuditKind.ACTIVE_AS_SILENT, name=facts.actor_names.get(actor_id), actual=str(deeds)))
    for credit in coverage.credits:
        owner = facts.deed_owner.get(credit.entity_id)
        if owner is not None and credit.actor_id != owner:
            found.append(
                finding(
                    ChronicleAuditKind.DEED_MISCREDITED,
                    name=facts.record_names.get(credit.entity_id),
                    stated=facts.actor_names.get(credit.actor_id, str(credit.actor_id)),
                    actual=facts.actor_names.get(owner),
                )
            )
    for count in coverage.counts:
        actual = facts.counts.get(count.ref)
        if actual is not None and count.value != actual:
            label = ", ".join(facts.names.get(count.ref, [])) or count.ref
            found.append(finding(ChronicleAuditKind.NUMBER_CONTRADICTION, ref=count.ref, detail=label, stated=str(count.value), actual=str(actual)))
    return found


def audit(facts: EpochFacts, text: ChronicleText, coverage: ChronicleCoverage, taken_heads: set[str], rules: Rules) -> list[ChronicleAuditFinding]:
    if not text.whole().strip():
        return []
    return [
        *rejected_findings(facts, text, coverage, taken_heads, rules),
        *coverage_findings(facts, text, coverage, rules),
        *claim_findings(facts, coverage, rules),
    ]


def weight(findings: Iterable[ChronicleAuditFinding], rules: Rules) -> int:
    settings = rules.chronicle_audit
    return sum(settings.heavy_weight if item.kind in HEAVY_AUDIT_KINDS else settings.light_weight for item in findings)


def drop_sentences(text: str, banned: set[str]) -> tuple[str, int]:
    removed = 0
    paragraphs = []
    for paragraph in PARAGRAPHS.split(text):
        parts = sentences(paragraph)
        kept = [part for part in parts if part not in banned]
        removed += len(parts) - len(kept)
        paragraphs.append(" ".join(kept) if len(kept) < len(parts) else paragraph)
    cleaned = EXTRA_BLANK_LINES.sub("\n\n", "\n".join(paragraphs)).strip()
    return (cleaned, removed) if cleaned else (text, 0)


def repair(text: ChronicleText, findings: Iterable[ChronicleAuditFinding], rules: Rules) -> tuple[ChronicleText, int]:
    banned = {item.sentence for item in findings if item.kind is ChronicleAuditKind.REJECTED_MENTIONED and item.sentence}
    narrative, changed = drop_sentences(text.narrative, banned)
    repeated = {sentence.strip() for sentence in sentences(narrative) if len(sentence.strip()) >= rules.chronicle_audit.duplicate_sentence_chars}
    sections: dict[int, str] = {}
    for world_id, section in text.sections.items():
        cleaned, removed = drop_sentences(section, banned | repeated)
        sections[world_id] = cleaned
        changed += removed
    return ChronicleText(narrative, sections), changed


async def taken_first_words(runtime: AgentRuntime, rejected: Iterable[int]) -> set[str]:
    excluded = set(rejected)
    async with runtime.database.read() as session:
        rows = await session.execute(select(NodeRow.id, NodeRow.name))
        return {first_word(name) for node_id, name in rows if node_id not in excluded and name}


def finding_items(findings: Iterable[ChronicleAuditFinding], worlds: dict[int, str], limit: int) -> list[AuditFindingItem]:
    return [
        AuditFindingItem(
            kind=item.kind.value,
            ref=item.ref,
            name=item.name,
            world=worlds.get(item.world_id) if item.world_id is not None else None,
            sentence=item.sentence,
            detail=item.detail,
            stated=item.stated,
            actual=item.actual,
        )
        for item in list(findings)[:limit]
    ]


async def rewrite(
    runtime: AgentRuntime, rules: Rules, facts: EpochFacts, text: ChronicleText, *, findings: list[ChronicleAuditFinding], worlds: list[WorldItem]
) -> tuple[ChronicleText, ChronicleCoverage]:
    async with runtime.database.read() as session:
        scope = await load_scope(session, rules)
        system = ChroniclerSystemContext(lore_language=scope.cosmos.lore_language, world_name=scope.cosmos.name)
        language = scope.cosmos.lore_language
    names = {world.id: world.name for world in worlds}
    context = ChroniclerAuditFixContext(
        lore_language=language,
        rules=rules,
        facts=facts.sheet,
        findings=finding_items(findings, names, rules.chronicle_audit.findings_shown),
        narrative=text.narrative,
        worlds=worlds if len(worlds) > 1 else [],
        sections=dict(text.sections) if len(worlds) > 1 else {},
    )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CHRONICLE_FIX,
        system=(PromptId.CHRONICLER_SYSTEM, system),
        user=(PromptId.CHRONICLER_AUDIT_FIX_USER, context),
        output=ChronicleFixOutput,
        time_limit=rules.chronicle_audit.rewrite_timeout,
    )
    sections = dict(text.sections)
    for section in output.worlds or []:
        if section.world_id in sections and section.narrative.strip():
            sections[section.world_id] = sanitize(section.narrative)
    return ChronicleText(sanitize(output.narrative) or text.narrative, sections), coverage_from(output.coverage)


async def review(
    runtime: AgentRuntime, epoch: int, text: ChronicleText, coverage: ChronicleCoverage, *, allow_rewrite: bool = True
) -> tuple[ChronicleText, ChronicleAuditReport]:
    rules = await runtime.current_rules()
    if not rules.chronicle_audit.enabled or not text.narrative.strip():
        return text, ChronicleAuditReport(coverage=coverage)
    async with runtime.database.read() as session:
        scope = await load_scope(session, rules)
        facts = await epoch_facts(scope, epoch)
        worlds = living_world_items(scope, epoch)
    taken = await taken_first_words(runtime, facts.rejected)
    findings = audit(facts, text, coverage, taken, rules)
    first = len(findings)
    rewritten = False
    if findings and allow_rewrite and rules.chronicle_audit.rewrite and runtime.llm_enabled:
        try:
            candidate, candidate_coverage = await rewrite(runtime, rules, facts, text, findings=findings, worlds=worlds)
            again = audit(facts, candidate, candidate_coverage, taken, rules)
            if weight(again, rules) < weight(findings, rules):
                text, coverage, findings, rewritten = candidate, candidate_coverage, again, True
        except Exception as error:
            runtime.error(f"The chronicle correction could not be written: {error}")
    repaired, changed = repair(text, findings, rules)
    remaining = audit(facts, repaired, coverage, taken, rules)
    if first:
        corrected = ", the chronicler corrected them" if rewritten else ""
        findings_counted = several(first, "finding", "findings")
        sentences_counted = several(changed, "sentence", "sentences")
        runtime.step(f"Chronicle audit: {findings_counted}{corrected}, {len(remaining)} remain; {sentences_counted} repaired by rule.")
    return repaired, ChronicleAuditReport(found=first, remaining=tuple(remaining), rewritten=rewritten, repaired_sentences=changed, coverage=coverage)
