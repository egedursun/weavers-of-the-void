import logging
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.random import SeededRandom
from aerona.db.repositories.chronicle import ChronicleClock, ChronicleDraft, ChronicleRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.epochs import EpochRunRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.meta import NotificationRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.epoch import EpochPhase
from aerona.engine.context import phase_window
from aerona.events.feed_categories import feed_category
from aerona.rules.registry import Rules
from aerona.services.narrative import clean_chronicle_text
from aerona.services.notifications import Notifier

logger = logging.getLogger(__name__)

YEAR_STREAM = "chronicle.year"
CREATOR_HAND_TEMPLATE = "creator.hand"
WORLD_BIRTH_TEMPLATE = "cosmos.world_birth"
CREATOR_HAND_TEXT = "{creator}'s hand: {text}"
WORLD_BIRTH_TEXT = "{birther} brought forth a new world, {world} ({kind})."
FEED_KINDS = frozenset({ChronicleKind.WORLD, ChronicleKind.ENGINE_RAW})


@dataclass(frozen=True)
class ChronicleLine:
    kind: ChronicleKind
    text: str
    entity_ids: Sequence[int] = ()
    son_id: int | None = None
    world_id: int | None = None
    epoch: int | None = None
    template_key: str | None = None
    feed_category: FeedCategory | None = None
    phase: EpochPhase | None = None


async def phase_of_epoch(session: AsyncSession, epoch: int) -> EpochPhase:
    run = await session.get(EpochRunRow, epoch)
    return run.phase_value if run is not None else EpochPhase.NOT_STARTED


class ChronicleWriter:
    def __init__(self, notifier: Notifier) -> None:
        self._notifier = notifier

    async def write(self, session: AsyncSession, rules: Rules, line: ChronicleLine) -> ChronicleRow:
        cosmos = await CosmosRepository(session).require_cosmos()
        epoch = line.epoch if line.epoch is not None else cosmos.epoch
        text = clean_chronicle_text(line.text)
        category = line.feed_category
        if category is None and line.kind in FEED_KINDS:
            category = feed_category(line.template_key, text)
        phase = line.phase if line.phase is not None else await phase_of_epoch(session, epoch)
        salt = int(await session.scalar(select(func.coalesce(func.max(ChronicleRow.id), 0))) or 0)
        clock = ChronicleClock(
            years_per_epoch=rules.time.years_per_epoch,
            window=phase_window(rules, phase),
            pace_divisor=rules.time.year_pace_divisor,
            rng=SeededRandom.for_epoch(cosmos.rng_seed, epoch, f"{YEAR_STREAM}.{salt}"),
        )
        draft = ChronicleDraft(
            epoch=epoch,
            kind=line.kind,
            text=text,
            entity_ids=line.entity_ids,
            son_id=line.son_id,
            world_id=line.world_id,
            feed_category=category,
            template_key=line.template_key,
        )
        written = await ChronicleRepository(session).append(draft, clock)
        await self._notify(session, rules, written.row, list(line.entity_ids))
        return written.row

    async def creator_hand(self, session: AsyncSession, rules: Rules, text: str, entity_ids: Sequence[int] = ()) -> ChronicleRow:
        creator = await CosmosRepository(session).require_creator()
        line = ChronicleLine(
            kind=ChronicleKind.CREATOR_HAND,
            text=CREATOR_HAND_TEXT.format(creator=creator.name, text=text),
            entity_ids=entity_ids,
            template_key=CREATOR_HAND_TEMPLATE,
        )
        return await self.write(session, rules, line)

    async def world_birth(
        self, session: AsyncSession, rules: Rules, birther_name: str, world: WorldRow, *, linked_entity_ids: Sequence[int] = (), son_id: int | None = None
    ) -> ChronicleRow:
        line = ChronicleLine(
            kind=ChronicleKind.WORLD_BIRTH,
            text=WORLD_BIRTH_TEXT.format(birther=birther_name, world=world.name, kind=WORLD_TYPES[world.world_type].label.lower()),
            entity_ids=linked_entity_ids,
            son_id=son_id,
            world_id=world.id,
            template_key=WORLD_BIRTH_TEMPLATE,
        )
        return await self.write(session, rules, line)

    async def notify_unclassified(self, session: AsyncSession, rules: Rules, since_id: int) -> int:
        notified = select(NotificationRow.chronicle_id).where(NotificationRow.chronicle_id.is_not(None))
        statement = select(ChronicleRow).where(ChronicleRow.id > since_id, ChronicleRow.id.not_in(notified)).order_by(ChronicleRow.id)
        created = 0
        for row in await session.scalars(statement):
            ids = await ChronicleRepository(session).entity_ids(row.id)
            created += await self._notify(session, rules, row, ids)
        return created

    async def _notify(self, session: AsyncSession, rules: Rules, row: ChronicleRow, entity_ids: list[int]) -> bool:
        try:
            async with session.begin_nested():
                created = await self._notifier.from_chronicle(
                    session,
                    rules,
                    chronicle_id=row.id,
                    epoch=row.epoch,
                    kind=row.kind,
                    text=row.text,
                    son_id=row.son_id,
                    entity_ids=entity_ids,
                    feed_category=row.feed_category,
                )
        except Exception:
            logger.exception("notification for chronicle line %s failed", row.id)
            return False
        return created is not None


async def linked_entity_ids(session: AsyncSession, chronicle_id: int) -> list[int]:
    statement = select(ChronicleEntityRow.entity_id).where(ChronicleEntityRow.chronicle_id == chronicle_id).order_by(ChronicleEntityRow.position)
    return list(await session.scalars(statement))
