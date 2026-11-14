from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.domain.enums.nature import PlantDefence
from aerona.rules.registry import Rules

Cover = dict[int, dict[PlantDefence, float]]


@memoized(SpeciesRangeRow, PlantProfileRow)
async def defence_cover(session: AsyncSession) -> Cover:
    found: Cover = defaultdict(dict)
    rows = await session.execute(
        select(SpeciesRangeRow.region_entity_id, SpeciesRangeRow.abundance, PlantProfileRow.defence, PlantProfileRow.defence_potency)
        .join(PlantProfileRow, PlantProfileRow.species_entity_id == SpeciesRangeRow.species_entity_id)
        .where(PlantProfileRow.defence != PlantDefence.NONE, SpeciesRangeRow.abundance > 0)
    )
    for region, abundance, defence, potency in rows:
        found[region][defence] = min(1.0, found[region].get(defence, 0.0) + abundance / PERCENT * potency / PERCENT)
    return dict(found)


async def cover_of(session: AsyncSession, region_id: int | None, defence: PlantDefence) -> float:
    return (await defence_cover(session)).get(region_id, {}).get(defence, 0.0) if region_id is not None else 0.0


def passage(rules: Rules, thorns: float) -> float:
    return 1 - thorns * rules.plant_defences.thorn_passage_pct / PERCENT


def grazing(rules: Rules, thorns: float) -> float:
    return 1 - thorns * rules.plant_defences.thorn_grazing_pct / PERCENT


def smothered(rules: Rules, allelopathy: float) -> float:
    return 1 - allelopathy * rules.plant_defences.allelopathy_pct / PERCENT


def poisoned_forage(rules: Rules, toxins: float) -> float:
    return toxins * rules.plant_defences.toxin_forage_pct / PERCENT
