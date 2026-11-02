import asyncio
import logging
from collections.abc import Callable, Sequence
from typing import Any

from aerona.db.session import Database
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import ITEMS_KEY
from aerona.rules.registry import Rules
from aerona.services.notifications import Notifier

logger = logging.getLogger(__name__)

SUMMARY_COUNTS = (
    ("rejected", "{count} creations rejected by Fate"),
    ("fixed", "{count} creations corrected by Fate"),
    ("worlds_born", "{count} sensed worlds born"),
    ("engine_notes", "{count} events in the world's own course"),
    ("localised_lines", "{count} lines localised"),
)
EPOCH_NAME_LINE = 'The age was named "{name}"'
COUNCIL_LINE = "Council: {motion}"
DURATION_LINE = "The epoch took {seconds} seconds"
UNKNOWN_ERROR = "Something went wrong in the background."


def count_of(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, list | tuple | dict | set):
        return len(value)
    return 0


def summary_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    name = summary.get("epoch_name")
    if isinstance(name, str) and name:
        lines.append(EPOCH_NAME_LINE.format(name=name))
    for key, template in SUMMARY_COUNTS:
        count = count_of(summary.get(key))
        if count:
            lines.append(template.format(count=count))
    motion = summary.get("council")
    if isinstance(motion, str) and motion:
        lines.append(COUNCIL_LINE.format(motion=motion))
    duration = count_of(summary.get("duration_s"))
    if duration:
        lines.append(DURATION_LINE.format(seconds=duration))
    return lines


class NotificationStream:
    def __init__(self, bus: EventBus, database: Database, notifier: Notifier, rules: Callable[[], Rules], read_only: Callable[[], bool]) -> None:
        self._bus = bus
        self._database = database
        self._notifier = notifier
        self._rules = rules
        self._read_only = read_only
        self._tasks: set[asyncio.Task[None]] = set()

    def attach(self) -> None:
        self._bus.add_listener(self.on_event)

    def on_event(self, event: Event) -> None:
        if event.kind is EventKind.EPOCH_FINISHED:
            self._spawn(self.epoch_finished(event.payload))
        elif event.kind is EventKind.SYSTEM_ERROR and not event.payload.get("will_retry"):
            self._spawn(self.agent_error(event.payload))
        elif event.kind is EventKind.JOB_FINISHED:
            self._spawn(self.job_finished(event.payload))

    def _spawn(self, work: Any) -> None:
        if self._read_only():
            work.close()
            return
        try:
            task = asyncio.get_running_loop().create_task(work)
        except RuntimeError:
            work.close()
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def epoch_finished(self, payload: dict[str, Any]) -> None:
        epoch = payload.get("epoch")
        summary = payload.get("summary")
        if not isinstance(epoch, int):
            return
        lines: Sequence[str] = summary_lines(summary) if isinstance(summary, dict) else []
        try:
            async with self._database.write() as session:
                await self._notifier.epoch_finished(session, self._rules(), epoch, lines)
        except Exception:
            logger.exception("epoch notification failed")

    async def job_finished(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        items = result.get(ITEMS_KEY) if isinstance(result, dict) else None
        job_id = payload.get("job_id")
        if not isinstance(items, list) or not items or not isinstance(job_id, str):
            return
        label = payload.get("label")
        title = label if isinstance(label, str) and label else str(payload.get("kind") or "work")
        try:
            async with self._database.write() as session:
                await self._notifier.job_finished(session, self._rules(), job_id, title, [item for item in items if isinstance(item, dict)])
        except Exception:
            logger.exception("job notification failed")

    async def agent_error(self, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        son_id = payload.get("son_id")
        try:
            async with self._database.write() as session:
                await self._notifier.agent_error(session, self._rules(), str(text) if text else UNKNOWN_ERROR, son_id if isinstance(son_id, int) else None)
        except Exception:
            logger.exception("error notification failed")

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
