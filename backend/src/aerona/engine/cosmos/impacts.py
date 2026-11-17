from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, several, spoken
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.physics import CosmicFeatureRow, ImpactEventRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.environment import NotableYearKind, ScarKind, WeatherKind
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.physics import CosmicFeatureKind, ImpactBody, ImpactOutcome
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import LegendStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import cold_snap
from aerona.engine.cosmos.features import live_features, returned_now, worlds_of
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.economy.deposits import Deposit, open_deposit
from aerona.engine.environment.places import write_kind
from aerona.engine.environment.years import world_years
from aerona.engine.industry.stores import perishables
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.research import has_technique
from aerona.engine.notes import note
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.phases.environment import Notable, YearHarvest, record_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import scale_stat, shift_bounded

PIETY_KEY = "piety"
ABUNDANCE_KEY = "abundance"
PENDING = ImpactOutcome.PENDING


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
    ctx: TickContext, world: WorldRow, body: ImpactBody, *, feature: CosmicFeatureRow | None = None, size: int | None = None, called_by: int | None = None
) -> ImpactEventRow:
    table = ctx.rules.impacts
    region = await landing(ctx, world, f"{body.value}.{ctx.epoch}")
    seers = [] if called_by is not None else await foreseers(ctx, world.id)
    lead = table.warning_epochs if seers else 0
    impact = ImpactEventRow(
        world_id=world.id,
        region_entity_id=region.id if region is not None else None,
        feature_id=feature.id if feature is not None else None,
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
        await note(ctx, f"{town.name} left its land before the body from the sky could fall on it.", key="impact.fled", ids=[town.id], world_id=world.id)
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
    epochs_counted = several(impact.due_epoch - ctx.epoch, "epoch", "epochs")
    await note(
        ctx,
        f"The astronomers of {seers[0].name} foresaw a body that will strike {world.name} in {epochs_counted}; its peoples prepare.",
        key="impact.foreseen",
        ids=[seers[0].id],
        world_id=world.id,
        kind=ChronicleKind.SKY,
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
    impact.outcome = ImpactOutcome.STRUCK
    spared = table.prepared_pct / PERCENT if impact.warned_epoch is not None else 0.0
    severity = impact.size * table.devastation_pct / PERCENT / PERCENT * (1 - spared)
    place = None
    if region is not None and not held(region.id):
        await apply_disaster(ctx, region, Disaster.EARTHQUAKE, min(1.0, severity))
        place = await crater(ctx, impact, region)
        impact.crater_place_id = place.id
    impact.winter_epochs = impact.size // max(1, table.winter_per_size)
    for species in await canon(ctx.session, [EntityType.SPECIES], world.id):
        if held(species.id):
            continue
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        bears = table.hardy_pct / PERCENT if profile is not None and profile.temperature_min <= table.hardy_cold else 1.0
        scale_stat(ctx.rules, species, ABUNDANCE_KEY, 1 - impact.size * table.extinction_pct / PERCENT / PERCENT * (1 - spared) * bears)
    impact.text = f"{an(spoken(impact.body), capital=True)} struck {region.name if region is not None else world.name}."
    await note(ctx, impact.text, key="impact.struck", ids=[region.id] if region is not None else [], world_id=world.id, kind=ChronicleKind.SKY)
    if place is not None:
        await legend_of(ctx, impact, world, place)
    await remember_the_fall(ctx, world, region, impact)
    return True


async def remember_the_fall(ctx: TickContext, world: WorldRow, region: EntityRow | None, impact: ImpactEventRow) -> NotableYearRow | None:
    years = world_years(ctx.environment, world.id, "impact")
    if not years:
        return None
    sampled = years[0]
    name = f"the year of the impact on {region.name if region is not None else world.name}"
    return await record_notable(
        ctx,
        world,
        region,
        Notable(NotableYearKind.WEATHER, YearHarvest(sampled.offset, sampled.year, 0, WeatherKind.ASH_FALL), clamp_percent(impact.size), name, impact.text),
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
    world = await ctx.session.get(WorldRow, impact.world_id)
    impact.outcome = ImpactOutcome.MISSED
    impact.text = f"The body passed {world.name if world is not None else 'its world'} by."
    await note(ctx, impact.text, key="impact.missed", world_id=impact.world_id, kind=ChronicleKind.SKY)


async def impact_winters(ctx: TickContext) -> int:
    chilled = 0
    statement = select(ImpactEventRow).where(ImpactEventRow.outcome == ImpactOutcome.STRUCK, ImpactEventRow.winter_epochs > 0).order_by(ImpactEventRow.id)
    for impact in list(await ctx.session.scalars(statement)):
        if held(impact.world_id) or "winter_epochs" in impact.locked:
            continue
        chilled += await cold_snap(ctx, impact.world_id, ctx.rules.impacts.winter_cold, "An impact winter")
        impact.winter_epochs -= 1
    return chilled


async def call_impact(ctx: TickContext, world_id: int, region_id: int | None, by_node_id: int | None, by: str, *, size: int | None = None) -> ImpactEventRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    impact = await schedule(ctx, world, ImpactBody.CALLED, size=size if size is not None else ctx.rules.impacts.called_size, called_by=by_node_id)
    if region_id is not None:
        region = await ctx.session.get(EntityRow, region_id)
        if region is None or region.world_id != world.id or region.entity_type is not EntityType.REGION:
            raise ValidationFailedError("An impact falls on a region of its own world.")
        impact.region_entity_id = region.id
    await note(ctx, f"{by} called a body down upon {world.name}.", key="impact.called", world_id=world.id, kind=ChronicleKind.MIRACLE)
    await ctx.session.flush()
    return impact


async def deflect_impact(ctx: TickContext, impact_id: int, by_node_id: int | None, by: str) -> ImpactEventRow:
    impact = await ctx.session.get(ImpactEventRow, impact_id)
    if impact is None:
        raise NotFoundError("No such impact.")
    if impact.outcome is not PENDING:
        raise ValidationFailedError("That body has already struck or passed.")
    impact.outcome = ImpactOutcome.DEFLECTED
    impact.deflected_by_node_id = by_node_id
    world = await ctx.session.get(WorldRow, impact.world_id)
    impact.text = f"{by} turned the body aside from {world.name if world is not None else 'its world'}."
    await note(ctx, impact.text, key="impact.deflected", world_id=impact.world_id, kind=ChronicleKind.MIRACLE)
    await ctx.session.flush()
    return impact
