from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.kin_dynamics import KinDynamicRow, KinRivalryRow
from aerona.domain.enums.bond import BondKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import active_bonds, living_entity


@dataclass
class KinTally:
    favoured: int = 0
    rivalries: int = 0
    disowned: int = 0
    reconciled: int = 0
    blends: int = 0
    elders: int = 0
    steered: int = 0
    splits: int = 0
    designated: int = 0


async def dynamic_of(ctx: TickContext, *, house: int | None = None, household: int | None = None) -> KinDynamicRow:
    query = select(KinDynamicRow).where(KinDynamicRow.house_entity_id == house, KinDynamicRow.household_id == household)
    found = await ctx.session.scalar(query.order_by(KinDynamicRow.id).limit(1))
    if found is not None:
        return found
    row = KinDynamicRow(house_entity_id=house, household_id=household, formed_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def children_of(session: AsyncSession, parent_id: int) -> list[int]:
    found: list[int] = []
    for bond in await active_bonds(session, [BondKind.PARENT_OF], sources=[parent_id]):
        child = await living_entity(session, bond.target_node_id)
        if child is not None and child.id not in found:
            found.append(child.id)
    return sorted(found)


async def parents_of(session: AsyncSession, child_id: int) -> list[int]:
    return sorted({bond.source_node_id for bond in await active_bonds(session, [BondKind.PARENT_OF], targets=[child_id])})


async def rivalry_between(session: AsyncSession, first: int, second: int) -> KinRivalryRow | None:
    pair = sorted((first, second))
    query = select(KinRivalryRow).where(KinRivalryRow.first_node_id == pair[0], KinRivalryRow.second_node_id == pair[1], KinRivalryRow.ended_epoch.is_(None))
    return await session.scalar(query.limit(1))
