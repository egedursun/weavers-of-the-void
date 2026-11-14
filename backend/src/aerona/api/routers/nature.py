from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.nature import (
    DefenceCoverView,
    FermentCultureView,
    FolkNatureView,
    KindBondView,
    KindNatureView,
    NatureNodeView,
    PlantNatureView,
    SenseView,
    SoilLifeView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.nature import FermentCultureRow, SenseProfileRow, SoilMicrobiotaRow, SpeciesRelationRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.engine.nature.cover import defence_cover
from aerona.engine.nature.microbes import keepers_in, microbe_factor
from aerona.engine.nature.seasons import activity, asleep, band_at, region_of
from aerona.engine.nature.senses import sense_holder
from aerona.engine.nature.sleepers import awake_now

router = APIRouter(tags=["nature"])
NodeId = Annotated[int, Path(ge=1)]
KEEPERS = (EntityType.FACTION, EntityType.STRUCTURE, EntityType.HOUSE)


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def culture_rows(session: AsyncSession, entity: EntityRow | None) -> list[FermentCultureRow]:
    if entity is None:
        return []
    if entity.entity_type is EntityType.SETTLEMENT:
        holders = await keepers_in(session, entity.id)
    elif entity.entity_type in KEEPERS:
        holders = [entity.id]
    elif entity.entity_type is EntityType.MORTAL and entity.location_id is not None:
        holders = await keepers_in(session, entity.location_id)
    else:
        return []
    return list(await session.scalars(select(FermentCultureRow).where(FermentCultureRow.holder_entity_id.in_(holders)).order_by(FermentCultureRow.id)))


@router.get("/nature/of/{node_id}", response_model=NatureNodeView)
async def node_nature(services: ServicesDep, node_id: NodeId) -> NatureNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).get()
        epoch = cosmos.epoch if cosmos is not None else 0
        entity = await session.get(EntityRow, node_id)
        region = await region_of(session, node_id)
        band = await band_at(session, rules, epoch, node_id)
        profile = await session.get(SpeciesProfileRow, node_id)
        biology = await session.get(PeopleBiologyRow, node_id)
        plant = await session.get(PlantProfileRow, node_id)
        holder = await sense_holder(session, node_id)
        senses = (
            list(await session.scalars(select(SenseProfileRow).where(SenseProfileRow.holder_entity_id == holder).order_by(SenseProfileRow.sense)))
            if holder
            else []
        )
        if profile is not None:
            bonds = select(SpeciesRelationRow).where((SpeciesRelationRow.first_species_id == node_id) | (SpeciesRelationRow.second_species_id == node_id))
        elif entity is not None and entity.entity_type is EntityType.REGION:
            present = select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == node_id, SpeciesRangeRow.abundance > 0)
            bonds = select(SpeciesRelationRow).where(SpeciesRelationRow.first_species_id.in_(present), SpeciesRelationRow.second_species_id.in_(present))
        else:
            bonds = select(SpeciesRelationRow).where(SpeciesRelationRow.id.is_(None))
        bond_rows = list(await session.scalars(bonds.order_by(SpeciesRelationRow.id)))
        soil = await session.get(SoilMicrobiotaRow, node_id)
        cover = (await defence_cover(session)).get(node_id, {})
        cultures = await culture_rows(session, entity)
        named = {node_id, *(item for item in (region, holder) if item is not None), *(row.holder_entity_id for row in cultures)}
        named |= {item for row in bond_rows for item in (row.first_species_id, row.second_species_id)}
        refs = await node_refs(session, sorted(named))
    return NatureNodeView(
        node=ref(refs, node_id),
        region=refs.get(region) if region is not None else None,
        season_band=band,
        kind_profile=KindNatureView(
            dormancy=profile.dormancy,
            thermoregulation=profile.thermoregulation,
            woken_epoch=profile.woken_epoch,
            endemic=profile.endemic,
            relict=profile.relict,
            island_epochs=profile.island_epochs,
            range_peak=profile.range_peak,
            asleep_now=asleep(profile.dormancy, band) and not awake_now(profile, epoch),
            activity_pct=round(activity(rules, profile.thermoregulation, band) * PERCENT),
            locked=profile.locked,
        )
        if profile is not None
        else None,
        folk_profile=FolkNatureView(
            thermoregulation=biology.thermoregulation, activity_pct=round(activity(rules, biology.thermoregulation, band) * PERCENT), locked=biology.locked
        )
        if biology is not None
        else None,
        plant=PlantNatureView(defence=plant.defence, defence_potency=plant.defence_potency, locked=plant.locked) if plant is not None else None,
        sense_holder=refs.get(holder) if holder is not None else None,
        senses=[SenseView(sense=row.sense, acuity=row.acuity, locked=row.locked) for row in senses],
        bonds=[
            KindBondView(
                id=row.id,
                first=ref(refs, row.first_species_id),
                second=ref(refs, row.second_species_id),
                kind=row.kind,
                strength=row.strength,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in bond_rows
        ],
        soil=SoilLifeView(
            life=soil.life,
            sterile_epochs=soil.sterile_epochs,
            updated_epoch=soil.updated_epoch,
            recycling_pct=round(microbe_factor(rules, soil.life) * PERCENT),
            locked=soil.locked,
        )
        if soil is not None
        else None,
        defences=[
            DefenceCoverView(defence=defence, cover_pct=round(share * PERCENT)) for defence, share in sorted(cover.items(), key=lambda item: item[0].value)
        ],
        cultures=[
            FermentCultureView(
                id=row.id,
                holder=ref(refs, row.holder_entity_id),
                kind=row.kind,
                quality=row.quality,
                since_epoch=row.since_epoch,
                lost_epoch=row.lost_epoch,
                locked=row.locked,
            )
            for row in cultures
        ],
    )
