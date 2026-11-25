import asyncio
import json
import math
import shutil
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select

from aerona.core.errors import AeronaError, BusyError, ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.authorship import may_see, owns
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.divine_will import DivineWillForecastRow
from aerona.db.tables.epochs import EpochEnginePhaseRow
from aerona.domain.enums.divine_will import ForecastStatus
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.audience import private_audience
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog, coerce, constraint_violations, with_value
from aerona.services.divine_will.forecast_report import database_at, scenario, world_state
from aerona.services.divine_will.ownership import ownership_of
from aerona.services.divine_will.rule_steps import RULE_ACTIONS, RuleStepInput, is_rule_step, rule_problem
from aerona.services.player.catalog import ACTIONS_BY_ID, run_ledgered
from aerona.services.player.scope import PlayerScope
from aerona.tools.divine_will.library_ports import AppliedIntervention, ForecastEstimate, ForecastReport, ForecastView, Intervention

FORECAST_GROUP = "divine_will_forecast"
FORECAST_WORKER = "aerona.services.divine_will.forecast_worker"
FOLDER_PREFIX = "forecast-"
ETA_FACTOR = 1.15
START_SECONDS = 8
FALLBACK_EPOCH_SECONDS = 30.0
CANCEL_WAIT_SECONDS = 15.0
CANCEL_POLL_SECONDS = 0.1
ERROR_TAIL = 600
FORECAST_ID_KEY = "forecast_id"
BASELINE = "baseline"
INTERVENED = "intervened"
SCENARIOS = (BASELINE, INTERVENED)
OPEN_FORECASTS = frozenset({ForecastStatus.QUEUED, ForecastStatus.RUNNING})
REPORT = TypeAdapter(ForecastReport)
INTERVENTIONS = TypeAdapter(list[Intervention])
STOPPED_MIDWAY = "The forecast stopped when the server stopped; run it again."
NOT_YOURS = "Only its author can stop this forecast."


@dataclass
class Living:
    epochs: int
    done: dict[str, int] = field(default_factory=lambda: dict.fromkeys(SCENARIOS, 0))
    seconds: dict[str, float] = field(default_factory=lambda: dict.fromkeys(SCENARIOS, 0.0))
    processes: list[asyncio.subprocess.Process] = field(default_factory=list)

    @property
    def share(self) -> float:
        return sum(self.done.values()) / max(1, self.epochs * len(SCENARIOS))


def eta_of(seconds: float, epochs: int) -> int:
    return math.ceil(seconds * epochs * ETA_FACTOR + START_SECONDS)


def online_copy(source: Path, target: Path) -> None:
    with closing(sqlite3.connect(source)) as origin, closing(sqlite3.connect(target)) as copy:
        origin.backup(copy)


def checked_interventions(interventions: Sequence[Intervention]) -> list[Intervention]:
    problems: list[str] = []
    for number, item in enumerate(interventions, start=1):
        if is_rule_step(item.action_id):
            problem = rule_problem(item.action_id, item.input)
            if problem:
                problems.append(f"Intervention {number} ({item.action_id}): {problem}.")
            continue
        spec = ACTIONS_BY_ID.get(item.action_id)
        if spec is None:
            problems.append(f"Intervention {number}: there is no act called {item.action_id}.")
            continue
        if spec.sync is None:
            problems.append(f"Intervention {number} ({item.action_id}) runs as a job that needs the language model; a forecast lives its copy without it.")
            continue
        try:
            spec.input_model.model_validate(item.input)
        except ValidationError as error:
            problems.append(f"Intervention {number} ({item.action_id}): the input did not fit: {error.errors(include_url=False)}.")
    if problems:
        raise ValidationFailedError(" ".join(problems))
    return list(interventions)


async def rule_on_copy(database: Database, number: int, item: Intervention) -> AppliedIntervention:
    step = RuleStepInput.model_validate(dict(item.input))
    async with database.write() as session:
        repository = CosmosRepository(session)
        cosmos = await repository.require_cosmos()
        current = rules_from_snapshot(cosmos.rules_snapshot)
        found = next(entry for entry in catalog(current) if entry.namespace == step.namespace and entry.key == step.name)
        target = found.default if step.value is None else coerce(current, step.namespace, step.name, step.value)
        changed = with_value(current, step.namespace, step.name, target)
        violations = constraint_violations(changed)
        if violations:
            raise ValidationFailedError(f"Intervention {number} ({item.action_id}) was refused on the copy: {' '.join(violations)}")
        await repository.store_rules(changed)
        before = found.value
    message = f"The rule {step.namespace}.{step.name} goes from {before} to {target} on the copy."
    return AppliedIntervention(item.action_id, RULE_ACTIONS[item.action_id], message, 0)


def stored_report(row: DivineWillForecastRow) -> ForecastReport | None:
    if "baseline" not in row.report:
        return None
    return REPORT.validate_python({key: value for key, value in row.report.items() if key not in ("error", "epochs_done")})


def forecast_view(row: DivineWillForecastRow) -> ForecastView:
    return ForecastView(
        id=row.id,
        cycle_id=row.cycle_id,
        epochs=row.epochs,
        status=row.status,
        eta_seconds=row.eta_seconds,
        interventions=INTERVENTIONS.validate_python(row.interventions),
        report=stored_report(row),
        job_id=row.job_id,
        error=str(row.report.get("error", "")),
        epochs_done=int(row.report.get("epochs_done", 0)),
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        owner=ownership_of(row.author_account_id, row.author_name, row.shared),
    )


def stderr_tail(path: Path) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    return lines[-1][-ERROR_TAIL:] if lines else ""


class Foresight:
    def __init__(self, database: Database, bus: EventBus, jobs: JobManager, root: Path) -> None:
        self.database = database
        self.bus = bus
        self.jobs = jobs
        self.root = root

    @property
    def live_path(self) -> Path:
        return Path(str(self.database.engine.url.database))

    def progress(self, view: ForecastView, share: float) -> None:
        self.bus.publish(
            EventKind.DIVINE_WILL_FORECAST_PROGRESS,
            {
                FORECAST_ID_KEY: view.id,
                "status": view.status.value,
                "done_epochs": view.epochs_done,
                "epochs": view.epochs,
                "eta_seconds": view.eta_seconds,
                "progress": round(share, 4),
            },
            audience=private_audience(view.owner.author_account_id, view.owner.shared),
        )

    async def estimate(self, epochs: int, rules: Rules) -> ForecastEstimate:
        most = rules.divine_will.forecast_max_epochs
        if not 1 <= epochs <= most:
            raise ValidationFailedError(f"A forecast lives from 1 epoch up to {several(most, 'epoch', 'epochs')}; {epochs} is outside that.")
        async with self.database.read() as session:
            measured = await session.scalar(select(func.max(EpochEnginePhaseRow.epoch)))
            total = select(func.coalesce(func.sum(EpochEnginePhaseRow.seconds), 0.0)).where(EpochEnginePhaseRow.epoch == measured)
            seconds = float(await session.scalar(total) or 0.0) if measured is not None else 0.0
            earlier = await session.scalar(
                select(DivineWillForecastRow).where(DivineWillForecastRow.status == ForecastStatus.DONE).order_by(DivineWillForecastRow.id.desc()).limit(1)
            )
        if measured is not None and seconds > 0:
            return ForecastEstimate(epochs, round(seconds, 2), eta_of(seconds, epochs), int(measured), None)
        report = stored_report(earlier) if earlier is not None else None
        if earlier is not None and report is not None:
            seconds = max(report.baseline.seconds, report.intervened.seconds) / max(1, earlier.epochs)
            return ForecastEstimate(epochs, round(seconds, 2), eta_of(seconds, epochs), None, earlier.id)
        return ForecastEstimate(epochs, FALLBACK_EPOCH_SECONDS, eta_of(FALLBACK_EPOCH_SECONDS, epochs), None, None)

    async def run(self, interventions: Sequence[Intervention], epochs: int, *, cycle_id: int | None, rules: Rules) -> ForecastView:
        chosen = checked_interventions(interventions)
        estimate = await self.estimate(epochs, rules)
        if self.jobs.busy_group(WORLD_GROUP) is not None:
            raise BusyError("The world is busy with an epoch or a plan; a forecast copies it once that has finished.")
        if self.jobs.busy_group(FORECAST_GROUP) is not None:
            raise BusyError("Another forecast is running; wait for it or cancel it.")
        async with self.database.write() as session:
            row = DivineWillForecastRow(
                cycle_id=cycle_id,
                epochs=epochs,
                status=ForecastStatus.QUEUED,
                eta_seconds=estimate.eta_seconds,
                interventions=[item.model_dump(mode="json") for item in chosen],
                report={"epochs_done": 0, "error": ""},
                created_at=datetime.now(UTC),
            )
            session.add(row)
            await session.flush()
            forecast_id = row.id
        try:
            job_id = await self.jobs.submit(
                JobKind.DIVINE_WILL_FORECAST,
                lambda context: self.work(forecast_id, chosen, rules, context),
                {FORECAST_ID_KEY: forecast_id},
                exclusive_group=FORECAST_GROUP,
                as_person=True,
            )
        except AeronaError as error:
            await self.finish(forecast_id, ForecastStatus.FAILED, error=error.message)
            raise
        async with self.database.write() as session:
            stored = await self.row(session, forecast_id)
            if not stored.job_id:
                stored.job_id = job_id
            view = forecast_view(stored)
        self.progress(view, 0.0)
        return view

    async def row(self, session: Any, forecast_id: int) -> DivineWillForecastRow:
        found: DivineWillForecastRow | None = await session.get(DivineWillForecastRow, forecast_id)
        if found is None or not may_see(found.author_account_id, found.shared):
            raise NotFoundError(f"No forecast {forecast_id}.")
        return found

    def active(self, row: DivineWillForecastRow) -> bool:
        return bool(row.job_id) and self.jobs.running_context(row.job_id) is not None

    async def read(self, forecast_id: int) -> ForecastView:
        async with self.database.read() as session:
            row = await self.row(session, forecast_id)
            stale = row.status in OPEN_FORECASTS and bool(row.job_id) and not self.active(row)
            view = forecast_view(row)
        if stale:
            return await self.finish(forecast_id, ForecastStatus.FAILED, error=STOPPED_MIDWAY)
        return view

    async def share(self, forecast_id: int, shared: bool) -> ForecastView:
        async with self.database.write() as session:
            row = await self.row(session, forecast_id)
            if not owns(row.author_account_id):
                raise ForbiddenError(NOT_YOURS)
            row.shared = shared
            await session.flush()
            return forecast_view(row)

    async def cancel(self, forecast_id: int) -> ForecastView:
        async with self.database.read() as session:
            row = await self.row(session, forecast_id)
            if not owns(row.author_account_id):
                raise ForbiddenError(NOT_YOURS)
            if row.status not in OPEN_FORECASTS:
                raise ConflictError(f"Forecast {forecast_id} has already ended.")
            job_id, running = row.job_id, self.active(row)
        if running:
            await self.jobs.cancel(job_id)
            waited = 0.0
            while self.jobs.running_context(job_id) is not None and waited < CANCEL_WAIT_SECONDS:
                await asyncio.sleep(CANCEL_POLL_SECONDS)
                waited += CANCEL_POLL_SECONDS
        async with self.database.read() as session:
            still_open = (await self.row(session, forecast_id)).status in OPEN_FORECASTS
        if still_open:
            await asyncio.to_thread(shutil.rmtree, self.folder(forecast_id), True)
            return await self.finish(forecast_id, ForecastStatus.CANCELLED)
        return await self.read(forecast_id)

    def folder(self, forecast_id: int) -> Path:
        return self.root / f"{FOLDER_PREFIX}{forecast_id}"

    def prepared(self, forecast_id: int) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for leftover in self.root.glob(f"{FOLDER_PREFIX}*"):
            shutil.rmtree(leftover, ignore_errors=True)
        folder = self.folder(forecast_id)
        folder.mkdir(parents=True)
        return folder

    async def finish(self, forecast_id: int, status: ForecastStatus, *, error: str = "", report: ForecastReport | None = None) -> ForecastView:
        async with self.database.write() as session:
            row = await self.row(session, forecast_id)
            row.status = status
            row.finished_at = datetime.now(UTC)
            stored: dict[str, Any] = {"epochs_done": row.epochs if report is not None else int(row.report.get("epochs_done", 0)), "error": error}
            if report is not None:
                stored.update(REPORT.dump_python(report, mode="json"))
            row.report = stored
            view = forecast_view(row)
        self.progress(view, 1.0 if status is ForecastStatus.DONE else 0.0)
        return view

    async def began(self, forecast_id: int) -> ForecastView:
        async with self.database.write() as session:
            row = await self.row(session, forecast_id)
            row.status = ForecastStatus.RUNNING
            row.started_at = datetime.now(UTC)
            view = forecast_view(row)
        self.progress(view, 0.0)
        return view

    async def lived_epoch(self, forecast_id: int, living: Living, scenario_name: str, context: JobContext) -> None:
        async with self.database.write() as session:
            row = await self.row(session, forecast_id)
            row.report = {**row.report, "epochs_done": min(living.done.values())}
            view = forecast_view(row)
        context.report(living.share, f"{scenario_name} epoch {living.done[scenario_name]}")
        self.progress(view, living.share)

    async def intervene(self, path: Path, interventions: Sequence[Intervention], rules: Rules) -> tuple[list[AppliedIntervention], list[int]]:
        database = database_at(path)
        try:
            async with database.read() as session:
                mark = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
            applied: list[AppliedIntervention] = []
            named: set[int] = set()
            for number, item in enumerate(interventions, start=1):
                if is_rule_step(item.action_id):
                    applied.append(await rule_on_copy(database, number, item))
                    continue
                spec = ACTIONS_BY_ID[item.action_id]
                try:
                    async with database.write() as session:
                        outcome = await run_ledgered(PlayerScope(session, rules), item.action_id, dict(item.input))
                except (AeronaError, ValidationError) as error:
                    reason = error.message if isinstance(error, AeronaError) else str(error)
                    raise ValidationFailedError(f"Intervention {number} ({spec.title}) was refused on the copy: {reason}") from error
                applied.append(AppliedIntervention(item.action_id, spec.title, outcome.message, outcome.essence_spent))
                named.update(outcome.created_ids)
                if outcome.target_node_id is not None:
                    named.add(outcome.target_node_id)
            async with database.read() as session:
                changed = await session.scalars(select(StateChangeRow.node_id).where(StateChangeRow.id > mark, StateChangeRow.node_id.is_not(None)).distinct())
                named.update(int(node_id) for node_id in changed if node_id is not None)
            return applied, sorted(named)
        finally:
            await database.dispose()

    async def spawn(self, errors: Path) -> asyncio.subprocess.Process:
        with errors.open("wb") as sink:
            return await asyncio.create_subprocess_exec(
                sys.executable, "-m", FORECAST_WORKER, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=sink
            )

    async def ordered(self, process: asyncio.subprocess.Process, path: Path, epochs: int) -> None:
        if process.stdin is None:
            raise ConflictError("The forecast worker takes no orders.")
        process.stdin.write((json.dumps({"path": str(path), "epochs": epochs}) + "\n").encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()

    async def live(self, forecast_id: int, process: asyncio.subprocess.Process, scenario_name: str, living: Living, context: JobContext) -> None:
        if process.stdout is None:
            raise ConflictError("The forecast worker has no output.")
        async for raw in process.stdout:
            line = raw.decode(errors="replace").strip()
            if not line.startswith("{"):
                continue
            lived = json.loads(line)
            if "epoch" not in lived:
                continue
            living.done[scenario_name] = int(lived["epoch"])
            living.seconds[scenario_name] += float(lived["seconds"])
            await self.lived_epoch(forecast_id, living, scenario_name, context)
        code = await process.wait()
        if code != 0 or living.done[scenario_name] < living.epochs:
            tail = await asyncio.to_thread(stderr_tail, self.folder(forecast_id) / f"{scenario_name}.log")
            raise ConflictError(f"The {scenario_name} copy could not live its epochs: {tail or f'exit {code}'}")

    async def work(self, forecast_id: int, interventions: Sequence[Intervention], rules: Rules, context: JobContext) -> dict[str, Any]:
        living: Living | None = None
        try:
            view = await self.began(forecast_id)
            folder = await asyncio.to_thread(self.prepared, forecast_id)
            living = Living(view.epochs)
            for name in SCENARIOS:
                living.processes.append(await self.spawn(folder / f"{name}.log"))
            workers = dict(zip(SCENARIOS, living.processes, strict=True))
            paths = {name: folder / f"{name}.db" for name in SCENARIOS}
            for path in paths.values():
                await asyncio.to_thread(online_copy, self.live_path, path)
            started = asyncio.get_running_loop().time()
            await self.ordered(workers[BASELINE], paths[BASELINE], view.epochs)
            baseline = asyncio.ensure_future(self.live(forecast_id, workers[BASELINE], BASELINE, living, context))
            try:
                start = await world_state(paths[INTERVENED])
                applied, touched = await self.intervene(paths[INTERVENED], interventions, rules)
                await self.ordered(workers[INTERVENED], paths[INTERVENED], view.epochs)
                await asyncio.gather(baseline, self.live(forecast_id, workers[INTERVENED], INTERVENED, living, context))
            finally:
                if not baseline.done():
                    baseline.cancel()
            outcomes = await asyncio.gather(
                scenario(paths[BASELINE], start.epoch, touched, living.seconds[BASELINE]),
                scenario(paths[INTERVENED], start.epoch, touched, living.seconds[INTERVENED]),
            )
            report = ForecastReport(
                start_epoch=start.epoch,
                end_epoch=start.epoch + view.epochs,
                start_population=start.population,
                start_prosperity=start.prosperity,
                start_communities=start.communities,
                start_wars=start.wars,
                interventions=applied,
                baseline=outcomes[0],
                intervened=outcomes[1],
                seconds=round(asyncio.get_running_loop().time() - started, 2),
            )
            await self.clean(forecast_id, living)
            await self.finish(forecast_id, ForecastStatus.DONE, report=report)
            return {FORECAST_ID_KEY: forecast_id, "status": ForecastStatus.DONE.value}
        except asyncio.CancelledError:
            await self.clean(forecast_id, living)
            await self.finish(forecast_id, ForecastStatus.CANCELLED)
            raise
        except Exception as error:
            await self.clean(forecast_id, living)
            await self.finish(forecast_id, ForecastStatus.FAILED, error=error.message if isinstance(error, AeronaError) else str(error) or type(error).__name__)
            raise
        finally:
            await self.clean(forecast_id, living)

    async def clean(self, forecast_id: int, living: Living | None) -> None:
        await self.stop(living)
        await asyncio.to_thread(shutil.rmtree, self.folder(forecast_id), True)

    async def stop(self, living: Living | None) -> None:
        for process in living.processes if living is not None else []:
            if process.returncode is None:
                process.kill()
                await process.wait()
