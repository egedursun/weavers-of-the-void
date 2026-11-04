from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.ecology.ranges import Wilds


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
            ctx.session.add(SpeciesHostRow(species_entity_id=species_id, disease_entity_id=disease.id, immune=False, locked=[]))
            linked += 1
    return linked


async def acquire_immunity(ctx: TickContext, wilds: Wilds) -> int:
    table = ctx.rules.habitat
    grown = 0
    raging: dict[int, set[int]] = defaultdict(set)
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
        raging[outbreak.disease_entity_id].add(outbreak.region_entity_id)
    for host in list(await ctx.session.scalars(select(SpeciesHostRow).where(SpeciesHostRow.immune.is_(False)).order_by(SpeciesHostRow.species_entity_id))):
        if "immune" in host.locked or not raging.get(host.disease_entity_id, set()) & set(wilds.ranges.get(host.species_entity_id, {})):
            continue
        hardy = CreatureTrait.REGENERATING in wilds.traits.get(host.species_entity_id, set())
        chance = min(PERCENT, table.immunity_chance * (2 if hardy else 1))
        if ctx.rng(f"immunity.{host.species_entity_id}.{host.disease_entity_id}.{ctx.epoch}").chance(chance):
            host.immune = True
            grown += 1
    return grown
