from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.depth_society import AfflictionView, HostView, IncidentRefView, NamedMortalView
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.disease import DiseaseTarget, OutbreakStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.demography.promotion import DORMANT_KEY, MAIMED_KEY
from aerona.engine.disease.sickness import SICK_KEY
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules

COMMUNITY_HOLDS = (SICK_KEY, MAIMED_KEY)


def unseen_pct(rules: Rules, profile: DiseaseProfileRow | None, outbreak: OutbreakRow | None, epoch: int) -> int:
    if profile is None or (outbreak is not None and epoch - outbreak.started_epoch > 1):
        return 0
    return min(PERCENT, profile.incubation * rules.epidemiology.incubation_hidden_pct)


async def incident_views(session: AsyncSession, ids: list[int]) -> list[IncidentRefView]:
    if not ids:
        return []
    rows = await session.execute(
        select(IncidentRow, ChronicleRow.text)
        .outerjoin(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(IncidentRow.id.in_(ids))
        .order_by(IncidentRow.epoch, IncidentRow.id)
    )
    return [
        IncidentRefView(id=row.id, epoch=row.epoch, year=row.year, kind=row.kind, text=text or row.note or row.kind, place_id=row.place_entity_id)
        for row, text in rows
    ]


async def disease_incidents(session: AsyncSession, disease_id: int, origin_id: int | None) -> list[IncidentRefView]:
    ids = set(await session.scalars(select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == disease_id)))
    if origin_id is not None:
        ids.add(origin_id)
    return await incident_views(session, sorted(ids))


async def host_views(session: AsyncSession, profile: DiseaseProfileRow) -> list[HostView]:
    links = {
        row.species_entity_id: row.immune
        for row in await session.scalars(select(SpeciesHostRow).where(SpeciesHostRow.disease_entity_id == profile.disease_entity_id))
    }
    if profile.host_species_id is not None:
        links.setdefault(profile.host_species_id, False)
    if not links:
        return []
    species = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(links))))}
    ranges: dict[int, list[int]] = {}
    for row in await session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id.in_(list(links)), SpeciesRangeRow.abundance > 0)):
        ranges.setdefault(row.species_entity_id, []).append(row.abundance)
    return [
        HostView(
            species_id=species_id,
            name=species[species_id].name if species_id in species else "",
            immune=immune,
            lands=len(ranges.get(species_id, [])),
            abundance=max(ranges.get(species_id, [0])) if species.get(species_id) is not None and species[species_id].status is EntityStatus.CANON else 0,
            primary=species_id == profile.host_species_id,
        )
        for species_id, immune in sorted(links.items())
    ]


async def disease_sick(session: AsyncSession, disease_id: int) -> int:
    atlas = await RegionAtlas.load(session)
    regions = set(
        await session.scalars(
            select(OutbreakRow.region_entity_id).where(OutbreakRow.disease_entity_id == disease_id, OutbreakRow.status != OutbreakStatus.ENDED)
        )
    )
    communities = [community for region in regions for community in atlas.communities_in(region)]
    if not communities:
        return 0
    rows = await session.scalars(select(CohortRow.count).where(CohortRow.community_entity_id.in_(communities), CohortRow.condition == CohortCondition.SICK))
    return sum(rows)


async def afflictions(session: AsyncSession, community_id: int) -> list[AfflictionView]:
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(community_id)
    if region is None:
        return []
    statement = (
        select(OutbreakRow, DiseaseProfileRow, EntityRow.name)
        .join(DiseaseProfileRow, DiseaseProfileRow.disease_entity_id == OutbreakRow.disease_entity_id)
        .join(EntityRow, EntityRow.id == OutbreakRow.disease_entity_id)
        .where(OutbreakRow.region_entity_id == region, OutbreakRow.status != OutbreakStatus.ENDED)
        .order_by(OutbreakRow.id)
    )
    return [
        AfflictionView(
            disease_id=profile.disease_entity_id,
            disease=name,
            vector=profile.vector,
            target_functions=[DiseaseTarget(item) for item in profile.target_functions if item in DiseaseTarget._value2member_map_],
            severity=outbreak.severity,
            status=outbreak.status,
            outbreak_id=outbreak.id,
        )
        for outbreak, profile, name in await session.execute(statement)
    ]


async def named_mortals(session: AsyncSession, community_id: int) -> list[NamedMortalView]:
    members = select(BondRow.source_node_id).where(
        BondRow.target_node_id == community_id, BondRow.kind.in_([BondKind.LIVES_IN, BondKind.MEMBER_OF]), BondRow.state == BondState.ACTIVE
    )
    mortals = list(
        await session.scalars(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                or_(EntityRow.location_id == community_id, EntityRow.id.in_(members)),
            )
            .order_by(EntityRow.importance.desc(), EntityRow.id)
        )
    )
    ids = [mortal.id for mortal in mortals]
    if not ids:
        return []
    dormant = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DORMANT, EntityFlagRow.entity_id.in_(ids))))
    held = set(
        await session.scalars(
            select(ModifierRow.target_node_id).where(
                ModifierRow.source_kind == ModifierSource.PIN, ModifierRow.target_key == DORMANT_KEY, ModifierRow.target_node_id.in_(ids)
            )
        )
    )
    return [
        NamedMortalView(id=mortal.id, name=mortal.name, dormant=mortal.id in dormant, held=mortal.id in held, importance=mortal.importance or 0)
        for mortal in mortals
    ]


async def community_holds(session: AsyncSession, community_id: int) -> list[str]:
    return sorted(
        set(
            await session.scalars(
                select(ModifierRow.target_key).where(
                    ModifierRow.source_kind == ModifierSource.PIN, ModifierRow.target_node_id == community_id, ModifierRow.target_key.in_(COMMUNITY_HOLDS)
                )
            )
        )
    )
