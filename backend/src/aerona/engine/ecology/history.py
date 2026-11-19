from collections import defaultdict

from sqlalchemy import select

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.evolution import SpeciesTraitRow, TraitHistoryRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.lore.history import scope_incident
from aerona.engine.primitives.numbers import round_half_up

PATHOGEN_TRAITS = ("virulence", "lethality", "cold_tolerance", "heat_tolerance", "resistance")


async def keep_points(ctx: TickContext, points: dict[tuple[int, str], int]) -> None:
    holders = sorted({holder for holder, _ in points})
    if not holders:
        return
    stored = {
        (row.holder_entity_id, row.trait): row
        for row in await ctx.session.scalars(select(TraitHistoryRow).where(TraitHistoryRow.epoch == ctx.epoch, TraitHistoryRow.holder_entity_id.in_(holders)))
    }
    for (holder_id, trait), value in sorted(points.items()):
        row = stored.get((holder_id, trait))
        if row is None:
            ctx.session.add(TraitHistoryRow(holder_entity_id=holder_id, trait=trait, epoch=ctx.epoch, value=value, incident_id=scope_incident()))
        else:
            row.value = value


async def record_species(ctx: TickContext, rows: list[SpeciesTraitRow]) -> int:
    means: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in rows:
        if not held(row.species_entity_id):
            means[(row.species_entity_id, row.trait.value)].append(row.mean)
    await keep_points(ctx, {key: round_half_up(sum(values) / len(values)) for key, values in means.items()})
    await ctx.session.flush()
    return len(means)


async def record_pathogen(ctx: TickContext, profile: DiseaseProfileRow) -> None:
    if held(profile.disease_entity_id):
        return
    await keep_points(ctx, {(profile.disease_entity_id, trait): int(getattr(profile, trait)) for trait in PATHOGEN_TRAITS})
