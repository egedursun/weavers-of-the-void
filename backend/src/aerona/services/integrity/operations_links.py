from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import bond_spec
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.operations import (
    AdmiraltyRow,
    DepotRow,
    EchelonRow,
    ExpeditionMemberRow,
    ExpeditionRow,
    TheatreRow,
    TransportAssetRow,
)
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.operations import ExpeditionStatus
from aerona.domain.enums.war import WarStatus
from aerona.engine.primitives.stats import stat_or

UNDER_WAY = (ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED)
OWNER_LABEL = bond_spec(BondKind.OWNS).label


async def mend_operations_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    disbanded = select(ArmyRow.entity_id).where(ArmyRow.disbanded_epoch.is_not(None))
    ended = select(WarRow.id).where(WarRow.status != WarStatus.ONGOING)
    foreign = (
        select(ArmyUnitRow.id)
        .join(EchelonRow, EchelonRow.id == ArmyUnitRow.echelon_id)
        .where(EchelonRow.army_entity_id.is_not(None), EchelonRow.army_entity_id != ArmyUnitRow.army_entity_id)
    )
    alive = select(ExpeditionMemberRow.expedition_id).where(ExpeditionMemberRow.fallen.is_(False))
    statements = [
        delete(EchelonRow).where(EchelonRow.army_entity_id.in_(disbanded)),
        delete(EchelonRow).where(EchelonRow.owner_entity_id.in_(vanished)),
        update(EchelonRow).where(EchelonRow.commander_entity_id.in_(vanished)).values(commander_entity_id=None),
        update(ArmyUnitRow).where(ArmyUnitRow.id.in_(foreign)).values(echelon_id=None),
        delete(DepotRow).where(DepotRow.owner_entity_id.in_(vanished)),
        delete(TransportAssetRow).where(TransportAssetRow.owner_entity_id.in_(vanished)),
        delete(TheatreRow).where(TheatreRow.war_id.in_(ended)),
        update(TheatreRow).where(TheatreRow.marshal_entity_id.in_(vanished)).values(marshal_entity_id=None),
        update(AdmiraltyRow).where(AdmiraltyRow.admiral_entity_id.in_(vanished)).values(admiral_entity_id=None),
        update(ExpeditionMemberRow).where(ExpeditionMemberRow.mortal_entity_id.in_(vanished), ExpeditionMemberRow.fallen.is_(False)).values(fallen=True),
        update(ExpeditionRow).where(ExpeditionRow.status.in_(UNDER_WAY), ExpeditionRow.id.not_in(alive)).values(status=ExpeditionStatus.LOST),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended


async def yard_town(session: AsyncSession, polity_id: int) -> int | None:
    profile = await session.get(PolityProfileRow, polity_id)
    if profile is not None and profile.capital_entity_id is not None:
        return profile.capital_entity_id
    members = list(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))
    towns = [item for member in members if (item := await session.get(EntityRow, member)) is not None and item.status is EntityStatus.CANON]
    return max(towns, key=lambda item: (stat_or(item, "population", 0), -item.id)).id if towns else None


async def own_stray_ships(session: AsyncSession, epoch: int) -> int:
    owned = select(BondRow.target_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    strays = await session.execute(
        select(BondRow, EntityRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .join(VesselProfileRow, VesselProfileRow.entity_id == BondRow.target_node_id)
        .where(
            BondRow.kind == BondKind.RELATED,
            BondRow.state == BondState.ACTIVE,
            BondRow.description.like(f"{OWNER_LABEL}%"),
            EntityRow.entity_type == EntityType.POLITY,
            BondRow.target_node_id.not_in(owned),
        )
        .order_by(BondRow.id)
    )
    bonds = BondRepository(session)
    mended = 0
    for bond, polity in list(strays):
        town = await yard_town(session, polity.id)
        if town is None:
            continue
        await bonds.deactivate(bond, epoch, "its realm holds its ships through its towns")
        await bonds.connect(BondDraft(town, bond.target_node_id, BondKind.OWNS, epoch, f"held for {polity.name}"))
        mended += 1
    return mended
