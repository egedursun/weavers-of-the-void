from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmic_state import WorldLeakItemRow
from aerona.db.tables.cosmography import PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import AddictionRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, PhenomenonKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import DARK_STAR_TYPES, StarType
from aerona.domain.models.records import LedgerItem
from aerona.engine.cosmos.placement import world_pull
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import BondIndex, canon, flags_by_entity
from aerona.engine.primitives.society import class_shares
from aerona.rules.registry import Rules

LEAKING_METHODS = frozenset({TravelMethod.ANCIENT_GATE, TravelMethod.CARRIED_WITHIN, TravelMethod.DREAM_JOURNEY})
LAND_COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
PATRON_KINDS = frozenset({NodeKind.SON, NodeKind.CREATOR})
BREAKDOWN_DECIMALS = 1


@dataclass
class LeakDelta:
    delta: int
    items: dict[str, float] = field(default_factory=dict)
    young: bool = False


@dataclass(frozen=True)
class LeakSources:
    forbidden: int
    gates: int
    dark_star: bool
    star_type: StarType | None
    godless: int
    addicted: int
    outer_cults: int
    outer_beings: int


async def _sources(session: AsyncSession, world: WorldRow, knowledge: KnowledgeMap) -> LeakSources:
    entities = await canon(session, None, world.id)
    ids = {entity.id for entity in entities}
    statement = select(RouteRow.id).where(
        RouteRow.active.is_(True), RouteRow.method.in_(list(LEAKING_METHODS)), or_(RouteRow.world_a_id == world.id, RouteRow.world_b_id == world.id)
    )
    gates = len(list(await session.scalars(statement)))
    star_id = await WorldRepository(session).root_star_id(world)
    star = await session.get(StarRow, star_id) if star_id is not None else None
    addicted = set(await session.scalars(select(AddictionRow.community_entity_id).where(AddictionRow.addicted_since_epoch.is_not(None))))
    return LeakSources(
        forbidden=sum(1 for entity in entities if knowledge.knows(entity.id, KnowledgeBranch.FORBIDDEN)),
        gates=gates,
        dark_star=star is not None and star.star_type in DARK_STAR_TYPES,
        star_type=star.star_type if star is not None else None,
        godless=len(ids & await flags_by_entity(session, EntityFlag.GODLESS)),
        addicted=len(ids & addicted),
        outer_cults=len(ids & await flags_by_entity(session, EntityFlag.OUTER_CULT)),
        outer_beings=sum(1 for entity in entities if entity.entity_type is EntityType.OUTER_BEING),
    )


async def _worship_counts(session: AsyncSession, world_id: int) -> tuple[int, int]:
    communities = await canon(session, COMMUNITY_TYPES, world_id)
    index = await BondIndex.load(session, [BondKind.WORSHIPS])
    nodes = NodeRepository(session)
    worshipping = 0
    for community in communities:
        targets = [bond.target_node_id for bond in index.outgoing(community.id, BondKind.WORSHIPS)]
        kinds = await nodes.kinds_of(targets)
        if any(kind in PATRON_KINDS for kind in kinds.values()):
            worshipping += 1
    return worshipping, len(communities)


async def _priest_communities(session: AsyncSession, rules: Rules, world_id: int) -> int:
    count = 0
    for community in await canon(session, LAND_COMMUNITIES, world_id):
        if (await class_shares(session, rules, community.id))[SocialClass.PRIEST] >= rules.cosmic_horror.priest_min_pct:
            count += 1
    return count


async def _temples(session: AsyncSession, world_id: int) -> int:
    statement = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.engine_kind == EngineKind.TEMPLE, EntityRow.status == EntityStatus.CANON)
    return len(list(await session.scalars(statement)))


async def open_rifts(session: AsyncSession, world_id: int) -> int:
    statement = select(func.count()).select_from(RiftRow).where(RiftRow.world_id == world_id, RiftRow.state.in_(list(OPEN_RIFT_STATES)))
    return int(await session.scalar(statement) or 0)


async def wound_leak(session: AsyncSession, rules: Rules, world_id: int) -> float:
    statement = (
        select(PhenomenonProfileRow.intensity)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, PhenomenonProfileRow.kind == PhenomenonKind.OUTSIDE_OPENING)
    )
    return sum(intensity * rules.phenomena.leak_wound_leak / PERCENT for intensity in await session.scalars(statement))


def young(rules: Rules, world: WorldRow, epoch: int) -> bool:
    return epoch - (world.created_epoch or 1) < rules.deep_world.young_world_epochs


def leak_cap(rules: Rules, world: WorldRow, epoch: int) -> int:
    if not young(rules, world, epoch):
        return 100
    horror = rules.cosmic_horror
    age = epoch - (world.created_epoch or 1)
    return min(PERCENT, max(horror.young_cap, horror.young_cap + horror.young_cap_growth * age))


async def leak_delta(session: AsyncSession, rules: Rules, world: WorldRow, epoch: int, doom_share: float, *, knowledge: KnowledgeMap) -> LeakDelta:
    horror = rules.cosmic_horror
    sources = await _sources(session, world, knowledge)
    view = await view_of(session, rules, world.id)
    star = star_mechanics(sources.star_type) if sources.star_type is not None else None

    def capped(value: float) -> float:
        return min(float(horror.source_cap), value) if horror.source_cap > 0 else value

    increases = {
        "forbidden knowledge": capped(sources.forbidden * horror.forbidden_knowledge_leak),
        "gates": capped(sources.gates * horror.gate_leak),
        "star": (horror.dead_star_leak if sources.dark_star else 0) + (star.leak(rules) if star is not None else 0),
        "godless": capped(sources.godless * horror.godless_leak),
        "addicted": capped(sources.addicted * horror.addicted_leak),
        "outer cults": capped(sources.outer_cults * horror.outer_cult_leak),
        "outer beings": sources.outer_beings * horror.outer_being_leak,
        "doom": doom_share * horror.apocalypse_leak,
        "world nature": view.leak,
        "the heavens": float((await world_pull(session, rules, world)).leak),
        "rifts": capped(await open_rifts(session, world.id) * rules.rifts.world_leak),
        "phenomena": await wound_leak(session, rules, world.id),
    }
    is_young = young(rules, world, epoch)
    factor = horror.young_growth_pct / PERCENT if is_young else 1.0
    scale_m = min(1.0, world.leakage / max(1, horror.repair_full_at))
    worshipping, communities = await _worship_counts(session, world.id)
    worship_repair = (
        min(scaled_cap(horror.worshipper_cap, horror.repair_cap_community_divisor, communities), worshipping * horror.worshipper_repair / PERCENT)
        + (worshipping / communities if communities else 0) * horror.worshipper_ratio_repair
    ) * scale_m
    decreases = {
        "worshippers": worship_repair,
        "temples": min(scaled_cap(horror.temple_cap, horror.repair_cap_community_divisor, communities), await _temples(session, world.id)) * scale_m,
        "priests": min(scaled_cap(horror.priest_cap, horror.repair_cap_community_divisor, communities), await _priest_communities(session, rules, world.id))
        * scale_m,
        "fabric repair": horror.fabric_self_repair + max(0.0, (world.leakage - horror.repair_threshold) / horror.repair_divisor) + view.leak_repair,
        "star's hold": star.leak_repair(rules) if star is not None else 0,
    }
    items = {key: round(value * factor, BREAKDOWN_DECIMALS) for key, value in increases.items() if value}
    items.update({key: -round(value, BREAKDOWN_DECIMALS) for key, value in decreases.items() if value})
    total = round(sum(increases.values()) * factor - sum(decreases.values()))
    return LeakDelta(total, items, is_young)


def apply_leak(world: WorldRow, delta: int, cap: int) -> int:
    raw = max(0, min(PERCENT, world.leakage + delta))
    world.leakage = min(raw, world.leakage) if world.leakage > cap else min(raw, cap)
    return world.leakage


def record_breakdown(session: AsyncSession, epoch: int, world_id: int, change: LeakDelta) -> None:
    session.add_all(WorldLeakItemRow(epoch=epoch, world_id=world_id, item=item, delta=value) for item, value in change.items.items())


async def leak_breakdown(session: AsyncSession, epoch: int) -> dict[int, tuple[LedgerItem, ...]]:
    statement = select(WorldLeakItemRow).where(WorldLeakItemRow.epoch == epoch).order_by(WorldLeakItemRow.world_id, WorldLeakItemRow.id)
    grouped: dict[int, list[LedgerItem]] = {}
    for row in await session.scalars(statement):
        grouped.setdefault(row.world_id, []).append(LedgerItem(item=row.item, delta=row.delta))
    return {world_id: tuple(items) for world_id, items in grouped.items()}
