import math
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import MAP_NOTE_COLOR_MAX_LENGTH, MAP_NOTE_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.meta import MapNoteRow, MapSnapshotRow
from aerona.db.tables.region import RegionDangerRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import LIVING_STATUSES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.war import WarStatus
from aerona.domain.models.records import GroundSnapshot, MapSnapshotData, RegionControl
from aerona.engine.environment.ley import LeyWeb
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

POLITICAL_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.CULT})
ROAD_STOP_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})
POPULATED_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
BATTLE_KINDS = frozenset({EngineKind.WAR, EngineKind.BATTLE, EngineKind.SIEGE})
DEFAULT_NOTE_COLOR = "gold"
PERCENT = 100
SIMILAR_CANDIDATES = 200
SIMILAR_MIN_SCORE = 2.0
SHARED_WEIGHT = 3.0
SAME_TYPE_WEIGHT = 2.0
SAME_CREATOR_WEIGHT = 1.5
SAME_REGION_WEIGHT = 1.5
DIRECT_WEIGHT = 1.0
SCORE_DECIMALS = 1


class RoadKind(StrEnum):
    ROAD = "road"
    TRADE = "trade"


class SettlementTier(StrEnum):
    CAPITAL = "capital"
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    GREAT_CITY = "great_city"


class MarkerKind(StrEnum):
    BATTLE = "battle"
    DISASTER = "disaster"
    RUIN = "ruin"
    REMNANT = "remnant"
    EVENT = "event"


@dataclass(frozen=True)
class Road:
    first: int
    second: int
    kind: RoadKind
    length: float


@dataclass(frozen=True)
class SettlementInfo:
    tier: SettlementTier
    population: int
    previous_population: int | None


@dataclass(frozen=True)
class EventMarker:
    id: int
    name: str
    entity_type: EntityType
    subtype: str | None
    location_id: int
    epoch: int
    kind: MarkerKind


@dataclass(frozen=True)
class SimilarEntity:
    entity: EntityRow
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class RegionDominance:
    son_id: int | None
    language_id: int | None


@dataclass(frozen=True)
class HistoricalView:
    epoch: int
    entities: list[EntityRow]
    population: dict[int, int]
    political: dict[int, RegionControl]
    snapshot_epochs: list[int]
    ground: dict[int, GroundSnapshot]


async def _canon(session: AsyncSession, world_id: int | None = None) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.status == EntityStatus.CANON)
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def _rulers(session: AsyncSession) -> dict[int, int]:
    statement = select(BondRow.target_node_id, BondRow.source_node_id).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE)
    return {target: source for target, source in (await session.execute(statement.order_by(BondRow.id)))}


def share_of(rules: Rules, entity: EntityRow) -> float:
    politics = rules.politics
    if entity.entity_type is EntityType.FACTION:
        strength = stat(entity, "strength")
        sway = stat(entity, "sway")
        return float((strength if strength is not None else politics.faction_default) * politics.faction_strength_weight) + float(
            (sway if sway is not None else politics.faction_default) * politics.faction_sway_weight
        )
    if entity.entity_type is EntityType.CULT:
        return float((stat(entity, "followers") or 0) * politics.cult_follower_share_pct / PERCENT)
    return float(stat(entity, "population") or 0)


async def political_map(session: AsyncSession, rules: Rules, world_id: int | None = None) -> dict[int, RegionControl]:
    entities = await _canon(session, world_id)
    by_id = {entity.id: entity for entity in entities}
    rulers = await _rulers(session)
    atlas = await RegionAtlas.load(session)
    power: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for entity in entities:
        if entity.entity_type not in POLITICAL_TYPES:
            continue
        region = atlas.top_region(entity.id)
        if region is None:
            continue
        holder = entity
        current = entity.id
        for _ in range(rules.politics.rule_chain_depth):
            ruler_id = rulers.get(current)
            ruler = by_id.get(ruler_id) if ruler_id is not None else None
            if ruler is None:
                break
            if ruler.entity_type in POLITICAL_TYPES:
                holder = ruler
            current = ruler.id
        power[region][holder.id] += share_of(rules, entity)
    result: dict[int, RegionControl] = {}
    for region, holders in power.items():
        total = sum(holders.values())
        if total <= 0:
            continue
        top_id, top_value = max(holders.items(), key=lambda item: (item[1], -item[0]))
        top = by_id[top_id]
        result[region] = RegionControl(
            ruler_id=top_id, ruler_name=top.name, ruler_type=top.entity_type, share=round(top_value / total * PERCENT), contested=len(holders) > 1
        )
    return result


async def road_network(session: AsyncSession, world_id: int) -> list[Road]:
    atlas = await RegionAtlas.load(session)
    stops = [
        entity
        for entity in await session.scalars(
            select(EntityRow).where(
                EntityRow.world_id == world_id,
                EntityRow.entity_type.in_(list(ROAD_STOP_TYPES)),
                EntityRow.status != EntityStatus.REJECTED,
                EntityRow.map_x.is_not(None),
                EntityRow.map_y.is_not(None),
            )
        )
    ]
    regions = {stop.id: atlas.top_region(stop.id) for stop in stops}

    def neighbours(first: EntityRow, second: EntityRow) -> bool:
        a, b = regions[first.id], regions[second.id]
        return a is not None and b is not None and (a == b or b in atlas.neighbour_regions(a))

    def distance(first: EntityRow, second: EntityRow) -> float:
        return math.dist((first.map_x or 0.0, first.map_y or 0.0), (second.map_x or 0.0, second.map_y or 0.0))

    trade = {
        frozenset((source, target))
        for source, target in await session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE)
        )
    }
    roads: list[Road] = []
    remaining = {stop.id: stop for stop in stops}
    while remaining:
        start = remaining.pop(min(remaining))
        tree = [start]
        while True:
            candidates = [(distance(inside, outside), inside, outside) for inside in tree for outside in remaining.values() if neighbours(inside, outside)]
            if not candidates:
                break
            length, inside, outside = min(candidates, key=lambda item: (item[0], item[2].id))
            remaining.pop(outside.id)
            tree.append(outside)
            kind = RoadKind.TRADE if frozenset((inside.id, outside.id)) in trade else RoadKind.ROAD
            roads.append(Road(inside.id, outside.id, kind, round(length, 2)))
    return roads


WILD = "wild"


def main_use(ground: RegionEnvironmentRow) -> str:
    uses = {use.value: getattr(ground, use.value) for use in LandUse}
    best = max(sorted(uses), key=lambda key: uses[key])
    return best if uses[best] > 0 else WILD


async def ground_snapshot(session: AsyncSession, world_id: int) -> dict[int, GroundSnapshot]:
    degree = (await LeyWeb.load(session)).degree()
    nexus = set(
        await session.scalars(
            select(PlaceEnvironmentRow.region_entity_id).where(PlaceEnvironmentRow.nexus.is_(True), PlaceEnvironmentRow.region_entity_id.is_not(None))
        )
    )
    rows = list(await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world_id)))
    dangers: dict[int, list[RegionDangerRow]] = defaultdict(list)
    for danger in await session.scalars(select(RegionDangerRow).where(RegionDangerRow.world_id == world_id).order_by(RegionDangerRow.id)):
        dangers[danger.region_entity_id].append(danger)
    danger_stat = {
        row.id: round(stat(row, "danger") or 0) for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_([row.entity_id for row in rows])))
    }
    found: dict[int, GroundSnapshot] = {}
    for row in rows:
        top = max(dangers.get(row.entity_id, []), key=lambda item: (item.strength, -item.id), default=None)
        scar = max(sorted(row.scars), key=lambda key: row.scars[key], default=None)
        found[row.entity_id] = GroundSnapshot(
            terrain=row.dominant_terrain,
            soil=row.soil,
            climate=row.temperature_band,
            land_use=main_use(row),
            ley_lines=degree[row.entity_id],
            nexus=row.entity_id in nexus,
            rainfall=row.rainfall,
            danger=danger_stat.get(row.entity_id, 0),
            danger_source=top.source if top is not None and top.strength > 0 else None,
            sacredness=row.sacredness,
            scar=scar,
            scar_depth=row.scars.get(scar, 0) if scar is not None else 0,
        )
    return found


async def take_snapshot(session: AsyncSession, rules: Rules, epoch: int) -> int:
    worlds = list(await session.scalars(select(WorldRow.id)))
    living = list(await session.scalars(select(EntityRow).where(EntityRow.status.in_([EntityStatus.CANON, EntityStatus.FULFILLED]))))
    wars = list(await session.scalars(select(WarRow).where(WarRow.status == WarStatus.ONGOING)))
    for world_id in worlds:
        in_world = [entity for entity in living if entity.world_id == world_id]
        data = MapSnapshotData(
            living_ids=tuple(entity.id for entity in in_world),
            population={
                entity.id: round(stat(entity, "population") or 0)
                for entity in in_world
                if entity.entity_type in POPULATED_TYPES and entity.status is EntityStatus.CANON
            },
            political=await political_map(session, rules, world_id),
            ongoing_war_ids=tuple(war.event_entity_id for war in wars if war.world_id == world_id),
            ground=await ground_snapshot(session, world_id),
        )
        row = await session.get(MapSnapshotRow, (epoch, world_id))
        if row is None:
            session.add(MapSnapshotRow(epoch=epoch, world_id=world_id, data=data))
        else:
            row.data = data
    await session.flush()
    return len(worlds)


async def snapshot(session: AsyncSession, epoch: int, world_id: int) -> MapSnapshotData | None:
    row = await session.get(MapSnapshotRow, (epoch, world_id))
    return row.data if row is not None else None


async def snapshot_epochs(session: AsyncSession, world_id: int) -> list[int]:
    return list(await session.scalars(select(MapSnapshotRow.epoch).where(MapSnapshotRow.world_id == world_id).order_by(MapSnapshotRow.epoch)))


async def historical_view(session: AsyncSession, world_id: int, epoch: int) -> HistoricalView | None:
    data = await snapshot(session, epoch, world_id)
    if data is None:
        return None
    alive = set(data.living_ids)
    entities = [
        entity
        for entity in await session.scalars(
            select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id)
        )
        if entity.birth_epoch <= epoch and (entity.entity_type is EntityType.REGION or entity.id in alive)
    ]
    return HistoricalView(epoch, entities, dict(data.population), dict(data.political), await snapshot_epochs(session, world_id), dict(data.ground))


async def map_notes(session: AsyncSession, world_id: int | None = None) -> list[MapNoteRow]:
    statement = select(MapNoteRow)
    if world_id is not None:
        statement = statement.where(MapNoteRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(MapNoteRow.id)))


async def add_map_note(session: AsyncSession, *, x: float, y: float, text: str, color: str | None, world_id: int | None) -> MapNoteRow:
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValidationFailedError("Invalid position.")
    cleaned = text.strip()[:MAP_NOTE_MAX_LENGTH]
    if not cleaned:
        raise ValidationFailedError("A note needs a text.")
    target = world_id if world_id is not None and await session.get(WorldRow, world_id) is not None else await CosmosRepository(session).first_world_id()
    if target is None:
        raise ValidationFailedError("Create the world first.")
    note = MapNoteRow(world_id=target, x=round(x), y=round(y), text=cleaned, color=(color or DEFAULT_NOTE_COLOR)[:MAP_NOTE_COLOR_MAX_LENGTH])
    session.add(note)
    await session.flush()
    return note


async def delete_map_note(session: AsyncSession, note_id: int) -> None:
    result = await session.execute(delete(MapNoteRow).where(MapNoteRow.id == note_id))
    if not getattr(result, "rowcount", 0):
        raise NotFoundError("No such map note.")


async def _bond_keys(session: AsyncSession, node_id: int) -> set[int]:
    rows = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id), BondRow.state == BondState.ACTIVE
        )
    )
    return {target if source == node_id else source for source, target in rows}


async def similar_entities(session: AsyncSession, entity_id: int, count: int) -> list[SimilarEntity]:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError("No such record.")
    mine = await _bond_keys(session, entity_id)
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(entity_id)
    conditions = [EntityRow.entity_type == entity.entity_type]
    if entity.creator_son_id is not None:
        conditions.append(EntityRow.creator_son_id == entity.creator_son_id)
    if entity.location_id is not None:
        conditions.append(EntityRow.location_id == entity.location_id)
    statement = select(EntityRow).where(or_(*conditions), EntityRow.status.in_(list(LIVING_STATUSES))).order_by(EntityRow.id.desc()).limit(SIMILAR_CANDIDATES)
    candidates = {row.id: row for row in await session.scalars(statement)}
    for neighbour in await session.scalars(select(EntityRow).where(EntityRow.id.in_(mine), EntityRow.status.in_(list(LIVING_STATUSES)))):
        candidates[neighbour.id] = neighbour
    candidates.pop(entity_id, None)
    scored: list[SimilarEntity] = []
    for candidate in candidates.values():
        shared = len(mine & await _bond_keys(session, candidate.id))
        reasons: list[str] = []
        score = SHARED_WEIGHT * shared
        if shared:
            reasons.append(several(shared, "shared bond", "shared bonds"))
        if candidate.entity_type is entity.entity_type:
            score += SAME_TYPE_WEIGHT
            reasons.append("same type")
        if entity.creator_son_id is not None and candidate.creator_son_id == entity.creator_son_id:
            score += SAME_CREATOR_WEIGHT
            reasons.append("same creator")
        if region is not None and atlas.top_region(candidate.id) == region:
            score += SAME_REGION_WEIGHT
            reasons.append("same region")
        if candidate.id in mine:
            score += DIRECT_WEIGHT
        if score >= SIMILAR_MIN_SCORE:
            scored.append(SimilarEntity(candidate, round(score, SCORE_DECIMALS), reasons))
    return sorted(scored, key=lambda item: (-item.score, item.entity.id))[:count]


async def favorites(session: AsyncSession) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.favorite.is_(True), EntityRow.status != EntityStatus.DESTROYED).order_by(EntityRow.name)
    return list(await session.scalars(statement))


async def set_favorite(session: AsyncSession, entity_id: int, favorite: bool) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError("No such record.")
    entity.favorite = favorite
    await session.flush()
    return entity


def settlement_tier(rules: Rules, population: int) -> SettlementTier:
    politics = rules.politics
    if population >= politics.metropolis_population:
        return SettlementTier.GREAT_CITY
    if population >= politics.city_population:
        return SettlementTier.CITY
    if population >= politics.town_population:
        return SettlementTier.TOWN
    return SettlementTier.VILLAGE


def capital_rank(settlement: EntityRow, designated: set[int]) -> tuple[bool, int]:
    return settlement.id in designated, stat(settlement, "population") or 0


async def designate_capital(session: AsyncSession, settlement: EntityRow, epoch: int) -> EntityRow:
    if settlement.entity_type is not EntityType.SETTLEMENT:
        raise ValidationFailedError("Only a settlement can be a capital.")
    rulers = await _rulers(session)
    ruler = rulers.get(settlement.id)
    if ruler is None:
        raise ValidationFailedError(f"{settlement.name} is ruled by no one; there is no realm to seat.")
    ruled = [target for target, source in rulers.items() if source == ruler]
    await session.execute(delete(EntityFlagRow).where(EntityFlagRow.flag == EntityFlag.CAPITAL, EntityFlagRow.entity_id.in_(ruled)))
    session.add(EntityFlagRow(entity_id=settlement.id, flag=EntityFlag.CAPITAL, epoch=epoch))
    await session.flush()
    ruler_row = await session.get(EntityRow, ruler)
    if ruler_row is None:
        raise NotFoundError("No such ruler.")
    return ruler_row


async def settlement_tiers(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> dict[int, SettlementInfo]:
    settlements = [entity for entity in await _canon(session, world_id) if entity.entity_type is EntityType.SETTLEMENT]
    rulers = await _rulers(session)
    designated = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.CAPITAL)))
    capitals: dict[int, EntityRow] = {}
    for settlement in settlements:
        ruler = rulers.get(settlement.id)
        if ruler is None:
            continue
        best = capitals.get(ruler)
        if best is None or capital_rank(settlement, designated) > capital_rank(best, designated):
            capitals[ruler] = settlement
    capital_ids = {settlement.id for settlement in capitals.values()}
    previous = await snapshot(session, epoch - 1, world_id)
    result: dict[int, SettlementInfo] = {}
    for settlement in settlements:
        population = max(0, stat(settlement, "population") or 0)
        tier = SettlementTier.CAPITAL if settlement.id in capital_ids else settlement_tier(rules, population)
        before = previous.population.get(settlement.id) if previous is not None else None
        result[settlement.id] = SettlementInfo(tier, population, before)
    return result


async def event_markers(session: AsyncSession, world_id: int) -> list[EventMarker]:
    flagged = select(EntityFlagRow.entity_id, EntityFlagRow.flag).where(EntityFlagRow.flag.in_([EntityFlag.DISASTER, EntityFlag.RUIN, EntityFlag.REMNANT]))
    flags: dict[int, set[EntityFlag]] = defaultdict(set)
    for entity_id, flag in await session.execute(flagged):
        flags[entity_id].add(flag)
    statement = select(EntityRow).where(
        EntityRow.world_id == world_id,
        EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD]),
        EntityRow.location_id.is_not(None),
        or_(EntityRow.entity_type == EntityType.EVENT, EntityRow.id.in_(list(flags))),
    )
    markers: list[EventMarker] = []
    for entity in await session.scalars(statement.order_by(EntityRow.id)):
        own = flags.get(entity.id, set())
        if entity.engine_kind in BATTLE_KINDS:
            kind = MarkerKind.BATTLE
        elif EntityFlag.DISASTER in own:
            kind = MarkerKind.DISASTER
        elif EntityFlag.RUIN in own:
            kind = MarkerKind.RUIN
        elif EntityFlag.REMNANT in own:
            kind = MarkerKind.REMNANT
        else:
            kind = MarkerKind.EVENT
        if entity.location_id is not None:
            markers.append(EventMarker(entity.id, entity.name, entity.entity_type, entity.subtype, entity.location_id, entity.birth_epoch, kind))
    return markers


async def region_dominance(session: AsyncSession, world_id: int) -> dict[int, RegionDominance]:
    atlas = await RegionAtlas.load(session)
    communities = [entity for entity in await _canon(session, world_id) if entity.entity_type in POPULATED_TYPES]
    ids = [entity.id for entity in communities]
    worship = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(ids)
        )
    )
    speaks = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(ids)
        )
    )
    worshipped = {source: target for source, target in worship}
    spoken = {source: target for source, target in speaks}
    kinds = await NodeRepository(session).kinds_of(list(set(worshipped.values())))
    son_weight: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    language_weight: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for community in communities:
        region = atlas.top_region(community.id)
        if region is None:
            continue
        weight = math.log10((stat(community, "population") or 0) + 1)
        god = worshipped.get(community.id)
        if god is not None and kinds.get(god) is NodeKind.SON:
            son_weight[region][god] += weight
        language = spoken.get(community.id)
        if language is not None:
            language_weight[region][language] += weight
    regions = set(son_weight) | set(language_weight)
    return {
        region: RegionDominance(
            son_id=max(son_weight[region].items(), key=lambda item: item[1])[0] if son_weight.get(region) else None,
            language_id=max(language_weight[region].items(), key=lambda item: item[1])[0] if language_weight.get(region) else None,
        )
        for region in regions
    }
