from collections import defaultdict

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.evolution import SpeciesTraitRow, TraitHistoryRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.lore.history import scope_incident
from aerona.engine.primitives.numbers import round_half_up

PATHOGEN_TRAITS = ("virulence", "lethality", "cold_tolerance", "heat_tolerance", "resistance")


async def keep_point(ctx: TickContext, holder_id: int, trait: str, value: int) -> None:
    row = await ctx.session.get(TraitHistoryRow, (holder_id, trait, ctx.epoch))
    if row is None:
        ctx.session.add(TraitHistoryRow(holder_entity_id=holder_id, trait=trait, epoch=ctx.epoch, value=value, incident_id=scope_incident()))
    else:
        row.value = value


async def record_species(ctx: TickContext, rows: list[SpeciesTraitRow]) -> int:
    means: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in rows:
        if not held(row.species_entity_id):
            means[(row.species_entity_id, row.trait.value)].append(row.mean)
    for (species_id, trait), values in sorted(means.items()):
        await keep_point(ctx, species_id, trait, round_half_up(sum(values) / len(values)))
    await ctx.session.flush()
    return len(means)


async def record_pathogen(ctx: TickContext, profile: DiseaseProfileRow) -> None:
    if held(profile.disease_entity_id):
        return
    for trait in PATHOGEN_TRAITS:
        await keep_point(ctx, profile.disease_entity_id, trait, int(getattr(profile, trait)))
