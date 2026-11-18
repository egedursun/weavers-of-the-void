from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import MANUAL_STREAM_PREFIX
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.engine.context import Publisher, TickContext, TickEnvironment
from aerona.engine.notes import last_chronicle_id
from aerona.engine.stats import TickStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules


def silent(kind: EventKind, payload: dict[str, Any]) -> None:
    del kind, payload


async def manual_context(
    session: AsyncSession, action: str, rules: Rules | None = None, publish: Publisher | None = None, *, key: str = "", progress: float | None = None
) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    environment = TickEnvironment(
        rules=rules or rules_from_snapshot(cosmos.rules_snapshot),
        epoch=cosmos.epoch,
        world_seed=cosmos.rng_seed,
        lore_language=cosmos.lore_language,
        publish=publish or silent,
        stats=TickStats(),
        progress=progress,
    )
    nonce = await last_chronicle_id(session)
    stream = f"{MANUAL_STREAM_PREFIX}.{action}.{key}.{nonce}" if key else f"{MANUAL_STREAM_PREFIX}.{action}.{nonce}"
    return TickContext(environment, session, stream)
