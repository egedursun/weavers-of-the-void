import json
from typing import Any

from pydantic import Field

from aerona.core.errors import AeronaError
from aerona.core.grammar import several, spoken
from aerona.domain.enums.divine_will import PlanStatus
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.library_ports import PlanStepView, PlanView, StepDraft, library_of
from aerona.tools.divine_will.paging import failed, paged
from aerona.tools.framework.inputs import ToolInput

W = DivineWillToolId
PLANNING = frozenset({Toolset.PLAN})


class PlanCreateInput(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    steps: list[StepDraft] = Field(min_length=1)


class PlanReadInput(PagedInput):
    plan_id: int = Field(ge=1)


class PlanReviseInput(ToolInput):
    plan_id: int = Field(ge=1)
    steps: list[StepDraft] = Field(min_length=1)
    title: str = Field(default="", max_length=300)


def step_text(step: PlanStepView) -> str:
    facts = [
        f"act {step.action_id} ({step.action_title})",
        f"state {spoken(step.status)}",
        f"declared {spoken(step.declared_impact)}",
        f"estimated essence {step.estimated_essence}",
    ]
    if step.depends_on:
        facts.append(f"waits for steps {', '.join(map(str, step.depends_on))}")
    if step.ledger_entry_id is not None:
        facts.append(f"ledger entry {step.ledger_entry_id}")
    if step.job_id:
        facts.append(f"job {step.job_id}")
    lines = [f"step {step.ordinal}: {step.title} — {'; '.join(facts)}", f"  input: {json.dumps(step.input, ensure_ascii=False, sort_keys=True)}"]
    if step.result_text:
        lines.append(f"  outcome: {step.result_text}")
    if step.error:
        lines.append(f"  stopped: {step.error}")
    return "\n".join(lines)


def plan_head(view: PlanView) -> str:
    lines = [f"plan {view.id}: {view.title} — status {spoken(view.status)}, {several(len(view.steps), 'step', 'steps')}"]
    if view.artifact_id is not None:
        lines.append(f"Its text is kept as artifact {view.artifact_id}.")
    if view.waiting_step is not None:
        lines.append(f"Step {view.waiting_step} waits for the player's decision.")
    if view.status is PlanStatus.ABANDONED:
        lines.append("The player abandoned it. Do not write it again unless the player asks; say it was abandoned and offer a new plan.")
    if view.status is PlanStatus.PAUSED and view.waiting_step is None:
        lines.append("The player paused it; it goes on only when the player resumes it from the plan card.")
    return "\n".join(lines)


def next_move(view: PlanView) -> str:
    return (
        f"Saved {plan_head(view)}. Nothing runs until the player approves the plan and executes it from the plan card; "
        "revise it with plan_revise while it waits."
    )


async def create_plan(call: WillCall, query: PlanCreateInput) -> WillResult:
    try:
        view = await library_of(call).plans.create(query.title, query.steps, cycle_id=call.cycle_id)
    except AeronaError as error:
        return failed(error.message)
    return WillResult(text=next_move(view), payload={"plan_id": view.id, "artifact_id": view.artifact_id})


async def read_plan(call: WillCall, query: PlanReadInput) -> WillResult:
    try:
        view = await library_of(call).plans.read(query.plan_id)
    except AeronaError as error:
        return failed(error.message)
    return await paged(call, W.PLAN_READ, query, [step_text(step) for step in view.steps], head=plan_head(view), empty="The plan has no steps.")


async def revise_plan(call: WillCall, query: PlanReviseInput) -> WillResult:
    try:
        view = await library_of(call).plans.revise(query.plan_id, query.steps, title=query.title or None)
    except AeronaError as error:
        return failed(error.message)
    return WillResult(text=next_move(view), payload={"plan_id": view.id, "artifact_id": view.artifact_id})


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.PLAN_CREATE, PLANNING, PlanCreateInput, create_plan),
        WillTool(W.PLAN_READ, PLANNING, PlanReadInput, read_plan),
        WillTool(W.PLAN_REVISE, PLANNING, PlanReviseInput, revise_plan),
    ]
