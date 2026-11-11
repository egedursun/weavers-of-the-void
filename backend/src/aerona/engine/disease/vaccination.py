from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import ImmunityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat
from aerona.rules.registry import Rules


@dataclass
class VaccinationTally:
    variolated: int = 0
    vaccinated: int = 0


def protection(rules: Rules, *, vaccine: bool) -> int:
    table = rules.vaccination
    return table.immune_gain if vaccine else round_half_up(table.immune_gain * table.variolation_pct / PERCENT)


async def protect(ctx: TickContext, book: DiseaseBook, community: EntityRow, disease_id: int, gain: int) -> int:
    raised = 0
    for band in AgeBand:
        row = book.immunity.get((community.id, disease_id), {}).get(band)
        if row is None:
            row = ImmunityRow(community_entity_id=community.id, disease_entity_id=disease_id, age_band=band, immune_pct=0, since_epoch=ctx.epoch, locked=False)
            ctx.session.add(row)
            book.immunity.setdefault((community.id, disease_id), {})[band] = row
        if row.locked or row.immune_pct >= PERCENT:
            continue
        row.immune_pct = clamp_int(row.immune_pct + gain, 0, PERCENT)
        row.since_epoch = ctx.epoch
        raised += 1
    return raised


async def vaccinate(ctx: TickContext, tally: VaccinationTally) -> None:
    table = ctx.rules.vaccination
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    near: dict[int, set[int]] = {}
    for outbreak in book.outbreaks:
        for region in [outbreak.region_entity_id, *book.atlas.neighbour_regions(outbreak.region_entity_id)]:
            near.setdefault(region, set()).add(outbreak.disease_entity_id)
    for community in await canon(ctx.session, SOCIETY_TYPES):
        if community.id not in book.inoculated or held(community.id):
            continue
        vaccine = book.medicine.get(community.id, 0) >= ctx.rules.carriers.theory_truth
        gain = protection(ctx.rules, vaccine=vaccine)
        for disease_id in sorted(near.get(book.atlas.top_region(community.id) or -1, set())):
            profile = book.profiles.get(disease_id)
            if profile is None or held(disease_id) or not await protect(ctx, book, community, disease_id, gain):
                continue
            if vaccine:
                tally.vaccinated += 1
            else:
                tally.variolated += 1
                with flowing(FlowCategory.PLAGUE):
                    scale_stat(ctx.rules, community, POPULATION_KEY, 1 - table.risk_pct / PERCENT * gain / PERCENT * profile.lethality / PERCENT)
    await ctx.session.flush()
