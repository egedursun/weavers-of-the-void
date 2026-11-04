from sqlalchemy import select

from aerona.db.tables.ecology import SpeciesHostRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext


async def link_hosts(ctx: TickContext, disease: EntityRow, region_id: int, host: EntityRow | None) -> int:
    carriers = {host.id} if host is not None and host.entity_type is EntityType.SPECIES else set()
    bearers = select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.PLAGUE_BEARER)
    carriers |= set(
        await ctx.session.scalars(
            select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.species_entity_id.in_(bearers))
        )
    )
    linked = 0
    for species_id in sorted(carriers):
        if await ctx.session.get(SpeciesHostRow, (species_id, disease.id)) is None:
            ctx.session.add(SpeciesHostRow(species_entity_id=species_id, disease_entity_id=disease.id, immune=False))
            linked += 1
    return linked
