import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import ChronicleRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.meta import NotificationRow
from aerona.rules.registry import Rules
from aerona.services.notifications import Notifier

logger = logging.getLogger(__name__)


class ChronicleWriter:
    def __init__(self, notifier: Notifier) -> None:
        self._notifier = notifier

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
