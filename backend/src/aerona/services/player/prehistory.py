from typing import Any

from pydantic import Field

from aerona.core.errors import BusyError
from aerona.core.grammar import several
from aerona.db.tables.prehistory import EPOCHS_MAX, RESOLUTION_MAX
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.job import JobKind
from aerona.engine.prehistory import control
from aerona.engine.prehistory.deep_time import fast_forward
from aerona.engine.prehistory.run import run_prehistory
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.player.cosmography import Edited
from aerona.services.player.runtime import CostedJob, FreeJob, PlayerRuntime, submit_costed, submit_free
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action


class PrehistoryPlan(Command):
    world_id: int
    epochs: int = Field(ge=1, le=EPOCHS_MAX)
    resolution: int = Field(default=1, ge=1, le=RESOLUTION_MAX)


class PrehistoryTarget(Command):
    world_id: int


class PrehistoryEdit(Edited):
    world_id: int


class PrehistoryEventEdit(Edited):
    event_id: int


class PrehistoryEventTarget(Command):
    event_id: int


class DeepTimePlan(Command):
    epochs: int = Field(ge=1)


class DeepTimeTarget(Command):
    run_id: int


class DeepTimeEdit(Edited):
    run_id: int


class DeepTimeEventEdit(Edited):
    event_id: int


class DeepTimeEventTarget(Command):
    event_id: int


@player_action("prehistory:configure", ActionKind.EDIT_RECORD)
async def prehistory_configure(scope: PlayerScope, command: PrehistoryPlan) -> Effect:
    row = await control.configure(await scope.context("prehistory_configure"), command.world_id, command.epochs, command.resolution)
    return Effect(f"A prehistory of {several(row.epochs, 'epoch', 'epochs')} is planned for this world.", target_node_id=command.world_id)


@player_action("prehistory:edit", ActionKind.EDIT_RECORD)
async def prehistory_edit(scope: PlayerScope, command: PrehistoryEdit) -> Effect:
    await control.edit(await scope.context("prehistory_edit"), command.world_id, command.values, command.release)
    return Effect("The prehistory keeps its new values.", target_node_id=command.world_id)


@player_action("prehistory:abort", ActionKind.EDIT_RECORD)
async def prehistory_abort(scope: PlayerScope, command: PrehistoryTarget) -> Effect:
    row = await control.abort(await scope.context("prehistory_abort"), command.world_id)
    told = f"The prehistory stops after {row.rounds_done} of {several(row.epochs, 'epoch', 'epochs')}; it can be run on later."
    return Effect(told, target_node_id=command.world_id)


@player_action("prehistory:remove", ActionKind.EDIT_RECORD)
async def prehistory_remove(scope: PlayerScope, command: PrehistoryTarget) -> Effect:
    await control.remove(await scope.context("prehistory_remove"), command.world_id)
    return Effect("The record of the prehistory and its digest are struck out; what happened in the world stays.", target_node_id=command.world_id)


@player_action("prehistory_event:edit", ActionKind.EDIT_RECORD)
async def prehistory_event_edit(scope: PlayerScope, command: PrehistoryEventEdit) -> Effect:
    row = await control.edit_event(await scope.context("prehistory_event_edit"), command.event_id, command.values, command.release)
    return Effect("The happening of the prehistory keeps its new values.", target_node_id=row.world_id)


@player_action("prehistory_event:remove", ActionKind.EDIT_RECORD)
async def prehistory_event_remove(scope: PlayerScope, command: PrehistoryEventTarget) -> Effect:
    await control.remove_event(await scope.context("prehistory_event_remove"), command.event_id)
    return Effect("The happening is struck out of the digest.")


@player_action("deep_time:stop", ActionKind.EDIT_RECORD)
async def deep_time_stop(scope: PlayerScope, command: DeepTimeTarget) -> Effect:
    run = await control.stop_run(await scope.context("deep_time_stop"), command.run_id)
    return Effect(f"The fast-forward stops after {run.ran} of {several(run.epochs, 'epoch', 'epochs')}.")


@player_action("deep_time:edit", ActionKind.EDIT_RECORD)
async def deep_time_edit(scope: PlayerScope, command: DeepTimeEdit) -> Effect:
    await control.edit_run(await scope.context("deep_time_edit"), command.run_id, command.values, command.release)
    return Effect("The fast-forward keeps its new values.")


@player_action("deep_time:remove", ActionKind.EDIT_RECORD)
async def deep_time_remove(scope: PlayerScope, command: DeepTimeTarget) -> Effect:
    await control.remove_run(await scope.context("deep_time_remove"), command.run_id)
    return Effect("The record of the fast-forward and its digest are struck out; the epochs it ran stay run.")


@player_action("deep_time_event:edit", ActionKind.EDIT_RECORD)
async def deep_time_event_edit(scope: PlayerScope, command: DeepTimeEventEdit) -> Effect:
    await control.edit_run_event(await scope.context("deep_time_event_edit"), command.event_id, command.values, command.release)
    return Effect("The happening of the fast-forward keeps its new values.")


@player_action("deep_time_event:remove", ActionKind.EDIT_RECORD)
async def deep_time_event_remove(scope: PlayerScope, command: DeepTimeEventTarget) -> Effect:
    await control.remove_run_event(await scope.context("deep_time_event_remove"), command.event_id)
    return Effect("The happening is struck out of the digest of the fast-forward.")


async def prehistory_work(runtime: PlayerRuntime, rules: Rules, world_id: int, context: JobContext) -> dict[str, Any]:
    context.report(0.0, "prehistory")
    summary = await run_prehistory(runtime.database, world_id, rules=rules, publish=runtime.publish)
    told = f"The prehistory ran {several(summary.rounds, 'epoch', 'epochs')} and kept {several(summary.events, 'happening', 'happenings')}."
    runtime.publish(EventKind.SYSTEM_NOTE, {"text": told, "entity_ids": []})
    return {"world_id": world_id, "rounds": summary.rounds, "events": summary.events, "state": summary.state.value}


def require_quiet(runtime: PlayerRuntime) -> None:
    if runtime.jobs.busy_group(WORLD_GROUP) is not None:
        raise BusyError("Busy: an epoch or another run is changing the world; wait for it to finish.")


async def run_planned(runtime: PlayerRuntime, rules: Rules, command: PrehistoryTarget) -> ActionOutcome:
    require_quiet(runtime)
    async with runtime.database.write() as session:
        await control.ready(await runtime.scope(session, rules).context("prehistory_run"), command.world_id)

    async def work(context: JobContext) -> dict[str, Any] | None:
        return await prehistory_work(runtime, rules, command.world_id, context)

    return await submit_free(runtime, FreeJob("prehistory:run", JobKind.PREHISTORY, WORLD_GROUP), command, work)


async def seed_prehistory(runtime: PlayerRuntime, rules: Rules, command: PrehistoryPlan) -> ActionOutcome:
    require_quiet(runtime)
    async with runtime.database.write() as session:
        await control.seed(await runtime.scope(session, rules).context("prehistory_seed"), command.world_id, command.epochs, command.resolution)

    async def work(context: JobContext) -> dict[str, Any] | None:
        return await prehistory_work(runtime, rules, command.world_id, context)

    job = CostedJob("prehistory:seed", ActionKind.OTHER, JobKind.PREHISTORY, WORLD_GROUP, rules.prehistory.seed_cost, "prehistory.seed_cost", command.world_id)
    return await submit_costed(runtime, rules, job, command, work)


async def run_deep_time(runtime: PlayerRuntime, rules: Rules, command: DeepTimePlan) -> ActionOutcome:
    require_quiet(runtime)
    async with runtime.database.write() as session:
        run = await control.open_run(await runtime.scope(session, rules).context("deep_time_run"), command.epochs)
        run_id = run.id

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "deep_time")
        summary = await fast_forward(runtime.database, run_id, rules=rules, publish=runtime.publish)
        told = f"Deep time ran {several(summary.epochs, 'epoch', 'epochs')} and kept {several(summary.events, 'happening', 'happenings')}."
        runtime.publish(EventKind.SYSTEM_NOTE, {"text": told, "entity_ids": []})
        return {"run_id": run_id, "epochs": summary.epochs, "events": summary.events, "state": summary.state.value}

    cost = rules.prehistory.deep_time_cost * command.epochs
    job = CostedJob("deep_time:run", ActionKind.OTHER, JobKind.DEEP_TIME, WORLD_GROUP, cost, "prehistory.deep_time_cost")
    return await submit_costed(runtime, rules, job, command, work)
