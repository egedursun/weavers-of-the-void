import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.warfare import WAR_NAME_TEMPLATE
from aerona.db.tables.node import NodeRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.war import WarSide
from aerona.engine.primitives.renames import rename_everywhere
from aerona.engine.services.war import every_side

PAIRED = re.compile(WAR_NAME_TEMPLATE.format(first="(?P<first>.+)", second="(?P<second>.+)"))


async def parties_of(session: AsyncSession, war: WarRow) -> tuple[str, str] | None:
    sides = await every_side(session, war.id)
    attacker = next((row.entity_id for row in sides if row.side is WarSide.ATTACKER), None)
    defender = next((row.entity_id for row in sides if row.side is WarSide.DEFENDER), None)
    if attacker is None or defender is None:
        return None
    first, second = await session.get(NodeRow, attacker), await session.get(NodeRow, defender)
    return (first.name, second.name) if first is not None and second is not None else None


async def wars_named_after_strangers(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for war in await session.scalars(select(WarRow).order_by(WarRow.id)):
        event = await session.get(NodeRow, war.event_entity_id)
        if event is None or held(event.id) or PAIRED.fullmatch(event.name) is None:
            continue
        sides = [await session.get(NodeRow, row.entity_id) for row in await every_side(session, war.id)]
        if not any(side.name in event.name for side in sides if side is not None):
            found.append(war.id)
    return found


async def name_war_by_its_parties(session: AsyncSession, war_id: int) -> None:
    war = await session.get(WarRow, war_id)
    parties = await parties_of(session, war) if war is not None else None
    if war is None or parties is None:
        return
    await rename_everywhere(session, war.event_entity_id, WAR_NAME_TEMPLATE.format(first=parties[0], second=parties[1]), free=True)
