from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus

God = SonRow | ForeignGodRow


async def god_of(session: AsyncSession, node_id: int | None) -> God | None:
    if node_id is None:
        return None
    son = await session.get(SonRow, node_id)
    if son is not None:
        return son
    return await session.get(ForeignGodRow, node_id)


async def divine_of(session: AsyncSession, node_id: int | None) -> God | CreatorRow | None:
    found = await god_of(session, node_id)
    if found is not None:
        return found
    return await session.get(CreatorRow, node_id) if node_id is not None else None


def alive(god: God) -> bool:
    if isinstance(god, SonRow):
        return god.status is not SonStatus.DEAD
    return god.status is not ForeignGodStatus.DEAD


def domains_of(god: God) -> tuple[Domain, ...]:
    if isinstance(god, SonRow):
        return god.domains
    return tuple(domain for domain in (god.domain_primary, god.domain_secondary) if domain is not None)


async def living_gods(session: AsyncSession) -> list[God]:
    sons: list[God] = list(await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))
    gods = await session.scalars(select(ForeignGodRow).where(ForeignGodRow.status != ForeignGodStatus.DEAD).order_by(ForeignGodRow.id))
    return sons + list(gods)


async def faithful_communities(session: AsyncSession, god_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == god_id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        )
        .order_by(EntityRow.id)
    )
    return list(dict.fromkeys(await session.scalars(statement)))
