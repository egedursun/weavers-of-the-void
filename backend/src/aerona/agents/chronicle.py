from collections.abc import Mapping, Sequence
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.rules.registry import Rules


class ChroniclePhase(StrEnum):
    GODS = "gods"
    MORTALS = "mortals"
    ENGINE = "engine"
    FATE = "fate"
    NEW_EPOCH = "new_epoch"


async def record_line(
    session: AsyncSession,
    rules: Rules,
    key: str,
    *,
    roles: Mapping[IncidentRole, RoleValue],
    facts: Mapping[str, FactInput] | None = None,
    phase: ChroniclePhase = ChroniclePhase.FATE,
    kind: ChronicleKind | None = None,
    son_id: int | None = None,
    world_id: int | None = None,
    feed: FeedCategory | None = None,
    steps: Sequence[StepDraft] = (),
) -> str:
    ctx = await manual_context(session, f"agents.{phase.value}", rules, key=key)
    written = await record(ctx, key, roles=roles, facts=facts, kind=kind, son_id=son_id, world_id=world_id, feed=feed, steps=steps)
    return written.text
