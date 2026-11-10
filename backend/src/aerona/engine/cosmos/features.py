import math

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import SkyEventRow, WorldRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import CosmicFeatureRow, StarPhysicsRow, WorldPhysicsRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.physics import PERIODIC_BODIES, CosmicFeatureKind
from aerona.domain.enums.travel import RouteClosure, TravelMethod, VehicleKind
from aerona.domain.enums.world import SkyEventKind, StarType
from aerona.domain.models.entity_stats import ProphecyStats, TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.catastrophe import scorch_world
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.vessels import owned_vessels
from aerona.engine.lore.traditions import profile_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat

AGE_KEY = "age"
WANDERING_SUBTYPES: dict[str, CosmicFeatureKind] = {"comet": CosmicFeatureKind.PERIODIC_COMET, "wandering light": CosmicFeatureKind.WANDERING_STAR}
LIVE = CosmicFeatureRow.ended_epoch.is_(None)


def lit_by(cosmography: Cosmography, world: WorldRow, star_id: int) -> bool:
    star = cosmography.place_world(world).star
    return star is not None and star.id == star_id


def worlds_of(cosmography: Cosmography, star_id: int | None) -> list[WorldRow]:
    if star_id is None:
        return []
    return sorted((world for world in cosmography.worlds.values() if lit_by(cosmography, world, star_id)), key=lambda row: row.id)


async def live_features(ctx: TickContext, kind: CosmicFeatureKind | None = None) -> list[CosmicFeatureRow]:
    statement = select(CosmicFeatureRow).where(LIVE)
    if kind is not None:
        statement = statement.where(CosmicFeatureRow.kind == kind)
    return list(await ctx.session.scalars(statement.order_by(CosmicFeatureRow.id)))


async def add_stock(ctx: TickContext, community: EntityRow, commodity: CommodityKind, amount: int, material: MaterialKind | None = None) -> None:
    stock = await ctx.session.scalar(
        select(CommunityStockRow).where(
            CommunityStockRow.community_entity_id == community.id, CommunityStockRow.commodity == commodity, CommunityStockRow.material == material
        )
    )
    if stock is None:
        stock = CommunityStockRow(community_entity_id=community.id, commodity=commodity, material=material, quantity=0, quality=PERCENT // 2, preserved=0)
        ctx.session.add(stock)
    if not stock.held:
        stock.quantity += amount


async def mine_fields(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.cosmic_features
    mined = 0
    for field in await live_features(ctx, CosmicFeatureKind.ASTEROID_FIELD):
        if held(field.star_id) or field.richness <= 0:
            continue
        for world in worlds_of(cosmography, field.star_id):
            for community in sorted(await canon(ctx.session, COMMUNITY_TYPES, world.id), key=lambda row: row.id):
                if held(community.id) or not await owned_vessels(ctx.session, community.id, VehicleKind.SHIP):
                    continue
                await add_stock(ctx, community, CommodityKind.ORE, field.richness * table.mining_per_richness)
                if ctx.rng(f"star_metal.{field.id}.{community.id}").chance(table.star_metal_chance):
                    await add_stock(ctx, community, CommodityKind.ORE, field.richness, MaterialKind.STAR_METAL)
                mined += 1
    return mined


async def harbour_pirates(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.cosmic_features
    raised = 0
    for field in await live_features(ctx, CosmicFeatureKind.ASTEROID_FIELD):
        lift = field.pirates // 10 * table.pirate_piracy
        if not lift:
            continue
        ids = {world.id for world in worlds_of(cosmography, field.star_id)}
        for route in await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id)):
            if (route.world_a_id in ids or route.world_b_id in ids) and "piracy" not in route.locked and not held(route.world_a_id, route.world_b_id):
                route.piracy = clamp_percent(route.piracy + lift)
                raised += 1
    return raised


async def keep_wormholes(ctx: TickContext) -> int:
    table = ctx.rules.cosmic_features
    kept = 0
    for hole in await live_features(ctx, CosmicFeatureKind.WORMHOLE):
        if hole.world_id is None or hole.world_b_id is None or held(hole.world_id, hole.world_b_id):
            continue
        route = await ctx.session.get(RouteRow, hole.route_id) if hole.route_id is not None else None
        if route is None:
            route = RouteRow(
                world_a_id=hole.world_id,
                world_b_id=hole.world_b_id,
                method=TravelMethod.WORMHOLE,
                duration_epochs=table.wormhole_duration,
                danger=hole.instability,
                known=True,
                created_epoch=ctx.epoch,
                active=True,
                locked=[],
            )
            ctx.session.add(route)
            await ctx.session.flush()
            hole.route_id = route.id
        if "active" in route.locked:
            continue
        open_now = not ctx.rng(f"wormhole.{hole.id}").chance(hole.instability)
        if route.active != open_now:
            route.active = open_now
            route.closure = None if open_now else RouteClosure.COLLAPSED
            text = f"The throat of {hole.name} opened again." if open_now else f"The throat of {hole.name} closed for a time."
            await note(ctx, text, key="feature.wormhole_window", world_id=hole.world_id, kind=ChronicleKind.COSMIC)
        kept += 1
    return kept


def well_reach(ctx: TickContext, physics: StarPhysicsRow | None) -> float:
    mass = physics.mass if physics is not None else 10.0
    return mass * ctx.rules.cosmic_features.well_reach_per_mass / 10


async def ensure_wells(ctx: TickContext, cosmography: Cosmography) -> int:
    made = 0
    wells = {row.star_id for row in await live_features(ctx, CosmicFeatureKind.GRAVITY_WELL)}
    for star in sorted(cosmography.stars.values(), key=lambda row: row.id):
        if star.star_type is not StarType.BLACK_HOLE or star.id in wells or held(star.id):
            continue
        physics = await ctx.session.get(StarPhysicsRow, star.id)
        ctx.session.add(
            CosmicFeatureRow(
                kind=CosmicFeatureKind.GRAVITY_WELL,
                name=f"The well of {star.name}",
                galaxy_id=star.galaxy_id,
                star_id=star.id,
                x=star.x,
                y=star.y,
                radius=well_reach(ctx, physics),
                density=PERCENT,
                radiation=PERCENT // 2,
                travel=-ctx.rules.cosmic_features.slingshot_cut,
                created_epoch=max(1, ctx.epoch),
                locked=[],
            )
        )
        made += 1
    await ctx.session.flush()
    return made


async def devour(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.cosmic_features
    swallowed = 0
    for well in await live_features(ctx, CosmicFeatureKind.GRAVITY_WELL):
        star = cosmography.stars.get(well.star_id) if well.star_id is not None else None
        if star is None or star.star_type is not StarType.BLACK_HOLE:
            if "ended_epoch" not in well.locked:
                well.ended_epoch = ctx.epoch
            continue
        for world in worlds_of(cosmography, star.id):
            if world.parent_world_id is not None or world.orbit > well.radius or held(world.id) or "orbit" in world.locked:
                continue
            world.orbit = round(world.orbit * (PERCENT - table.devour_pct) / PERCENT, 4)
            if world.orbit <= table.horizon_orbit_hundredths / PERCENT and await scorch_world(ctx, world, f"{star.name} swallowed", lost=True):
                swallowed += 1
    return swallowed


async def slingshot(ctx: TickContext, journey: JourneyRow, route: RouteRow, traveller: EntityRow) -> bool:
    cosmography = await Cosmography.load(ctx.session)
    stars = {cosmography.place_world_id(world_id).star for world_id in (route.world_a_id, route.world_b_id)}
    if not any(star is not None and star.star_type is StarType.BLACK_HOLE for star in stars):
        return False
    years = ctx.rules.cosmic_features.dilation_years
    age = stat(traveller, AGE_KEY)
    if age is not None and not held(traveller.id):
        set_stats(traveller, age=max(0, age - years))
    await note(
        ctx,
        f"{traveller.name} passed the well of a black hole and arrived {years} years younger than their kin.",
        key="feature.slingshot",
        ids=[traveller.id],
        world_id=journey.destination_world_id,
    )
    return True


async def pass_rogues(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.cosmic_features
    perturbed = 0
    for rogue in await live_features(ctx, CosmicFeatureKind.ROGUE_WORLD):
        if held(rogue.star_id) or rogue.galaxy_id is None:
            continue
        candidates = sorted(
            (star for star in cosmography.stars.values() if star.galaxy_id == rogue.galaxy_id), key=lambda row: math.hypot(row.x - rogue.x, row.y - rogue.y)
        )
        if rogue.star_id is None or (rogue.next_return_epoch is not None and ctx.epoch >= rogue.next_return_epoch):
            visited = {rogue.star_id}
            target = next((star for star in candidates if star.id not in visited), None)
            if target is None or "star_id" in rogue.locked:
                continue
            rogue.star_id = target.id
            rogue.x, rogue.y = target.x, target.y
            rogue.next_return_epoch = ctx.epoch + table.rogue_pass_epochs
            await note(ctx, f"{rogue.name} drifted into the system of {target.name}.", key="feature.rogue_arrived", kind=ChronicleKind.SKY)
        for world in worlds_of(cosmography, rogue.star_id):
            physics = await ctx.session.get(WorldPhysicsRow, world.id)
            if physics is None or held(world.id) or "eccentricity" in physics.locked:
                continue
            physics.eccentricity = min(0.95, round(physics.eccentricity + table.rogue_perturb_pct / PERCENT, 3))
            perturbed += 1
    return perturbed


def periodic_period(ctx: TickContext, kind: CosmicFeatureKind) -> int:
    table = ctx.rules.cosmic_features
    return table.wanderer_period if kind is CosmicFeatureKind.WANDERING_STAR else table.comet_period


def returned_now(row: CosmicFeatureRow, epoch: int) -> bool:
    if row.next_return_epoch is None:
        return False
    return row.next_return_epoch == epoch or (row.created_epoch < epoch and row.next_return_epoch - max(1, row.period_epochs) == epoch)


async def return_comets(ctx: TickContext, cosmography: Cosmography) -> int:
    returned = 0
    bodies = [row for kind in sorted(PERIODIC_BODIES) for row in await live_features(ctx, kind)]
    for comet in sorted(bodies, key=lambda row: row.id):
        if comet.next_return_epoch is None or comet.next_return_epoch > ctx.epoch or held(comet.star_id, comet.entity_id):
            continue
        if "next_return_epoch" not in comet.locked:
            comet.next_return_epoch = ctx.epoch + max(1, comet.period_epochs)
        body = await ctx.session.get(EntityRow, comet.entity_id) if comet.entity_id is not None else None
        for world in worlds_of(cosmography, comet.star_id):
            if comet.kind is CosmicFeatureKind.PERIODIC_COMET:
                ctx.session.add(
                    SkyEventRow(
                        kind=SkyEventKind.COMET,
                        epoch=ctx.epoch,
                        until_epoch=ctx.epoch,
                        world_id=world.id,
                        star_id=comet.star_id,
                        text=f"{comet.name} returned.",
                    )
                )
            await note(
                ctx,
                f"{comet.name} returned to the sky of {world.name}.",
                key="feature.comet_returned",
                ids=[body.id] if body is not None else [],
                world_id=world.id,
                kind=ChronicleKind.SKY,
            )
            if body is not None:
                await festival(ctx, comet, body, world)
                await foretell(ctx, comet, body, world)
        returned += 1
    return returned


def omen_of(comet: CosmicFeatureRow) -> float:
    return comet.omen_weight / (PERCENT // 2)


async def festival(ctx: TickContext, comet: CosmicFeatureRow, body: EntityRow, world: WorldRow) -> EntityRow | None:
    keepers = [row for row in await canon(ctx.session, COMMUNITY_TYPES, world.id) if not held(row.id)]
    chance = ctx.rules.cosmic_features.comet_festival_chance * omen_of(comet)
    if not keepers or not ctx.rng(f"comet_festival.{comet.id}.{world.id}.{ctx.epoch}").chance(chance):
        return None
    tradition = await create_record(
        ctx,
        RecordSpec(
            name=f"The Festival of {comet.name}",
            entity_type=EntityType.TRADITION,
            stats=TraditionStats(spread=PERCENT // 5, rigidity=PERCENT // 3),
            body=f"Kept whenever {comet.name} returns to the sky.",
            power=2,
            world_id=world.id,
            location_id=keepers[0].location_id,
        ),
    )
    await profile_of(ctx, tradition, TraditionKind.FESTIVAL)
    await connect(ctx.session, tradition.id, body.id, BondKind.TELLS_OF, ctx.epoch, description="kept at its returns")
    for keeper in sorted(keepers, key=lambda row: row.id):
        await connect(ctx.session, keeper.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="at the comet's return")
    return tradition


async def foretell(ctx: TickContext, comet: CosmicFeatureRow, body: EntityRow, world: WorldRow) -> EntityRow | None:
    if not ctx.rng(f"comet_prophecy.{comet.id}.{world.id}.{ctx.epoch}").chance(ctx.rules.cosmic_features.comet_prophecy_chance * omen_of(comet)):
        return None
    prophecy = await create_record(
        ctx,
        RecordSpec(
            name=f"The Prophecy of {comet.name}",
            entity_type=EntityType.PROPHECY,
            stats=ProphecyStats(certainty=clamp_percent(comet.omen_weight)),
            body=f"Words spoken when {comet.name} returned, telling what its next return will bring.",
            power=3,
            world_id=world.id,
            subtype="comet prophecy",
        ),
    )
    await connect(ctx.session, prophecy.id, body.id, BondKind.TELLS_OF, ctx.epoch, description="foretold at its return")
    return prophecy


async def adopt_comets(ctx: TickContext) -> int:
    known = {row.entity_id for row in await ctx.session.scalars(select(CosmicFeatureRow).where(CosmicFeatureRow.kind.in_(sorted(PERIODIC_BODIES))))}
    adopted = 0
    flagged = select(EntityRow).where(EntityRow.entity_type == EntityType.CELESTIAL, EntityRow.subtype.in_(sorted(WANDERING_SUBTYPES))).order_by(EntityRow.id)
    for body in await ctx.session.scalars(flagged):
        if body.id in known or held(body.id) or body.subtype is None:
            continue
        world = await ctx.session.get(WorldRow, body.world_id) if body.world_id is not None else None
        star_id = world.star_id if world is not None else None
        kind = WANDERING_SUBTYPES[body.subtype]
        period = periodic_period(ctx, kind)
        ctx.session.add(
            CosmicFeatureRow(
                kind=kind,
                name=body.name,
                star_id=star_id,
                entity_id=body.id,
                omen_weight=PERCENT // 2,
                period_epochs=period,
                next_return_epoch=ctx.epoch + period,
                created_epoch=max(1, ctx.epoch),
                locked=[],
            )
        )
        adopted += 1
    await ctx.session.flush()
    return adopted
