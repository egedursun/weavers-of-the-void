import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import WaterSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules

GROWING_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT})
LAND_COMMUNITY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})

RegionKey = tuple[str, int]
FRESH_WATERS = frozenset({WaterSource.RIVER, WaterSource.LAKE, WaterSource.SPRING})


@dataclass
class RegionLoad:
    key: RegionKey
    region: EntityRow | None
    population: float = 0.0
    followers: float = 0.0
    agriculture: float = 0.0
    communities: list[EntityRow] = field(default_factory=list)
    cults: list[EntityRow] = field(default_factory=list)


@dataclass(frozen=True)
class CapacityReading:
    capacity: int
    region_population: int
    occupancy_pct: int
    region_id: int | None
    region_name: str | None
    sharing: int


class CapacityModel:
    def __init__(
        self,
        rules: Rules,
        atlas: RegionAtlas,
        knowledge: KnowledgeMap,
        physics: PhysicsTable,
        entities: dict[int, EntityRow],
        *,
        water: dict[int, WaterSource] | None = None,
    ) -> None:
        self.rules = rules
        self.atlas = atlas
        self.knowledge = knowledge
        self.physics = physics
        self.entities = entities
        self.water = water or {}

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "CapacityModel":
        atlas = await RegionAtlas.load(session)
        knowledge = await KnowledgeMap.load(session)
        physics = await PhysicsTable.load(session, rules)
        places = await canon(session, [EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT])
        water = {entity_id: source for entity_id, source in await session.execute(select(PlaceEnvironmentRow.entity_id, PlaceEnvironmentRow.water_source))}
        return cls(rules, atlas, knowledge, physics, {entity.id: entity for entity in places}, water=water)

    def water_factor(self, community: EntityRow) -> float:
        source = self.water.get(community.location_id or -1)
        if source is None:
            return 1.0
        settings = self.rules.environment
        if source is WaterSource.NONE:
            return settings.dry_place_capacity_pct / PERCENT
        if source in FRESH_WATERS:
            return settings.fresh_water_capacity_pct / PERCENT
        return 1.0

    def region_key(self, entity: EntityRow) -> RegionKey:
        region = self.atlas.top_region(entity.id)
        return ("region", region) if region is not None else ("world", entity.world_id)

    def effective_fertility(self, entity: EntityRow) -> int:
        unknown = self.rules.world_effects.unknown_fertility
        region = self.entities.get(self.atlas.top_region(entity.id) or -1)
        region_fertility = stat(region, "fertility") if region is not None else None
        place = self.entities.get(entity.location_id or -1)
        place_fertility = stat(place, "fertility") if place is not None else None
        if place is None or place.entity_type is EntityType.REGION or region_fertility is None:
            if place_fertility is not None:
                return place_fertility
            return region_fertility if region_fertility is not None else unknown
        share = self.rules.world_epoch_transition.place_fertility_share_pct
        own = place_fertility if place_fertility is not None else unknown
        return round_half_up(own * share / PERCENT + region_fertility * (PERCENT - share) / PERCENT)

    def build_loads(self, communities: Iterable[EntityRow]) -> dict[RegionKey, RegionLoad]:
        loads: dict[RegionKey, RegionLoad] = {}
        for community in communities:
            key = self.region_key(community)
            load = loads.get(key)
            if load is None:
                load = RegionLoad(key=key, region=self.entities.get(key[1]) if key[0] == "region" else None)
                loads[key] = load
            if community.entity_type is EntityType.CULT:
                load.followers += stat_or(community, "followers", 0)
                load.cults.append(community)
                continue
            population = stat_or(community, "population", 0)
            load.population += population
            load.communities.append(community)
            if self.knowledge.knows(community.id, KnowledgeBranch.AGRICULTURE):
                load.agriculture += population
        return loads

    def capacity(self, load: RegionLoad, community: EntityRow, fertility: float) -> float:
        rules = self.rules
        transition = rules.world_epoch_transition
        engine = rules.world_engine
        breadth = stat(load.region, "breadth") if load.region is not None else None
        breadth_value = breadth if breadth is not None else rules.world_effects.unknown_breadth
        farming_share = load.agriculture / load.population if load.population else 0.0
        builder = community.entity_type is EntityType.SETTLEMENT and self.knowledge.knows(community.id, KnowledgeBranch.ARCHITECTURE)
        architecture = transition.capacity_architecture_pct / PERCENT if builder else 1.0
        crowding = min(engine.capacity_crowded_cap_pct / PERCENT, max(1.0, math.sqrt(len(load.communities))))
        return (
            self.physics.of(community.world_id).capacity
            * engine.carrying_capacity
            * (transition.capacity_fertility_base_pct / PERCENT + fertility / transition.capacity_fertility_divisor)
            * (transition.capacity_breadth_base_pct / PERCENT + breadth_value / PERCENT)
            * (1 + engine.capacity_agriculture_pct / PERCENT * farming_share)
            * architecture
            * crowding
            * self.water_factor(community)
        )


async def carrying_capacity(session: AsyncSession, rules: Rules, entity: EntityRow) -> CapacityReading | None:
    if entity.entity_type not in LAND_COMMUNITY_TYPES:
        return None
    model = await CapacityModel.load(session, rules)
    communities = await canon(session, LAND_COMMUNITY_TYPES)
    loads = model.build_loads(communities)
    key = model.region_key(entity)
    load = loads.get(key) or model.build_loads([entity])[key]
    capacity = model.capacity(load, entity, model.effective_fertility(entity))
    population = round_half_up(load.population)
    return CapacityReading(
        capacity=round_half_up(capacity),
        region_population=population,
        occupancy_pct=round_half_up(population / max(1.0, capacity) * PERCENT),
        region_id=load.region.id if load.region is not None else None,
        region_name=load.region.name if load.region is not None else None,
        sharing=len(load.communities),
    )
