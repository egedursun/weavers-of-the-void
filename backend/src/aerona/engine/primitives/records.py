from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import can_contain, entity_type_spec
from aerona.core.grammar import an
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin import KinGroupMemberRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import (
    COMMUNITY_TYPES,
    ENDED_STATUSES,
    EngineKind,
    EntityFlag,
    EntityOrigin,
    EntityStatus,
    EntityType,
    LegendCategory,
    MortalRole,
)
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic, SocialClass
from aerona.domain.models.entity_stats import EntityStats
from aerona.engine.context import TickContext
from aerona.engine.economy.provenance import ensure_materials
from aerona.engine.interconnect.guards import CONSERVED_KEYS, record_flow
from aerona.engine.kin_dynamics.heirs import disowned_by, favoured_by, leaves_a_choice
from aerona.engine.primitives.queries import active_bonds, connect, living_entity

SOURCE_STATE_KINDS = frozenset(
    {
        BondKind.LIVES_IN,
        BondKind.INSIDE,
        BondKind.PROTECTS,
        BondKind.WORSHIPS,
        BondKind.SPEAKS,
        BondKind.RULES,
        BondKind.COMMANDS,
        BondKind.OWNS,
        BondKind.KNOWS,
        BondKind.LOVES,
        BondKind.COMPANION,
        BondKind.HOLDS_CAPTIVE,
        BondKind.SPY_NETWORK,
        BondKind.PURSUES,
        BondKind.TAMED,
        BondKind.ALLY,
        BondKind.TRADES_WITH,
        BondKind.ENEMY,
        BondKind.PAYS_TRIBUTE,
        BondKind.TRUCE,
        BondKind.HUNTS,
        BondKind.CAPTAIN_OF,
        BondKind.PASSENGER_OF,
        BondKind.RIVAL,
        BondKind.APPRENTICE_OF,
        BondKind.MEMBER_OF,
        BondKind.SPOUSE_OF,
        BondKind.BETROTHED_TO,
        BondKind.CONCUBINE_OF,
        BondKind.SWORN_KIN,
        BondKind.GODPARENT_OF,
    }
)
TARGET_STATE_KINDS = frozenset(
    {
        BondKind.RULES,
        BondKind.PROTECTS,
        BondKind.COMMANDS,
        BondKind.OWNS,
        BondKind.WORSHIPS,
        BondKind.ALLY,
        BondKind.TRADES_WITH,
        BondKind.ENEMY,
        BondKind.PAYS_TRIBUTE,
        BondKind.LOVES,
        BondKind.COMPANION,
        BondKind.SPY_NETWORK,
        BondKind.TAMED,
        BondKind.SPEAKS,
        BondKind.TRUCE,
        BondKind.CAPTAIN_OF,
        BondKind.PASSENGER_OF,
        BondKind.HUNTS,
        BondKind.PURSUES,
        BondKind.HOLDS_CAPTIVE,
        BondKind.RIVAL,
        BondKind.APPRENTICE_OF,
        BondKind.MEMBER_OF,
        BondKind.SPOUSE_OF,
        BondKind.BETROTHED_TO,
        BondKind.CONCUBINE_OF,
        BondKind.SWORN_KIN,
        BondKind.GODPARENT_OF,
    }
)
INHERITED_KINDS = frozenset({BondKind.OWNS, BondKind.RULES})
HEIR_TYPES = COMMUNITY_TYPES | {EntityType.MORTAL}
DEATH_CLOSE_REASON = "death"
MINIMUM_POWER_LEVEL = 1


@dataclass(frozen=True)
class RecordSpec:
    entity_type: EntityType
    name: str
    body: str
    stats: EntityStats
    power: int
    location_id: int | None = None
    world_id: int | None = None
    subtype: str | None = None
    engine_kind: EngineKind | None = None
    mortal_role: MortalRole | None = None
    title: str | None = None
    flags: Sequence[EntityFlag] = field(default_factory=tuple)
    creator_son_id: int | None = None
    domain: Domain | None = None
    knowledge_branch: KnowledgeBranch | None = None
    natural_law: NaturalLaw | None = None
    resource_mechanic: ResourceMechanic | None = None
    social_class: SocialClass | None = None
    is_underworld: bool = False
    is_water: bool = False
    maker_entity_id: int | None = None
    affiliated_entity_id: int | None = None
    sacred_to_son_id: int | None = None
    traits: Sequence[CreatureTrait] = field(default_factory=tuple)
    sanity: int | None = None
    origin: EntityOrigin = EntityOrigin.ENGINE
    pending: bool = True
    image_prompt: str | None = None
    legend_category: LegendCategory | None = None


@dataclass(frozen=True)
class SweepResult:
    closed: int
    transferred: int
    passed: Mapping[int, tuple[int, tuple[int, ...]]] = field(default_factory=dict)
    closed_of: Mapping[int, int] = field(default_factory=dict)


def sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:]


def definite(name: str) -> str:
    return name if name.lower().startswith("the ") else f"the {name}"


def introduce(name: str, noun: str, location_name: str | None, body: str) -> str:
    place = f" in {location_name}" if location_name else ""
    return f"{name}, {an(noun)}{place}. {body}".strip()


async def valid_location(session: AsyncSession, entity_type: EntityType, location_id: int | None) -> EntityRow | None:
    current = await session.get(EntityRow, location_id) if location_id is not None else None
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        if current.status not in ENDED_STATUSES and can_contain(current.entity_type, entity_type):
            return current
        seen.add(current.id)
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    return None


async def open_record(session: AsyncSession, epoch: int, spec: RecordSpec) -> EntityRow:
    location = await valid_location(session, spec.entity_type, spec.location_id)
    name = await NameRepository(session).unique_name(spec.name.strip())
    noun = spec.subtype or entity_type_spec(spec.entity_type).noun
    description = introduce(name, noun, location.name if location is not None else None, spec.body)
    world_id = spec.world_id if spec.world_id is not None else (location.world_id if location is not None else None)
    created = await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=spec.entity_type,
            description=description,
            stats=spec.stats,
            power_level=max(MINIMUM_POWER_LEVEL, spec.power),
            origin=spec.origin,
            birth_epoch=epoch,
            world_id=world_id,
            location_id=location.id if location is not None else None,
            creator_son_id=spec.creator_son_id,
            maker_entity_id=spec.maker_entity_id,
            title=spec.title,
            subtype=spec.subtype,
            engine_kind=spec.engine_kind,
            mortal_role=spec.mortal_role,
            domain=spec.domain,
            pending_name=spec.pending,
            knowledge_branch=spec.knowledge_branch,
            natural_law=spec.natural_law,
            resource_mechanic=spec.resource_mechanic,
            social_class=spec.social_class,
            affiliated_entity_id=spec.affiliated_entity_id,
            sacred_to_son_id=spec.sacred_to_son_id,
            is_underworld=spec.is_underworld,
            is_water=spec.is_water,
            sanity=spec.sanity,
            image_prompt=spec.image_prompt,
            legend_category=spec.legend_category,
            flags=tuple(spec.flags),
            traits=tuple(spec.traits),
            split_title=False,
        )
    )
    founded(created)
    await ensure_materials(session, created)
    return created


def founded(entity: EntityRow) -> None:
    for key in CONSERVED_KEYS:
        value = getattr(entity.stats, key, None)
        if isinstance(value, int) and value:
            record_flow(entity.id, key, value)


async def create_record(ctx: TickContext, spec: RecordSpec) -> EntityRow:
    return await open_record(ctx.session, ctx.epoch, spec)


async def retire_in(ctx: TickContext, entity: EntityRow, note: str, status: EntityStatus = EntityStatus.DEAD, *, close_bonds: bool = False) -> EntityRow:
    return await retire(ctx.session, entity, ctx.epoch, f"Epoch {ctx.epoch}: {note}.", status=status, append=True, close_bonds=close_bonds)


def append_sentence(text: str | None, sentence: str) -> str:
    current = (text or "").strip()
    if sentence in current:
        return current
    return f"{current} {sentence}".strip()


async def retire(
    session: AsyncSession,
    entity: EntityRow,
    epoch: int,
    note: str | None = None,
    *,
    status: EntityStatus = EntityStatus.DEAD,
    append: bool = False,
    close_bonds: bool = False,
) -> EntityRow:
    entities = EntityRepository(session)
    await entities.load_columns(entity)
    if note:
        entity.description = append_sentence(entity.description, note)
    fate_note = append_sentence(entity.fate_note, note) if note and append else note
    await entities.set_status(entity, status, epoch, fate_note)
    if entity.end_epoch is None or entity.end_epoch != epoch:
        entity.end_epoch = epoch
    if close_bonds:
        await sweep_dead_bonds(session, epoch, entity.id)
    return entity


async def kin_heir(session: AsyncSession, dead: EntityRow) -> EntityRow | None:
    groups = select(KinGroupMemberRow.group_id).where(KinGroupMemberRow.member_node_id == dead.id)
    kin = await session.scalars(
        select(KinGroupMemberRow.member_node_id)
        .where(KinGroupMemberRow.group_id.in_(groups), KinGroupMemberRow.member_node_id != dead.id)
        .order_by(KinGroupMemberRow.joined_epoch, KinGroupMemberRow.member_node_id)
    )
    for member_id in list(kin):
        candidate = await living_entity(session, member_id)
        if candidate is not None and candidate.entity_type in HEIR_TYPES:
            return candidate
    return None


async def child_heir(session: AsyncSession, dead: EntityRow, favour_reach: int) -> EntityRow | None:
    cast_out = await disowned_by(session, dead.id)
    chosen = await favoured_by(session, dead.id, favour_reach) if favour_reach and await leaves_a_choice(session, dead) else []
    children = [bond.target_node_id for bond in reversed(await active_bonds(session, [BondKind.PARENT_OF], sources=[dead.id]))]
    for child_id in [*chosen, *children]:
        candidate = await living_entity(session, child_id)
        if candidate is not None and candidate.entity_type in HEIR_TYPES and candidate.id not in cast_out:
            return candidate
    return None


async def heir_of(session: AsyncSession, dead: EntityRow, *, favour_reach: int = 0) -> EntityRow | None:
    child = await child_heir(session, dead, favour_reach)
    if child is not None:
        return child
    for bond in reversed(await active_bonds(session, [BondKind.DESCENDS_FROM], targets=[dead.id])):
        candidate = await living_entity(session, bond.source_node_id)
        if candidate is not None and candidate.entity_type in HEIR_TYPES:
            return candidate
    kin = await kin_heir(session, dead)
    if kin is not None:
        return kin
    location = await living_entity(session, dead.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    sources = [bond.target_node_id for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[dead.id])]
    sources += [bond.source_node_id for bond in await active_bonds(session, [BondKind.RULES], targets=[dead.id])]
    sources += [bond.target_node_id for bond in await active_bonds(session, [BondKind.PROTECTS], sources=[dead.id])]
    for candidate_id in sources:
        candidate = await living_entity(session, candidate_id)
        if candidate is not None and candidate.entity_type in COMMUNITY_TYPES:
            return candidate
    return None


async def _dead_ids(session: AsyncSession, single_id: int | None) -> set[int]:
    statement = select(EntityRow.id).where(EntityRow.status.in_(list(ENDED_STATUSES)))
    if single_id is not None:
        statement = statement.where(EntityRow.id == single_id)
    return set(await session.scalars(statement))


async def _has_other_ruler(session: AsyncSession, target_id: int, heir_id: int) -> bool:
    for bond in await active_bonds(session, [BondKind.RULES], targets=[target_id]):
        if bond.source_node_id != heir_id and await living_entity(session, bond.source_node_id) is not None:
            return True
    return False


async def sweep_dead_bonds(session: AsyncSession, epoch: int, single_id: int | None = None) -> SweepResult:
    dead_ids = await _dead_ids(session, single_id)
    if not dead_ids:
        return SweepResult(0, 0)
    bonds = BondRepository(session)
    heirs: dict[int, EntityRow | None] = {}
    closed = 0
    transferred = 0
    passed: dict[int, list[int]] = defaultdict(list)
    closed_of: dict[int, int] = defaultdict(int)
    statement = select(BondRow).where(BondRow.state == BondState.ACTIVE, BondRow.kind.in_(list(SOURCE_STATE_KINDS)), BondRow.source_node_id.in_(list(dead_ids)))
    for bond in list(await session.scalars(statement.order_by(BondRow.id))):
        await bonds.deactivate(bond, epoch, DEATH_CLOSE_REASON)
        closed += 1
        closed_of[bond.source_node_id] += 1
        if bond.kind not in INHERITED_KINDS:
            continue
        target = await living_entity(session, bond.target_node_id)
        if target is None:
            continue
        if bond.source_node_id not in heirs:
            dead = await session.get(EntityRow, bond.source_node_id)
            heirs[bond.source_node_id] = await heir_of(session, dead) if dead is not None else None
        heir = heirs[bond.source_node_id]
        if heir is None or heir.id == target.id:
            continue
        if await active_bonds(session, [bond.kind], sources=[heir.id], targets=[target.id]):
            continue
        if bond.kind is BondKind.RULES and await _has_other_ruler(session, target.id, heir.id):
            continue
        dead = await session.get(EntityRow, bond.source_node_id)
        await connect(session, heir.id, target.id, bond.kind, epoch, description=f"inherited from {dead.name if dead is not None else 'the dead'}")
        transferred += 1
        passed[bond.source_node_id].append(target.id)
    target_statement = select(BondRow).where(
        BondRow.state == BondState.ACTIVE, BondRow.kind.in_(list(TARGET_STATE_KINDS)), BondRow.target_node_id.in_(list(dead_ids))
    )
    for bond in list(await session.scalars(target_statement.order_by(BondRow.id))):
        await bonds.deactivate(bond, epoch, DEATH_CLOSE_REASON)
        closed += 1
        closed_of[bond.target_node_id] += 1
    for route in list(await session.scalars(select(RouteRow).where(RouteRow.controller_entity_id.in_(list(dead_ids))))):
        dead = await session.get(EntityRow, route.controller_entity_id) if route.controller_entity_id is not None else None
        heir = heirs.get(dead.id) if dead is not None and dead.id in heirs else (await heir_of(session, dead) if dead is not None else None)
        route.controller_entity_id = heir.id if heir is not None and heir.entity_type in COMMUNITY_TYPES else None
    await session.flush()
    inherited = {dead_id: (heir.id, tuple(targets)) for dead_id, targets in passed.items() if (heir := heirs.get(dead_id)) is not None}
    return SweepResult(closed, transferred, inherited, dict(closed_of))
