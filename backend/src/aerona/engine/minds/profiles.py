from dataclasses import dataclass

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindLawRow, MindProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import MadeMindsLaw, MindAffect, MindOrigin, MindPurpose, MindSeat, MindUpkeep
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules

GODS = frozenset({NodeKind.SON, NodeKind.CREATOR, NodeKind.FOREIGN_GOD})
MADE_SEATS = frozenset({MindSeat.OBJECT, MindSeat.STRUCTURE, MindSeat.NETWORK, MindSeat.MEDIUM, MindSeat.PLACE, MindSeat.REALM, MindSeat.BODIES})
MADE_ORIGINS = frozenset(
    {MindOrigin.MADE, MindOrigin.TRAINED, MindOrigin.COPIED, MindOrigin.AWAKENED, MindOrigin.SUMMONED, MindOrigin.MERGED, MindOrigin.DIVIDED}
)
MINDED_TYPES = frozenset({EntityType.MORTAL, EntityType.BEAST, EntityType.SPIRIT, EntityType.COSMIC_BEING, EntityType.OUTER_BEING})
WILL_ORDER = (MindWill.NONE, MindWill.INSTRUCTED, MindWill.EMERGENT, MindWill.FULL, MindWill.EXCEEDING)


@dataclass(frozen=True)
class Seed:
    seat: MindSeat
    origin: MindOrigin
    will: MindWill
    affect: MindAffect
    purpose: MindPurpose
    upkeep: MindUpkeep
    capacity: int


SOULED_ORIGINS = frozenset({MindOrigin.BORN, MindOrigin.GRANTED})
NO_MIND = Seed(MindSeat.NONE, MindOrigin.BORN, MindWill.NONE, MindAffect.NONE, MindPurpose.FREE, MindUpkeep.NONE, 0)


def born(capacity: int) -> Seed:
    return Seed(MindSeat.BODY, MindOrigin.BORN, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.FOOD, capacity)


async def entity_seed(session: AsyncSession, rules: Rules, entity: EntityRow) -> Seed:
    baseline = rules.minds.baseline_capacity
    construct = await session.get(ConstructRow, entity.id)
    if construct is not None:
        return Seed(MindSeat.BODY, MindOrigin.MADE, MindWill.INSTRUCTED, MindAffect.NONE, MindPurpose.SERVANT, MindUpkeep.MAINTENANCE, baseline // 2)
    if entity.entity_type is EntityType.BEAST:
        beast = await session.get(BeastProfileRow, entity.id)
        wit = beast.intelligence if beast is not None else baseline // 2
        will = MindWill.FULL if wit >= baseline else MindWill.EMERGENT
        return Seed(MindSeat.BODY, MindOrigin.BORN, will, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.FOOD, wit)
    fixed = {
        EntityType.MORTAL: born(baseline),
        EntityType.SPIRIT: Seed(MindSeat.NONE, MindOrigin.SUMMONED, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.BELIEF, baseline),
        EntityType.COSMIC_BEING: Seed(MindSeat.BODY, MindOrigin.BORN, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.NONE, 100),
        EntityType.OUTER_BEING: Seed(MindSeat.BODY, MindOrigin.BORN, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.NONE, 100),
    }
    return fixed.get(entity.entity_type, NO_MIND)


async def seed_for(session: AsyncSession, rules: Rules, node: NodeRow) -> Seed:
    if node.kind in GODS:
        return Seed(MindSeat.DIVINE, MindOrigin.GRANTED, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.BELIEF, 100)
    if node.kind is NodeKind.WORLD:
        world = await session.get(WorldRow, node.id)
        living = world is not None and world.world_type is WorldType.LIVING
        capacity = rules.minds.baseline_capacity
        return Seed(MindSeat.PLACE, MindOrigin.AWAKENED, MindWill.FULL, MindAffect.FELT, MindPurpose.FREE, MindUpkeep.PLACE, capacity) if living else NO_MIND
    entity = await session.get(EntityRow, node.id) if node.kind is NodeKind.ENTITY else None
    return await entity_seed(session, rules, entity) if entity is not None else NO_MIND


def profile_from(node_id: int, seed: Seed, epoch: int) -> MindProfileRow:
    return MindProfileRow(
        node_id=node_id,
        seat=seed.seat,
        seat_node_id=node_id if seed.seat in {MindSeat.BODY, MindSeat.PLACE} else None,
        origin=seed.origin,
        will=seed.will,
        affect=seed.affect,
        purpose=seed.purpose,
        capacity=seed.capacity,
        speed_pct=100,
        stability=100,
        fidelity_pct=100,
        upkeep=seed.upkeep,
        pausable=False,
        copyable=False,
        restorable=False,
        mergeable=False,
        transferable=False,
        dormant=False,
        perfect_recall=False,
        maker_bond=0,
        drift_pct=0,
        souled=seed.will is not MindWill.NONE and (seed.origin in SOULED_ORIGINS or seed.seat is MindSeat.DIVINE),
        run_epochs=0,
        updated_epoch=epoch,
        locked=[],
    )


def minded_nodes() -> Select[int]:
    minded_entities = select(EntityRow.id).where(or_(EntityRow.entity_type.in_(MINDED_TYPES), EntityRow.id.in_(select(ConstructRow.entity_id))))
    living_worlds = select(WorldRow.id).where(WorldRow.world_type == WorldType.LIVING)
    return select(NodeRow.id).where(or_(NodeRow.kind.in_(GODS), NodeRow.id.in_(living_worlds), NodeRow.id.in_(minded_entities)))


async def seed_missing(session: AsyncSession, rules: Rules, epoch: int) -> int:
    known = select(MindProfileRow.node_id)
    added = 0
    for node in await session.scalars(select(NodeRow).where(NodeRow.id.in_(minded_nodes()), NodeRow.id.not_in(known)).order_by(NodeRow.id)):
        seed = await seed_for(session, rules, node)
        if held(node.id) or seed is NO_MIND:
            continue
        session.add(profile_from(node.id, seed, epoch))
        added += 1
    await session.flush()
    return added


async def profile_of(session: AsyncSession, rules: Rules, node_id: int, epoch: int) -> MindProfileRow:
    row = await session.get(MindProfileRow, node_id)
    if row is not None:
        return row
    node = await session.get_one(NodeRow, node_id)
    row = profile_from(node_id, await seed_for(session, rules, node), epoch)
    session.add(row)
    await session.flush()
    return row


def is_made(row: MindProfileRow) -> bool:
    return row.origin in MADE_ORIGINS or row.seat in MADE_SEATS


def will_rank(will: MindWill) -> int:
    return WILL_ORDER.index(will)


async def law_of(session: AsyncSession, world_id: int | None) -> MadeMindsLaw:
    row = await session.get(MindLawRow, world_id) if world_id is not None else None
    return row.made_minds if row is not None else MadeMindsLaw.WILL_MAY_EMERGE


async def world_of(session: AsyncSession, node_id: int) -> int | None:
    entity = await session.get(EntityRow, node_id)
    if entity is not None:
        return entity.world_id
    world = await session.get(WorldRow, node_id)
    return world.id if world is not None else None


def will_allowed(law: MadeMindsLaw, will: MindWill) -> bool:
    if law is MadeMindsLaw.NO_WILL:
        return will is MindWill.NONE
    if law is MadeMindsLaw.INSTRUCTED_ONLY:
        return will_rank(will) <= will_rank(MindWill.INSTRUCTED)
    return True


def law_lets_will_grow(law: MadeMindsLaw) -> bool:
    return law is MadeMindsLaw.WILL_MAY_EMERGE
