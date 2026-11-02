from collections.abc import Sequence
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.db.repositories.chronicle import ChronicleClock, ChronicleDraft, ChronicleRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.epoch import EpochPhase
from aerona.engine.context import phase_window
from aerona.rules.registry import Rules

CHRONICLE_STREAM = "agents.chronicle"


class ChroniclePhase(StrEnum):
    GODS = "gods"
    MORTALS = "mortals"
    ENGINE = "engine"
    FATE = "fate"
    NEW_EPOCH = "new_epoch"


EPOCH_PHASES = {
    ChroniclePhase.GODS: EpochPhase.GODS,
    ChroniclePhase.MORTALS: EpochPhase.MORTALS,
    ChroniclePhase.ENGINE: EpochPhase.ENGINE,
    ChroniclePhase.FATE: EpochPhase.FATE,
    ChroniclePhase.NEW_EPOCH: EpochPhase.NOT_STARTED,
}


async def write_line(
    session: AsyncSession,
    rules: Rules,
    epoch: int,
    kind: ChronicleKind,
    text: str,
    *,
    key: str,
    phase: ChroniclePhase = ChroniclePhase.FATE,
    entity_ids: Sequence[int] = (),
    son_id: int | None = None,
    world_id: int | None = None,
    feed: FeedCategory | None = None,
) -> ChronicleRow:
    cosmos = await CosmosRepository(session).require_cosmos()
    clock = ChronicleClock(
        years_per_epoch=rules.time.years_per_epoch,
        window=phase_window(rules, EPOCH_PHASES[phase]),
        pace_divisor=1,
        rng=SeededRandom.for_epoch(cosmos.rng_seed, epoch, f"{CHRONICLE_STREAM}.{key}"),
    )
    draft = ChronicleDraft(epoch=epoch, kind=kind, text=text, entity_ids=entity_ids, son_id=son_id, world_id=world_id, feed_category=feed, template_key=key)
    write = await ChronicleRepository(session).append(draft, clock)
    return write.row
