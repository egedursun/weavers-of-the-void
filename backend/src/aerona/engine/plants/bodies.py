from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life.plants import CLASS_FORMS
from aerona.catalog.life_traits import SPECIES_CLASS_TRAITS, having
from aerona.catalog.nature_kinds50 import REPRODUCTIONS
from aerona.catalog.plants import FORMS, PARTS
from aerona.catalog.weather import with_trait
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow, RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow, RegionCropRow
from aerona.db.tables.plants import PlantAnatomyRow, PlantPartRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import GrowthCycle, RangeTrend
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import WeatherTrait
from aerona.domain.enums.life_traits import SpeciesClassTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.plants import PlantForm
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules

PLANT_CLASSES = having(SPECIES_CLASS_TRAITS, SpeciesClassTrait.PLANT_CLASSES)
CYCLE_FORMS = {GrowthCycle.TREE: PlantForm.TREE, GrowthCycle.PERENNIAL: PlantForm.SHRUB, GrowthCycle.ANNUAL: PlantForm.HERB}
MONTHS = 12


@dataclass
class PlantTally:
    grown: int = 0
    goods: int = 0
    damaged: int = 0
    spread: int = 0
    invaded: int = 0
    tamed: int = 0


def form_of(profile: SpeciesProfileRow, plant: PlantProfileRow | None) -> PlantForm:
    if profile.species_class in CLASS_FORMS:
        return CLASS_FORMS[profile.species_class]
    return CYCLE_FORMS[plant.growth_cycle] if plant is not None else PlantForm.HERB


async def grow(ctx: TickContext, profile: SpeciesProfileRow, tally: PlantTally) -> PlantAnatomyRow:
    row = await ctx.session.get(PlantAnatomyRow, profile.species_entity_id)
    if row is not None:
        return row
    plant = await ctx.session.get(PlantProfileRow, profile.species_entity_id)
    form = form_of(profile, plant)
    spec = FORMS[form]
    first = ctx.rules.plants.years_to_first_harvest_tree if form is PlantForm.TREE else 0
    seasons = plant.growing_seasons if plant is not None else 1
    row = PlantAnatomyRow(
        species_entity_id=profile.species_entity_id,
        form=form,
        reproduction=spec.reproduction,
        lifespan_years=spec.lifespan_years,
        growth_months=clamp_int(seasons * 3, 1, MONTHS),
        first_harvest_years=first,
        locked=[],
    )
    ctx.session.add(row)
    for part in spec.parts:
        ctx.session.add(PlantPartRow(species_entity_id=profile.species_entity_id, part=part, commodity=PARTS[part].commodity, locked=[]))
    tally.grown += 1
    return row


async def yield_goods(ctx: TickContext, species_id: int, tally: PlantTally) -> None:
    for part in list(await ctx.session.scalars(select(PlantPartRow).where(PlantPartRow.species_entity_id == species_id).order_by(PlantPartRow.id))):
        if part.commodity is None or await ctx.session.get(SpeciesProductRow, (species_id, part.part.value)) is not None:
            continue
        ctx.session.add(SpeciesProductRow(species_entity_id=species_id, product=part.part.value, commodity=part.commodity, part=PARTS[part.part].product))
        tally.goods += 1


def exposed(rules: Rules, form: PlantForm, stormed: bool, burned: bool) -> int:
    spec = FORMS[form]
    loss = rules.plants.storm_damage_tree_pct if stormed and spec.storm_prone else 0
    return loss + (rules.plants.fire_damage_grass_pct if burned and spec.fire_prone else 0)


async def weather_crops(ctx: TickContext, forms: dict[int, PlantForm], tally: PlantTally) -> None:
    stormy = set(
        await ctx.session.scalars(
            select(ForcedWeatherRow.region_entity_id).where(
                ForcedWeatherRow.kind.in_(sorted(with_trait(WeatherTrait.STORM))),
                ForcedWeatherRow.from_epoch <= ctx.epoch,
                ForcedWeatherRow.until_epoch >= ctx.epoch,
            )
        )
    )
    burned = set(await ctx.session.scalars(select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.burned_epoch == ctx.epoch)))
    if not stormy and not burned:
        return
    crops = await ctx.session.scalars(
        select(RegionCropRow).where(RegionCropRow.region_entity_id.in_(stormy | burned)).order_by(RegionCropRow.region_entity_id, RegionCropRow.plant_entity_id)
    )
    for crop in list(crops):
        form = forms.get(crop.plant_entity_id)
        if form is None or held(crop.region_entity_id) or "share" in crop.locked:
            continue
        loss = exposed(ctx.rules, form, crop.region_entity_id in stormy, crop.region_entity_id in burned)
        if loss <= 0:
            continue
        with explaining_alone():
            term("plants.weather", -loss, source_node_id=crop.region_entity_id)
            crop.share = clamp_int(crop.share * (PERCENT - loss) // PERCENT, 0, PERCENT)
        tally.damaged += 1


async def spread(ctx: TickContext, anatomy: PlantAnatomyRow, atlas: RegionAtlas, tally: PlantTally) -> None:
    table = ctx.rules.plants
    carried = REPRODUCTIONS[anatomy.reproduction]
    chance = (table.spread_by_wind_pct if carried.by_wind else 0) + (table.spread_by_animal_pct if carried.by_beasts else 0)
    if chance <= 0:
        return
    species = anatomy.species_entity_id
    homes = list(
        await ctx.session.scalars(
            select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species).order_by(SpeciesRangeRow.region_entity_id)
        )
    )
    rng = ctx.rng(seed_of("plant.spread", species, ctx.epoch))
    if not homes or not rng.chance(chance):
        return
    options = sorted({other for home in homes for other in atlas.neighbours(home)} - set(homes))
    if not options:
        return
    land = options[rng.below(len(options))]
    if held(land):
        return
    ctx.session.add(SpeciesRangeRow(species_entity_id=species, region_entity_id=land, abundance=table.spread_abundance, trend=RangeTrend.RISING, locked=[]))
    tally.spread += 1
    roles = {IncidentRole.SUBJECT: species, IncidentRole.PLACE: land}
    await record(ctx, "life.plant_spread", roles=roles, facts={"abundance": table.spread_abundance}, place=land)
    kinds = await ctx.session.scalar(select(func.count()).select_from(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == land)) or 0
    if kinds < table.invasion_kinds:
        return
    tally.invaded += 1
    for other in list(
        await ctx.session.scalars(
            select(SpeciesRangeRow)
            .where(SpeciesRangeRow.region_entity_id == land, SpeciesRangeRow.species_entity_id != species)
            .order_by(SpeciesRangeRow.species_entity_id)
        )
    ):
        if "abundance" not in other.locked and not held(other.species_entity_id):
            other.abundance = clamp_int(other.abundance - table.invasion_loss, 0, PERCENT)
    await record(ctx, "life.plant_invaded", roles=roles, facts={"kinds": kinds}, place=land)


async def tame(ctx: TickContext, anatomy: PlantAnatomyRow, tally: PlantTally) -> None:
    if anatomy.domesticated or "domesticated" in anatomy.locked:
        return
    widest = await ctx.session.scalar(select(func.max(RegionCropRow.share)).where(RegionCropRow.plant_entity_id == anatomy.species_entity_id)) or 0
    if widest < ctx.rules.plants.domesticated_share:
        return
    anatomy.domesticated = True
    tally.tamed += 1
    await record(ctx, "life.plant_domesticated", roles={IncidentRole.SUBJECT: anatomy.species_entity_id}, facts={"share": widest})


async def keep_plants(ctx: TickContext, tally: PlantTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    forms: dict[int, PlantForm] = {}
    plants = await ctx.session.scalars(
        select(SpeciesProfileRow)
        .join(EntityRow, EntityRow.id == SpeciesProfileRow.species_entity_id)
        .where(SpeciesProfileRow.species_class.in_(PLANT_CLASSES), EntityRow.status == EntityStatus.CANON)
        .order_by(SpeciesProfileRow.species_entity_id)
    )
    for profile in list(plants):
        if held(profile.species_entity_id):
            continue
        anatomy = await grow(ctx, profile, tally)
        forms[profile.species_entity_id] = anatomy.form
        await yield_goods(ctx, profile.species_entity_id, tally)
        await spread(ctx, anatomy, atlas, tally)
        await tame(ctx, anatomy, tally)
    await weather_crops(ctx, forms, tally)
    await ctx.session.flush()
