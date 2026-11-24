from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.body import AIR, GRAVITY
from aerona.constants.units import PERCENT
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.made import AugmentKind
from aerona.domain.enums.world import Atmosphere
from aerona.engine.primitives.augment_bonus import kind_strength
from aerona.rules.registry import Rules

TOXIC = 80
CLEAN = 10


@dataclass(frozen=True)
class Ground:
    air: int
    gravity: int
    warmth: int
    toxins: int
    radiation: int = 0
    light: int = PERCENT // 2
    humidity: int = PERCENT // 2


def ground_of(world: WorldRow, land: RegionEnvironmentRow | None, *, radiation: int = 0, light: int = PERCENT // 2) -> Ground:
    toxins = TOXIC if world.atmosphere is Atmosphere.TOXIC else CLEAN
    humidity = land.moisture if land is not None else PERCENT // 2
    return Ground(AIR[world.atmosphere], GRAVITY[world.gravity], land.temperature if land is not None else PERCENT // 2, toxins, radiation, light, humidity)


def excess(row: BodySystemRow, ground: Ground) -> int:
    if not row.present:
        return 0
    over = [
        ground.gravity - row.gravity_max,
        row.cold_min - ground.warmth,
        ground.warmth - row.heat_max,
        ground.toxins - row.toxin_tolerance,
        ground.radiation - row.radiation_max,
        row.light_min - ground.light,
        abs(ground.humidity - PERCENT // 2) - row.humidity_range // 2,
    ]
    if row.system is BodySystem.BREATH:
        over.append(row.air_need - ground.air)
    return max(0, *over)


async def world_excess(session: AsyncSession, rules: Rules, holder_id: int, world: WorldRow, *, bearer_id: int | None = None) -> int:
    rows = await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == holder_id).order_by(BodySystemRow.id))
    ground = ground_of(world, None)
    worst = max((excess(row, ground) for row in rows), default=0)
    support = await kind_strength(session, bearer_id, AugmentKind.LIFE_SUPPORT) * rules.augments.life_support_pct // PERCENT if bearer_id is not None else 0
    return max(0, worst - support)
