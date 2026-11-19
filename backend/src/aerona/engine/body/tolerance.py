from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.world import Atmosphere, Gravity

AIR: dict[Atmosphere, int] = {Atmosphere.NONE: 0, Atmosphere.THIN: 25, Atmosphere.NORMAL: 50, Atmosphere.DENSE: 75, Atmosphere.TOXIC: 50}
GRAVITY: dict[Gravity, int] = {Gravity.LOW: 25, Gravity.NORMAL: 50, Gravity.HIGH: 80}
TOXIC = 80
CLEAN = 10


@dataclass(frozen=True)
class Ground:
    air: int
    gravity: int
    warmth: int
    toxins: int


def ground_of(world: WorldRow, land: RegionEnvironmentRow | None) -> Ground:
    toxins = TOXIC if world.atmosphere is Atmosphere.TOXIC else CLEAN
    return Ground(AIR[world.atmosphere], GRAVITY[world.gravity], land.temperature if land is not None else PERCENT // 2, toxins)


def excess(row: BodySystemRow, ground: Ground) -> int:
    if not row.present:
        return 0
    over = [
        ground.gravity - row.gravity_max,
        row.cold_min - ground.warmth,
        ground.warmth - row.heat_max,
        ground.toxins - row.toxin_tolerance,
    ]
    if row.system is BodySystem.BREATH:
        over.append(row.air_need - ground.air)
    return max(0, *over)


async def world_excess(session: AsyncSession, holder_id: int, world: WorldRow) -> int:
    rows = await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == holder_id).order_by(BodySystemRow.id))
    ground = ground_of(world, None)
    return max((excess(row, ground) for row in rows), default=0)
