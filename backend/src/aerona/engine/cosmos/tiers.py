from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import unlocked
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import CivilizationTierLockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import TributeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import CivilizationTier, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.war import TributeStatus
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import BondIndex, canon, flags_by_entity
from aerona.engine.primitives.stats import headcount
from aerona.rules.registry import Rules

T = CivilizationTier
POLITICAL_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})


def tier_of(entity: EntityRow) -> int:
    return entity.civ_tier if entity.civ_tier is not None else T.TRIBE


def may(rules: Rules, entity: EntityRow, capability: TierCapability) -> bool:
    return entity.entity_type is EntityType.MORTAL or unlocked(rules, tier_of(entity), capability)


@dataclass
class TierScene:
    rules: Rules
    atlas: RegionAtlas
    rules_index: BondIndex
    knows_index: BondIndex
    knowledge_ids: set[int]
    tributes: dict[int, list[int]]
    entities: dict[int, EntityRow]
    deposit_owners: set[int]
    monopolies: set[int]
    holders: dict[int, int] = field(default_factory=dict)
    world_population: dict[int, int] = field(default_factory=dict)
    world_regions: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "TierScene":
        entities = {entity.id: entity for entity in await canon(session, None)}
        tribute_rows = await session.scalars(select(TributeRow).where(TributeRow.status == TributeStatus.ACTIVE))
        tributes: dict[int, list[int]] = defaultdict(list)
        for row in tribute_rows:
            tributes[row.receiver_entity_id].append(row.payer_entity_id)
        owns = await BondIndex.load(session, [BondKind.OWNS])
        deposits = {entity.id for entity in entities.values() if entity.engine_kind is EngineKind.COSMIC_TRAVEL_RESOURCE}
        scene = cls(
            rules=rules,
            atlas=await RegionAtlas.load(session),
            rules_index=await BondIndex.load(session, [BondKind.RULES]),
            knows_index=await BondIndex.load(session, [BondKind.KNOWS]),
            knowledge_ids={entity.id for entity in entities.values() if entity.entity_type is EntityType.KNOWLEDGE},
            tributes=tributes,
            entities=entities,
            deposit_owners={bond.source_node_id for bond in owns.bonds if bond.target_node_id in deposits},
            monopolies=await flags_by_entity(session, EntityFlag.COSMIC_MONOPOLY),
        )
        scene.build_political_map()
        return scene

    def governed(self, entity: EntityRow) -> list[EntityRow]:
        found = (self.entities.get(bond.target_node_id) for bond in self.rules_index.outgoing(entity.id, BondKind.RULES))
        return [item for item in found if item is not None]

    def subjects(self, entity: EntityRow) -> set[int]:
        ids = {entity.id, *(item.id for item in self.governed(entity)), *self.tributes.get(entity.id, [])}
        return {item for item in ids if item in self.entities and self.entities[item].world_id == entity.world_id}

    def known_count(self, entity: EntityRow) -> int:
        return sum(1 for bond in self.knows_index.outgoing(entity.id, BondKind.KNOWS) if bond.target_node_id in self.knowledge_ids)

    def build_political_map(self) -> None:
        best: dict[int, tuple[int, int]] = {}
        for entity in self.entities.values():
            if entity.entity_type is EntityType.REGION and entity.location_id is None:
                self.world_regions[entity.world_id] = self.world_regions.get(entity.world_id, 0) + 1
            if entity.entity_type not in POLITICAL_TYPES:
                continue
            if entity.entity_type in (EntityType.PEOPLE, EntityType.SETTLEMENT):
                self.world_population[entity.world_id] = self.world_population.get(entity.world_id, 0) + headcount(entity)
            region = self.atlas.top_region(entity.id)
            if region is None:
                continue
            ruler = next(
                (bond.source_node_id for bond in self.rules_index.incoming(entity.id, BondKind.RULES) if bond.source_node_id in self.entities), entity.id
            )
            weight = headcount(entity)
            if region not in best or weight > best[region][0]:
                best[region] = (weight, ruler)
        self.holders = {region: holder for region, (_weight, holder) in best.items()}

    def subject_population(self, entity: EntityRow) -> int:
        return sum(
            headcount(self.entities[item]) for item in self.subjects(entity) if self.entities[item].entity_type in (EntityType.PEOPLE, EntityType.SETTLEMENT)
        )

    def strongest(self, world_id: int, candidates: list[EntityRow]) -> int:
        return max((self.subject_population(item) for item in candidates if item.world_id == world_id), default=0)


def stay_factor(rules: Rules) -> float:
    return (PERCENT - rules.civilization.stage_demotion_pct) / PERCENT


def base_tier(scene: TierScene, entity: EntityRow) -> tuple[int, set[int]]:
    civ = scene.rules.civilization
    old = tier_of(entity)
    governed = scene.governed(entity)
    worlds = {entity.world_id, *(item.world_id for item in governed)}
    population = headcount(entity) + sum(headcount(item) for item in governed)
    known = scene.known_count(entity)
    stay = stay_factor(scene.rules)

    def threshold(value: int, tier: int) -> float:
        return value * (stay if old >= tier else 1)

    tier = T.TRIBE
    if population >= threshold(civ.city_state_population, T.CITY_STATE) and known >= civ.city_state_knowledge:
        tier = T.CITY_STATE
        if (len(governed) >= civ.kingdom_ruled_places or population >= threshold(civ.kingdom_population, T.KINGDOM)) and known >= civ.kingdom_knowledge:
            tier = T.KINGDOM
    return tier, worlds


def is_empire(scene: TierScene, entity: EntityRow, candidates: list[EntityRow], stay: float) -> bool:
    civ = scene.rules.civilization
    if scene.world_regions.get(entity.world_id, 0) < civ.empire_min_world_regions:
        return False
    settled = [
        region for region, _holder in scene.holders.items() if scene.entities.get(region) is not None and scene.entities[region].world_id == entity.world_id
    ]
    if not settled:
        return False
    subjects = scene.subjects(entity)
    ruled = sum(1 for region in settled if scene.holders[region] in subjects)
    if ruled / len(settled) >= civ.empire_region_pct / PERCENT * stay:
        return True
    world_population = scene.world_population.get(entity.world_id, 0)
    own = scene.subject_population(entity)
    return world_population > 0 and own / world_population >= civ.empire_population_pct / PERCENT * stay


def compute_tier(scene: TierScene, entity: EntityRow, candidates: list[EntityRow]) -> int:
    civ = scene.rules.civilization
    tier, worlds = base_tier(scene, entity)
    old = tier_of(entity)
    if tier >= T.KINGDOM and is_empire(scene, entity, candidates, stay_factor(scene.rules) if old >= T.WORLD_EMPIRE else 1.0):
        tier = T.WORLD_EMPIRE
    if tier >= T.WORLD_EMPIRE and len(worlds) >= civ.interstellar_worlds:
        tier = T.INTERSTELLAR_POWER
    cosmic_hold = entity.id in scene.deposit_owners or entity.id in scene.monopolies
    if tier >= T.INTERSTELLAR_POWER and len(worlds) >= civ.cosmic_worlds and cosmic_hold:
        tier = T.COSMIC_POWER
    return tier


def stepped(old: int, target: int) -> int:
    if target <= old or target < T.WORLD_EMPIRE:
        return target
    return min(target, old + 1 if old >= T.KINGDOM else T.KINGDOM)


def planned_tiers(scene: TierScene, candidates: list[EntityRow]) -> tuple[dict[int, int], set[int]]:
    targets = {entity.id: stepped(tier_of(entity), compute_tier(scene, entity, candidates)) for entity in candidates}
    emperors: dict[int, EntityRow] = {}
    for entity in candidates:
        if targets[entity.id] < T.WORLD_EMPIRE:
            continue
        current = emperors.get(entity.world_id)
        rank = (scene.subject_population(entity), 1 if tier_of(entity) >= T.WORLD_EMPIRE else 0, -entity.id)
        if current is None or rank > (scene.subject_population(current), 1 if tier_of(current) >= T.WORLD_EMPIRE else 0, -current.id):
            emperors[entity.world_id] = entity
    forced: set[int] = set()
    for entity in candidates:
        if targets[entity.id] >= T.WORLD_EMPIRE and emperors[entity.world_id].id != entity.id:
            targets[entity.id] = T.KINGDOM
            if tier_of(entity) >= T.WORLD_EMPIRE:
                forced.add(entity.id)
    return targets, forced


async def tier_lock(session: AsyncSession, entity_id: int) -> int | None:
    row = await session.get(CivilizationTierLockRow, entity_id)
    return row.tier if row is not None else None
