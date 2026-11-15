from collections.abc import Iterable

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import DiasporaRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType

RULED_COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT})
DUPLICATE_RULE = "duplicate rule"


async def homeland_to_lives_in(session: AsyncSession, epoch: int) -> int:
    repository = BondRepository(session)
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.role == BondRole.HOMELAND, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    converted = 0
    for bond in list(await session.scalars(statement)):
        await repository.deactivate(bond, epoch)
        living = [
            row
            for row in await repository.active_between(bond.source_node_id, bond.target_node_id, [BondKind.LIVES_IN])
            if row.source_node_id == bond.source_node_id
        ]
        for row in living:
            row.role = BondRole.HOMELAND
        if not living:
            await repository.connect(
                BondDraft(bond.source_node_id, bond.target_node_id, BondKind.LIVES_IN, epoch, description=bond.description, role=BondRole.HOMELAND)
            )
        converted += 1
    return converted


def homeland_draft(people_id: int, town: EntityRow) -> BondDraft:
    return BondDraft(people_id, town.id, BondKind.LIVES_IN, town.birth_epoch, "homeland", role=BondRole.HOMELAND)


async def first_source(session: AsyncSession, kinds: list[BondKind], target_id: int, sources: Select[int]) -> int | None:
    found = await session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.kind.in_(kinds), BondRow.state == BondState.ACTIVE, BondRow.target_node_id == target_id, BondRow.source_node_id.in_(sources))
        .order_by(BondRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def first_target(session: AsyncSession, kind: BondKind, source_id: int, targets: Iterable[int]) -> int | None:
    found = await session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.kind == kind, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == source_id, BondRow.target_node_id.in_(sorted(targets)))
        .order_by(BondRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def promote_roleless(session: AsyncSession, peoples: Select[int], towns: Select[int], homes: dict[int, int]) -> int:
    abroad = {(people, host) for people, host in await session.execute(select(DiasporaRow.people_entity_id, DiasporaRow.host_entity_id))}
    living = await session.scalars(
        select(BondRow)
        .where(
            BondRow.kind == BondKind.LIVES_IN,
            BondRow.state == BondState.ACTIVE,
            BondRow.role.is_(None),
            BondRow.source_node_id.in_(peoples),
            BondRow.target_node_id.in_(towns),
        )
        .order_by(BondRow.id)
    )
    promoted = 0
    for bond in list(living):
        if bond.target_node_id in homes or (bond.source_node_id, bond.target_node_id) in abroad:
            continue
        bond.role = BondRole.HOMELAND
        homes[bond.target_node_id] = bond.source_node_id
        promoted += 1
    return promoted


async def people_for(session: AsyncSession, town: EntityRow, peoples: Select[int], homes: dict[int, int]) -> int | None:
    ruler = await first_source(session, [BondKind.RULES], town.id, peoples)
    if ruler is not None:
        return ruler
    born = await first_source(session, [BondKind.DESCENDS_FROM], town.id, peoples)
    if born is not None:
        return born
    mother = await first_target(session, BondKind.DESCENDS_FROM, town.id, homes)
    if mother is not None:
        return homes[mother]
    settlers = await first_source(session, [BondKind.LIVES_IN], town.location_id, peoples) if town.location_id is not None else None
    if settlers is not None:
        return settlers
    guests = await first_source(session, [BondKind.LIVES_IN], town.id, peoples)
    if guests is not None:
        return guests
    tongue = await session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == town.id)
        .order_by(BondRow.id)
        .limit(1)
    )
    return await speakers_of(session, tongue, peoples) if tongue is not None else None


async def speakers_of(session: AsyncSession, tongue: int, peoples: Select[int]) -> int | None:
    found = await session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == tongue, BondRow.source_node_id.in_(peoples))
        .order_by(BondRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def restore_homelands(session: AsyncSession) -> int:
    peoples = select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
    towns = select(EntityRow.id).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    homes: dict[int, int] = {}
    for home_id, people_id in await session.execute(
        select(BondRow.target_node_id, BondRow.source_node_id)
        .where(
            BondRow.kind.in_([BondKind.LIVES_IN, BondKind.RULES]),
            BondRow.state == BondState.ACTIVE,
            BondRow.role == BondRole.HOMELAND,
            BondRow.source_node_id.in_(peoples),
        )
        .order_by(BondRow.id)
    ):
        homes.setdefault(home_id, people_id)
    for home_id, people_id in await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.DESCENDS_FROM, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(peoples), BondRow.source_node_id.in_(towns)
        )
    ):
        homes.setdefault(home_id, people_id)
    restored = await promote_roleless(session, peoples, towns, homes)
    repository = BondRepository(session)
    pending = list(await session.scalars(select(EntityRow).where(EntityRow.id.in_(towns), EntityRow.id.not_in(sorted(homes))).order_by(EntityRow.id)))
    while pending:
        settled = []
        for town in pending:
            people = await people_for(session, town, peoples, homes)
            if people is not None:
                await repository.connect(homeland_draft(people, town))
                homes[town.id] = people
                settled.append(town)
        if not settled:
            break
        restored += len(settled)
        pending = [town for town in pending if town.id not in homes]
    await session.flush()
    return restored


async def single_rule(session: AsyncSession, epoch: int) -> int:
    targets = {
        entity_id
        for entity_id in await session.scalars(
            select(EntityRow.id).where(EntityRow.entity_type.in_(list(RULED_COMMUNITIES)), EntityRow.status == EntityStatus.CANON)
        )
    }
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    by_target: dict[int, list[BondRow]] = {}
    for bond in await session.scalars(statement):
        if bond.target_node_id in targets and bond.source_node_id in living:
            by_target.setdefault(bond.target_node_id, []).append(bond)
    repository = BondRepository(session)
    closed = 0
    for bonds in by_target.values():
        if len(bonds) < 2:
            continue
        keeper = max((bond for bond in bonds if bond.role is not BondRole.HOMELAND), key=lambda bond: bond.id, default=bonds[-1])
        for bond in bonds:
            if bond.id != keeper.id:
                await repository.deactivate(bond, epoch, DUPLICATE_RULE)
                closed += 1
    return closed
