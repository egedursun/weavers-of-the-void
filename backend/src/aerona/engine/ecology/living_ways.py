from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.diets import DIETS
from aerona.catalog.domestication import STAGES
from aerona.catalog.plants import FORMS, PARTS
from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.plants import PlantAnatomyRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import AnimalRole, Biochemistry, Diet, DomesticationStage, SizeClass, Sociality, SpeciesClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.environment import ScarKind, TerrainKind
from aerona.domain.enums.evolution import KeystoneRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.plants import PlantForm
from aerona.engine.context import TickContext
from aerona.engine.ecology.domestication import heads_kept_for
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.book import add_scar
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record

DEAD_GROUND = (ScarKind.BATTLEFIELD, ScarKind.PLAGUE_GROUND, ScarKind.BURNED)
VENT_STRATA = frozenset(stratum for stratum, spec in STRATA.items() if spec.vents)
REFUSE_DIETS = frozenset(diet for diet, spec in DIETS.items() if spec.eats_refuse)
KEPT_BEFORE = frozenset(stage for stage, spec in STAGES.items() if spec.kept)


@dataclass
class WaysTally:
    drained: int = 0
    returned: int = 0
    thinned: int = 0
    swarmed: int = 0
    commensal: int = 0
    feral: int = 0
    weathered: int = 0
    escaped: int = 0


@dataclass(frozen=True)
class Living:
    profiles: dict[int, SpeciesProfileRow]
    forms: dict[int, PlantForm]
    ranges: dict[int, list[SpeciesRangeRow]]
    grounds: dict[int, RegionEnvironmentRow]


async def load(ctx: TickContext) -> Living:
    profiles = {row.species_entity_id: row for row in await ctx.session.scalars(select(SpeciesProfileRow))}
    forms = {species: form for species, form in await ctx.session.execute(select(PlantAnatomyRow.species_entity_id, PlantAnatomyRow.form))}
    ranges: dict[int, list[SpeciesRangeRow]] = defaultdict(list)
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.region_entity_id, SpeciesRangeRow.species_entity_id)
    ):
        ranges[row.region_entity_id].append(row)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    return Living(profiles, forms, ranges, grounds)


def thin(row: SpeciesRangeRow, amount: int) -> bool:
    if amount <= 0 or "abundance" in (row.locked or []) or held(row.species_entity_id):
        return False
    row.abundance = clamp_int(row.abundance - amount, 0, PERCENT)
    return True


def diet_of(living: Living, species_id: int) -> Diet | None:
    profile = living.profiles.get(species_id)
    return profile.diet if profile is not None else None


async def drain_hosts(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.diets
    for region_id, rows in sorted(living.ranges.items()):
        parasites = [row for row in rows if diet_of(living, row.species_entity_id) is Diet.PARASITE]
        hosts = [row for row in rows if diet_of(living, row.species_entity_id) not in (Diet.PARASITE, None)]
        if not parasites or held(region_id):
            continue
        load = sum(row.abundance for row in parasites)
        if sum(row.abundance for row in hosts) < table.parasite_host_need:
            tally.thinned += sum(thin(row, table.parasite_host_drain) for row in parasites)
            continue
        drain = round_half_up(table.parasite_host_drain * min(PERCENT, load) / PERCENT)
        struck = sum(thin(row, drain) for row in hosts)
        tally.drained += struck
        if struck:
            await record(ctx, "life.host_drained", roles={IncidentRole.PLACE: region_id}, facts={"drained": drain}, place=region_id)


async def decompose(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.diets
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        workers = sum(row.abundance for row in rows if diet_of(living, row.species_entity_id) is Diet.DECOMPOSER)
        dead = sum(ground.scars.get(scar.value, 0) for scar in DEAD_GROUND) if ground is not None else 0
        if ground is None or workers <= 0 or dead <= 0 or held(region_id) or "soil_fertility" in ground.locked:
            continue
        gain = round_half_up(dead * table.decomposer_return_pct / PERCENT * min(PERCENT, workers) / PERCENT / 10)
        ground.soil_fertility = clamp_int(ground.soil_fertility + gain, 0, PERCENT)
        tally.returned += int(gain > 0)


async def vents_and_power(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.diets
    vents = set(await ctx.session.scalars(select(RegionStratumRow.region_entity_id).where(RegionStratumRow.stratum.in_(sorted(VENT_STRATA)))))
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        if ground is None or held(region_id):
            continue
        vented = region_id in vents or ground.dominant_terrain is TerrainKind.VOLCANIC
        for row in rows:
            diet = diet_of(living, row.species_entity_id)
            if diet is Diet.CHEMOSYNTHETIC and not vented:
                tally.thinned += int(thin(row, table.chemosynthetic_vent_need // 10))
            if diet is Diet.ENERGY and "magic_density" not in ground.locked:
                ground.magic_density = clamp_int(ground.magic_density - round_half_up(table.energy_draw * row.abundance / PERCENT), 0, PERCENT)


async def warmth_bands(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.biochemistry
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        if ground is None or held(region_id):
            continue
        for row in rows:
            profile = living.profiles.get(row.species_entity_id)
            chemistry = profile.biochemistry if profile is not None else None
            outside = (
                (chemistry is Biochemistry.CARBON_METHANE and ground.temperature > table.carbon_methane_heat_max)
                or (chemistry is Biochemistry.PLASMA and ground.temperature < table.plasma_heat_min)
                or (chemistry is Biochemistry.METAL and not table.metal_temp_min <= ground.temperature <= table.metal_temp_max)
            )
            if outside and chemistry is not None and thin(row, table.out_of_band_loss):
                tally.thinned += 1
                await record(
                    ctx,
                    "life.out_of_its_world",
                    roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id},
                    facts={"biochemistry": chemistry},
                    place=region_id,
                )


async def colonies_and_swarms(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.species_forms
    atlas = await RegionAtlas.load(ctx.session)
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        for row in list(rows):
            profile = living.profiles.get(row.species_entity_id)
            if profile is None or held(region_id):
                continue
            left = row.abundance
            if profile.sociality is Sociality.COLONY and 0 < left < table.colony_collapse_pct and thin(row, left):
                await record(
                    ctx,
                    "ecology.colony_collapsed",
                    roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id},
                    facts={"abundance": left},
                    place=region_id,
                )
            if profile.sociality is not Sociality.SWARM:
                continue
            if ground is not None and "harvest_pct" not in ground.locked:
                harm = round_half_up(table.swarm_crop_harm * row.abundance / PERCENT)
                ground.harvest_pct = clamp_int(ground.harvest_pct - harm, 0, PERCENT * 2)
                tally.swarmed += 1
                await record(
                    ctx,
                    "life.swarm_struck",
                    roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id},
                    facts={"harm": harm},
                    place=region_id,
                )
            await swarm_on(ctx, atlas, row, table.swarm_move)


async def swarm_on(ctx: TickContext, atlas: RegionAtlas, row: SpeciesRangeRow, hops: int) -> None:
    neighbours = [other for other in atlas.neighbour_regions(row.region_entity_id) if not held(other)][:hops]
    for other in neighbours:
        there = await ctx.session.get(SpeciesRangeRow, (row.species_entity_id, other))
        if there is None:
            ctx.session.add(SpeciesRangeRow(species_entity_id=row.species_entity_id, region_entity_id=other, abundance=max(1, row.abundance // 2), locked=[]))
        elif "abundance" not in (there.locked or []):
            there.abundance = clamp_int(max(there.abundance, row.abundance // 2), 0, PERCENT)


async def settle_beside(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.domestication_depth
    atlas = await RegionAtlas.load(ctx.session)
    for region_id, rows in sorted(living.ranges.items()):
        towns = atlas.communities_in(region_id)
        for row in rows:
            profile = living.profiles.get(row.species_entity_id)
            if profile is None or held(row.species_entity_id) or "stage" in (getattr(profile, "locked", None) or []):
                continue
            beside = profile.stage is DomesticationStage.WILD and bool(towns) and profile.diet in REFUSE_DIETS
            if beside and ctx.rng(f"commensal.{row.species_entity_id}.{region_id}.{ctx.epoch}").chance(table.commensal_chance_pct):
                profile.stage = DomesticationStage.COMMENSAL
                tally.commensal += 1
                await record(ctx, "ecology.commensal", roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id}, place=region_id)
            abandoned = profile.stage in KEPT_BEFORE and not towns
            if abandoned and ctx.rng(f"feral.{row.species_entity_id}.{region_id}.{ctx.epoch}").chance(table.feral_chance_pct):
                profile.stage = DomesticationStage.FERAL
                tally.feral += 1
                await record(ctx, "ecology.gone_feral", roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id}, place=region_id)
            if profile.stage is DomesticationStage.FERAL:
                ground = living.grounds.get(region_id)
                if ground is not None and not held(region_id):
                    add_scar(ground, ScarKind.OVERGRAZED, round_half_up(table.feral_graze_harm * row.abundance / PERCENT))


FEEDING_FORMS = frozenset(form for form, spec in FORMS.items() if any(PARTS[part].feeds_pollinators for part in spec.parts))


async def feed_pollinators(living: Living, rows: list[SpeciesRangeRow], gain: int) -> None:
    for row in rows:
        profile = living.profiles.get(row.species_entity_id)
        if (
            gain > 0
            and profile is not None
            and profile.keystone is KeystoneRole.POLLINATOR
            and "abundance" not in (row.locked or [])
            and not held(row.species_entity_id)
        ):
            row.abundance = clamp_int(row.abundance + gain, 0, PERCENT)


async def plant_ways(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.plants_depth
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        if ground is None or held(region_id):
            continue
        for row in rows:
            form = living.forms.get(row.species_entity_id)
            if form in FEEDING_FORMS:
                await feed_pollinators(living, rows, ctx.rules.plants_depth.pollen_feed * row.abundance // PERCENT)
            if form is PlantForm.GEOPHYTE and ground.burned_epoch is not None and ground.burned_epoch >= ctx.epoch - 1 and "abundance" not in row.locked:
                row.abundance = clamp_int(row.abundance + table.geophyte_regrow, 0, PERCENT)
            if form is PlantForm.EPIPHYTE and ground.forest_cover < table.epiphyte_host_need:
                tally.thinned += int(thin(row, table.epiphyte_host_need // 10))
            if form is PlantForm.PARASITIC and "harvest_pct" not in ground.locked:
                harm = round_half_up(table.parasitic_host_harm * row.abundance / PERCENT)
                ground.harvest_pct = clamp_int(ground.harvest_pct - harm, 0, PERCENT * 2)
                if harm > 0:
                    await record(
                        ctx,
                        "life.host_weakened",
                        roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: region_id},
                        facts={"harm": harm},
                        place=region_id,
                    )


async def tap_resin(ctx: TickContext, living: Living, resin_species: set[int]) -> None:
    table = ctx.rules.plants_depth
    atlas = await RegionAtlas.load(ctx.session)
    goods = goods_of(ctx.session, ctx.epoch)
    for region_id, rows in sorted(living.ranges.items()):
        town = next(iter(atlas.communities_in(region_id)), None)
        if town is None or held(town):
            continue
        for row in rows:
            if row.species_entity_id in resin_species and thin(row, table.resin_tap_harm):
                taken = await goods.add(town, CommodityKind.INCENSE, round_half_up(table.resin_tap_yield * row.abundance / PERCENT), GoodsFlow.EXTRACTION)
                await record(
                    ctx,
                    "life.resin_tapped",
                    roles={IncidentRole.SUBJECT: row.species_entity_id, IncidentRole.PLACE: town},
                    facts={"taken": taken},
                    place=region_id,
                )


async def animal_roles(ctx: TickContext) -> None:
    table = ctx.rules.species_roles
    goods = goods_of(ctx.session, ctx.epoch)
    for town, heads in sorted((await heads_kept_for(ctx.session, AnimalRole.MEDICINE)).items()):
        if heads > 0 and not held(town):
            await goods.add(town, CommodityKind.MEDICINE, table.medicine_yield, GoodsFlow.PRODUCTION)
    sport = await heads_kept_for(ctx.session, AnimalRole.SPORT)
    for gathering in await ctx.session.scalars(
        select(GatheringRow).where(GatheringRow.epoch == ctx.epoch, GatheringRow.host_node_id.in_(sorted(sport))).order_by(GatheringRow.id)
    ):
        if "prestige" not in gathering.locked and not held(gathering.host_node_id):
            gathering.prestige = clamp_int(gathering.prestige + table.sport_draw, 0, PERCENT)
            await record(
                ctx,
                "life.contest_held",
                roles={IncidentRole.HOST: gathering.host_node_id},
                facts={"prestige": gathering.prestige},
                place=gathering.place_entity_id,
            )


async def feed_herds(ctx: TickContext) -> None:
    table = ctx.rules.plant_products
    goods = goods_of(ctx.session, ctx.epoch)
    for herd in list(await ctx.session.scalars(select(HerdRow).where(HerdRow.head > 0).order_by(HerdRow.community_entity_id, HerdRow.species_entity_id))):
        if held(herd.community_entity_id) or "head" in herd.locked:
            continue
        need = max(1, herd.head // table.fodder_per_head)
        fed = await goods.take_units(herd.community_entity_id, CommodityKind.FODDER, need, GoodsFlow.CONSUMPTION)
        if fed > 0:
            herd.head += round_half_up(herd.head * table.fodder_herd_gain / PERCENT * fed / need / 10)


async def keep_living_ways(ctx: TickContext, resin_species: set[int]) -> WaysTally:
    tally = WaysTally()
    living = await load(ctx)
    await drain_hosts(ctx, living, tally)
    await decompose(ctx, living, tally)
    await vents_and_power(ctx, living, tally)
    await warmth_bands(ctx, living, tally)
    await colonies_and_swarms(ctx, living, tally)
    await settle_beside(ctx, living, tally)
    await plant_ways(ctx, living, tally)
    await tap_resin(ctx, living, resin_species)
    await animal_roles(ctx)
    await deeper_ways(ctx, living, tally)
    await feed_herds(ctx)
    await ctx.session.flush()
    return tally


async def deeper_ways(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    await lichen_and_insects(ctx, living, tally)
    await captives(ctx, living, tally)
    await shown_and_herded(ctx)


async def lichen_and_insects(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    forms = ctx.rules.species_forms
    classes = {species: kind for species, kind in await ctx.session.execute(select(SpeciesProfileRow.species_entity_id, SpeciesProfileRow.species_class))}
    foul = {region: air for region, air in await ctx.session.execute(select(RegionPollutionRow.region_node_id, RegionPollutionRow.air))}
    for region_id, rows in sorted(living.ranges.items()):
        ground = living.grounds.get(region_id)
        if ground is None or held(region_id):
            continue
        for row in rows:
            if classes.get(row.species_entity_id) is not SpeciesClass.LICHEN:
                continue
            if foul.get(region_id, 0) >= forms.lichen_air_kill and thin(row, row.abundance // 2):
                tally.thinned += 1
            elif "soil_fertility" not in ground.locked:
                gain = round_half_up(forms.lichen_weathering_pct * row.abundance / PERCENT)
                ground.soil_fertility = clamp_int(ground.soil_fertility + gain, 0, PERCENT)
                tally.weathered += int(gain > 0)
        unseen = sum(
            row.abundance for row in rows if (profile := living.profiles.get(row.species_entity_id)) is not None and profile.size_class is SizeClass.MICROSCOPIC
        )
        if unseen and "disease_load" not in ground.locked:
            ground.disease_load = clamp_int(ground.disease_load + round_half_up(unseen * forms.microscopic_scale / (PERCENT * PERCENT * 10)), 0, PERCENT)
        eaters = sum(row.abundance for row in rows if diet_of(living, row.species_entity_id) is Diet.INSECTIVORE)
        swarms = [row for row in rows if (profile := living.profiles.get(row.species_entity_id)) is not None and profile.sociality is Sociality.SWARM]
        for row in swarms if eaters > 0 else []:
            tally.thinned += int(thin(row, round_half_up(ctx.rules.diets.insectivore_draw * min(PERCENT, eaters) / PERCENT)))
        for row in rows:
            profile = living.profiles.get(row.species_entity_id)
            if profile is not None and profile.sociality is Sociality.PAIR and 0 < row.abundance < forms.pair_low and "breeding_seasons" not in profile.locked:
                profile.breeding_seasons = max(1, round_half_up(profile.breeding_seasons * (PERCENT - forms.pair_widow_pct) / PERCENT))


async def captives(ctx: TickContext, living: Living, tally: WaysTally) -> None:
    table = ctx.rules.domestication_depth
    for species_id, profile in sorted(living.profiles.items()):
        if profile.stage is not DomesticationStage.CAPTIVE or held(species_id) or "stage" in profile.locked:
            continue
        if ctx.rng(f"captive.escape.{species_id}.{ctx.epoch}").chance(table.captive_escape_pct):
            profile.stage = DomesticationStage.FERAL
            profile.feral_epoch = ctx.epoch
            tally.escaped += 1
            await record(ctx, "species.escaped", roles={IncidentRole.SUBJECT: species_id}, facts={"stage": DomesticationStage.CAPTIVE})
    kept = select(HerdRow.community_entity_id).where(HerdRow.stage == DomesticationStage.CAPTIVE)
    for community_id in sorted(set(await ctx.session.scalars(kept))):
        town = await ctx.session.get(EntityRow, community_id)
        if town is not None and not held(town.id):
            shift_stat(town, "prosperity", -table.captive_upkeep)


async def shown_and_herded(ctx: TickContext) -> None:
    table = ctx.rules.species_roles
    for community_id, head in sorted((await heads_kept_for(ctx.session, AnimalRole.DISPLAY)).items()):
        profile = await ctx.session.get(SettlementProfileRow, community_id)
        if head > 0 and profile is not None and "prestige" not in profile.locked and not held(community_id):
            profile.prestige = clamp_int(profile.prestige + table.display_status, 0, PERCENT)
    for community_id, head in sorted((await heads_kept_for(ctx.session, AnimalRole.HERDING)).items()):
        if head <= 0 or held(community_id):
            continue
        for herd in await ctx.session.scalars(select(HerdRow).where(HerdRow.community_entity_id == community_id).order_by(HerdRow.species_entity_id)):
            if "head" not in herd.locked:
                herd.head = herd.head + round_half_up(herd.head * table.herding_output_pct / PERCENT / 10)
