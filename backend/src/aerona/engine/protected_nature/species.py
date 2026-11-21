from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.protected_nature import SpeciesProtectionRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import RangeTrend
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.protected_nature import ProtectionBasis, ProtectionMeasure
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import has_flag, living_entity
from aerona.engine.protected_nature.book import NatureTally, measures_of, protections_of
from aerona.engine.recording.record import record


async def protect_species(
    ctx: TickContext, species: EntityRow, basis: ProtectionBasis, measures: list[ProtectionMeasure], tally: NatureTally, *, holder: int | None = None
) -> SpeciesProtectionRow:
    found = next((row for row in await protections_of(ctx.session, species.id) if row.holder_node_id == holder), None)
    row = found or SpeciesProtectionRow(species_entity_id=species.id, holder_node_id=holder, since_epoch=ctx.epoch, locked=[])
    if "measures" not in (row.locked or []):
        row.measures = sorted({*(row.measures or []), *(measure.value for measure in measures)})
    row.basis = basis
    if found is None:
        row.endangered_at_start = await has_flag(ctx.session, species.id, EntityFlag.ENDANGERED)
        ctx.session.add(row)
    await ctx.session.flush()
    tally.species += 1
    await record(
        ctx,
        "nature.species_protected",
        roles={IncidentRole.SUBJECT: species.id, IncidentRole.ACTOR: holder},
        facts={"basis": basis, "measures": ", ".join(measure.value.replace("_", " ") for measure in measures) or "nothing"},
    )
    return row


async def left_lands(ctx: TickContext, species_id: int) -> list[SpeciesRangeRow]:
    query = select(SpeciesRangeRow).where(
        SpeciesRangeRow.species_entity_id == species_id, SpeciesRangeRow.abundance <= 0, SpeciesRangeRow.fit >= ctx.rules.protected_nature.habitat_fit
    )
    return list(await ctx.session.scalars(query.order_by(SpeciesRangeRow.region_entity_id)))


async def reintroduce(ctx: TickContext, species: EntityRow, region: int, tally: NatureTally, *, by: int | None = None) -> bool:
    table = ctx.rules.protected_nature
    row = await ctx.session.get(SpeciesRangeRow, (species.id, region))
    if row is None or row.abundance > 0 or row.fit < table.habitat_fit or held(region) or "abundance" in (row.locked or []):
        return False
    if not ctx.rng(f"nature.reintroduce.{species.id}.{region}.{ctx.epoch}").chance(table.reintroduction_success_pct):
        return False
    row.abundance, row.trend, row.since_epoch = table.reintroduced_abundance, RangeTrend.RISING, ctx.epoch
    tally.reintroduced += 1
    await record(
        ctx,
        "nature.species_reintroduced",
        roles={IncidentRole.SUBJECT: species.id, IncidentRole.PLACE: region, IncidentRole.ACTOR: by},
        facts={"abundance": row.abundance},
        place=region,
    )
    return True


async def breed(ctx: TickContext, species_id: int) -> None:
    gain = ctx.rules.protected_nature.recovery_per_epoch
    for row in list(await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == species_id, SpeciesRangeRow.abundance > 0))):
        if "abundance" not in (row.locked or []):
            row.abundance = clamp_int(row.abundance + max(1, row.abundance * gain // PERCENT), 0, PERCENT)


async def guard_habitat(ctx: TickContext, species_id: int) -> None:
    gain = ctx.rules.protected_nature.recovery_per_epoch // 2
    regions = await ctx.session.scalars(
        select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species_id, SpeciesRangeRow.abundance > 0)
    )
    for region in sorted(set(regions)):
        land = await ctx.session.get(RegionEnvironmentRow, region)
        if land is not None and not held(region) and "forest_cover" not in (land.locked or []):
            land.forest_cover = clamp_int(min(land.base_forest, land.forest_cover + gain), 0, PERCENT)


async def tend_species(ctx: TickContext, tally: NatureTally) -> None:
    for row in list(await ctx.session.scalars(select(SpeciesProtectionRow).order_by(SpeciesProtectionRow.id))):
        species = await living_entity(ctx.session, row.species_entity_id)
        if species is None or held(species.id):
            continue
        measures = measures_of(row)
        if ProtectionMeasure.BREEDING_PROGRAMME in measures:
            await breed(ctx, species.id)
        if ProtectionMeasure.HABITAT_GUARD in measures:
            await guard_habitat(ctx, species.id)
        if ProtectionMeasure.REINTRODUCTION in measures:
            target = next(iter(await left_lands(ctx, species.id)), None)
            if target is not None:
                await reintroduce(ctx, species, target.region_entity_id, tally, by=row.holder_node_id)
        if row.endangered_at_start and row.recovered_epoch is None and not await has_flag(ctx.session, species.id, EntityFlag.ENDANGERED):
            row.recovered_epoch = ctx.epoch
            tally.recovered += 1
            await record(ctx, "nature.species_recovered", roles={IncidentRole.SUBJECT: species.id}, facts={"epochs": ctx.epoch - row.since_epoch})
