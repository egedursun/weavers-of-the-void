from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import BODILY_DWELLING_KEYS
from aerona.catalog.plants import PARTS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesProductRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.households import DwellingRow, HouseholdRow
from aerona.db.tables.kin import WillHeirRow, WillRow
from aerona.db.tables.plants import PlantPartRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.domain.enums.body import InjuryState
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.engine.body.book import anatomy_for
from aerona.engine.body.customs import people_of
from aerona.engine.households.dwelling_kinds import dwelling_of_people
from aerona.engine.households.homes import born_dwelling, settled_kind
from aerona.rules.registry import Rules


async def landless_areas(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(ProtectedAreaRow).where(ProtectedAreaRow.lifted_epoch.is_(None)).order_by(ProtectedAreaRow.id)):
        region = await session.get(EntityRow, row.region_entity_id)
        if region is None or region.entity_type is not EntityType.REGION:
            found.append(row.id)
    return found


async def lift_landless(session: AsyncSession, key: int) -> None:
    row = await session.get(ProtectedAreaRow, key)
    if row is not None:
        row.lifted_epoch = row.since_epoch


async def kindless_protections(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(SpeciesProtectionRow).order_by(SpeciesProtectionRow.id)):
        species = await session.get(EntityRow, row.species_entity_id)
        if species is None or species.entity_type is not EntityType.SPECIES:
            found.append(row.id)
    return found


async def drop_protection(session: AsyncSession, key: int) -> None:
    row = await session.get(SpeciesProtectionRow, key)
    if row is not None:
        await session.delete(row)


async def stray_aims(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(ConservationMovementRow).order_by(ConservationMovementRow.movement_entity_id)):
        movement = await session.get(MovementProfileRow, row.movement_entity_id)
        if movement is None or movement.cause is not MovementCause.CONSERVATION:
            found.append(row.movement_entity_id)
    return found


async def drop_aims(session: AsyncSession, key: int) -> None:
    row = await session.get(ConservationMovementRow, key)
    if row is not None:
        await session.delete(row)


async def unsourced_products(session: AsyncSession) -> list[int]:
    parts: dict[int, set[ProductPart]] = defaultdict(set)
    for species_id, part in await session.execute(select(PlantPartRow.species_entity_id, PlantPartRow.part).order_by(PlantPartRow.id)):
        parts[species_id] |= PARTS[part].yields
    found: set[int] = set()
    for row in await session.scalars(
        select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id.in_(sorted(parts))).order_by(SpeciesProductRow.species_entity_id)
    ):
        if row.part is not None and row.part not in parts[row.species_entity_id]:
            found.add(row.species_entity_id)
    return sorted(found)


async def strike_unsourced_products(session: AsyncSession, key: int) -> None:
    sourced = set().union(*(PARTS[part].yields for part in await session.scalars(select(PlantPartRow.part).where(PlantPartRow.species_entity_id == key))))
    for row in list(await session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == key).order_by(SpeciesProductRow.product))):
        if row.part is not None and row.part not in sourced and "part" not in (row.locked or []):
            await session.delete(row)


async def uncarried_outbreaks(session: AsyncSession) -> list[int]:
    hosted = set(await session.scalars(select(DiseaseProfileRow.disease_entity_id).where(DiseaseProfileRow.host_species_id.is_not(None))))
    hosted |= set(await session.scalars(select(SpeciesHostRow.disease_entity_id).where(SpeciesHostRow.immune.is_(False))))
    rivers = set(await session.scalars(select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.river_class != RiverClass.NONE)))
    carried = select(OutbreakRow).where(OutbreakRow.path.in_([SpreadPath.WILDLIFE, SpreadPath.WATERWAY])).order_by(OutbreakRow.id)
    found: list[int] = []
    for outbreak in await session.scalars(carried):
        if outbreak.path is SpreadPath.WILDLIFE:
            if outbreak.disease_entity_id not in hosted:
                found.append(outbreak.id)
            continue
        source = await session.get(OutbreakRow, outbreak.source_outbreak_id) if outbreak.source_outbreak_id is not None else None
        if source is None or source.region_entity_id not in rivers:
            found.append(outbreak.id)
    return found


async def ground_outbreak(session: AsyncSession, key: int) -> None:
    row = await session.get(OutbreakRow, key)
    if row is not None and "path" not in row.locked:
        row.path = SpreadPath.ORIGIN


async def strayed_wounds(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for injury, body in await session.execute(select(InjuryRow, BodyRow).join(BodyRow, BodyRow.node_id == InjuryRow.bearer_node_id).order_by(InjuryRow.id)):
        if anatomy_for(body).part(injury.part) is None and injury.state is not InjuryState.HEALED_SCAR:
            found.append(injury.id)
    return found


async def settle_strayed_wound(session: AsyncSession, key: int) -> None:
    row = await session.get(InjuryRow, key)
    if row is not None:
        row.state = InjuryState.HEALED_SCAR


async def unbalanced_wills(session: AsyncSession) -> list[int]:
    totals: dict[int, int] = defaultdict(int)
    for will_id, share in await session.execute(select(WillHeirRow.will_id, WillHeirRow.share).order_by(WillHeirRow.will_id)):
        totals[will_id] += share
    wills = await session.scalars(select(WillRow.id).order_by(WillRow.id))
    return [will_id for will_id in wills if totals.get(will_id, 0) != PERCENT]


async def balance_will(session: AsyncSession, key: int) -> None:
    lines = list(await session.scalars(select(WillHeirRow).where(WillHeirRow.will_id == key).order_by(WillHeirRow.heir_node_id)))
    if not lines:
        will = await session.get(WillRow, key)
        if will is not None:
            await session.delete(will)
        return
    total = sum(line.share for line in lines) or 1
    for line in lines:
        line.share = max(1, line.share * PERCENT // total)
    lines[0].share += PERCENT - sum(line.share for line in lines)


async def unfit_dwellings(session: AsyncSession) -> list[int]:
    found: list[int] = []
    rows = await session.execute(
        select(DwellingRow, HouseholdRow, DwellingKindRow)
        .join(HouseholdRow, HouseholdRow.id == DwellingRow.household_id)
        .join(DwellingKindRow, DwellingKindRow.id == DwellingRow.dwelling_kind_id)
        .order_by(DwellingRow.id)
    )
    for dwelling, household, kind in rows:
        if kind.built_in_key not in BORN_KEYS or "dwelling_kind_id" in (dwelling.locked or []) or household.head_node_id is None:
            continue
        head = await session.get(EntityRow, household.head_node_id)
        if head is not None and await born_dwelling(session, head) != kind.built_in_key:
            found.append(dwelling.id)
    return found


async def refit_dwelling(session: AsyncSession, key: int) -> None:
    dwelling = await session.get(DwellingRow, key)
    household = await session.get(HouseholdRow, dwelling.household_id) if dwelling is not None else None
    head = await session.get(EntityRow, household.head_node_id) if household is not None and household.head_node_id is not None else None
    if dwelling is None or head is None:
        return
    people = await people_of(session, head)
    kind = await dwelling_of_people(session, people.id if people is not None else None, await settled_kind(session, Rules(), head))
    dwelling.dwelling_kind_id = kind.id


BORN_KEYS = BODILY_DWELLING_KEYS
