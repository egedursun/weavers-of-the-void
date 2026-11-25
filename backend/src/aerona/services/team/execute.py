from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.account_scope import AccountRef
from aerona.core.errors import ForbiddenError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.divine_will import DivineWillPlanStepRow
from aerona.domain.enums.divine_will import StepStatus
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.manager import running_group
from aerona.rules.registry import Rules
from aerona.services.accounts.guard import GrantedAccess, current_grant
from aerona.services.container import Services
from aerona.services.player.catalog import ActionSpec
from aerona.services.player.scope import ActionOutcome

NO_LONGER_MEMBER = "{author} no longer has access to this universe."
SOMEONE = "Someone"
PLAN_STEP: ContextVar[tuple[int, int] | None] = ContextVar("plan_step", default=None)


def world_busy(services: Services) -> bool:
    return services.jobs.busy_group(WORLD_GROUP) is not None and running_group() != WORLD_GROUP


async def rules_in(services: Services, session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None or not cosmos.rules_snapshot:
        return services.rules.current
    return rules_from_snapshot(cosmos.rules_snapshot)


async def run_lever(services: Services, spec: ActionSpec, payload: Mapping[str, Any]) -> ActionOutcome:
    command = spec.input_model.model_validate(dict(payload))
    if spec.sync is not None:
        async with services.database.write() as session:
            rules = await rules_in(services, session)
            return await spec.sync(services.player.scope(session, rules), command)
    if spec.job is None:
        raise LookupError(spec.id)
    async with services.database.read() as session:
        rules = await rules_in(services, session)
    return await spec.job(services.player, rules, command)


@contextmanager
def stepping(plan_id: int, ordinal: int) -> Iterator[None]:
    token = PLAN_STEP.set((plan_id, ordinal))
    try:
        yield
    finally:
        PLAN_STEP.reset(token)


def plan_step() -> tuple[int, int] | None:
    return PLAN_STEP.get()


async def settle_plan_step(session: AsyncSession, plan_id: int | None, ordinal: int | None, *, ok: bool, text: str, entry_id: int | None) -> None:
    if plan_id is None or ordinal is None:
        return
    step = await session.get(DivineWillPlanStepRow, (plan_id, ordinal))
    if step is None:
        return
    step.status = StepStatus.DONE if ok else StepStatus.FAILED
    step.result_text = text if ok else ""
    step.error = "" if ok else text
    step.ledger_entry_id = entry_id


def canon_gated() -> bool:
    grant = current_grant()
    return grant is not None and grant.canon_approval and not grant.access.admin


async def author_grant(services: Services, author: AccountRef | None) -> GrantedAccess | None:
    resolver = services.team.grant_of
    if resolver is None or author is None:
        return None
    grant = await resolver(author.id)
    if grant is None:
        raise ForbiddenError(NO_LONGER_MEMBER.format(author=author.name or SOMEONE))
    return grant
