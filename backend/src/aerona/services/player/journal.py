from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import capture_changes
from aerona.services.player.ports import LedgerCapture


class RowJournal:
    @asynccontextmanager
    async def capture(self, session: AsyncSession) -> AsyncIterator[LedgerCapture]:
        async with capture_changes(session) as capture:
            yield capture
