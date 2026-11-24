from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.evolution import PLANT_EATERS
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.nature import PlantDefence, SymbiosisKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.nature.cover import defence_cover
from aerona.engine.nature.symbiosis import SymbiosisBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record


@dataclass
class PlantTally:
    dangerous: int = 0
    medicine: int = 0


async def guard_plants(ctx: TickContext, region_id: int, cover: float, book: SymbiosisBook) -> None:
    present = {
        row.species_entity_id: row
        for row in await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0))
    }
    guarded = {row.species_entity_id for row in await ctx.session.scalars(select(PlantProfileRow).where(PlantProfileRow.defence == PlantDefence.GUARDIANS))}
    allies = {
        (relation.second_species_id if relation.first_species_id == plant else relation.first_species_id)
        for plant in sorted(guarded & set(present))
        for relation in book.of_species.get(plant, [])
        if relation.kind is SymbiosisKind.MUTUALISM
    }
    if not allies & set(present):
        return
    drive = round_half_up(cover * ctx.rules.plant_defences.guardian_harm)
    grazers = {row.species_entity_id for row in await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.diet.in_(sorted(PLANT_EATERS))))}
    struck = 0
    for species_id in sorted(grazers & set(present) - allies):
        row = present[species_id]
        if drive <= 0 or held(species_id) or "abundance" in (row.locked or []):
            continue
        row.abundance = clamp_int(row.abundance - drive, 0, PERCENT)
        struck += 1
    if struck:
        await record(ctx, "life.guardians_struck", roles={IncidentRole.PLACE: region_id}, facts={"driven": struck, "harm": drive}, place=region_id)


async def keep_plant_defences(ctx: TickContext, tally: PlantTally) -> None:
    table = ctx.rules.plant_defences
    atlas = await RegionAtlas.load(ctx.session)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    book = await SymbiosisBook.load(ctx.session)
    for region_id, cover in sorted((await defence_cover(ctx.session)).items()):
        if held(region_id):
            continue
        region = await ctx.session.get(EntityRow, region_id)
        floor = round_half_up(cover.get(PlantDefence.CARNIVOROUS, 0.0) * table.carnivorous_danger)
        if region is not None and floor > 0 and (stat(region, "danger") or 0) < floor:
            shift_stat(region, "danger", floor - (stat(region, "danger") or 0))
            tally.dangerous += 1
        stung = round_half_up(cover.get(PlantDefence.STINGING, 0.0) * table.stinging_harm)
        if region is not None and stung > 0 and (stat(region, "danger") or 0) < stung:
            shift_stat(region, "danger", stung - (stat(region, "danger") or 0))
        spared = cover.get(PlantDefence.MIMICRY, 0.0) * table.mimicry_cut_pct + cover.get(PlantDefence.REGROWTH, 0.0) * table.regrowth_cut_pct
        land = await ctx.session.get(RegionEnvironmentRow, region_id) if spared > 0 else None
        if land is not None and "scar.overgrazed" not in land.locked and land.scars.get(ScarKind.OVERGRAZED.value, 0) > 0:
            worn = land.scars[ScarKind.OVERGRAZED.value]
            left = round_half_up(worn * (PERCENT - min(float(PERCENT), spared)) / PERCENT)
            land.scars = {key: value for key, value in land.scars.items() if key != ScarKind.OVERGRAZED.value} | (
                {ScarKind.OVERGRAZED.value: left} if left > 0 else {}
            )
        if cover.get(PlantDefence.GUARDIANS, 0.0) > 0:
            await guard_plants(ctx, region_id, cover[PlantDefence.GUARDIANS], book)
        gathered = round_half_up(cover.get(PlantDefence.TOXINS, 0.0) * table.toxin_medicine)
        for town in atlas.communities_in(region_id):
            if held(town):
                continue
            if gathered > 0:
                tally.medicine += await ledger.add(town, CommodityKind.MEDICINE, gathered, GoodsFlow.HARVEST)
            if stung > 0:
                await ledger.add(town, CommodityKind.FIBRE, stung // 2, GoodsFlow.HARVEST)
    await ctx.session.flush()
