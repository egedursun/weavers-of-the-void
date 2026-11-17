from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from aerona.agents.fate.apply import record_verdict
from aerona.agents.fate.rollback import roll_back_rejection
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.recording.record import record
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.player import guards
from aerona.services.player.ports import FateControls
from aerona.services.player.runtime import CostedJob, PlayerRuntime, submit_costed, unavailable
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action

RATIONALE_MAX = 400
HISTORIAN_TEXT_MAX = 6000
OVERRIDE_RATIONALE = "Overruled by the Creator."


class VerdictChoice(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class NoInput(Command):
    pass


class EpochTarget(Command):
    epoch: int


class OverrideVerdict(Command):
    entity_id: int
    choice: VerdictChoice
    rationale: str | None = None


class HistorianViewTarget(Command):
    view_id: int


class EditHistorianView(Command):
    view_id: int
    text: str


def _controls(runtime: PlayerRuntime) -> FateControls:
    controls = runtime.ports.fate
    if controls is None:
        raise unavailable("Fate")
    return controls


async def _submit(
    runtime: PlayerRuntime, rules: Rules, command: Command, job: CostedJob, run: Callable[[FateControls], Awaitable[dict[str, int]]]
) -> ActionOutcome:
    controls = _controls(runtime)

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, job.action)
        return dict(await run(controls))

    return await submit_costed(runtime, rules, job, command, work)


def _job(action: str, kind: ActionKind, cost: int, rule_name: str) -> CostedJob:
    return CostedJob(action, kind, JobKind.RETRY, WORLD_GROUP, cost, rule_name)


async def retry_fate(runtime: PlayerRuntime, rules: Rules, command: NoInput) -> ActionOutcome:
    job = _job("fate:retry", ActionKind.RETRY_FATE, rules.costs.rejudge_fate, "costs.rejudge_fate")
    return await _submit(runtime, rules, command, job, lambda controls: controls.retry_fate())


async def rejudge_debt(runtime: PlayerRuntime, rules: Rules, command: NoInput) -> ActionOutcome:
    job = _job("fate:rejudge_debt", ActionKind.REJUDGE_FATE, rules.costs.rejudge_fate, "costs.rejudge_fate")
    return await _submit(runtime, rules, command, job, lambda controls: controls.rejudge_debt())


async def rejudge_limbo(runtime: PlayerRuntime, rules: Rules, command: NoInput) -> ActionOutcome:
    job = _job("fate:rejudge_limbo", ActionKind.REJUDGE_FATE, rules.costs.rejudge_fate, "costs.rejudge_fate")
    return await _submit(runtime, rules, command, job, lambda controls: controls.rejudge_limbo())


async def retry_voices(runtime: PlayerRuntime, rules: Rules, command: NoInput) -> ActionOutcome:
    job = _job("voices:retry", ActionKind.RETRY_VOICES, rules.costs.retry_voices, "costs.retry_voices")
    return await _submit(runtime, rules, command, job, lambda controls: controls.retry_voices())


async def retry_births(runtime: PlayerRuntime, rules: Rules, command: NoInput) -> ActionOutcome:
    job = _job("births:retry", ActionKind.RETRY_BIRTHS, rules.costs.retry_births, "costs.retry_births")
    return await _submit(runtime, rules, command, job, lambda controls: controls.retry_births())


async def audit_chronicle(runtime: PlayerRuntime, rules: Rules, command: EpochTarget) -> ActionOutcome:
    job = _job("chronicle:audit", ActionKind.AUDIT_CHRONICLE, rules.chronicle_audit.manual_cost, "chronicle_audit.manual_cost")
    return await _submit(runtime, rules, command, job, lambda controls: controls.audit_chronicle(command.epoch))


@player_action("fate:override_verdict", ActionKind.OVERRIDE_VERDICT)
async def override_verdict(scope: PlayerScope, command: OverrideVerdict) -> Effect:
    entity: EntityRow = await guards.entity(scope.session, command.entity_id)
    if entity.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{entity.name} is not in the canon; Fate's verdict cannot be overruled.")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.costs.override_verdict, "costs.override_verdict")
    epoch = await scope.epoch()
    rationale = guards.clip(command.rationale, RATIONALE_MAX) or OVERRIDE_RATIONALE
    if command.choice is VerdictChoice.REJECT:
        await EntityRepository(scope.session).set_status(entity, EntityStatus.REJECTED, epoch, rationale)
        await record_verdict(scope.session, entity, Verdict.REJECTED, rationale, epoch)
        await roll_back_rejection(scope.session, scope.rules, entity.id)
    else:
        entity.fate_note = rationale
        await record_verdict(scope.session, entity, Verdict.ACCEPTED, rationale, epoch)
    ctx = await scope.context("override_verdict")
    message = (
        await record(
            ctx,
            "player.fate.verdict_override",
            roles={IncidentRole.TARGET: entity.id, IncidentRole.AUTHORITY: creator.id},
            facts={"verdict": str(command.choice.value + "ed")},
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    return Effect(message, entity.id, essence_spent=spent)


async def _view(scope: PlayerScope, view_id: int) -> tuple[HistorianViewRow, EntityRow]:
    view = await scope.session.get(HistorianViewRow, view_id)
    if view is None:
        raise NotFoundError("No such historian account.")
    return view, await guards.entity(scope.session, view.people_entity_id)


@player_action("voices:edit_view", ActionKind.EDIT_HISTORIAN_VIEW)
async def edit_view(scope: PlayerScope, command: EditHistorianView) -> Effect:
    view, people = await _view(scope, command.view_id)
    text = guards.clip(command.text, HISTORIAN_TEXT_MAX)
    if not text:
        raise ValidationFailedError("A historian's account cannot be empty.")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.costs.edit_historian_view, "costs.edit_historian_view")
    view.text = text
    ctx = await scope.context("edit_historian_view")
    message = (
        await record(
            ctx,
            "player.fate.historian_edit",
            roles={IncidentRole.AUTHORITY: creator.id, IncidentRole.SUBJECT: people.id},
            facts={"people": people.name},
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    return Effect(message, people.id, essence_spent=spent)


@player_action("voices:delete_view", ActionKind.DELETE_HISTORIAN_VIEW)
async def delete_view(scope: PlayerScope, command: HistorianViewTarget) -> Effect:
    view, people = await _view(scope, command.view_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.costs.edit_historian_view, "costs.edit_historian_view")
    await scope.session.delete(view)
    ctx = await scope.context("delete_historian_view")
    message = (
        await record(
            ctx,
            "player.fate.historian_delete",
            roles={IncidentRole.AUTHORITY: creator.id, IncidentRole.SUBJECT: people.id},
            facts={"people": people.name},
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    return Effect(message, people.id, essence_spent=spent)
