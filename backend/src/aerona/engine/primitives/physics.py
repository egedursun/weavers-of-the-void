from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.domain.enums.world import Atmosphere, Gravity, WorldType
from aerona.engine.cosmos.star_types import star_capacity_pct
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class WorldPhysics:
    time: float = 1.0
    capacity: float = 1.0
    war: int = 0
    world_type: WorldType = WorldType.ORDINARY


def capacity_pct(rules: Rules, atmosphere: Atmosphere) -> int:
    physics = rules.world_physics
    return {
        Atmosphere.NONE: physics.capacity_no_atmosphere,
        Atmosphere.THIN: physics.capacity_thin,
        Atmosphere.NORMAL: physics.capacity_normal,
        Atmosphere.DENSE: physics.capacity_dense,
        Atmosphere.TOXIC: physics.capacity_toxic,
    }[atmosphere]


def gravity_war(rules: Rules, gravity: Gravity) -> int:
    physics = rules.world_physics
    return {Gravity.LOW: physics.martiality_low_gravity, Gravity.NORMAL: physics.martiality_normal_gravity, Gravity.HIGH: physics.martiality_high_gravity}[
        gravity
    ]


def world_physics(rules: Rules, world: WorldRow | None, star: StarRow | None = None) -> WorldPhysics:
    if world is None:
        return WorldPhysics()
    type_capacity = mechanics_of(world.world_type).capacity_pct
    capacity = capacity_pct(rules, world.atmosphere) / PERCENT * (type_capacity(rules) / PERCENT if type_capacity is not None else 1.0)
    capacity *= star_capacity_pct(rules, star) / PERCENT
    return WorldPhysics(world.time_factor or 1.0, capacity, gravity_war(rules, world.gravity), world.world_type)


class PhysicsTable:
    def __init__(self, worlds: dict[int, WorldRow], rules: Rules, stars: dict[int, StarRow] | None = None) -> None:
        found = stars or {}
        self._physics = {
            world_id: world_physics(rules, world, found.get(world.star_id) if world.star_id is not None else None) for world_id, world in worlds.items()
        }

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "PhysicsTable":
        worlds = {world.id: world for world in await session.scalars(select(WorldRow))}
        stars = {star.id: star for star in await session.scalars(select(StarRow))}
        return cls(worlds, rules, stars)

    def of(self, world_id: int | None) -> WorldPhysics:
        if world_id is None:
            return WorldPhysics()
        return self._physics.get(world_id, WorldPhysics())
