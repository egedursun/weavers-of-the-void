from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from aerona.db.tables.intrigue import BeliefRow
from aerona.domain.enums.intrigue import BeliefSource
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal, settlement


async def test_believing_and_deleting_never_rescan_every_pending_row(session: AsyncSession, world: CoreWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = await manual_context(session, "pending_scans")
    town = await settlement(session, "Ashby", world, world.regions[0])
    holders = [await mortal(session, f"Holder {index}", world, town.id) for index in range(3)]
    await session.flush()
    scans = {"count": 0}
    original = Session.new

    def counted(self: Session) -> Any:
        scans["count"] += 1
        return original.fget(self) if original.fget is not None else None

    monkeypatch.setattr(Session, "new", property(counted))
    for holder in holders:
        for subject in range(200):
            await believe(ctx, holder.id, town.id, f"price.{subject}", 50, source=BeliefSource.RUMOUR, confidence=60)
    loose = BeliefRow(
        holder_node_id=holders[0].id, subject_node_id=town.id, attribute="defense", value=1, confidence=1, as_of_epoch=0, source=BeliefSource.RUMOUR, locked=[]
    )
    session.add(loose)
    await session.delete(loose)
    monkeypatch.setattr(Session, "new", original)
    assert scans["count"] == 0
