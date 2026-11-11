from collections import defaultdict
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import COLD_BANDS, WARM_BANDS, new_strain
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or

INCUBATION_MAX = 20


@dataclass
class PathogenTally:
    milder: int = 0
    spreading: int = 0
    resistant: int = 0
    escaped: int = 0
    adapted: int = 0


def nudge(profile: DiseaseProfileRow, key: str, step: int) -> bool:
    if key in profile.locked:
        return False
    before = int(getattr(profile, key))
    after = clamp_int(before + step, 0, PERCENT)
    setattr(profile, key, after)
    return after != before


async def evolve_pathogens(ctx: TickContext, tally: PathogenTally) -> None:
    table = ctx.rules.pathogen_evolution
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    folk: dict[int, list[EntityRow]] = defaultdict(list)
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = book.atlas.top_region(community.id)
        if region is not None:
            folk[region].append(community)
    regions: dict[int, list[int]] = defaultdict(list)
    for outbreak in book.outbreaks:
        regions[outbreak.disease_entity_id].append(outbreak.region_entity_id)
    for disease_id, lands in sorted(regions.items()):
        disease = book.diseases.get(disease_id)
        profile = book.profiles.get(disease_id)
        if disease is None or profile is None or held(disease_id):
            continue
        hosts = [community for land in lands for community in folk.get(land, [])]
        people = sum(stat_or(community, "population", 0) for community in hosts) / max(1, len(lands))
        if people < table.sparse_population and nudge(profile, "lethality", -table.lethality_drop):
            tally.milder += 1
        if people < table.sparse_population and "incubation" not in profile.locked and profile.incubation < INCUBATION_MAX:
            profile.incubation = min(INCUBATION_MAX, profile.incubation + table.incubation_step)
        if people > table.crowd_population and nudge(profile, "virulence", table.transmission_gain):
            tally.spreading += 1
        treated = any(
            book.cured(disease_id, community.id) or community.id in book.tended or book.hospital_strength.get(land, 0.0) > 0
            for land in lands
            for community in folk.get(land, [])
        )
        if treated and nudge(profile, "resistance", table.resistance_gain):
            tally.resistant += 1
        grounds = [ground for ground in [await ctx.session.get(RegionEnvironmentRow, land) for land in lands] if ground is not None]
        cold = sum(1 for ground in grounds if ground.temperature_band in COLD_BANDS)
        warm = sum(1 for ground in grounds if ground.temperature_band in WARM_BANDS)
        if (cold > warm and nudge(profile, "cold_tolerance", table.climate_step)) or (warm > cold and nudge(profile, "heat_tolerance", table.climate_step)):
            tally.adapted += 1
        immune = [book.immune_share(community.id, disease_id) for community in hosts]
        share = round_half_up(sum(immune) / len(immune) * PERCENT) if immune else 0
        if share >= table.escape_immune_pct and ctx.rng(f"immune_escape.{disease_id}").chance(table.escape_pct):
            land = await ctx.session.get(EntityRow, sorted(lands)[0])
            strain = await new_strain(ctx, book, disease, land) if land is not None else None
            if strain is not None and land is not None:
                tally.escaped += 1
                await note(
                    ctx,
                    f"{disease.name} changed past the immunity of {land.name}; {strain.name} spreads where the old sickness could not.",
                    key="disease.immune_escape",
                    ids=[disease.id, strain.id, land.id],
                )
    await ctx.session.flush()
