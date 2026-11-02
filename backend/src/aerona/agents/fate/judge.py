import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.chronicler import age_events
from aerona.agents.context.fate_judgment import fate_judgment_context
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.fate.apply import FateApplied, FateRuling, Marker, apply_fate_ruling
from aerona.agents.fate.selection import Fitted, batches, fit, old_prophecies, records_to_judge
from aerona.agents.fate.threads import ThreadQuota, quota, thread_states
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.constants.agents import SESSION_ERROR_CHARS
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import FateMode
from aerona.prompts import PromptId
from aerona.prompts.contexts.fate import FateExtraJudgmentContext, FateSystemContext
from aerona.prompts.schemas.constraints import ITEMS, ArrayBounds, Constraint, EnumValues, OmitField, RequireField
from aerona.prompts.schemas.fate import ExtraJudgmentOutput, FateJudgmentOutput, VerdictOutput
from aerona.rules.registry import Rules

UNLIMITED = float("inf")


@dataclass
class FateInputs:
    epoch: int
    start: int
    fate_off: bool
    judged: Fitted
    overflow: list[EntityRow]
    pending: Fitted
    prophecies: Fitted
    quota: ThreadQuota
    system: FateSystemContext
    unjudged_ids: list[int] = field(default_factory=list)
    language_ids: list[int] = field(default_factory=list)
    events: str = ""


async def gather_inputs(scope: Scope, epoch: int) -> FateInputs:
    cosmos = scope.cosmos
    start = min(epoch, cosmos.fate_debt_epoch) if cosmos.fate_debt_epoch is not None else epoch
    fate_off = cosmos.fate_mode is FateMode.OFF
    records = await records_to_judge(scope, start, epoch)
    overflow: list[EntityRow] = []
    if fate_off:
        judged = Fitted()
    else:
        judged, overflow = await fit(scope, records, scope.rules.fate.budget_new_creations_chars, True)
    pending_rows = list(await scope.session.scalars(select(EntityRow).where(EntityRow.pending_name.is_(True)).order_by(EntityRow.world_id, EntityRow.id)))
    pending, _ = await fit(scope, pending_rows, UNLIMITED, False)
    languages = await scope.session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON))
    return FateInputs(
        epoch=epoch,
        start=start,
        fate_off=fate_off,
        judged=judged,
        overflow=overflow,
        pending=pending,
        prophecies=await old_prophecies(scope, epoch),
        quota=quota(scope.rules, await thread_states(scope.session, scope.rules, epoch)),
        unjudged_ids=[record.id for record in records] if fate_off else [],
        language_ids=list(languages),
        system=FateSystemContext(lore_language=cosmos.lore_language, world_name=cosmos.name),
        events=await age_events(scope, epoch),
    )


def judgment_constraints(rules: Rules, inputs: FateInputs) -> list[Constraint]:
    fate = rules.fate
    candidates = inputs.quota.candidates
    constraints: list[Constraint] = [
        ArrayBounds(("closed_threads",), min_items=max(0, inputs.quota.min_close - (1 if candidates else 0))),
        ArrayBounds(("new_threads",), max_items=inputs.quota.new_max),
        ArrayBounds(("facts",), min_items=min(fate.canon_facts_min, fate.canon_facts_max, len(inputs.judged.ids) + len(inputs.pending.ids))),
    ]
    if candidates:
        constraints += [EnumValues(("resolved_thread", "id"), tuple(candidates)), RequireField(("resolved_thread",))]
    else:
        constraints.append(OmitField(("resolved_thread",)))
    if inputs.language_ids:
        constraints.append(EnumValues(("words", ITEMS, "language_id"), tuple(inputs.language_ids)))
    if inputs.quota.closable_ids:
        constraints.append(EnumValues(("closed_threads", ITEMS, "id"), tuple(inputs.quota.closable_ids)))
    return constraints


async def judgment(runtime: AgentRuntime, rules: Rules, inputs: FateInputs, engine_notes: Sequence[str]) -> FateJudgmentOutput:
    async with runtime.database.read() as session:
        scope = await load_scope(session, rules)
        context = await fate_judgment_context(
            scope,
            inputs.epoch,
            age_events=inputs.events,
            engine_notes=engine_notes,
            creations=inputs.judged.entries,
            pending=inputs.pending.entries,
            prophecies=inputs.prophecies.entries,
            quota=inputs.quota,
        )
    return await ask(
        runtime.model,
        rules,
        label=AgentRole.FATE,
        system=(PromptId.FATE_JUDGMENT_SYSTEM, inputs.system),
        user=(PromptId.FATE_JUDGMENT_USER, context),
        output=FateJudgmentOutput,
        time_limit=rules.fate.fate_timeout,
        constraints=judgment_constraints(rules, inputs),
    )


async def extra_round(runtime: AgentRuntime, rules: Rules, inputs: FateInputs, batch: Fitted) -> list[VerdictOutput]:
    async with runtime.database.read() as session:
        header = await world_header(await load_scope(session, rules))
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.FATE_EXTRA,
        system=(PromptId.FATE_JUDGMENT_SYSTEM, inputs.system),
        user=(PromptId.FATE_EXTRA_JUDGMENT_USER, FateExtraJudgmentContext(world_header=header, entries=batch.entries)),
        output=ExtraJudgmentOutput,
        time_limit=rules.fate.fate_timeout,
    )
    return [verdict for verdict in output.verdicts if verdict.id in batch.ids]


@dataclass
class OverflowResult:
    verdicts: list[VerdictOutput] = field(default_factory=list)
    epochs: dict[int, int] = field(default_factory=dict)
    debt: int | None = None


async def judge_overflow(runtime: AgentRuntime, rules: Rules, inputs: FateInputs) -> OverflowResult:
    result = OverflowResult()
    async with runtime.database.read() as session:
        scope = await load_scope(session, rules)
        rounds = await batches(scope, inputs.overflow, rules.fate.budget_new_creations_chars)
    group_size = rules.fate.judgment_parallel
    runtime.step(f"Fate is weighing the remaining {len(inputs.overflow)} creations of this age in {len(rounds)} rounds.")
    for start in range(0, len(rounds), group_size):
        group = rounds[start : start + group_size]
        outcomes = await asyncio.gather(*(extra_round(runtime, rules, inputs, batch) for batch in group), return_exceptions=True)
        failed = [batch for batch, outcome in zip(group, outcomes, strict=True) if isinstance(outcome, BaseException)]
        for batch, outcome in zip(group, outcomes, strict=True):
            if not isinstance(outcome, BaseException):
                result.verdicts.extend(outcome)
                result.epochs.update(batch.epochs)
        if failed:
            left = failed + rounds[start + group_size :]
            result.debt = min(epoch for batch in left for epoch in batch.epochs.values())
            error = next(outcome for outcome in outcomes if isinstance(outcome, BaseException))
            count = sum(len(batch.ids) for batch in left)
            runtime.error(f"Fate could not weigh the remaining {count} creations ({error}); it will be the first task of the next age.")
            break
    return result


async def unjudged_verdicts(runtime: AgentRuntime, ids: Sequence[int], epoch: int) -> None:
    async with runtime.database.write() as session:
        for entity_id in ids:
            entity = await session.get(EntityRow, entity_id)
            if entity is None:
                continue
            row = await session.get(CreationVerdictRow, entity_id)
            if row is None:
                session.add(CreationVerdictRow(entity_id=entity_id, epoch=entity.birth_epoch, verdict=Verdict.UNJUDGED, judged_epoch=epoch))


async def run_fate(runtime: AgentRuntime, epoch: int, engine_notes: Sequence[str], marker: Marker | None = None) -> FateApplied:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        inputs = await gather_inputs(await load_scope(session, rules), epoch)
    if inputs.unjudged_ids:
        await unjudged_verdicts(runtime, inputs.unjudged_ids, epoch)
    output: FateJudgmentOutput | None = None
    debt: int | None = None
    verdicts: list[VerdictOutput] = []
    judged_epochs = dict(inputs.judged.epochs)
    if runtime.llm_enabled:
        runtime.step(f"Fate is weighing {len(inputs.judged.ids) + len(inputs.overflow)} creations, naming {len(inputs.pending.ids)} unnamed records.")
        started = time.monotonic()
        try:
            output = await judgment(runtime, rules, inputs, engine_notes)
            verdicts = list(output.verdicts)
            runtime.step(f"Fate gave its verdict ({round(time.monotonic() - started)} s).")
        except Exception as error:
            debt = inputs.start if inputs.judged.ids or inputs.overflow else None
            runtime.error(
                f"Fate could not give a verdict this age ({str(error)[:SESSION_ERROR_CHARS]}). "
                "The creations remain in the canon; Fate will weigh them next age."
            )
        if output is not None and inputs.overflow:
            overflow = await judge_overflow(runtime, rules, inputs)
            verdicts.extend(overflow.verdicts)
            judged_epochs.update(overflow.epochs)
            debt = overflow.debt
            if debt is None:
                runtime.note(f"Fate weighed all {len(judged_epochs)} creations of this age.")
    else:
        pending_debt = [*inputs.judged.epochs.values(), *(entity.birth_epoch for entity in inputs.overflow)]
        debt = min(pending_debt) if pending_debt else None
    ruling = FateRuling(
        epoch=epoch,
        judged_epochs=judged_epochs,
        pending_ids=set(inputs.pending.ids),
        prophecy_ids=set(inputs.prophecies.ids),
        output=output,
        verdicts=verdicts,
        debt=debt,
        fate_off=inputs.fate_off,
    )
    async with runtime.database.write() as session:
        applied = await apply_fate_ruling(session, rules, ruling, marker)
    return applied
