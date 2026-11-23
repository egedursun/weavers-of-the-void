from sqlalchemy import select

from aerona.catalog.impacts import IMPACT_BODIES, IMPACT_OUTCOMES
from aerona.catalog.life_traits import WORLD_TYPE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.physics import CosmicFeatureRow, ImpactEventRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.environment import NotableYearKind, ScarKind, WeatherKind
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.life_traits import WorldTypeTrait
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.physics import CosmicFeatureKind, ImpactBody, ImpactOutcome
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats, LegendStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import cold_snap
from aerona.engine.cosmos.features import live_features, returned_now, worlds_of
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.economy.deposits import Deposit, open_deposit
from aerona.engine.environment.long_seasons import impact_spell
from aerona.engine.environment.places import write_kind
from aerona.engine.environment.years import world_years
from aerona.engine.industry.stores import perishables
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.research import has_technique
from aerona.engine.made.control import mark_relic, open_salvage
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.phases.environment import Notable, YearHarvest, record_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import scale_stat, shift_bounded
from aerona.engine.recording.record import FactInput, StepDraft, record

PIETY_KEY = "piety"
ABUNDANCE_KEY = "abundance"
PENDING = ImpactOutcome.PENDING
BROKEN_WORLDS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.BROKEN_WORLDS)


async def foreseers(ctx: TickContext, world_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    for community in sorted(await canon(ctx.session, COMMUNITY_TYPES, world_id), key=lambda row: row.id):
        level = await lagged(ctx, BalanceLoop.IMPACT_PREPARATION, community.id, await branch_level(ctx.session, community.id, KnowledgeBranch.ASTRONOMY))
        if level >= ctx.rules.impacts.predict_level or await has_technique(ctx.session, community.id, Technique.ECLIPSE_PREDICTION):
            found.append(community)
    return found


async def pending_on(ctx: TickContext, world_id: int) -> ImpactEventRow | None:
    statement = select(ImpactEventRow).where(ImpactEventRow.world_id == world_id, ImpactEventRow.outcome == PENDING).order_by(ImpactEventRow.due_epoch)
    return await ctx.session.scalar(statement.limit(1))


async def landing(ctx: TickContext, world: WorldRow, salt: str) -> EntityRow | None:
    regions = sorted(await canon(ctx.session, [EntityType.REGION], world.id), key=lambda row: row.id)
    return ctx.rng(f"impact_site.{world.id}.{salt}").pick(regions) if regions else None


async def schedule(
    ctx: TickContext,
    world: WorldRow,
    body: ImpactBody,
    *,
    feature: CosmicFeatureRow | None = None,
    size: int | None = None,
    called_by: int | None = None,
    fragment_world_id: int | None = None,
    wreck_remnant_id: int | None = None,
) -> ImpactEventRow:
    table = ctx.rules.impacts
    region = await landing(ctx, world, f"{body.value}.{ctx.epoch}")
    seers = [] if called_by is not None else await foreseers(ctx, world.id)
    lead = table.warning_epochs if seers else 0
    impact = ImpactEventRow(
        world_id=world.id,
        region_entity_id=region.id if region is not None else None,
        feature_id=feature.id if feature is not None else None,
        fragment_world_id=fragment_world_id,
        wreck_remnant_id=wreck_remnant_id,
        body=body,
        size=clamp_percent(size if size is not None else ctx.rng(f"impact_size.{world.id}.{ctx.epoch}").die(table.size_die)),
        due_epoch=ctx.epoch + max(1, lead),
        warned_epoch=ctx.epoch if seers else None,
        outcome=PENDING,
        called_by_node_id=called_by,
        winter_epochs=0,
        text="",
        locked=[],
    )
    ctx.session.add(impact)
    await ctx.session.flush()
    if seers:
        await warn(ctx, world, impact, seers)
    return impact


async def flee(ctx: TickContext, world: WorldRow, impact: ImpactEventRow) -> int:
    if impact.region_entity_id is None:
        return 0
    away = sorted((await RegionAtlas.load(ctx.session)).neighbour_regions(impact.region_entity_id))
    if not away:
        return 0
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.world_id == world.id, EntityRow.location_id == impact.region_entity_id
    )
    fled = 0
    for town in list(await ctx.session.scalars(statement.order_by(EntityRow.id))):
        if held(town.id):
            continue
        town.location_id = away[0]
        await BondRepository(ctx.session).refresh_location(town.id, town.location_id, ctx.epoch)
        await record(
            ctx,
            "impact.fled",
            roles={IncidentRole.SUBJECT: town.id, IncidentRole.ORIGIN: impact.region_entity_id, IncidentRole.DESTINATION: away[0]},
            steps=(StepDraft(StepAction.DEPART, actor=town.id), StepDraft(StepAction.ARRIVE, actor=town.id, locus_kind=StepLocus.REGION, locus_node=away[0])),
            origin=impact.region_entity_id,
            destination=away[0],
            world_id=world.id,
        )
        fled += 1
    return fled


async def hoard(ctx: TickContext, community: EntityRow) -> int:
    kept = 0
    for lot in await perishables(ctx, community.id):
        if lot.held:
            continue
        part = round_half_up((lot.quantity - lot.preserved) * ctx.rules.impacts.hoard_pct / PERCENT)
        lot.preserved += part
        kept += part
    return kept


async def warn(ctx: TickContext, world: WorldRow, impact: ImpactEventRow, seers: list[EntityRow]) -> None:
    for community in await canon(ctx.session, COMMUNITY_TYPES, world.id):
        if not held(community.id):
            shift_bounded(ctx.rules, community, PIETY_KEY, ctx.rules.impacts.prepare_piety)
            await hoard(ctx, community)
    await flee(ctx, world, impact)
    await record(
        ctx,
        "impact.foreseen",
        roles={IncidentRole.ACTOR: seers[0].id, IncidentRole.SUBJECT: world.id, IncidentRole.TELLER: [seer.id for seer in seers[1:]]},
        facts={"body": impact.body, "size": impact.size, "epochs": impact.due_epoch - ctx.epoch, "piety": ctx.rules.impacts.prepare_piety},
        steps=(StepDraft(StepAction.FORESEE, actor=seers[0].id, outcome=StepOutcome.SUCCESS),),
        world_id=world.id,
    )


async def forecast(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.impacts
    made = 0
    fields = await live_features(ctx, CosmicFeatureKind.ASTEROID_FIELD)
    comets = [row for row in await live_features(ctx, CosmicFeatureKind.PERIODIC_COMET) if returned_now(row, ctx.epoch)]
    rogues = await live_features(ctx, CosmicFeatureKind.ROGUE_WORLD)
    for source, body, chance in (
        *((row, ImpactBody.ASTEROID, row.density / 10 * table.field_chance_per_density / 10) for row in fields),
        *((row, ImpactBody.COMET, float(table.comet_chance)) for row in comets),
        *((row, ImpactBody.ROGUE_WORLD, float(table.rogue_chance)) for row in rogues),
    ):
        for world in worlds_of(cosmography, source.star_id):
            if world.parent_world_id is not None or held(world.id) or await pending_on(ctx, world.id) is not None:
                continue
            if ctx.rng(f"impact.{source.id}.{world.id}").chance(chance):
                await schedule(ctx, world, body, feature=source)
                made += 1
    return made + await falls_from_rings(ctx, cosmography) + await falls_from_orbit(ctx)


async def broken_moon_of(ctx: TickContext, world: WorldRow) -> int | None:
    statement = select(WorldRow.id).where(WorldRow.parent_world_id == world.id, WorldRow.world_type.in_(sorted(BROKEN_WORLDS)))
    found: int | None = await ctx.session.scalar(statement.order_by(WorldRow.id).limit(1))
    return found


async def orbiting_wreck(ctx: TickContext, world: WorldRow) -> int | None:
    statement = select(WarRemnantRow.id).where(WarRemnantRow.orbit_world_id == world.id, WarRemnantRow.density > 0)
    found: int | None = await ctx.session.scalar(statement.order_by(WarRemnantRow.id).limit(1))
    return found


async def falls_from_rings(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.impacts
    made = 0
    worlds = dict(cosmography.worlds)
    for moon in sorted(worlds.values(), key=lambda row: row.id):
        planet = worlds.get(moon.parent_world_id) if moon.parent_world_id is not None else None
        if planet is None or moon.world_type not in BROKEN_WORLDS or held(planet.id) or await pending_on(ctx, planet.id) is not None:
            continue
        if ctx.rng(f"impact.fragment.{moon.id}.{ctx.epoch}").chance(table.fragment_rate):
            await schedule(ctx, planet, ImpactBody.MOON_FRAGMENT, size=table.fragment_size, fragment_world_id=moon.id)
            made += 1
    return made


async def falls_from_orbit(ctx: TickContext) -> int:
    table = ctx.rules.impacts
    made = 0
    orbiting = select(WarRemnantRow).where(WarRemnantRow.orbit_world_id.is_not(None), WarRemnantRow.density > 0).order_by(WarRemnantRow.id)
    for remnant in list(await ctx.session.scalars(orbiting)):
        world = await ctx.session.get(WorldRow, remnant.orbit_world_id)
        if world is None or held(world.id) or await pending_on(ctx, world.id) is not None:
            continue
        if ctx.rng(f"impact.wreck.{remnant.id}.{ctx.epoch}").chance(table.wreck_rate):
            await schedule(ctx, world, ImpactBody.WRECK, size=table.wreck_size, wreck_remnant_id=remnant.id)
            made += 1
    return made


async def crater(ctx: TickContext, impact: ImpactEventRow, region: EntityRow) -> EntityRow:
    place = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PLACE,
            name=f"The Crater of {region.name}",
            body=f"A crater left where a body from the sky struck {region.name}.",
            stats=PlaceStats(danger=impact.size // 2, fertility=0, mystery=impact.size // 2),
            power=2,
            world_id=region.world_id,
            location_id=region.id,
        ),
    )
    await write_kind(ctx.session, ctx.rules, place.id, PlaceKind.CRATER)
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    if ground is not None and "scars" not in ground.locked:
        ground.scars = {**ground.scars, ScarKind.CRATER.value: ground.scars.get(ScarKind.CRATER.value, 0) + 1}
    if impact.size >= ctx.rules.impacts.star_metal_size:
        await open_deposit(
            ctx,
            Deposit(
                name=f"Star Metal of {place.name}",
                body=f"Metal from the body that struck {region.name}.",
                place=place,
                commodity=CommodityKind.ORE,
                material=MaterialKind.STAR_METAL,
                richness=impact.size,
                quality=impact.size,
                revealed=True,
            ),
        )
    return place


async def legend_of(ctx: TickContext, impact: ImpactEventRow, world: WorldRow, place: EntityRow) -> EntityRow | None:
    if impact.size < ctx.rules.impacts.legend_size:
        return None
    witnesses = sorted(await canon(ctx.session, COMMUNITY_TYPES, world.id), key=lambda row: row.id)
    if not witnesses:
        return None
    legend = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"The Fall at {place.name}",
            body=f"What the peoples of {world.name} tell of the body that struck {place.name}.",
            stats=LegendStats(spread=clamp_percent(len(witnesses) * 10)),
            power=3,
            world_id=world.id,
            location_id=place.id,
        ),
    )
    await connect(ctx.session, legend.id, place.id, BondKind.TELLS_OF, ctx.epoch, description="the fall from the sky")
    return legend


async def strike(ctx: TickContext, impact: ImpactEventRow) -> bool:
    table = ctx.rules.impacts
    world = await ctx.session.get(WorldRow, impact.world_id)
    region = await ctx.session.get(EntityRow, impact.region_entity_id) if impact.region_entity_id is not None else None
    if world is None or held(world.id):
        return False
    if impact.called_by_node_id is None and not IMPACT_BODIES[impact.body].made and ctx.rng(f"impact_airburst.{impact.id}").chance(table.airburst_pct):
        await airburst(ctx, impact, world, region)
        return True
    impact.outcome = ImpactOutcome.STRUCK
    spared = table.prepared_pct / PERCENT if impact.warned_epoch is not None else 0.0
    severity = impact.size * table.devastation_pct / PERCENT / PERCENT * (1 - spared)
    place = None
    if region is not None and not held(region.id):
        await apply_disaster(ctx, region, Disaster.EARTHQUAKE, min(1.0, severity), origin=WaveOrigin.IMPACT)
        place = await crater(ctx, impact, region)
        impact.crater_place_id = place.id
        if IMPACT_BODIES[impact.body].made:
            await strew_wreck(ctx, impact, place)
    impact.winter_epochs = impact.size // max(1, table.winter_per_size)
    for species in await canon(ctx.session, [EntityType.SPECIES], world.id):
        if held(species.id):
            continue
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        bears = table.hardy_pct / PERCENT if profile is not None and profile.temperature_min <= table.hardy_cold else 1.0
        scale_stat(ctx.rules, species, ABUNDANCE_KEY, 1 - impact.size * table.extinction_pct / PERCENT / PERCENT * (1 - spared) * bears)
    facts: dict[str, FactInput] = {
        "body": impact.body,
        "size": impact.size,
        "severity": severity * PERCENT,
        "winter": impact.winter_epochs,
        "spared": spared * PERCENT,
    }
    steps = (
        StepDraft(StepAction.COLLIDE, actor=impact.called_by_node_id, locus_kind=StepLocus.REGION, locus_node=impact.region_entity_id),
        StepDraft(StepAction.SPREAD, locus_kind=StepLocus.REALM, locus_node=world.id),
    )
    if region is not None:
        written = await record(
            ctx,
            "impact.struck",
            roles={
                IncidentRole.SUBJECT: world.id,
                IncidentRole.PLACE: region.id,
                IncidentRole.PRODUCT: place.id if place is not None else None,
                IncidentRole.AUTHORITY: impact.called_by_node_id,
            },
            facts=facts,
            steps=steps,
            place=region.id,
            world_id=world.id,
        )
    else:
        written = await record(
            ctx,
            "impact.struck_world",
            roles={IncidentRole.SUBJECT: world.id, IncidentRole.AUTHORITY: impact.called_by_node_id},
            facts=facts,
            steps=steps,
            world_id=world.id,
        )
    impact.text = written.text
    if place is not None:
        await legend_of(ctx, impact, world, place)
    await remember_the_fall(ctx, world, region, impact)
    return True


async def strew_wreck(ctx: TickContext, impact: ImpactEventRow, place: EntityRow) -> None:
    table = ctx.rules.impacts
    await open_salvage(ctx, place.id, None, round_half_up(impact.size * table.wreck_salvage_pct / PERCENT))
    remnant = await ctx.session.get(WarRemnantRow, impact.wreck_remnant_id) if impact.wreck_remnant_id is not None else None
    if remnant is not None and "density" not in remnant.locked:
        remnant.density = max(0, remnant.density - impact.size)
    if not ctx.rng(f"impact_relic.{impact.id}").chance(table.wreck_relic_pct):
        return
    relic = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=f"Relic of {place.name}",
            body=f"A made thing that fell from the sky into {place.name} and still holds its working.",
            stats=ItemStats(),
            power=2,
            world_id=place.world_id,
            location_id=place.id,
        ),
    )
    await mark_relic(ctx, relic.id, 0, 0)


async def airburst(ctx: TickContext, impact: ImpactEventRow, world: WorldRow, region: EntityRow | None) -> None:
    table = ctx.rules.impacts
    impact.outcome = ImpactOutcome.AIRBURST
    spared = table.prepared_pct / PERCENT if impact.warned_epoch is not None else 0.0
    severity = impact.size * table.devastation_pct / PERCENT / PERCENT * (1 - spared)
    struck: list[int] = []
    if region is not None:
        atlas = await RegionAtlas.load(ctx.session)
        reach = {region.id}
        for _step in range(table.airburst_reach):
            reach |= {near for place in sorted(reach) for near in atlas.neighbours(place)}
        for place_id in sorted(reach):
            land = await ctx.session.get(EntityRow, place_id)
            if land is None or land.entity_type is not EntityType.REGION or held(place_id):
                continue
            ground = await ctx.session.get(RegionEnvironmentRow, place_id)
            if ground is not None and "forest_cover" not in ground.locked:
                ground.forest_cover = clamp_percent(round_half_up(ground.forest_cover * (1 - min(1.0, severity))))
            await apply_disaster(ctx, land, Disaster.STORM, min(1.0, severity), origin=WaveOrigin.IMPACT)
            struck.append(place_id)
    impact.winter_epochs = round_half_up(impact.size // max(1, table.winter_per_size) * (PERCENT - table.airburst_winter_cut_pct) / PERCENT)
    written = await record(
        ctx,
        "impact.airburst",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.PLACE: region.id if region is not None else None, IncidentRole.AUTHORITY: impact.called_by_node_id},
        facts={"body": impact.body, "size": impact.size, "lands": len(struck), "winter": impact.winter_epochs},
        steps=(StepDraft(StepAction.COLLIDE, locus_kind=StepLocus.REALM, locus_node=world.id),),
        place=region.id if region is not None else None,
        world_id=world.id,
    )
    impact.text = written.text
    await remember_the_fall(ctx, world, region, impact)


async def remember_the_fall(ctx: TickContext, world: WorldRow, region: EntityRow | None, impact: ImpactEventRow) -> NotableYearRow | None:
    years = world_years(ctx.environment, world.id, "impact")
    if not years:
        return None
    sampled = years[0]
    name = f"the year of the impact on {region.name if region is not None else world.name}"
    return await record_notable(
        ctx,
        "year.weather",
        world,
        region,
        Notable(NotableYearKind.WEATHER, YearHarvest(sampled.offset, sampled.year, 0, WeatherKind.ASH_FALL), clamp_percent(impact.size), name),
    )


async def resolve(ctx: TickContext) -> int:
    struck = 0
    statement = select(ImpactEventRow).where(ImpactEventRow.outcome == PENDING, ImpactEventRow.due_epoch <= ctx.epoch).order_by(ImpactEventRow.id)
    for impact in list(await ctx.session.scalars(statement)):
        if held(impact.world_id) or "outcome" in impact.locked:
            continue
        if impact.called_by_node_id is None and ctx.rng(f"impact_miss.{impact.id}").chance(ctx.rules.impacts.miss_pct):
            await pass_by(ctx, impact)
            continue
        struck += int(await strike(ctx, impact))
    return struck


async def pass_by(ctx: TickContext, impact: ImpactEventRow) -> None:
    impact.outcome = ImpactOutcome.MISSED
    written = await record(
        ctx,
        "impact.missed",
        roles={IncidentRole.SUBJECT: impact.world_id},
        facts={"body": impact.body, "size": impact.size, "chance": ctx.rules.impacts.miss_pct},
        world_id=impact.world_id,
    )
    impact.text = written.text


async def impact_winters(ctx: TickContext) -> int:
    chilled = 0
    landed = [outcome for outcome, spec in IMPACT_OUTCOMES.items() if spec.landed]
    statement = select(ImpactEventRow).where(ImpactEventRow.outcome.in_(landed), ImpactEventRow.winter_epochs > 0).order_by(ImpactEventRow.id)
    for impact in list(await ctx.session.scalars(statement)):
        if held(impact.world_id) or "winter_epochs" in impact.locked:
            continue
        world = await ctx.session.get(WorldRow, impact.world_id)
        if world is not None and await impact_spell(ctx, world, impact.id, impact.size, impact.winter_epochs) is not None:
            impact.winter_epochs = 0
            continue
        cooled = await cold_snap(ctx, impact.world_id, ctx.rules.impacts.winter_cold)
        chilled += cooled
        impact.winter_epochs -= 1
        if cooled:
            await record(
                ctx,
                "climate.impact_winter",
                roles={IncidentRole.SUBJECT: impact.world_id, IncidentRole.PLACE: impact.region_entity_id},
                facts={"cold": ctx.rules.impacts.winter_cold, "regions": cooled, "epochs_left": impact.winter_epochs},
                world_id=impact.world_id,
            )
    return chilled


async def call_impact(
    ctx: TickContext, world_id: int, region_id: int | None, by_node_id: int | None, *, size: int | None = None, body: ImpactBody = ImpactBody.CALLED
) -> ImpactEventRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    spec = IMPACT_BODIES[body]
    fragment = await broken_moon_of(ctx, world) if spec.from_ring else None
    wreck = await orbiting_wreck(ctx, world) if spec.made else None
    if spec.from_ring and fragment is None:
        raise ValidationFailedError("A fragment falls only on a world circled by the ring of a broken moon.")
    if spec.made and wreck is None:
        raise ValidationFailedError("A made thing falls only where one circles the world.")
    impact = await schedule(
        ctx,
        world,
        body,
        size=size if size is not None else ctx.rules.impacts.called_size,
        called_by=by_node_id,
        fragment_world_id=fragment,
        wreck_remnant_id=wreck,
    )
    if region_id is not None:
        region = await ctx.session.get(EntityRow, region_id)
        if region is None or region.world_id != world.id or region.entity_type is not EntityType.REGION:
            raise ValidationFailedError("An impact falls on a region of its own world.")
        impact.region_entity_id = region.id
    await record(
        ctx,
        "impact.called",
        roles={IncidentRole.ACTOR: by_node_id, IncidentRole.SUBJECT: world.id, IncidentRole.PLACE: impact.region_entity_id},
        facts={"size": impact.size, "due": impact.due_epoch - ctx.epoch, "body": impact.body},
        steps=(StepDraft(StepAction.INVOKE, actor=by_node_id, outcome=StepOutcome.SUCCESS),),
        place=impact.region_entity_id,
        world_id=world.id,
    )
    await ctx.session.flush()
    return impact


async def deflect_impact(ctx: TickContext, impact_id: int, by_node_id: int | None) -> ImpactEventRow:
    impact = await ctx.session.get(ImpactEventRow, impact_id)
    if impact is None:
        raise NotFoundError("No such impact.")
    if impact.outcome is not PENDING:
        raise ValidationFailedError("That body has already struck or passed.")
    impact.outcome = ImpactOutcome.DEFLECTED
    impact.deflected_by_node_id = by_node_id
    written = await record(
        ctx,
        "impact.deflected",
        roles={IncidentRole.ACTOR: by_node_id, IncidentRole.SUBJECT: impact.world_id},
        facts={"body": impact.body, "size": impact.size},
        steps=(StepDraft(StepAction.BLOCK, actor=by_node_id, outcome=StepOutcome.BLOCKED),),
        world_id=impact.world_id,
    )
    impact.text = written.text
    await ctx.session.flush()
    return impact
