from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import LegendProfileRow
from aerona.domain.enums.bond import BondKind


@dataclass(frozen=True)
class DerivedBond:
    source_node_id: int
    target_node_id: int
    kind: BondKind
    description: str
    epoch: int


Deriver = Callable[[AsyncSession, int], Awaitable[list[DerivedBond]]]


async def tellers(session: AsyncSession, node_id: int) -> list[DerivedBond]:
    found: list[DerivedBond] = []
    own = await session.get(LegendProfileRow, node_id)
    if own is not None:
        found.extend(DerivedBond(teller, node_id, BondKind.TELLS, f"believes it at {own.credence}%", own.updated_epoch) for teller in own.tellers)
    for row in await session.scalars(select(LegendProfileRow).order_by(LegendProfileRow.legend_entity_id)):
        if node_id in row.tellers and row.legend_entity_id != node_id:
            found.append(DerivedBond(node_id, row.legend_entity_id, BondKind.TELLS, f"believes it at {row.credence}%", row.updated_epoch))
    return found


async def fixed(session: AsyncSession, node_id: int) -> list[DerivedBond]:
    rows = await session.scalars(
        select(LegendProfileRow).where((LegendProfileRow.legend_entity_id == node_id) | (LegendProfileRow.fixed_in_entity_id == node_id))
    )
    return [
        DerivedBond(row.legend_entity_id, row.fixed_in_entity_id, BondKind.FIXED_IN, "the telling is frozen in this work", row.updated_epoch)
        for row in rows
        if row.fixed_in_entity_id is not None
    ]


DERIVERS: dict[BondKind, Deriver] = {BondKind.TELLS: tellers, BondKind.FIXED_IN: fixed}


def register(kind: BondKind, deriver: Deriver) -> None:
    DERIVERS[kind] = deriver


async def derived_bonds(session: AsyncSession, node_id: int) -> list[DerivedBond]:
    found: list[DerivedBond] = []
    for kind in sorted(DERIVERS):
        found.extend(await DERIVERS[kind](session, node_id))
    return found
