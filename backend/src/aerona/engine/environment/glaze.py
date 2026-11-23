from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.terrain import terrain_has
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.water import RegionCryosphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TerrainTrait, WeatherKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.networks import OutageCause
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.networks.phase import cut
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.language.generator import NameKind

TORNADO_HARM_DIVISOR = 3
CYCLONE_HARM_DIVISOR = 4
SURGED = (TerrainTrait.COASTAL, TerrainTrait.WATERY)


@dataclass
class ColdHarm:
    frosts: dict[int, int] = field(default_factory=dict)
    late_frosts: dict[int, int] = field(default_factory=dict)
    ice_storms: set[int] = field(default_factory=set)
    thunder: set[int] = field(default_factory=set)
    tornadoes: set[int] = field(default_factory=set)
    cyclones: set[int] = field(default_factory=set)

    def note(self, kind: WeatherKind, region_id: int) -> None:
        if kind is WeatherKind.ICE_STORM:
            self.ice_storms.add(region_id)
        elif kind is WeatherKind.THUNDERSTORM:
            self.thunder.add(region_id)
        elif kind is WeatherKind.TORNADO:
            self.tornadoes.add(region_id)
        elif kind is WeatherKind.CYCLONE:
            self.cyclones.add(region_id)


def late_frost_loss(ctx: TickContext, harvest: int) -> int:
    return round_half_up(harvest * ctx.rules.weather.late_frost_growth_pct / PERCENT)


async def deepen_frost(ctx: TickContext, region_id: int, frosts: int) -> None:
    if held(region_id):
        return
    row = await ctx.session.get(RegionCryosphereRow, region_id)
    if row is None:
        row = RegionCryosphereRow(region_entity_id=region_id)
        ctx.session.add(row)
    if "frozen_depth" not in (row.locked or []):
        row.frozen_depth = clamp_int((row.frozen_depth or 0) + frosts * ctx.rules.weather.frost_ground_depth, 0, PERCENT)


async def break_structures(ctx: TickContext, region_id: int, harm: int) -> int:
    built = (
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(EntityRow.location_id == region_id, EntityRow.status == EntityStatus.CANON)
    )
    broken = 0
    for row in await ctx.session.scalars(built.order_by(StructureProfileRow.structure_entity_id)):
        if held(row.structure_entity_id) or "condition" in (row.locked or []):
            continue
        row.condition = clamp_int(row.condition - harm, 0, PERCENT)
        broken += 1
    return broken


async def break_timber(ctx: TickContext, ground: RegionEnvironmentRow) -> int:
    share = ctx.rules.weather.ice_storm_timber_loss_pct
    lost = 0
    if "forest_cover" not in ground.locked:
        lost = round_half_up(ground.forest_cover * share / PERCENT)
        ground.forest_cover = clamp_int(ground.forest_cover - lost, 0, PERCENT)
    for row in await ctx.session.scalars(select(PerennialRow).where(PerennialRow.region_entity_id == ground.entity_id).order_by(PerennialRow.id)):
        if "condition" not in (row.locked or []) and (row.owner_node_id is None or not held(row.owner_node_id)):
            row.condition = clamp_int(row.condition - round_half_up(row.condition * share / PERCENT), 0, PERCENT)
    return lost


async def towns_in(ctx: TickContext, region_id: int) -> list[int]:
    found = select(EntityRow.id).where(
        EntityRow.location_id == region_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON
    )
    return list(await ctx.session.scalars(found.order_by(EntityRow.id)))


async def break_networks(ctx: TickContext, region_id: int) -> int:
    towns = await towns_in(ctx, region_id)
    if not towns:
        return 0
    networks = sorted(set(await ctx.session.scalars(select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id.in_(towns)))))
    broken = 0
    for network_id in networks:
        network = await ctx.session.get(EntityRow, network_id)
        profile = await ctx.session.get(NetworkProfileRow, network_id)
        if network is None or profile is None or held(network_id) or (profile.down_until_epoch or 0) >= ctx.epoch:
            continue
        if ctx.rng(f"glaze.outage.{region_id}.{network_id}").chance(ctx.rules.weather.ice_storm_outage_pct):
            await cut(ctx, network, profile, OutageCause.ICE_STORM, ctx.rules.weather.ice_storm_outage_pct)
            broken += 1
    return broken


async def kill_herds(ctx: TickContext, region_id: int) -> int:
    share = ctx.rules.weather.ice_storm_herd_loss_pct
    ledger = goods_of(ctx.session, ctx.epoch)
    lost = 0
    for town in await towns_in(ctx, region_id):
        if held(town):
            continue
        herd = sum(row.quantity for row in await lots_of(ctx.session, town, CommodityKind.LIVESTOCK) if not row.held)
        taken = round_half_up(herd * share / PERCENT)
        if taken > 0:
            lost += sum(lot.quantity for lot in await ledger.take(town, CommodityKind.LIVESTOCK, taken, GoodsFlow.LOSS))
    return lost


async def ice_storm(ctx: TickContext, ground: RegionEnvironmentRow) -> None:
    structures = await break_structures(ctx, ground.entity_id, ctx.rules.weather.ice_storm_structure_harm)
    timber = await break_timber(ctx, ground)
    networks = await break_networks(ctx, ground.entity_id)
    herds = await kill_herds(ctx, ground.entity_id)
    await record(
        ctx,
        "weather.ice_storm_harm",
        roles={IncidentRole.PLACE: ground.entity_id},
        facts={"structures": structures, "timber": timber, "networks": networks, "herds": herds},
        place=ground.entity_id,
        world_id=ground.world_id,
    )


async def suffer_cold(ctx: TickContext, harm: ColdHarm, grounds: dict[int, RegionEnvironmentRow]) -> None:
    for region_id, frosts in sorted(harm.frosts.items()):
        await deepen_frost(ctx, region_id, frosts)
    for region_id, lost in sorted(harm.late_frosts.items()):
        ground = grounds[region_id]
        await record(ctx, "weather.late_frost", roles={IncidentRole.PLACE: region_id}, facts={"lost": lost}, place=region_id, world_id=ground.world_id)
    for region_id in sorted(harm.ice_storms):
        if not held(region_id):
            await ice_storm(ctx, grounds[region_id])
    for region_id in sorted(harm.thunder):
        if not held(region_id):
            await lightning(ctx, grounds[region_id])
    for region_id in sorted(harm.tornadoes):
        if not held(region_id):
            await tornado(ctx, grounds[region_id])
    if harm.cyclones:
        atlas = await RegionAtlas.load(ctx.session)
        for region_id in sorted(harm.cyclones):
            if not held(region_id):
                await cyclone(ctx, atlas, grounds, region_id)


async def lightning(ctx: TickContext, ground: RegionEnvironmentRow) -> None:
    settings = ctx.rules.weather
    if ground.rainfall >= settings.dry_threshold or not ctx.rng(f"lightning.{ground.entity_id}").chance(settings.lightning_fire_pct):
        return
    burned = 0
    if "forest_cover" not in ground.locked:
        burned = round_half_up(ground.forest_cover * settings.thunderstorm_lightning / PERCENT)
        ground.forest_cover = clamp_int(ground.forest_cover - burned, 0, PERCENT)
    await record(
        ctx, "weather.lightning", roles={IncidentRole.PLACE: ground.entity_id}, facts={"burned": burned}, place=ground.entity_id, world_id=ground.world_id
    )


async def tornado(ctx: TickContext, ground: RegionEnvironmentRow) -> None:
    harm = ctx.rules.weather.tornado_wind // TORNADO_HARM_DIVISOR
    structures = await break_structures(ctx, ground.entity_id, harm)
    await record(
        ctx, "weather.tornado", roles={IncidentRole.PLACE: ground.entity_id}, facts={"structures": structures}, place=ground.entity_id, world_id=ground.world_id
    )


def track_of(atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow], start: int, turns: int) -> list[int]:
    track = [start]
    while len(track) < turns:
        ahead = [
            region
            for region in atlas.neighbours(track[-1])
            if region not in track and region in grounds and terrain_has(grounds[region].dominant_terrain, *SURGED)
        ]
        if not ahead:
            break
        track.append(min(ahead))
    return track


async def cyclone(ctx: TickContext, atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow], start: int) -> None:
    settings = ctx.rules.weather
    track = track_of(atlas, grounds, start, settings.cyclone_turns)
    harm = settings.cyclone_flood // CYCLONE_HARM_DIVISOR
    structures = 0
    for region_id in track:
        if not held(region_id):
            structures += await break_structures(ctx, region_id, harm)
    world_id = grounds[start].world_id
    name = await Namer(ctx.session, ctx.rules).for_world(world_id, seed_of("cyclone", start, ctx.epoch), NameKind.GENERAL) or "a nameless storm"
    names = [entity.name for entity in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(track)).order_by(EntityRow.id))]
    await record(
        ctx,
        "weather.cyclone",
        roles={IncidentRole.PLACE: start, IncidentRole.TARGET: [region for region in track if region != start]},
        facts={"name": name, "track": ", ".join(names), "structures": structures},
        place=start,
        world_id=world_id,
    )
