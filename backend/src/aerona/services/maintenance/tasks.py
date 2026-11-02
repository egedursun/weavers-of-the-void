from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.network_repair import repair_loose_ends
from aerona.engine.cosmos.worlds import pair_mirrors
from aerona.engine.primitives.canon_facts import rebuild_certain_facts
from aerona.epoch.resume import requeue_intuitions
from aerona.rules.registry import Rules
from aerona.services.application import ApplicationServices
from aerona.services.images.records import clear_file_name_captions
from aerona.services.importance import persist
from aerona.services.integrity.age_consistency import raise_lifespans
from aerona.services.integrity.data_repairs import refresh_planner_statistics, sign_history
from aerona.services.integrity.epoch_years import align_epoch_years
from aerona.services.integrity.graph_ends import repair_graph_ends
from aerona.services.maintenance.models import MaintenanceTask
from aerona.services.narrative import backfill_endings, sweep_narratives
from aerona.services.notifications import prune_notifications

ProgressReport = Callable[[float, str], None]


@dataclass(frozen=True)
class TaskEnvironment:
    application: ApplicationServices
    session: AsyncSession
    rules: Rules
    epoch: int
    report: ProgressReport


TaskBody = Callable[[TaskEnvironment], Awaitable[dict[str, int]]]


@dataclass(frozen=True)
class TaskSpec:
    task: MaintenanceTask
    title: str
    description: str
    automatic: str
    rows: tuple[str, ...]
    run: TaskBody | None
    ledgered: bool = True
    needs_llm: bool = False


async def network_rules(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "loose ends")
    return {"location": await repair_loose_ends(env.session, env.epoch)}


async def loose_ends(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "dangling ends")
    counters = await repair_graph_ends(env.session, env.rules, env.epoch, env.application.repair_log)
    return counters.as_dict()


async def data_repairs(env: TaskEnvironment) -> dict[str, int]:
    def step(name: str, index: int, total: int) -> None:
        env.report((index - 1) / total, name)

    return await env.application.repairs.run(env.session, env.rules, step)


async def history_repairs(env: TaskEnvironment) -> dict[str, int]:
    repairs = env.application.repairs
    steps = repairs.history_steps()
    counters: dict[str, int] = {}
    for index, (name, step) in enumerate(steps):
        env.report(index / len(steps), name)
        async with env.session.begin_nested():
            counters[name] = await step(env.session, env.rules, env.epoch)
    await sign_history(env.session)
    return counters


async def epoch_years(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "epoch years")
    return {"aligned": await align_epoch_years(env.session, env.rules)}


async def mortal_ages(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "mortal ages")
    return {"raised": await raise_lifespans(env.session, env.rules)}


async def importance(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "importance")
    return {"scored": await persist(env.session, env.rules, env.epoch)}


async def endings(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "endings")
    return {"written": await backfill_endings(env.session)}


async def narrative_sweep(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "narratives")
    return {"cleaned": await sweep_narratives(env.session)}


async def certain_facts(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "certain facts")
    return {"written": await rebuild_certain_facts(env.session)}


async def intuitions(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "horizon intuitions")
    return {"requeued": await requeue_intuitions(env.session)}


async def mirror_pairs(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "mirror worlds")
    return {"paired": await pair_mirrors(env.session)}


async def captions(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "captions")
    return {"cleared": await clear_file_name_captions(env.session)}


async def planner_statistics(env: TaskEnvironment) -> dict[str, int]:
    env.report(0.0, "planner statistics")
    await refresh_planner_statistics(env.session)
    return {"refreshed": 1}


async def prune(env: TaskEnvironment) -> dict[str, int]:
    application = env.application
    env.report(0.0, "notifications")
    counters = {"notifications": await prune_notifications(env.session, env.rules)}
    env.report(0.2, "ledger")
    counters["ledger"] = await application.ledger.prune(env.session, env.rules, env.epoch)
    env.report(0.4, "model metrics")
    counters["metrics"] = await application.metrics.prune()
    env.report(0.6, "change log")
    counters["change_log"] = application.feed.prune(env.rules.ui.change_log_max_rows)
    env.report(0.8, "media")
    counters["media"] = await application.backups.prune_media()
    return counters


T = MaintenanceTask

TASKS: tuple[TaskSpec, ...] = (
    TaskSpec(
        T.COMPLETION,
        "Complete missing content",
        "Fill the Creator portrait, son powers, the first sky body and peoples, image prompts, "
        "undeepened foreign gods, pending names and past epoch narratives.",
        "Before every epoch and shortly after startup when something is missing",
        ("SVC-213", "LLM-026", "EPOCH-016", "EPOCH-049"),
        None,
        ledgered=False,
        needs_llm=True,
    ),
    TaskSpec(
        T.NETWORK_RULES,
        "Network rule repair",
        "Bond every located canon record to its location where the inside bond is missing.",
        "Every epoch end",
        ("CORE-020", "CORE-071"),
        network_rules,
    ),
    TaskSpec(
        T.LOOSE_ENDS,
        "Loose-end repair",
        "Repair dangling ends of the link graph: events, narratives, prophecies, remnants and lost records.",
        "Every epoch end when automatic graph repair is on, and at startup",
        ("SVC-204",),
        loose_ends,
    ),
    TaskSpec(
        T.DATA_REPAIRS,
        "Data repairs",
        "Run every idempotent bond and data repair: duplicates, shared thrones, reversed endpoints, stale location bonds, truces and epoch years.",
        "At startup; location and market containment also every epoch end",
        ("SVC-204", "ECO-017"),
        data_repairs,
    ),
    TaskSpec(
        T.HISTORY_REPAIRS,
        "Repair past data again",
        "Re-run the heavy history repairs over all past data: narrative leaks, missing endings, mortal ages and file-name captions.",
        "Once at startup whenever the repair code changed (code signature)",
        ("SVC-204",),
        history_repairs,
    ),
    TaskSpec(
        T.EPOCH_YEARS,
        "Epoch-year consistency",
        "Align epoch year ranges, chronicle years and the cosmos start year with the years-per-epoch rule.",
        "At startup",
        ("EPOCH-016", "EPOCH-036", "EPOCH-049"),
        epoch_years,
    ),
    TaskSpec(
        T.MORTAL_AGES,
        "Mortal age consistency",
        "Raise the base lifespan of dead mortals whose age exceeds it.",
        "At startup",
        ("SVC-203",),
        mortal_ages,
    ),
    TaskSpec(
        T.IMPORTANCE,
        "Recompute importance",
        "Recompute and persist the importance score of every visible record.",
        "Startup when any is missing, and every epoch end",
        ("CORE-071", "CORE-072", "SVC-199"),
        importance,
    ),
    TaskSpec(
        T.ENDINGS,
        "Write missing endings",
        "Give dead or destroyed records without one the ending sentence taken from their Fate note.",
        "At startup",
        ("CORE-020", "SVC-208"),
        endings,
    ),
    TaskSpec(
        T.NARRATIVE_SWEEP,
        "Scrub narratives",
        "Strip identity leaks, ids and meta sentences from stored narratives.",
        "At startup",
        ("CORE-021", "SVC-207"),
        narrative_sweep,
    ),
    TaskSpec(
        T.CERTAIN_FACTS,
        "Rebuild certain facts",
        "Write the deterministic canon facts of every living record that lacks them.",
        "At startup when the world has no facts, and on every judgment",
        ("CORE-060", "CORE-066"),
        certain_facts,
    ),
    TaskSpec(
        T.INTUITIONS,
        "Requeue stuck intuitions",
        "Put horizon intuitions stuck in processing back in the queue.",
        "When an epoch resumes",
        ("SVC-205",),
        intuitions,
    ),
    TaskSpec(
        T.MIRROR_PAIRS,
        "Pair mirror worlds",
        "Pair every mirror world that has no twin yet.",
        "At startup",
        ("SVC-206",),
        mirror_pairs,
    ),
    TaskSpec(
        T.CAPTIONS,
        "Clear file-name captions",
        "Remove image captions that are only file names.",
        "At startup",
        ("SVC-204",),
        captions,
    ),
    TaskSpec(
        T.PLANNER_STATISTICS,
        "Refresh planner statistics",
        "Refresh the database planner statistics.",
        "At startup and every epoch end",
        ("SVC-201", "EPOCH-036"),
        planner_statistics,
        ledgered=False,
    ),
    TaskSpec(
        T.PRUNE,
        "Prune old data",
        "Prune read notifications, old ledger pages, old model metrics, the change log and unreferenced media objects, then checkpoint the log.",
        "Every epoch end",
        ("SVC-011", "SVC-035", "SVC-037", "SVC-063", "SVC-200", "SVC-214"),
        prune,
        ledgered=False,
    ),
)
TASKS_BY_ID: dict[MaintenanceTask, TaskSpec] = {spec.task: spec for spec in TASKS}
