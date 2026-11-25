import asyncio
import heapq
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import BusyError, ConflictError, NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.authorship import may_see
from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillArtifactRow, DivineWillArtifactVersionRow, DivineWillPlanRow, DivineWillPlanStepRow
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, DivineWillMode, PlanStatus, StepImpact, StepStatus
from aerona.domain.enums.job import TERMINAL_JOB_STATUSES, JobKind, JobStatus
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.audience import private_audience
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.services.divine_will.artifacts import add_version, store_artifact
from aerona.services.divine_will.ownership import ownership_of
from aerona.services.divine_will.rule_steps import RULE_ACTIONS, RuleSteps, is_rule_step, rule_problem, wanted
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.team.execute import stepping
from aerona.tools.divine_will.framework import PlayerPort
from aerona.tools.divine_will.library_ports import ArtifactDraft, PlanStepView, PlanView, StepDraft

PlayerFactory = Callable[[str], PlayerPort]
WAITS_FOR_AGE = "Step {ordinal} waits in the queue for the age to end."
WAITS_FOR_APPROVAL = "Step {ordinal} waits for an administrator's approval."
FINISHED_STEPS = frozenset({StepStatus.DONE, StepStatus.SKIPPED, StepStatus.UNDONE})
OPEN_STEPS = frozenset({StepStatus.PENDING, StepStatus.FAILED})
SETTLED_PLANS = frozenset({PlanStatus.DONE, PlanStatus.ABANDONED})
RUNNABLE_PLANS = frozenset({PlanStatus.APPROVED, PlanStatus.PAUSED, PlanStatus.FAILED})
EDITABLE_PLANS = frozenset({PlanStatus.DRAFT, PlanStatus.APPROVED, PlanStatus.RUNNING, PlanStatus.PAUSED, PlanStatus.FAILED})
TERMINAL_JOBS = frozenset(status.value for status in TERMINAL_JOB_STATUSES)
JOB_POLL_SECONDS = 1.0
PLAN_ID_KEY = "plan_id"
STOPPED_MIDWAY = "The plan stopped while this step ran; read the ledger to see whether it took effect before running it again."
BUSY_WORLD = "The world is busy with an epoch or another plan; run the plan once it has finished."
PLAN_TIME_FORMAT = "%Y-%m-%d %H:%M"
PLAN_LABELS: dict[PlanStatus, str] = {
    PlanStatus.DRAFT: "Draft, waiting for approval",
    PlanStatus.APPROVED: "Approved, ready to run",
    PlanStatus.RUNNING: "Running",
    PlanStatus.PAUSED: "Paused",
    PlanStatus.DONE: "Done",
    PlanStatus.FAILED: "Stopped at a failed step",
    PlanStatus.ABANDONED: "Abandoned",
}
STEP_LABELS: dict[StepStatus, str] = {
    StepStatus.PENDING: "Waiting",
    StepStatus.RUNNING: "Running",
    StepStatus.DONE: "Done",
    StepStatus.SKIPPED: "Skipped",
    StepStatus.FAILED: "Failed",
    StepStatus.UNDONE: "Undone",
}
IMPACT_LABELS: dict[StepImpact, str] = {StepImpact.SAFE: "Safe", StepImpact.COSTLY: "Costly", StepImpact.DESTRUCTIVE: "Destructive"}


def input_problems(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(part) for part in item['loc']) or 'input'}: {item['msg']}" for item in error.errors(include_url=False))


def cycle_in(drafts: Sequence[StepDraft]) -> list[int]:
    remaining = {number: set(draft.depends_on) for number, draft in enumerate(drafts, start=1)}
    changed = True
    while changed:
        changed = False
        for number in [number for number, needs in remaining.items() if not needs & set(remaining)]:
            del remaining[number]
            changed = True
    return sorted(remaining)


def checked(drafts: Sequence[StepDraft]) -> list[StepDraft]:
    if not drafts:
        raise ValidationFailedError("A plan needs at least one step.")
    problems: list[str] = []
    count = len(drafts)
    for number, draft in enumerate(drafts, start=1):
        spec = ACTIONS_BY_ID.get(draft.action_id)
        if is_rule_step(draft.action_id):
            problem = rule_problem(draft.action_id, draft.input)
            if problem:
                problems.append(f"Step {number} ({draft.action_id}): {problem.rstrip('.')}.")
        elif spec is None:
            problems.append(f"Step {number}: there is no act called {draft.action_id}; find it with search_actions.")
            continue
        else:
            try:
                spec.input_model.model_validate(draft.input)
            except ValidationError as error:
                problems.append(f"Step {number} ({draft.action_id}): the input did not fit: {input_problems(error)}.")
        wrong = [needed for needed in draft.depends_on if needed < 1 or needed > count or needed == number]
        if wrong:
            problems.append(f"Step {number}: it can only depend on other steps of this plan, numbered 1 to {count}; not {', '.join(map(str, wrong))}.")
    if not problems:
        looped = cycle_in(drafts)
        if looped:
            problems.append(f"Steps {', '.join(map(str, looped))} wait on each other in a circle; break the circle.")
    if problems:
        raise ValidationFailedError(" ".join(problems))
    return list(drafts)


def run_order(steps: Sequence[DivineWillPlanStepRow]) -> list[DivineWillPlanStepRow]:
    by_ordinal = {step.ordinal: step for step in steps}
    waiting = {step.ordinal: {needed for needed in step.depends_on if needed in by_ordinal} for step in steps}
    ready = [ordinal for ordinal, needs in waiting.items() if not needs]
    heapq.heapify(ready)
    ordered: list[DivineWillPlanStepRow] = []
    while ready:
        ordinal = heapq.heappop(ready)
        ordered.append(by_ordinal[ordinal])
        for other, needs in waiting.items():
            if ordinal in needs:
                needs.discard(ordinal)
                if not needs:
                    heapq.heappush(ready, other)
    return ordered


def destruction(preview: Mapping[str, Any]) -> str:
    parts: list[str] = []
    nodes = [str(item.get("name") or item.get("node_id")) for item in preview.get("deleted_nodes", [])]
    if nodes:
        parts.append(f"it deletes {', '.join(nodes)}")
    records = len(preview.get("deleted_records", []))
    if records:
        parts.append(f"it deletes {several(records, 'record', 'records')}")
    ended = [str(item.get("node_name") or item.get("key") or "") for item in preview.get("ended", [])]
    if ended:
        parts.append(f"it ends {', '.join(name for name in ended if name) or several(len(ended), 'thing', 'things')}")
    return "; ".join(parts) or "it destroys something"


def undeclared(step: DivineWillPlanStepRow, preview: Mapping[str, Any]) -> str:
    if preview.get("destructive") and step.declared_impact is not StepImpact.DESTRUCTIVE:
        return (
            f"The preview shows destruction this step did not declare ({destruction(preview)}). Declare it destructive and approve the plan again, or skip it."
        )
    if preview.get("costly") and step.declared_impact is StepImpact.SAFE:
        spent = int(preview.get("essence") or 0)
        return f"The preview spends {spent} essence, a costly act this step declared safe. Declare it costly and approve the plan again, or skip it."
    return ""


def act_title(action_id: str) -> str:
    spec = ACTIONS_BY_ID.get(action_id)
    return spec.title if spec is not None else RULE_ACTIONS.get(action_id, action_id)


def step_line(step: DivineWillPlanStepRow) -> str:
    title = act_title(step.action_id)
    lines = [
        f"{step.ordinal}. **{step.title}** — {title} (`{step.action_id}`)",
        f"   - State: {STEP_LABELS[step.status]}",
        f"   - Declared impact: {IMPACT_LABELS[step.declared_impact]}",
        f"   - Estimated essence: {step.estimated_essence}",
    ]
    if step.depends_on:
        lines.append(f"   - Waits for: {', '.join(f'step {needed}' for needed in sorted(step.depends_on))}")
    if step.ledger_entry_id is not None:
        lines.append(f"   - Ledger entry: {step.ledger_entry_id}")
    if step.job_id:
        lines.append(f"   - Job: {step.job_id}")
    if step.result_text:
        lines.append(f"   - Outcome: {step.result_text}")
    if step.error:
        lines.append(f"   - Stopped: {step.error}")
    body = json.dumps(step.input, ensure_ascii=False, indent=2, sort_keys=True)
    lines.extend(["", "   ```json", *(f"   {line}" for line in body.splitlines()), "   ```"])
    return "\n".join(lines)


def plan_body(plan: DivineWillPlanRow, steps: Sequence[DivineWillPlanStepRow]) -> str:
    head = [f"**Plan status:** {PLAN_LABELS[plan.status]}", f"**Steps:** {len(steps)}"]
    if plan.approved_at is not None:
        head.append(f"**Approved:** {plan.approved_at.strftime(PLAN_TIME_FORMAT)}")
    if plan.finished_at is not None:
        head.append(f"**Finished:** {plan.finished_at.strftime(PLAN_TIME_FORMAT)}")
    return "  \n".join(head) + "\n\n" + "\n\n".join(step_line(step) for step in steps) + "\n"


def step_view(step: DivineWillPlanStepRow) -> PlanStepView:
    return PlanStepView(
        ordinal=step.ordinal,
        title=step.title,
        action_id=step.action_id,
        action_title=act_title(step.action_id),
        input=dict(step.input),
        depends_on=sorted(step.depends_on),
        declared_impact=step.declared_impact,
        estimated_essence=step.estimated_essence,
        status=step.status,
        ledger_entry_id=step.ledger_entry_id,
        job_id=step.job_id,
        result_text=step.result_text,
        error=step.error,
    )


def step_rows(plan_id: int, drafts: Sequence[StepDraft], kept: Mapping[int, DivineWillPlanStepRow]) -> list[DivineWillPlanStepRow]:
    rows: list[DivineWillPlanStepRow] = []
    for ordinal, draft in enumerate(drafts, start=1):
        old = kept.get(ordinal)
        if old is not None:
            old.title = draft.title
            rows.append(old)
            continue
        rows.append(
            DivineWillPlanStepRow(
                plan_id=plan_id,
                ordinal=ordinal,
                title=draft.title,
                action_id=draft.action_id,
                input=dict(draft.input),
                depends_on=sorted(set(draft.depends_on)),
                declared_impact=draft.declared_impact,
                estimated_essence=draft.estimated_essence,
            )
        )
    return rows


class PlanDesk:
    def __init__(
        self,
        database: Database,
        bus: EventBus,
        jobs: JobManager,
        player_for: PlayerFactory,
        rules: RuleSteps,
        *,
        poll_seconds: float = JOB_POLL_SECONDS,
    ) -> None:
        self.database = database
        self.bus = bus
        self.jobs = jobs
        self.player_for = player_for
        self.rules = rules
        self.poll_seconds = poll_seconds

    def running_job(self, plan_id: int) -> str:
        holder = self.jobs.busy_group(WORLD_GROUP)
        context = self.jobs.running_context(holder) if holder is not None else None
        return holder if holder is not None and context is not None and context.params.get(PLAN_ID_KEY) == plan_id else ""

    def changed(self, view: PlanView, step: int | None = None) -> None:
        audience = private_audience(view.owner.author_account_id, view.owner.shared)
        payload = {"plan_id": view.id, "status": view.status.value, "cycle_id": view.cycle_id, "step": step}
        self.bus.publish(EventKind.DIVINE_WILL_PLAN_CHANGED, payload, audience=audience)
        if view.artifact_id is not None:
            written = {"artifact_id": view.artifact_id, "version": 0, "cycle_id": view.cycle_id, "deleted": False}
            self.bus.publish(EventKind.DIVINE_WILL_ARTIFACT_CHANGED, written, audience=audience)

    async def plan_row(self, session: AsyncSession, plan_id: int) -> DivineWillPlanRow:
        row = await session.get(DivineWillPlanRow, plan_id)
        if row is None or not may_see(row.author_account_id, row.shared):
            raise NotFoundError(f"No plan {plan_id}.")
        return row

    async def healed(self, session: AsyncSession, plan_id: int) -> DivineWillPlanRow:
        plan = await self.plan_row(session, plan_id)
        if plan.status is PlanStatus.RUNNING and not self.running_job(plan_id):
            plan.status = PlanStatus.PAUSED
            for step in await self.step_rows_of(session, plan_id):
                if step.status is StepStatus.RUNNING:
                    step.status = StepStatus.PENDING
                    step.error = STOPPED_MIDWAY
            await self.mirror(session, plan, "The plan was stopped.")
        return plan

    async def step_rows_of(self, session: AsyncSession, plan_id: int) -> list[DivineWillPlanStepRow]:
        return list(
            await session.scalars(select(DivineWillPlanStepRow).where(DivineWillPlanStepRow.plan_id == plan_id).order_by(DivineWillPlanStepRow.ordinal))
        )

    async def step_row(self, session: AsyncSession, plan_id: int, ordinal: int) -> DivineWillPlanStepRow:
        row = await session.get(DivineWillPlanStepRow, (plan_id, ordinal))
        if row is None:
            raise NotFoundError(f"Plan {plan_id} has no step {ordinal}.")
        return row

    async def view(self, session: AsyncSession, plan: DivineWillPlanRow) -> PlanView:
        steps = await self.step_rows_of(session, plan.id)
        waiting = next((step.ordinal for step in steps if step.status is StepStatus.PENDING and step.error), None) if plan.status is PlanStatus.PAUSED else None
        return PlanView(
            id=plan.id,
            title=plan.title,
            status=plan.status,
            cycle_id=plan.cycle_id,
            artifact_id=plan.artifact_id,
            approved_at=plan.approved_at,
            finished_at=plan.finished_at,
            created_at=plan.created_at,
            steps=[step_view(step) for step in steps],
            job_id=self.running_job(plan.id),
            waiting_step=waiting,
            owner=ownership_of(plan.author_account_id, plan.author_name, plan.shared),
        )

    async def mirror(self, session: AsyncSession, plan: DivineWillPlanRow, summary: str) -> None:
        await session.flush()
        body = plan_body(plan, await self.step_rows_of(session, plan.id))
        artifact = await session.get(DivineWillArtifactRow, plan.artifact_id) if plan.artifact_id is not None else None
        if artifact is None:
            draft = ArtifactDraft(
                plan.title, ArtifactKind.PLAN, ArtifactFormat.MARKDOWN, body, "", DivineWillMode.PLAN, cycle_id=plan.cycle_id, summary=summary
            )
            plan.artifact_id = (await store_artifact(session, draft)).id
            await session.flush()
            return
        current = await session.get(DivineWillArtifactVersionRow, (artifact.id, artifact.current_version))
        artifact.title = plan.title
        if current is None or current.body != body:
            await add_version(session, artifact, body, summary, plan.cycle_id)

    async def create(self, title: str, steps: Sequence[StepDraft], *, cycle_id: int | None) -> PlanView:
        drafts = checked(steps)
        name = title.strip()
        if not name:
            raise ValidationFailedError("A plan needs a title.")
        async with self.database.write() as session:
            plan = DivineWillPlanRow(title=name, cycle_id=cycle_id, status=PlanStatus.DRAFT, created_at=datetime.now(UTC))
            session.add(plan)
            await session.flush()
            session.add_all(step_rows(plan.id, drafts, {}))
            await self.mirror(session, plan, "The plan was drafted.")
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def read(self, plan_id: int) -> PlanView:
        async with self.database.read() as session:
            return await self.view(session, await self.plan_row(session, plan_id))

    async def share(self, plan_id: int, shared: bool) -> PlanView:
        async with self.database.write() as session:
            plan = await self.plan_row(session, plan_id)
            plan.shared = shared
            await session.flush()
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def revise(self, plan_id: int, steps: Sequence[StepDraft], *, title: str | None = None) -> PlanView:
        drafts = checked(steps)
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status not in EDITABLE_PLANS:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}; its steps can no longer change.")
            current = await self.step_rows_of(session, plan_id)
            kept = {step.ordinal: step for step in current if step.status not in OPEN_STEPS}
            for ordinal, step in kept.items():
                draft = drafts[ordinal - 1] if ordinal <= len(drafts) else None
                if draft is None or draft.action_id != step.action_id or wanted(draft.input) != wanted(step.input):
                    raise ConflictError(f"Step {ordinal} is {STEP_LABELS[step.status].lower()}; it keeps its place, act and input in the revised plan.")
            await session.execute(
                delete(DivineWillPlanStepRow).where(DivineWillPlanStepRow.plan_id == plan_id, DivineWillPlanStepRow.status.in_(list(OPEN_STEPS)))
            )
            await session.flush()
            session.add_all(row for row in step_rows(plan_id, drafts, kept) if row.ordinal not in kept)
            if title is not None and title.strip():
                plan.title = title.strip()
            plan.status = PlanStatus.DRAFT
            plan.approved_at = None
            await self.mirror(session, plan, "The plan was revised.")
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def approve(self, plan_id: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status is not PlanStatus.DRAFT:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}; only a draft is approved.")
            steps = await self.step_rows_of(session, plan_id)
            checked(
                [
                    StepDraft(title=step.title, action_id=step.action_id, input=step.input, depends_on=step.depends_on, declared_impact=step.declared_impact)
                    for step in steps
                ]
            )
            plan.status = PlanStatus.APPROVED
            plan.approved_at = datetime.now(UTC)
            await self.mirror(session, plan, "The plan was approved.")
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def execute(self, plan_id: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status is PlanStatus.DRAFT or plan.approved_at is None:
                raise ConflictError(f"Plan {plan_id} is not approved; approve it before it runs.")
            if plan.status not in RUNNABLE_PLANS:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}.")
            steps = await self.step_rows_of(session, plan_id)
            if not any(step.status in OPEN_STEPS for step in steps):
                raise ConflictError(f"Plan {plan_id} has no step left to run.")
            if self.jobs.busy_group(WORLD_GROUP) is not None:
                raise BusyError(BUSY_WORLD)
            before = plan.status
            plan.status = PlanStatus.RUNNING
            for step in steps:
                if step.status is StepStatus.FAILED:
                    step.status = StepStatus.PENDING
                if step.status is StepStatus.PENDING:
                    step.error = ""
            await self.mirror(session, plan, "The plan began.")
        try:
            job_id = await self.jobs.submit(
                JobKind.DIVINE_WILL_PLAN, lambda context: self.drive(plan_id, context), {PLAN_ID_KEY: plan_id}, exclusive_group=WORLD_GROUP, as_person=True
            )
        except BaseException:
            async with self.database.write() as session:
                (await self.plan_row(session, plan_id)).status = before
            raise
        view = replace(await self.read(plan_id), job_id=job_id)
        self.changed(view)
        return view

    async def resume(self, plan_id: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status is not PlanStatus.PAUSED:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}; only a paused plan resumes.")
        return await self.execute(plan_id)

    async def pause(self, plan_id: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status is not PlanStatus.RUNNING:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}; only a running plan pauses.")
            plan.status = PlanStatus.PAUSED
            await self.mirror(session, plan, "The plan was paused.")
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def abandon(self, plan_id: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status in SETTLED_PLANS:
                raise ConflictError(f"Plan {plan_id} is already {PLAN_LABELS[plan.status].lower()}.")
            plan.status = PlanStatus.ABANDONED
            plan.finished_at = datetime.now(UTC)
            await self.mirror(session, plan, "The plan was abandoned.")
            view = await self.view(session, plan)
        self.changed(view)
        return view

    async def skip(self, plan_id: int, ordinal: int) -> PlanView:
        async with self.database.write() as session:
            plan = await self.healed(session, plan_id)
            if plan.status is PlanStatus.RUNNING or plan.status in SETTLED_PLANS:
                raise ConflictError(f"Plan {plan_id} is {PLAN_LABELS[plan.status].lower()}; pause it before skipping a step.")
            step = await self.step_row(session, plan_id, ordinal)
            if step.status not in OPEN_STEPS:
                raise ConflictError(f"Step {ordinal} is {STEP_LABELS[step.status].lower()}; only a waiting or failed step is skipped.")
            step.status = StepStatus.SKIPPED
            step.error = ""
            await self.mirror(session, plan, f"Step {ordinal} was skipped.")
            view = await self.view(session, plan)
        self.changed(view, ordinal)
        return view

    async def undo(self, plan_id: int, ordinal: int) -> PlanView:
        async with self.database.read() as session:
            plan = await self.plan_row(session, plan_id)
            step = await self.step_row(session, plan_id, ordinal)
            if plan.status is PlanStatus.RUNNING:
                raise ConflictError(f"Plan {plan_id} is running; pause it before undoing a step.")
            if step.status is not StepStatus.DONE:
                raise ConflictError(f"Step {ordinal} is {STEP_LABELS[step.status].lower()}; only a done step is undone.")
            if step.ledger_entry_id is None and not is_rule_step(step.action_id):
                raise ConflictError(f"Step {ordinal} left no ledger entry to undo; undo what its job made from the ledger.")
            entry_id, kept = step.ledger_entry_id, dict(step.input)
        result = await self.rules.undo(kept) if entry_id is None else await self.player_for("").undo(entry_id)
        if not result.get("ok", False):
            raise ConflictError(f"Step {ordinal} could not be undone: {result.get('error', '')}")
        async with self.database.write() as session:
            plan = await self.plan_row(session, plan_id)
            step = await self.step_row(session, plan_id, ordinal)
            step.status = StepStatus.UNDONE
            conflicts = [str(item) for item in result.get("conflicts", [])]
            if conflicts:
                step.result_text = f"{step.result_text} Undone, except: {'; '.join(conflicts)}".strip()
            await self.mirror(session, plan, f"Step {ordinal} was undone.")
            view = await self.view(session, plan)
        self.changed(view, ordinal)
        return view

    async def settle(self, plan_id: int, ordinal: int | None, summary: str, **values: Any) -> PlanView:
        async with self.database.write() as session:
            plan = await self.plan_row(session, plan_id)
            step = await self.step_row(session, plan_id, ordinal) if ordinal is not None else None
            for key, value in values.items():
                target = plan if key in ("status", "finished_at") else step
                if target is not None:
                    setattr(target, key.removeprefix("step_"), value)
            await self.mirror(session, plan, summary)
            view = await self.view(session, plan)
        self.changed(view, ordinal)
        return view

    async def next_step(self, plan_id: int) -> tuple[PlanStatus, DivineWillPlanStepRow | None, list[DivineWillPlanStepRow]]:
        async with self.database.read() as session:
            plan = await self.plan_row(session, plan_id)
            steps = await self.step_rows_of(session, plan_id)
        status = {step.ordinal: step.status for step in steps}
        for step in run_order(steps):
            if step.status is StepStatus.PENDING and all(status.get(needed) is StepStatus.DONE for needed in step.depends_on):
                return plan.status, step, steps
        return plan.status, None, steps

    async def drive(self, plan_id: int, context: JobContext) -> dict[str, Any]:
        player = self.player_for(context.job_id)
        running: int | None = None
        try:
            while True:
                status, step, steps = await self.next_step(plan_id)
                if status is not PlanStatus.RUNNING:
                    return {PLAN_ID_KEY: plan_id, "status": status.value}
                if step is None:
                    return await self.close(plan_id, steps)
                running = step.ordinal
                await self.settle(plan_id, running, f"Step {running} began.", step_status=StepStatus.RUNNING)
                await self.run_step(plan_id, step, player)
                running = None
                done = sum(1 for item in steps if item.status in FINISHED_STEPS) + 1
                context.report(done / max(1, len(steps)), f"step {step.ordinal}")
        except asyncio.CancelledError:
            await self.stopped(plan_id, running, "", PlanStatus.PAUSED)
            raise
        except Exception as error:
            await self.stopped(plan_id, running, str(error) or type(error).__name__, PlanStatus.FAILED)
            raise

    async def stopped(self, plan_id: int, running: int | None, error: str, status: PlanStatus) -> None:
        async with self.database.write() as session:
            plan = await self.plan_row(session, plan_id)
            if plan.status is PlanStatus.RUNNING:
                plan.status = status
            if running is not None:
                step = await self.step_row(session, plan_id, running)
                step.status = StepStatus.FAILED if error else StepStatus.PENDING
                step.error = error or STOPPED_MIDWAY
            await self.mirror(session, plan, "The plan was stopped.")
            view = await self.view(session, plan)
        self.changed(view, running)

    async def close(self, plan_id: int, steps: Sequence[DivineWillPlanStepRow]) -> dict[str, Any]:
        blocked = next((step for step in steps if step.status is StepStatus.PENDING), None)
        if blocked is None:
            await self.settle(plan_id, None, "The plan is done.", status=PlanStatus.DONE, finished_at=datetime.now(UTC))
            return {PLAN_ID_KEY: plan_id, "status": PlanStatus.DONE.value}
        missing = ", ".join(str(needed) for needed in blocked.depends_on)
        reason = f"It waits for step {missing}, which did not run; skip it or revise the plan."
        await self.settle(plan_id, blocked.ordinal, f"Step {blocked.ordinal} waits.", status=PlanStatus.PAUSED, step_error=reason)
        return {PLAN_ID_KEY: plan_id, "status": PlanStatus.PAUSED.value}

    async def run_rule_step(self, plan_id: int, step: DivineWillPlanStepRow) -> None:
        preview = self.rules.preview(step.action_id, step.input)
        if not preview.get("ok", False):
            await self.fail(plan_id, step.ordinal, str(preview.get("error", "")))
            return
        outcome, kept = await self.rules.perform(step.action_id, step.input)
        if not outcome.get("ok", False):
            await self.fail(plan_id, step.ordinal, str(outcome.get("error", "")))
            return
        done = f"Step {step.ordinal} is done."
        message = str(outcome.get("message", ""))
        await self.settle(plan_id, step.ordinal, done, step_status=StepStatus.DONE, step_result_text=message, step_input=kept, step_error="")

    async def run_step(self, plan_id: int, step: DivineWillPlanStepRow, player: PlayerPort) -> None:
        ordinal = step.ordinal
        if is_rule_step(step.action_id):
            await self.run_rule_step(plan_id, step)
            return
        preview = await player.preview(step.action_id, step.input)
        if not preview.get("ok", False):
            await self.fail(plan_id, ordinal, str(preview.get("error", "")))
            return
        stop = undeclared(step, preview)
        if stop:
            await self.settle(
                plan_id, ordinal, f"Step {ordinal} waits for a decision.", status=PlanStatus.PAUSED, step_status=StepStatus.PENDING, step_error=stop
            )
            return
        with stepping(plan_id, ordinal):
            outcome = await player.perform(step.action_id, step.input)
        if not outcome.get("ok", False):
            await self.fail(plan_id, ordinal, str(outcome.get("error", "")))
            return
        if outcome.get("queued") or outcome.get("proposed"):
            waits = WAITS_FOR_AGE if outcome.get("queued") else WAITS_FOR_APPROVAL
            await self.settle(plan_id, ordinal, waits.format(ordinal=ordinal), status=PlanStatus.PAUSED, step_status=StepStatus.RUNNING, step_error="")
            return
        message = str(outcome.get("message", ""))
        ledger = outcome.get("ledger_entry_id")
        job_id = str(outcome.get("job_id") or "")
        if job_id:
            await self.settle(plan_id, ordinal, f"Step {ordinal} waits for its job.", step_job_id=job_id, step_ledger_entry_id=ledger)
            finished = await self.waited(player, job_id)
            if finished.get("status") != JobStatus.SUCCEEDED.value:
                await self.fail(plan_id, ordinal, str(finished.get("error") or f"Its job ended {finished.get('status', '')}."))
                return
        await self.settle(
            plan_id, ordinal, f"Step {ordinal} is done.", step_status=StepStatus.DONE, step_result_text=message, step_ledger_entry_id=ledger, step_error=""
        )

    async def waited(self, player: PlayerPort, job_id: str) -> Mapping[str, Any]:
        while True:
            found = await player.job(job_id)
            if not found.get("ok", False) or found.get("status") in TERMINAL_JOBS:
                return found
            await asyncio.sleep(self.poll_seconds)

    async def fail(self, plan_id: int, ordinal: int, error: str) -> None:
        await self.settle(
            plan_id, ordinal, f"Step {ordinal} failed.", status=PlanStatus.FAILED, step_status=StepStatus.FAILED, step_error=error or "It failed."
        )
