from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.carriers import CARRIERS
from aerona.catalog.goods_tables import SOURCED_ORIGINS
from aerona.catalog.life.customs import ANIMAL_INTOXICANT_SOURCES, MADE_INTOXICANT_TECHNIQUES, SOURCED_INTOXICANTS
from aerona.catalog.means import NETWORKED_AIDS
from aerona.catalog.methods import METHODS
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.customs import IntoxicantCustomRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.economy import TradeRouteProfileRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.means import NavigationKitRow, WrittenWorkRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.relations import ContestRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import Intoxicant
from aerona.domain.enums.economy import MaterialOrigin, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.means import WritingMedium
from aerona.domain.enums.relations import ContestStake
from aerona.domain.enums.tongues import LanguageStage
from aerona.engine.eras.effects import era_techniques
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.tongues.modality import body_functions, fits, perceiving, suited

LAND_TYPES = frozenset({EntityType.REGION, EntityType.SETTLEMENT})
BROKEN_PROMISE = "a party to the promise is gone"


async def gone(session: AsyncSession, node_id: int) -> bool:
    entity = await session.get(EntityRow, node_id)
    return entity is None or entity.status is not EntityStatus.CANON


async def dead_promises(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for bond in await session.scalars(select(BondRow).where(BondRow.kind == BondKind.BETROTHED_TO, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)):
        if await gone(session, bond.source_node_id) or await gone(session, bond.target_node_id):
            found.append(bond.id)
    return found


async def end_promise(session: AsyncSession, key: int) -> None:
    bond = await session.get(BondRow, key)
    if bond is not None and bond.state is BondState.ACTIVE:
        bond.state = BondState.PAST
        bond.closed_reason = BROKEN_PROMISE


async def unnamed_stakes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(
        select(ContestRow).where(ContestRow.stake == ContestStake.LAND, ContestRow.stake_node_id.is_not(None)).order_by(ContestRow.id)
    ):
        entity = await session.get(EntityRow, row.stake_node_id)
        if entity is None or entity.entity_type not in LAND_TYPES:
            found.append(row.id)
    return found


async def clear_stake(session: AsyncSession, key: int) -> None:
    row = await session.get(ContestRow, key)
    if row is not None:
        row.stake_node_id = None


async def stray_customs(session: AsyncSession, people_id: int | None = None) -> list[IntoxicantCustomRow]:
    statement = select(IntoxicantCustomRow).where(IntoxicantCustomRow.intoxicant.in_(SOURCED_INTOXICANTS))
    if people_id is not None:
        statement = statement.where(IntoxicantCustomRow.people_entity_id == people_id)
    found: list[IntoxicantCustomRow] = []
    for row in await session.scalars(statement.order_by(IntoxicantCustomRow.people_entity_id, IntoxicantCustomRow.intoxicant)):
        if "intoxicant" in (row.locked or []):
            continue
        sourced = (
            await knows_making(session, row.people_entity_id) if row.intoxicant is Intoxicant.SYNTHETIC else await has_beasts(session, row.people_entity_id)
        )
        if not sourced:
            found.append(row)
    return found


async def unsourced_intoxicants(session: AsyncSession) -> list[int]:
    return sorted({row.people_entity_id for row in await stray_customs(session)})


async def knows_making(session: AsyncSession, people_id: int) -> bool:
    found = await session.scalar(
        select(HolderTechniqueRow.technique)
        .where(HolderTechniqueRow.holder_entity_id == people_id, HolderTechniqueRow.technique.in_(sorted(MADE_INTOXICANT_TECHNIQUES)))
        .limit(1)
    )
    return found is not None


async def has_beasts(session: AsyncSession, people_id: int) -> bool:
    towns = await towns_of_people(session, people_id)
    if not towns:
        return False
    lands = select(EntityRow.location_id).where(EntityRow.id.in_(towns), EntityRow.location_id.is_not(None))
    sources = select(SpeciesProductRow.species_entity_id).where(SpeciesProductRow.product.in_(sorted(product.value for product in ANIMAL_INTOXICANT_SOURCES)))
    found = await session.scalar(
        select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.species_entity_id.in_(sources)).limit(1)
    )
    return found is not None


async def drop_intoxicant(session: AsyncSession, key: int) -> None:
    for row in await stray_customs(session, key):
        await session.delete(row)


async def partnerless(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(BiologyRow).where(BiologyRow.partner_species_id.is_(None)).order_by(BiologyRow.holder_entity_id))
    return [row.holder_entity_id for row in rows if BiologyVariant.SYMBIOTIC.value in row.variants and "partner_species_id" not in row.locked]


async def name_partner(session: AsyncSession, key: int) -> None:
    row = await session.get(BiologyRow, key)
    if row is None:
        return
    atlas = await RegionAtlas.load(session)
    lands = sorted({region for town in await towns_of_people(session, key) if (region := atlas.top_region(town)) is not None})
    found = await session.scalar(
        select(SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.abundance > 0, SpeciesRangeRow.species_entity_id != key)
        .group_by(SpeciesRangeRow.species_entity_id)
        .order_by(func.sum(SpeciesRangeRow.abundance).desc(), SpeciesRangeRow.species_entity_id)
        .limit(1)
    )
    if found is not None:
        row.partner_species_id = int(found)
    else:
        row.variants = [value for value in row.variants if value != BiologyVariant.SYMBIOTIC.value]


async def ancestorless_revivals(session: AsyncSession) -> list[int]:
    return list(
        await session.scalars(
            select(LanguageProfileRow.entity_id)
            .where(LanguageProfileRow.stage == LanguageStage.REVIVED, LanguageProfileRow.parent_language_id.is_(None))
            .order_by(LanguageProfileRow.entity_id)
        )
    )


async def unrevive(session: AsyncSession, key: int) -> None:
    row = await session.get(LanguageProfileRow, key)
    if row is not None and row.parent_language_id is None:
        row.stage = LanguageStage.NATURAL


async def speaking_peoples(session: AsyncSession, language_id: int) -> list[int]:
    speakers = select(BondRow.source_node_id).where(BondRow.target_node_id == language_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    return list(
        await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(speakers), EntityRow.entity_type == EntityType.PEOPLE).order_by(EntityRow.id))
    )


async def unheard_tongues(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for profile in await session.scalars(select(LanguageProfileRow).order_by(LanguageProfileRow.entity_id)):
        peoples = await speaking_peoples(session, profile.entity_id)
        bodies = [(people, await body_functions(session, people)) for people in peoples]
        known = [(people, body) for people, body in bodies if body is not None]
        if known and not any([fits(profile.modality, body, await perceiving(session, people, body)) for people, body in known]):
            found.append(profile.entity_id)
    return found


async def settle_unheard(session: AsyncSession, key: int) -> None:
    row = await session.get(LanguageProfileRow, key)
    if row is None:
        return
    for people in await speaking_peoples(session, key):
        body = await body_functions(session, people)
        if body is not None:
            row.modality = suited(body, await perceiving(session, people, body))
            return


async def unpowered_records(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(WrittenWorkRow).where(WrittenWorkRow.medium == WritingMedium.ELECTRONIC).order_by(WrittenWorkRow.work_entity_id)):
        if "medium" in (row.locked or []):
            continue
        work = await session.get(EntityRow, row.work_entity_id)
        holders = [holder for holder in (work.id, work.location_id) if holder is not None] if work is not None else []
        known = await session.scalar(
            select(HolderTechniqueRow.holder_entity_id)
            .where(HolderTechniqueRow.holder_entity_id.in_(holders), HolderTechniqueRow.technique == Technique.COMPUTATION)
            .limit(1)
        )
        if known is None and not await era_knows(session, holders, Technique.COMPUTATION):
            found.append(row.work_entity_id)
    return found


async def era_knows(session: AsyncSession, holders: list[int], technique: Technique) -> bool:
    for holder in holders:
        if technique in await era_techniques(session, holder):
            return True
    return False


async def paper_record(session: AsyncSession, key: int) -> None:
    row = await session.get(WrittenWorkRow, key)
    if row is not None and row.medium is WritingMedium.ELECTRONIC:
        row.medium = WritingMedium.PAPER


async def sourceless_materials(session: AsyncSession) -> list[int]:
    return list(
        await session.scalars(
            select(WorldMaterialRow.id)
            .where(WorldMaterialRow.origin.in_(SOURCED_ORIGINS), WorldMaterialRow.source_node_id.is_(None))
            .order_by(WorldMaterialRow.id)
        )
    )


async def gift_material(session: AsyncSession, key: int) -> None:
    row = await session.get(WorldMaterialRow, key)
    if row is not None and row.source_node_id is None:
        row.origin = MaterialOrigin.CATALOG


async def stray_methods(session: AsyncSession) -> list[int]:
    return [
        row.id for row in await session.scalars(select(CommunityMethodRow).order_by(CommunityMethodRow.id)) if METHODS[row.method].process is not row.process
    ]


async def realign_method(session: AsyncSession, key: int) -> None:
    row = await session.get(CommunityMethodRow, key)
    if row is not None:
        row.process = METHODS[row.method].process


async def accountless_tellings(session: AsyncSession) -> list[int]:
    return list(
        await session.scalars(
            select(AccountRow.id)
            .where(AccountRow.collection_id.is_(None), AccountRow.incident_id.is_(None), AccountRow.subject_node_id.is_(None))
            .order_by(AccountRow.id)
        )
    )


async def tell_of_holder(session: AsyncSession, key: int) -> None:
    row = await session.get(AccountRow, key)
    if row is not None and row.subject_node_id is None:
        row.subject_node_id = row.holder_entity_id


async def unseasoned_routes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    rows = await session.execute(
        select(TradeRouteProfileRow, EntityRow.world_id)
        .join(EntityRow, EntityRow.id == TradeRouteProfileRow.route_entity_id)
        .where(TradeRouteProfileRow.status == TradeRouteStatus.SEASONAL)
        .order_by(TradeRouteProfileRow.route_entity_id)
    )
    for profile, world_id in rows.all():
        count = await session.scalar(select(func.count()).select_from(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id)) or 0
        if profile.closed_season is None or profile.closed_season >= count:
            found.append(profile.route_entity_id)
    return found


async def open_unseasoned(session: AsyncSession, key: int) -> None:
    row = await session.get(TradeRouteProfileRow, key)
    if row is not None and row.status is TradeRouteStatus.SEASONAL:
        row.status, row.closed_season = TradeRouteStatus.OPEN, None


async def misfit_carriers(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(TradeRouteProfileRow).where(TradeRouteProfileRow.carrier.is_not(None)).order_by(TradeRouteProfileRow.route_entity_id))
    return [row.route_entity_id for row in rows if row.carrier is not None and row.mode not in CARRIERS[row.carrier].modes]


async def unload_carrier(session: AsyncSession, key: int) -> None:
    row = await session.get(TradeRouteProfileRow, key)
    if row is not None and row.carrier is not None and row.mode not in CARRIERS[row.carrier].modes:
        row.carrier = None


async def unlinked_positioning(session: AsyncSession) -> list[int]:
    linked = select(NetworkNodeRow.member_node_id)
    return list(
        await session.scalars(
            select(NavigationKitRow.holder_entity_id)
            .where(NavigationKitRow.aid.in_(NETWORKED_AIDS), NavigationKitRow.holder_entity_id.not_in(linked))
            .order_by(NavigationKitRow.holder_entity_id)
        )
    )


async def drop_positioning(session: AsyncSession, key: int) -> None:
    for aid in NETWORKED_AIDS:
        row = await session.get(NavigationKitRow, (key, aid))
        if row is not None:
            await session.delete(row)
