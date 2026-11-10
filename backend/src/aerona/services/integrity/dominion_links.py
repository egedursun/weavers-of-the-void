from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.dominion import DivineCreatureRow, DominionRow, MagicSiteRow, RegionDominionRow, ThroneRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus


async def fallen_gods(session: AsyncSession) -> list[int]:
    sons = select(SonRow.id).where(SonRow.status == SonStatus.DEAD)
    gods = select(ForeignGodRow.id).where(ForeignGodRow.status == ForeignGodStatus.DEAD)
    return sorted({*await session.scalars(sons), *await session.scalars(gods)})


async def mend_dominion_links(session: AsyncSession) -> int:
    fallen = await fallen_gods(session)
    gone = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    statements = [
        delete(DivineCreatureRow).where(DivineCreatureRow.creature_entity_id.in_(gone)),
        delete(DivineCreatureRow).where(DivineCreatureRow.god_node_id.in_(fallen)),
        delete(DominionRow).where(DominionRow.god_node_id.in_(fallen)),
        delete(RegionDominionRow).where(RegionDominionRow.god_node_id.in_(fallen)),
        update(ThroneRow).where(ThroneRow.holder_node_id.in_(fallen)).values(holder_node_id=None, since_epoch=None),
        update(MagicSiteRow).where(MagicSiteRow.holder_node_id.in_(fallen)).values(holder_node_id=None),
        update(MagicSiteRow).where(MagicSiteRow.holder_node_id.in_(gone)).values(holder_node_id=None),
    ]
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
