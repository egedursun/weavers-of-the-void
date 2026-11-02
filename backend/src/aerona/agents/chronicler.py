from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.chronicle_audit import ChronicleText, coverage_from, review
from aerona.agents.context.chronicler import banned_openings, chronicler_context, living_world_items, opening_patterns
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import replace_name, sanitize, sentences
from aerona.constants.agents import AGE_NAME_ORDINALS, CHRONICLER_IDENTITY_CHARS, CHRONICLER_NAME_CHARS
from aerona.db.repositories.names import normalize_name
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.domain.models.records import ChronicleAuditReport, ChronicleCoverage
from aerona.prompts import PromptId
from aerona.prompts.contexts.chronicler import ChroniclerFixOpeningContext, ChroniclerSystemContext, ChroniclerUserContext
from aerona.prompts.contexts.common import WorldItem
from aerona.prompts.schemas.constraints import ArrayBounds, Constraint, EnumValues, OmitField, RequireField
from aerona.prompts.schemas.fate import ChronicleOutput, FirstSentenceOutput, WorldSectionOutput, WorldSectionsOutput
from aerona.rules.registry import Rules

ITEMS = "[]"


@dataclass
class Chronicle:
    age_name: str
    narrative: str
    summary: str
    chronicler_name: str | None = None
    chronicler_identity: str | None = None
    worlds: dict[int, WorldSectionOutput] = field(default_factory=dict)
    coverage: ChronicleCoverage = field(default_factory=ChronicleCoverage)
    audit: ChronicleAuditReport | None = None


def world_constraints(worlds: Sequence[WorldItem], path: tuple[str, ...]) -> list[Constraint]:
    ids = tuple(world.id for world in worlds)
    return [ArrayBounds(path, len(ids), len(ids)), EnumValues((*path, ITEMS, "world_id"), ids)]


def chronicle_constraints(worlds: Sequence[WorldItem]) -> list[Constraint]:
    required: list[Constraint] = [RequireField(("coverage",))]
    if len(worlds) < 2:
        return [*required, OmitField(("worlds",))]
    return [*required, *world_constraints(worlds, ("worlds",))]


def from_output(output: ChronicleOutput) -> Chronicle:
    return Chronicle(
        age_name=sanitize(output.age_name),
        narrative=sanitize(output.narrative),
        summary=sanitize(output.summary),
        chronicler_name=output.chronicler.name.strip()[:CHRONICLER_NAME_CHARS] or None,
        chronicler_identity=output.chronicler.who.strip()[:CHRONICLER_IDENTITY_CHARS] or None,
        worlds={section.world_id: section for section in output.worlds or []},
        coverage=coverage_from(output.coverage),
    )


def system_context(scope: Scope) -> ChroniclerSystemContext:
    return ChroniclerSystemContext(lore_language=scope.cosmos.lore_language, world_name=scope.cosmos.name)


async def write_chronicle(runtime: AgentRuntime, epoch: int, engine_notes: Sequence[str]) -> Chronicle:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        context = await chronicler_context(scope, epoch, engine_notes)
        system = system_context(scope)
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CHRONICLER,
        system=(PromptId.CHRONICLER_SYSTEM, system),
        user=(PromptId.CHRONICLER_USER, context),
        output=ChronicleOutput,
        time_limit=rules.fate.fate_timeout,
        constraints=chronicle_constraints(context.worlds),
    )
    return from_output(output)


async def fix_opening(runtime: AgentRuntime, chronicle: Chronicle, epoch: int) -> None:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        patterns = await opening_patterns(scope, epoch)
        system = system_context(scope)
    first = (sentences(chronicle.narrative) or [""])[0]
    found = banned_openings(first, patterns)
    if not rules.fate.opening_fix or not first or not found:
        return
    rest = chronicle.narrative[len(first) : len(first) + rules.fate.budget_chronicler_engine_chars]
    context = ChroniclerFixOpeningContext(lore_language=scope.cosmos.lore_language, rules=rules, patterns=found, first_sentence=first, continuation=rest)
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CHRONICLE_FIX,
        system=(PromptId.CHRONICLER_SYSTEM, system),
        user=(PromptId.CHRONICLER_FIX_OPENING_USER, context),
        output=FirstSentenceOutput,
        time_limit=rules.fate.fate_timeout,
    )
    replacement = sanitize(output.first_sentence)
    if replacement and not banned_openings(replacement, patterns):
        chronicle.narrative = replacement + chronicle.narrative[len(first) :]


async def missing_world_sections(runtime: AgentRuntime, epoch: int, missing: Sequence[WorldItem], prompt: PromptId) -> dict[int, WorldSectionOutput]:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        context = await chronicler_context(scope, epoch, worlds=living_world_items(scope, epoch), missing=missing, with_pending=False)
        system = system_context(scope)
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CHRONICLE_FIX,
        system=(PromptId.CHRONICLER_CONCISE_SYSTEM, system),
        user=(prompt, context),
        output=WorldSectionsOutput,
        time_limit=rules.fate.fate_timeout,
        constraints=world_constraints(missing, ("worlds",)),
    )
    return {section.world_id: section for section in output.worlds if section.world_id in {world.id for world in missing}}


async def complete_chronicle(runtime: AgentRuntime, chronicle: Chronicle, epoch: int) -> None:
    rules = await runtime.current_rules()
    try:
        await fix_opening(runtime, chronicle, epoch)
    except Exception as error:
        runtime.error(f"Chronicle completion: {error}")
    async with runtime.database.read() as session:
        worlds = living_world_items(await load_scope(session, rules), epoch)
    missing = [world for world in worlds if world.id not in chronicle.worlds]
    if len(worlds) > 1 and missing and rules.fate.complete_missing_worlds:
        try:
            chronicle.worlds.update(await missing_world_sections(runtime, epoch, missing, PromptId.CHRONICLER_MISSING_WORLDS_USER))
        except Exception as error:
            runtime.error(f"Chronicle completion: {error}")


async def audit_chronicle(runtime: AgentRuntime, chronicle: Chronicle, epoch: int) -> None:
    text = ChronicleText(chronicle.narrative, {world_id: section.narrative for world_id, section in chronicle.worlds.items()})
    try:
        repaired, report = await review(runtime, epoch, text, chronicle.coverage)
    except Exception as error:
        runtime.error(f"Chronicle audit: {error}")
        return
    chronicle.narrative = repaired.narrative
    for world_id, narrative in repaired.sections.items():
        section = chronicle.worlds.get(world_id)
        if section is not None and narrative != section.narrative:
            chronicle.worlds[world_id] = section.model_copy(update={"narrative": narrative})
    chronicle.coverage = report.coverage
    chronicle.audit = report


async def unique_age_name(scope: Scope, name: str, epoch: int) -> str:
    taken = {
        normalize_name(row) for row in await scope.session.scalars(select(EpochRow.name).where(EpochRow.epoch != epoch, EpochRow.name.is_not(None))) if row
    }
    if normalize_name(name) not in taken:
        return name
    for ordinal in AGE_NAME_ORDINALS:
        candidate = f"{ordinal} {name}"
        if normalize_name(candidate) not in taken:
            return candidate
    return f"{name} (Age {epoch})"


def apply_renames(chronicle: Chronicle, renames: Sequence[tuple[str, str]]) -> None:
    for old, new in renames:
        chronicle.narrative = replace_name(chronicle.narrative, old, new)
        chronicle.summary = replace_name(chronicle.summary, old, new)
        for world_id, section in list(chronicle.worlds.items()):
            chronicle.worlds[world_id] = section.model_copy(
                update={"narrative": replace_name(section.narrative, old, new), "summary": replace_name(section.summary, old, new)}
            )


async def record_age(scope: Scope, chronicle: Chronicle, epoch: int) -> EpochRow:
    rules: Rules = scope.rules
    row = await scope.session.get(EpochRow, epoch)
    years = rules.time.years_per_epoch
    if row is None:
        row = EpochRow(epoch=epoch)
        scope.session.add(row)
    row.name = await unique_age_name(scope, chronicle.age_name, epoch) if chronicle.age_name else row.name
    row.narrative = chronicle.narrative or row.narrative
    row.summary = chronicle.summary or row.summary
    row.year_start = epoch_start_year(epoch, years)
    row.year_end = epoch_end_year(epoch, years)
    row.closed_at = datetime.now(UTC)
    row.chronicler_name = chronicle.chronicler_name or row.chronicler_name
    row.chronicler_identity = chronicle.chronicler_identity or row.chronicler_identity
    row.audit = chronicle.audit or row.audit
    for world_id, section in chronicle.worlds.items():
        if world_id not in scope.worlds:
            continue
        existing = await scope.session.get(EpochWorldNarrativeRow, (epoch, world_id))
        if existing is None:
            scope.session.add(EpochWorldNarrativeRow(epoch=epoch, world_id=world_id, narrative=sanitize(section.narrative), summary=sanitize(section.summary)))
        else:
            existing.narrative = sanitize(section.narrative)
            existing.summary = sanitize(section.summary)
    await scope.session.flush()
    return row


async def lost_chronicle_epochs(scope: Scope, limit: int) -> list[int]:
    written = select(EpochRow.epoch).where(EpochRow.narrative.is_not(None))
    rows = await scope.session.scalars(
        select(ChronicleRow.epoch)
        .where(ChronicleRow.epoch < scope.epoch, ChronicleRow.epoch.not_in(written))
        .distinct()
        .order_by(ChronicleRow.epoch)
        .limit(limit)
    )
    return list(rows)


async def epochs_missing_sections(scope: Scope, limit: int) -> list[tuple[int, list[WorldItem]]]:
    found: list[tuple[int, list[WorldItem]]] = []
    rows = await scope.session.scalars(select(EpochRow).where(EpochRow.epoch < scope.epoch, EpochRow.narrative.is_not(None)).order_by(EpochRow.epoch.desc()))
    for row in rows:
        worlds = living_world_items(scope, row.epoch)
        if len(worlds) < 2:
            continue
        written = set(await scope.session.scalars(select(EpochWorldNarrativeRow.world_id).where(EpochWorldNarrativeRow.epoch == row.epoch)))
        missing = [world for world in worlds if world.id not in written]
        if missing:
            found.append((row.epoch, missing))
        if len(found) >= limit:
            break
    return found


async def backfill_epoch(runtime: AgentRuntime, epoch: int) -> None:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        context: ChroniclerUserContext = await chronicler_context(scope, epoch, with_pending=False)
        system = system_context(scope)
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.LOST_CHRONICLE,
        system=(PromptId.CHRONICLER_SYSTEM, system),
        user=(PromptId.CHRONICLER_LOST_AGE_USER, context),
        output=ChronicleOutput,
        time_limit=rules.fate.backfill_timeout,
        constraints=chronicle_constraints(context.worlds),
    )
    chronicle = from_output(output)
    await audit_chronicle(runtime, chronicle, epoch)
    async with runtime.database.write() as session:
        await record_age(await load_scope(session, rules), chronicle, epoch)


async def backfill_chronicles(runtime: AgentRuntime) -> int:
    rules = await runtime.current_rules()
    async with runtime.database.read() as session:
        scope = await load_scope(session, rules)
        lost = await lost_chronicle_epochs(scope, rules.fate.backfill_chronicles)
    written = 0
    for epoch in lost:
        runtime.step(f"The chronicle of Age {epoch} is being written…")
        try:
            await backfill_epoch(runtime, epoch)
            written += 1
        except Exception as error:
            runtime.error(f"The chronicle of Age {epoch} still could not be written: {error}")
    async with runtime.database.read() as session:
        gaps = await epochs_missing_sections(await load_scope(session, rules), rules.fate.backfill_world_sections)
    for epoch, missing in gaps:
        try:
            sections = await missing_world_sections(runtime, epoch, missing, PromptId.CHRONICLER_LOST_WORLD_SECTIONS_USER)
        except Exception as error:
            runtime.error(f"The world sections of Age {epoch} could not be written: {error}")
            continue
        async with runtime.database.write() as session:
            scope = await load_scope(session, rules)
            row = await session.get(EpochRow, epoch)
            if row is not None:
                await record_age(scope, Chronicle(age_name="", narrative="", summary="", worlds=sections), epoch)
    return written
