from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.leader_cults import CultFate
from aerona.engine.minds.profiles import MADE_ORIGINS


async def cults(session: AsyncSession) -> list[LeaderCultRow]:
    return list(await session.scalars(select(LeaderCultRow).order_by(LeaderCultRow.id)))


async def leads(session: AsyncSession, node_id: int) -> bool:
    entity = await session.get(EntityRow, node_id)
    if entity is None:
        return False
    if entity.entity_type is EntityType.MORTAL:
        return True
    mind = await session.get(MindProfileRow, node_id)
    return mind is not None and mind.origin in MADE_ORIGINS


async def godly_cults(session: AsyncSession) -> list[int]:
    return [cult.id for cult in await cults(session) if cult.fate is CultFate.LIVING and not await leads(session, cult.leader_node_id)]


async def end_godly(session: AsyncSession, key: int) -> None:
    cult = await session.get(LeaderCultRow, key)
    if cult is not None:
        cult.fate, cult.ended_epoch = CultFate.TORN_DOWN, cult.begun_epoch


async def lost_promoters(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for cult in await cults(session):
        promoters = list(cult.promoters or [])
        known = set(await session.scalars(select(NodeRow.id).where(NodeRow.id.in_(promoters)))) if promoters else set()
        if any(node not in known for node in promoters):
            found.append(cult.id)
    return found


async def keep_promoters(session: AsyncSession, key: int) -> None:
    cult = await session.get(LeaderCultRow, key)
    if cult is not None:
        known = set(await session.scalars(select(NodeRow.id).where(NodeRow.id.in_(list(cult.promoters or [])))))
        cult.promoters = [node for node in cult.promoters or [] if node in known]


async def mismatched_ends(session: AsyncSession) -> list[int]:
    return [cult.id for cult in await cults(session) if (cult.fate is CultFate.LIVING) != (cult.ended_epoch is None)]


async def mend_end(session: AsyncSession, key: int) -> None:
    cult = await session.get(LeaderCultRow, key)
    if cult is not None:
        cult.ended_epoch = None if cult.fate is CultFate.LIVING else max(cult.begun_epoch, cult.ended_epoch or cult.begun_epoch)
