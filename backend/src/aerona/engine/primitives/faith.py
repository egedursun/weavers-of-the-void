from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.powers import unlocked_power_slots
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import DivineWoundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.society import ReverenceRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.divine import DivineWoundKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import PowerEffect, SonStatus
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import active_bonds, connect, living_son, remove_flag
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

GOD_NODE_KINDS = frozenset({NodeKind.SON, NodeKind.CREATOR})


async def patron_node(session: AsyncSession, entity: EntityRow) -> int | None:
    return await BondRepository(session).patron(entity.id)


async def patron_son(session: AsyncSession, entity: EntityRow) -> SonRow | None:
    node_id = await patron_node(session, entity)
    if node_id is None:
        return None
    found = await session.get(SonRow, node_id)
    return found


async def living_patron(session: AsyncSession, entity: EntityRow) -> SonRow | None:
    found = await patron_son(session, entity)
    return found if found is not None and found.status is not SonStatus.DEAD else None


async def foreign_patron(session: AsyncSession, entity: EntityRow) -> ForeignGodRow | None:
    for bond in await active_bonds(session, [BondKind.WORSHIPS], sources=[entity.id]):
        god = await session.get(ForeignGodRow, bond.target_node_id)
        if god is not None:
            return god
    return None


async def worships_anyone(session: AsyncSession, entity_id: int) -> bool:
    return bool(await active_bonds(session, [BondKind.WORSHIPS], sources=[entity_id]))


async def clear_seeking(session: AsyncSession, entity_id: int) -> None:
    await remove_flag(session, entity_id, EntityFlag.GODLESS)
    await remove_flag(session, entity_id, EntityFlag.SEEKING_GOD)


class FaithIndex:
    def __init__(
        self,
        patrons: dict[int, int],
        sons: dict[int, SonRow],
        creator_id: int | None,
        reverences: dict[int, set[int]],
        foreign_worshippers: set[int],
    ) -> None:
        self._patrons = patrons
        self.sons = sons
        self.creator_id = creator_id
        self._reverences = reverences
        self._foreign_worshippers = foreign_worshippers

    @classmethod
    async def load(cls, session: AsyncSession) -> "FaithIndex":
        node_rows = await session.execute(select(NodeRow.id, NodeRow.kind).where(NodeRow.kind.in_([*GOD_NODE_KINDS, NodeKind.FOREIGN_GOD])))
        kinds = {node_id: kind for node_id, kind in node_rows}
        patrons: dict[int, int] = {}
        foreign: set[int] = set()
        statement = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        for source, target in await session.execute(statement.order_by(BondRow.id)):
            kind = kinds.get(target)
            if kind in GOD_NODE_KINDS:
                patrons.setdefault(source, target)
            elif kind is NodeKind.FOREIGN_GOD:
                foreign.add(source)
        creators = select(EntityRow.id, EntityRow.creator_son_id).where(EntityRow.creator_son_id.is_not(None))
        for entity_id, son_id in await session.execute(creators):
            if son_id is not None:
                patrons.setdefault(entity_id, son_id)
        sons = {son.id: son for son in await session.scalars(select(SonRow).order_by(SonRow.id))}
        creator_id = await session.scalar(select(CreatorRow.id).limit(1))
        reverences: dict[int, set[int]] = defaultdict(set)
        for entity_id, god_id in await session.execute(select(ReverenceRow.entity_id, ReverenceRow.god_node_id)):
            reverences[entity_id].add(god_id)
        return cls(patrons, sons, creator_id, reverences, foreign)

    def patron(self, entity_id: int) -> int | None:
        return self._patrons.get(entity_id)

    def living_patron_son(self, entity_id: int) -> SonRow | None:
        son = self.sons.get(self._patrons.get(entity_id, -1))
        return son if son is not None and son.status is not SonStatus.DEAD else None

    def has_living_god(self, entity_id: int) -> bool:
        patron = self._patrons.get(entity_id)
        if patron is None:
            return False
        if patron == self.creator_id:
            return True
        return self.living_patron_son(entity_id) is not None

    def worships_anything(self, entity_id: int) -> bool:
        return entity_id in self._patrons or entity_id in self._foreign_worshippers

    def reverences(self, entity_id: int) -> set[int]:
        return set(self._reverences.get(entity_id, set()))

    def god_fame(self, god_id: int | None) -> int:
        son = self.sons.get(god_id) if god_id is not None else None
        return son.fame if son is not None else 0

    def is_living_god(self, god_id: int) -> bool:
        if god_id == self.creator_id:
            return True
        son = self.sons.get(god_id)
        return son is not None and son.status is not SonStatus.DEAD

    def record_patron(self, entity_id: int, god_id: int) -> None:
        self._patrons[entity_id] = god_id
        self._reverences.get(entity_id, set()).discard(god_id)

    def record_reverence(self, entity_id: int, god_id: int) -> None:
        self._reverences[entity_id].add(god_id)


async def is_living_god(session: AsyncSession, god_id: int) -> bool:
    son = await session.get(SonRow, god_id)
    if son is not None:
        return son.status is not SonStatus.DEAD
    return await NodeRepository(session).kind_of(god_id) is NodeKind.CREATOR


async def change_religion(
    session: AsyncSession, entity: EntityRow, god_id: int | None, epoch: int, reason: str, *, syncretic: bool = False, faith: FaithIndex | None = None
) -> bool:
    if entity.status is not EntityStatus.CANON or god_id is None:
        return False
    if not (faith.is_living_god(god_id) if faith is not None else await is_living_god(session, god_id)):
        return False
    current = faith.patron(entity.id) if faith is not None else await patron_node(session, entity)
    if current == god_id:
        return False
    if syncretic and current is not None:
        if await session.get(ReverenceRow, (entity.id, god_id)) is not None:
            return False
        session.add(ReverenceRow(entity_id=entity.id, god_node_id=god_id, since_epoch=epoch))
        await session.flush()
        if faith is not None:
            faith.record_reverence(entity.id, god_id)
        return True
    await connect(session, entity.id, god_id, BondKind.WORSHIPS, epoch, description=reason)
    await session.execute(delete(ReverenceRow).where(ReverenceRow.entity_id == entity.id, ReverenceRow.god_node_id == god_id))
    await remove_flag(session, entity.id, EntityFlag.GODLESS)
    await clear_seeking(session, entity.id)
    if faith is not None:
        faith.record_patron(entity.id, god_id)
    return True


async def worship_creator(session: AsyncSession, entity: EntityRow, epoch: int, reason: str) -> bool:
    creator_id = await NodeRepository(session).creator_id()
    if creator_id is None or entity.status is not EntityStatus.CANON:
        return False
    existing = await active_bonds(session, [BondKind.WORSHIPS], sources=[entity.id], targets=[creator_id])
    if not existing:
        await connect(session, entity.id, creator_id, BondKind.WORSHIPS, epoch, description=reason)
    await remove_flag(session, entity.id, EntityFlag.GODLESS)
    await remove_flag(session, entity.id, EntityFlag.SEEKING_GOD)
    return not existing


async def first_faith_god(session: AsyncSession, rules: Rules, entity: EntityRow, atlas: RegionAtlas, roll: float) -> SonRow | None:
    life = rules.deep_life
    counts: dict[int, float] = defaultdict(float)
    statement = select(EntityRow).where(
        EntityRow.world_id == entity.world_id,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        EntityRow.id != entity.id,
    )
    for other in await session.scalars(statement.order_by(EntityRow.id)):
        patron = await living_patron(session, other)
        if patron is None:
            continue
        counts[patron.id] += life.first_faith_region_weight if atlas.same_region(entity.id, other.id) else 1
    weights: dict[int, float] = {son_id: count ** (life.first_faith_crowd_exponent / PERCENT) for son_id, count in counts.items()}
    active = await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == entity.world_id))
    for son in active:
        weights[son.id] = weights.get(son.id, 0.0) + life.first_faith_son_base_weight
    candidates = sorted(son_id for son_id, weight in weights.items() if weight > 0)
    if candidates:
        total = sum(weights[son_id] for son_id in candidates)
        threshold = roll * total
        running = 0.0
        for son_id in candidates:
            running += weights[son_id]
            if threshold < running:
                return await living_son(session, son_id)
        return await living_son(session, candidates[-1])
    world = await session.get(WorldRow, entity.world_id)
    guardian = await living_son(session, world.patron_son_id if world is not None else None)
    if guardian is not None:
        return guardian
    fallback: SonRow | None = await session.scalar(
        select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == entity.world_id).order_by(SonRow.id).limit(1)
    )
    return fallback


async def has_unlocked_power(session: AsyncSession, rules: Rules, son: SonRow, effect: PowerEffect) -> bool:
    slots = unlocked_power_slots(rules, son.level)
    severed = len(
        list(
            await session.scalars(
                select(DivineWoundRow.id).where(
                    DivineWoundRow.god_node_id == son.id, DivineWoundRow.kind == DivineWoundKind.SEVERED_DOMAIN, DivineWoundRow.healed < PERCENT
                )
            )
        )
    )
    slots = tuple(sorted(slots)[: max(0, len(slots) - severed)])
    if not slots:
        return False
    statement = select(SonPowerRow.slot).where(SonPowerRow.son_id == son.id, SonPowerRow.effect == effect, SonPowerRow.slot.in_(list(slots)))
    return await session.scalar(statement.limit(1)) is not None


def saturated_followers(rules: Rules, followers: float, per_faith: float) -> float:
    faith = rules.faith
    raw = max(0.0, followers) / max(1.0, per_faith)
    knee = faith.cult_saturation
    return float(knee * (raw / knee) ** (faith.cult_saturation_exponent_pct / PERCENT)) if knee > 0 and raw > knee else raw


def dominance_multiplier(rules: Rules, share_pct: float) -> float:
    threshold = rules.religion.dominant_god_threshold_pct
    if share_pct <= threshold:
        return 1.0
    return max(0.0, (PERCENT - share_pct) / max(1, PERCENT - threshold))


async def faith_shares(session: AsyncSession) -> dict[int, float]:
    rows = list(await session.execute(select(SonRow.id, SonRow.faith).where(SonRow.status != SonStatus.DEAD)))
    total = sum(max(0, faith) for _, faith in rows)
    return {son_id: max(0, faith) / total * PERCENT if total else 0.0 for son_id, faith in rows}


def faith_dominance(rules: Rules, god_id: int, shares: dict[int, float], community_share_pct: float = 0.0) -> float:
    return min(dominance_multiplier(rules, community_share_pct), dominance_multiplier(rules, shares.get(god_id, 0.0)))


async def worships_creator(session: AsyncSession, entity_id: int) -> bool:
    creator_id = await NodeRepository(session).creator_id()
    return creator_id is not None and bool(await active_bonds(session, [BondKind.WORSHIPS], sources=[entity_id], targets=[creator_id]))


def worshipper_faith(rules: Rules, worshipper: EntityRow) -> float:
    faith = rules.faith
    if worshipper.entity_type is EntityType.CULT:
        followers = stat(worshipper, "followers") or 0
        influence = stat(worshipper, "influence") or 0
        return max(float(faith.community_min), saturated_followers(rules, followers, faith.followers_per_faith) * (1 + influence / PERCENT))
    if worshipper.entity_type in (EntityType.PEOPLE, EntityType.SETTLEMENT):
        recorded = stat(worshipper, "piety")
        piety = faith.default_piety if recorded is None else recorded
        population = stat(worshipper, "population") or 0
        floor = faith.community_min if piety > 0 else 0
        return max(float(floor), population / faith.pious_population_per_faith * piety / PERCENT)
    return float(faith.other_worshipper)


async def son_faith(session: AsyncSession, rules: Rules, son: SonRow) -> int:
    worshipping = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == son.id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    worshippers = {entity.id: entity for entity in await session.scalars(worshipping)}
    revering = (
        select(EntityRow)
        .join(ReverenceRow, ReverenceRow.entity_id == EntityRow.id)
        .where(ReverenceRow.god_node_id == son.id, EntityRow.status == EntityStatus.CANON)
    )
    reverent = [entity for entity in await session.scalars(revering) if entity.id not in worshippers]
    total = sum(worshipper_faith(rules, worshipper) for worshipper in worshippers.values())
    total += sum(worshipper_faith(rules, entity) for entity in reverent) * rules.religion.reverence_weight_pct / PERCENT
    if await has_unlocked_power(session, rules, son, PowerEffect.WORSHIPPED):
        total *= rules.faith.multiplier_power_pct / PERCENT
    return round_half_up(total)


async def worshipper_count(session: AsyncSession, son_id: int) -> int:
    statement = (
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.target_node_id == son_id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    return len(set(await session.scalars(statement)))
