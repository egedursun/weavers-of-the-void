from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.chronicle import ChroniclePhase, record_line
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.epoch import EpochStepKind, EpochStepStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import Discovery, SonDistribution
from aerona.engine.cosmos.canon_domains import canon_counts
from aerona.engine.divine.council_order import bound_elsewhere
from aerona.epoch.context import EpochContext
from aerona.epoch.state import attempted
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

PEOPLE_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
INHABITED_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION, EntityType.MORTAL)


@dataclass(frozen=True)
class Move:
    son: SonRow
    world: WorldRow
    godless: bool
    detail: str


async def count_in(session: AsyncSession, world_id: int, types: tuple[EntityType, ...]) -> int:
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(types))
    )
    return int(await session.scalar(statement) or 0)


async def worship_count(session: AsyncSession, son: SonRow, world_id: int | None) -> int:
    statement = (
        select(func.count())
        .select_from(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.world_id == world_id)
    )
    return int(await session.scalar(statement) or 0)


async def worshipped_here(session: AsyncSession, world_id: int, son_ids: set[int]) -> bool:
    statement = (
        select(BondRow.id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        .where(BondRow.target_node_id.in_(son_ids))
    )
    return await session.scalar(statement.limit(1)) is not None


async def wanted_domains(session: AsyncSession, world: WorldRow) -> set[Domain]:
    return set(await canon_counts(session, world))


def protected(rules: Rules, son: SonRow, epoch: int) -> bool:
    return son.manually_assigned_epoch is not None and epoch - son.manually_assigned_epoch < rules.god_hand.assignment_protection_epochs


def donor_ok(rules: Rules, son: SonRow, sons: list[SonRow]) -> bool:
    staying = sum(1 for other in sons if other.current_world_id == son.current_world_id)
    return staying >= rules.god_hand.dispatch_donor_min_sons


async def patronless_moves(session: AsyncSession, rules: Rules, epoch: int, sons: list[SonRow], worlds: list[WorldRow]) -> list[Move]:
    moves: list[Move] = []
    son_ids = {son.id for son in sons}
    for world in worlds:
        peoples = await count_in(session, world.id, PEOPLE_TYPES)
        if peoples == 0 and epoch - world.created_epoch < rules.empty_world.dispatch_wait_epochs:
            continue
        if peoples == 0 and await count_in(session, world.id, (EntityType.REGION,)) == 0:
            continue
        if any(son.current_world_id == world.id for son in sons) or await worshipped_here(session, world.id, son_ids):
            continue
        wanted = await wanted_domains(session, world)
        candidates = [
            son
            for son in sons
            if not son.chained
            and not bound_elsewhere(son, world.id, epoch)
            and not protected(rules, son, epoch)
            and son.current_world_id != world.id
            and donor_ok(rules, son, sons)
        ]
        if not candidates:
            continue
        scored = [(len(set(son.domains) & wanted), await worship_count(session, son, son.current_world_id), son) for son in candidates]
        fit, _, chosen = sorted(scored, key=lambda item: (-item[0], item[1], item[2].id))[0]
        place = "where nobody lives" if peoples == 0 else "which has a people but no god"
        life = " to bring life there" if peoples == 0 else ""
        reason = f" (its domains {DOMAIN_LABELS[chosen.domain_primary]}/{DOMAIN_LABELS[chosen.domain_secondary]} suit that world)" if fit else ""
        chosen.current_world_id = world.id
        moves.append(Move(chosen, world, False, f" ({place}){life}{reason}"))
    return moves


async def godless_moves(session: AsyncSession, rules: Rules, epoch: int, sons: list[SonRow], worlds: list[WorldRow]) -> list[Move]:
    moves: list[Move] = []
    for world in worlds:
        if any(son.current_world_id == world.id for son in sons) or await count_in(session, world.id, INHABITED_TYPES) == 0:
            continue
        candidates = [son for son in sons if not protected(rules, son, epoch) and donor_ok(rules, son, sons)]
        if not candidates:
            continue
        guardians = {item.patron_son_id for item in worlds if item.patron_son_id is not None}
        scored = [
            (await worship_count(session, son, son.current_world_id) + (rules.god_hand.protector_bond_weight if son.id in guardians else 0), son)
            for son in candidates
        ]
        _, chosen = sorted(scored, key=lambda item: (item[0], item[1].id))[0]
        chosen.current_world_id = world.id
        moves.append(Move(chosen, world, True, ""))
    return moves


async def distribute_sons(ec: EpochContext) -> None:
    if ec.resuming:
        return
    async with ec.database.read() as session:
        if await attempted(session, ec.epoch, EpochStepKind.DISTRIBUTION):
            return
    await ec.mark(EpochStepKind.DISTRIBUTION, EpochStepStatus.RUNNING)
    moved: list[str] = []
    planners = (patronless_moves,) if ec.hooks.distribute is not None else (patronless_moves, godless_moves)
    for planner in planners:
        try:
            async with ec.database.write() as session:
                rules = await ec.runtime.rules(session)
                cosmos = await CosmosRepository(session).require_cosmos()
                if cosmos.son_distribution is not SonDistribution.AUTO:
                    break
                sons = list(await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)))
                worlds = list(await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
                for move in await planner(session, rules, ec.epoch, sons, worlds):
                    text = await record_line(
                        session,
                        rules,
                        "epoch.son_distributed",
                        roles={IncidentRole.SUBJECT: move.son.id, IncidentRole.DESTINATION: move.world.id},
                        facts={"kind_of_world": " godless" if move.godless else "", "detail": move.detail},
                        phase=ChroniclePhase.GODS,
                        kind=ChronicleKind.COSMIC,
                        son_id=move.son.id,
                        world_id=move.world.id,
                    )
                    moved.append(text)
                    ec.publish(EventKind.SON_DISTRIBUTED, {"son_id": move.son.id, "world_id": move.world.id, "text": text})
        except Exception as error:
            ec.runtime.error(f"Son distribution: {error}")
    if ec.hooks.distribute is not None:
        try:
            count = await ec.hooks.distribute()
            if count:
                ec.publish(EventKind.SON_DISTRIBUTED, {"moved": count})
        except Exception as error:
            ec.runtime.error(f"Son distribution: {error}")
    for text in moved:
        ec.runtime.note(f"Distribution: {text}")
    await ec.mark(EpochStepKind.DISTRIBUTION, EpochStepStatus.DONE)
