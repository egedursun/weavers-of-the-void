from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gravity import GRAVITY
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
        Atmosphere.STEAM: physics.capacity_steam,
        Atmosphere.LAYERED: physics.capacity_layered,
    }[atmosphere]


def gravity_war(rules: Rules, gravity: Gravity) -> int:
    return GRAVITY[gravity].martial(rules)


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
    return GRAVITY[world.gravity].speed(rules) if world is not None else PERCENT


def gravity_build_pct(rules: Rules, world: WorldRow | None) -> int:
    return GRAVITY[world.gravity].build(rules) if world is not None else PERCENT


def flight_capacity_pct(rules: Rules, world: WorldRow | None) -> int:
    return GRAVITY[world.gravity].flight(rules) if world is not None else PERCENT


def body_strain(rules: Rules, world: WorldRow | None) -> int:
    return GRAVITY[world.gravity].strain(rules) if world is not None else 0


def launch_delay(world: WorldRow | None) -> int:
    return GRAVITY[world.gravity].launch if world is not None else 0


def air_attrition_pct(rules: Rules, world: WorldRow | None) -> int:
    thin = world is not None and world.atmosphere in AIR_ATTRITION_PCT_ATMOSPHERES
    return PERCENT + rules.world_life.thin_air_attrition_pct if thin else PERCENT
