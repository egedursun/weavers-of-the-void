import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.team import PROPOSED_TEXT, QUEUED_TEXT
from aerona.core.act_note import current_note
from aerona.core.errors import AeronaError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.divine_will import ConfirmationReason
from aerona.domain.enums.team import QueuedActSource
from aerona.engine.primitives.manual import silent
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.divine_will.reading import Reading, summarise
from aerona.services.player.catalog import ActionSpec, action
from aerona.services.player.scope import ActionOutcome, PlayerScope
from aerona.services.team.execute import world_busy
from aerona.services.team.gate import admit
from aerona.services.team.queue import QueueDraft, enqueue

UNDO_ACTION = "ledger:undo"
UNDO_TITLE = "Undo ledger entry {entry_id}"
DECLARED_ESSENCE = re.compile(r"(\d+)\s+essence")
JOB_ID_KEY = "job_id"


class PreviewRolledBackError(Exception):
    pass


def refusal(error: Exception, *, busy: bool = False) -> dict[str, Any]:
    if isinstance(error, ValidationError):
        text = f"The input did not fit the act: {error.errors(include_url=False)}"
    elif isinstance(error, AeronaError):
        text = error.message
    else:
        text = str(error) or type(error).__name__
    return {"ok": False, "busy": busy, "error": text}


def declared_essence(cost: str) -> int:
    return max((int(found) for found in DECLARED_ESSENCE.findall(cost)), default=0)


def outcome_fields(outcome: ActionOutcome) -> dict[str, Any]:
    job_id = outcome.values.get(JOB_ID_KEY)
    return {
        "message": outcome.message,
        "essence": outcome.essence_spent,
        "essence_gained": outcome.essence_gained,
        "target_node_id": outcome.target_node_id,
        "created_ids": list(outcome.created_ids),
        "ledger_entry_id": outcome.ledger_entry_id,
        "job_id": str(job_id) if job_id is not None else "",
        "values": {key: value for key, value in outcome.values.items() if key != JOB_ID_KEY},
    }


def verdict(destructive: bool, costly: bool) -> str:
    if destructive and costly:
        return ConfirmationReason.BOTH.value
    if destructive:
        return ConfirmationReason.DESTRUCTIVE.value
    if costly:
        return ConfirmationReason.COSTLY.value
    return ""


class CatalogPlayer:
    def __init__(self, services: Services) -> None:
        self.services = services

    def epoch_running(self) -> bool:
        return world_busy(self.services)

    async def rules(self, session: AsyncSession) -> Rules:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None or not cosmos.rules_snapshot:
            return self.services.rules.current
        return rules_from_snapshot(cosmos.rules_snapshot)

    async def current_rules(self) -> Rules:
        async with self.services.database.read() as session:
            return await self.rules(session)

    def spec(self, action_id: str) -> ActionSpec:
        return action(action_id)

    def head(self, spec: ActionSpec, rules: Rules) -> dict[str, Any]:
        return {"ok": True, "busy": False, "error": "", "action_id": spec.id, "title": spec.title, "job": spec.job is not None, "cost": spec.cost(rules)}

    async def preview(self, action_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            spec = self.spec(action_id)
            command = spec.input_model.model_validate(dict(payload))
        except (AeronaError, ValidationError) as error:
            return refusal(error)
        rules = await self.current_rules()
        threshold = rules.divine_will.costly_essence
        if spec.sync is None or self.epoch_running():
            declared = declared_essence(spec.cost(rules))
            costly = declared >= threshold
            return {
                **self.head(spec, rules),
                "essence": declared,
                "essence_gained": 0,
                "deleted_nodes": [],
                "deleted_records": [],
                "ended": [],
                "tallies": [],
                "changes": [],
                "destructive": False,
                "costly": costly,
                "reason": verdict(False, costly),
                "busy": self.epoch_running(),
                "message": QUEUED_TEXT if self.epoch_running() else "",
            }
        try:
            return await self.rehearse(spec, command)
        except (AeronaError, ValidationError) as error:
            return refusal(error)

    async def rehearse(self, spec: ActionSpec, command: Any) -> dict[str, Any]:
        captured: dict[str, Any] = {}
        try:
            await self.rehearsed(spec, command, captured)
        except PreviewRolledBackError:
            return captured
        return captured

    async def rehearsed(self, spec: ActionSpec, command: Any, captured: dict[str, Any]) -> None:
        sync = spec.sync
        if sync is None:
            raise AeronaError(spec.id)
        async with self.services.database.write() as session:
            rules = await self.rules(session)
            outer = await session.begin_nested()
            try:
                captured.update(await self.rehearsal(session, rules, spec, sync, command))
            finally:
                if outer.is_active:
                    await outer.rollback()
            raise PreviewRolledBackError

    async def rehearsal(self, session: AsyncSession, rules: Rules, spec: ActionSpec, sync: Any, command: Any) -> dict[str, Any]:
        marker = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
        outcome = await sync(PlayerScope(session, rules, silent), command)
        await session.flush()
        changes = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.id > marker).order_by(StateChangeRow.id)))
        ids = {row.node_id for row in changes if row.node_id is not None} | {row.after_node_id for row in changes if row.after_node_id is not None}
        named = await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(ids))) if ids else None
        names = {int(node_id): str(name) for node_id, name in named} if named is not None else {}
        summary = summarise(Reading(changes, names))
        destructive = bool(summary["deleted_nodes"] or summary["deleted_records"] or summary["ended"])
        costly = outcome.essence_spent >= rules.divine_will.costly_essence
        found = {**self.head(spec, rules), **outcome_fields(outcome), **summary, "destructive": destructive, "costly": costly}
        found["ledger_entry_id"] = None
        found["reason"] = verdict(destructive, costly)
        return found

    async def perform(self, action_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            spec = self.spec(action_id)
            command = spec.input_model.model_validate(dict(payload))
        except (AeronaError, ValidationError) as error:
            return refusal(error)
        try:
            self.services.application.discovery.ensure_writable()
            rules = await self.current_rules()
            admitted = await admit(self.services, spec, command.model_dump(mode="json", exclude_unset=True), QueuedActSource.DIVINE_WILL)
        except (AeronaError, ValidationError) as error:
            return refusal(error)
        if admitted.queued is not None:
            return {**self.head(spec, rules), "queued": True, "queued_act_id": admitted.queued.id, "message": QUEUED_TEXT}
        if admitted.proposal is not None:
            return {**self.head(spec, rules), "proposed": True, "proposal_id": admitted.proposal.id, "message": PROPOSED_TEXT}
        if admitted.outcome is None:
            return refusal(AeronaError(spec.id))
        return {**self.head(spec, rules), **outcome_fields(admitted.outcome)}

    async def run(self, spec: ActionSpec, command: Any) -> tuple[ActionOutcome, Rules]:
        if spec.sync is not None:
            async with self.services.database.write() as session:
                rules = await self.rules(session)
                return await spec.sync(self.services.player.scope(session, rules), command), rules
        if spec.job is None:
            raise AeronaError(spec.id)
        rules = await self.current_rules()
        return await spec.job(self.services.player, rules, command), rules

    async def undo(self, ledger_entry_id: int) -> dict[str, Any]:
        running = self.epoch_running()
        if running:
            draft = QueueDraft(
                QueuedActSource.UNDO, UNDO_ACTION, UNDO_TITLE.format(entry_id=ledger_entry_id), {"entry_id": ledger_entry_id}, current_note().reason
            )
            queued = await enqueue(self.services, draft)
            return {"ok": True, "busy": False, "error": "", "queued": True, "queued_act_id": queued.id, "message": QUEUED_TEXT}
        try:
            self.services.application.discovery.ensure_writable()
            async with self.services.database.write() as session:
                rules = await self.rules(session)
                result = await self.services.application.ledger.undo(session, rules, ledger_entry_id, epoch_running=running)
        except AeronaError as error:
            return refusal(error, busy=running)
        return {"ok": True, "busy": False, "error": "", "entry_id": result.entry_id, "applied": list(result.applied), "conflicts": list(result.conflicts)}

    async def job(self, job_id: str) -> dict[str, Any]:
        try:
            row = await self.services.jobs.get(job_id)
        except AeronaError as error:
            return refusal(error)
        return {
            "ok": True,
            "busy": False,
            "error": row.error or "",
            "job_id": row.id,
            "kind": row.kind.value,
            "status": row.status.value,
            "progress": row.progress,
            "stage": row.stage or "",
            "result": row.result or {},
            "started_at": row.started_at.isoformat() if row.started_at is not None else "",
            "finished_at": row.finished_at.isoformat() if row.finished_at is not None else "",
        }
