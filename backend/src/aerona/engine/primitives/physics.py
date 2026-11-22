from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.primitives import AIR_ATTRITION_PCT_ATMOSPHERES
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.domain.enums.world import Atmosphere, Gravity, WorldType
from aerona.engine.cosmos.placement import CosmicPull, Cosmography, cosmography_of
from aerona.engine.cosmos.star_types import star_capacity_pct
from aerona.engine.cosmos.world_views import WorldView, default_view, world_views
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


def world_physics(
    rules: Rules, world: WorldRow | None, star: StarRow | None = None, pull: CosmicPull | None = None, view: WorldView | None = None
) -> WorldPhysics:
    if world is None:
        return WorldPhysics()
    heavens = pull or CosmicPull()
    shown = view or default_view(rules, world.world_type)
    capacity = capacity_pct(rules, world.atmosphere) / PERCENT * shown.capacity_pct / PERCENT
    capacity *= star_capacity_pct(rules, star) / PERCENT
    capacity *= heavens.capacity
    return WorldPhysics((world.time_factor or 1.0) * heavens.time, capacity, gravity_war(rules, world.gravity), world.world_type)


class PhysicsTable:
    def __init__(
        self,
        worlds: dict[int, WorldRow],
        rules: Rules,
        stars: dict[int, StarRow] | None = None,
        cosmography: Cosmography | None = None,
        views: dict[int, WorldView] | None = None,
    ) -> None:
        found = stars or {}
        shown = views or {}
        self._physics = {
            world_id: world_physics(
                rules,
                world,
                found.get(world.star_id) if world.star_id is not None else None,
                cosmography.pull(rules, cosmography.place_world(world)) if cosmography is not None else None,
                shown.get(world_id),
            )
            for world_id, world in worlds.items()
        }

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "PhysicsTable":
        cosmography = await cosmography_of(session)
        return cls(dict(cosmography.worlds), rules, dict(cosmography.stars), cosmography, await world_views(session, rules))

    def of(self, world_id: int | None) -> WorldPhysics:
        if world_id is None:
            return WorldPhysics()
        return self._physics.get(world_id, WorldPhysics())


def gravity_speed_pct(rules: Rules, world: WorldRow | None) -> int:
    table = rules.world_life
    if world is None:
        return PERCENT
    return {Gravity.LOW: PERCENT + table.low_gravity_speed_pct, Gravity.NORMAL: PERCENT, Gravity.HIGH: PERCENT - table.high_gravity_speed_pct}[world.gravity]


def gravity_build_pct(rules: Rules, world: WorldRow | None) -> int:
    return PERCENT + rules.world_life.high_gravity_build_pct if world is not None and world.gravity is Gravity.HIGH else PERCENT


def flight_capacity_pct(rules: Rules, world: WorldRow | None) -> int:
    return PERCENT + rules.world_life.low_gravity_flight_pct if world is not None and world.gravity is Gravity.LOW else PERCENT


def air_attrition_pct(rules: Rules, world: WorldRow | None) -> int:
    thin = world is not None and world.atmosphere in AIR_ATTRITION_PCT_ATMOSPHERES
    return PERCENT + rules.world_life.thin_air_attrition_pct if thin else PERCENT
