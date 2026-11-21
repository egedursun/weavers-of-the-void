from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow, WarRemnantRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.mass_weapons import ProgrammeStage
from aerona.domain.enums.war import WarStatus
from aerona.engine.mass_weapons.book import can_build

OPEN_WARS = frozenset({WarStatus.ONGOING, WarStatus.MOBILIZING})


async def unskilled_weapons(session: AsyncSession) -> list[int]:
    weapons = await session.scalars(select(MassWeaponRow).order_by(MassWeaponRow.id))
    made = [weapon for weapon in weapons if weapon.count or weapon.readiness or weapon.stage is not ProgrammeStage.SOUGHT]
    return [weapon.id for weapon in made if not await can_build(session, weapon.holder_entity_id, weapon.harm, weapon.reach)]


async def dismantle(session: AsyncSession, key: int) -> None:
    weapon = await session.get(MassWeaponRow, key)
    if weapon is not None:
        weapon.count, weapon.readiness, weapon.stage = 0, 0, ProgrammeStage.SOUGHT


async def unended_wars(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(WarRemnantRow).where(WarRemnantRow.war_id.is_not(None)).order_by(WarRemnantRow.id)):
        war = await session.get(WarRow, row.war_id)
        if war is not None and war.status in OPEN_WARS:
            found.append(row.id)
    return found


async def forget_war(session: AsyncSession, key: int) -> None:
    row = await session.get(WarRemnantRow, key)
    if row is not None:
        row.war_id = None


async def misplaced_remnants(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(WarRemnantRow).order_by(WarRemnantRow.id))
    return [row.id for row in rows if (row.region_entity_id is None) == (row.orbit_world_id is None)]


async def place_remnant(session: AsyncSession, key: int) -> None:
    row = await session.get(WarRemnantRow, key)
    if row is None:
        return
    if row.region_entity_id is not None:
        row.orbit_world_id = None
    else:
        await session.delete(row)


async def self_postures(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(DeterrencePostureRow).order_by(DeterrencePostureRow.id))
    return [row.id for row in rows if row.toward_entity_id == row.holder_entity_id]


async def widen_posture(session: AsyncSession, key: int) -> None:
    row = await session.get(DeterrencePostureRow, key)
    if row is not None:
        row.toward_entity_id = None
