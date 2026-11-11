from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import HerdRow, SpeciesHostRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import SpreadPath
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.carriers import folk_by_region
from aerona.engine.disease.emergence import new_strain
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.notes import note
from aerona.rules.registry import Rules

HARD_HUNT = 10


@dataclass
class SpilloverTally:
    jumped: int = 0


def jump_chance(rules: Rules, land: RegionEnvironmentRow | None, hunted: int, herded: bool) -> float:
    table = rules.spillover
    chance = float(table.base_pct)
    if land is not None:
        chance += land.cleared / PERCENT * table.cleared_pct
    chance += min(1.0, hunted / HARD_HUNT) * table.hunted_pct
    if herded:
        chance += table.herd_pct
    return chance


async def spill(ctx: TickContext, tally: SpilloverTally) -> None:
    table = ctx.rules.spillover
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    folk = await folk_by_region(ctx, book)
    herded: dict[int, set[int]] = defaultdict(set)
    for herd in await ctx.session.scalars(select(HerdRow)):
        region = book.atlas.top_region(herd.community_entity_id)
        if region is not None:
            herded[region].add(herd.community_entity_id)
    hosts = list(
        await ctx.session.execute(
            select(SpeciesHostRow.species_entity_id, SpeciesHostRow.disease_entity_id)
            .where(SpeciesHostRow.immune.is_(False))
            .order_by(SpeciesHostRow.disease_entity_id, SpeciesHostRow.species_entity_id)
        )
    )
    for species_id, disease_id in hosts:
        disease = book.diseases.get(disease_id)
        if disease is None or held(disease_id, species_id):
            continue
        for row in await ctx.session.scalars(
            select(SpeciesRangeRow)
            .where(SpeciesRangeRow.species_entity_id == species_id, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.region_entity_id)
        ):
            if tally.jumped >= table.per_epoch:
                return
            region_id = row.region_entity_id
            if not folk.get(region_id) or held(region_id) or book.active_of(disease_id, region_id) is not None:
                continue
            land = await ctx.session.get(RegionEnvironmentRow, region_id)
            chance = jump_chance(ctx.rules, land, row.hunted, bool(herded.get(region_id))) * row.abundance / PERCENT
            if not ctx.rng(f"spillover.{disease_id}.{species_id}.{region_id}").chance(chance):
                continue
            land_row = await ctx.session.get(EntityRow, region_id)
            jumped = await new_strain(ctx, book, disease, land_row) if land_row is not None else None
            await open_outbreak(ctx, book, jumped or disease, region_id, path=SpreadPath.ORIGIN, severity=table.severity)
            tally.jumped += 1
            species = await ctx.session.get(EntityRow, species_id)
            if species is not None and land_row is not None:
                await note(
                    ctx,
                    f"{(jumped or disease).name} passed from {species.name} to the folk of {land_row.name}.",
                    key="disease.spillover",
                    ids=[(jumped or disease).id, species.id, land_row.id],
                )
