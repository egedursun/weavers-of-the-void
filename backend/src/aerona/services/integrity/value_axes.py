from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mind import CultureValueRow, PersonalityValueRow
from aerona.domain.enums.mind import ValueAxis


async def complete_value_axes(session: AsyncSession) -> int:
    added = 0
    cultures: dict[int, set[ValueAxis]] = defaultdict(set)
    for owner, axis in await session.execute(select(CultureValueRow.entity_id, CultureValueRow.axis).order_by(CultureValueRow.entity_id, CultureValueRow.axis)):
        cultures[owner].add(axis)
    for owner, present in sorted(cultures.items()):
        for axis in ValueAxis:
            if axis not in present:
                session.add(CultureValueRow(entity_id=owner, axis=axis, value=0))
                added += 1
    persons: dict[int, set[ValueAxis]] = defaultdict(set)
    for owner, axis in await session.execute(
        select(PersonalityValueRow.node_id, PersonalityValueRow.axis).order_by(PersonalityValueRow.node_id, PersonalityValueRow.axis)
    ):
        persons[owner].add(axis)
    for owner, present in sorted(persons.items()):
        for axis in ValueAxis:
            if axis not in present:
                session.add(PersonalityValueRow(node_id=owner, axis=axis, value=0))
                added += 1
    await session.flush()
    return added
