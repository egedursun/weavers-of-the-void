from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import climate_fit, profiles_of
from aerona.engine.demography.urban import town_pull_factor
from aerona.engine.disease.load import endemic_repel
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.legends import haunted_regions
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.drives import closeness, hunger
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.settlements import resettle_ruin
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.society import stock
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat
from aerona.engine.services.community_relations import relation
from aerona.language.generator import NameKind

MIGRANT_SUBTYPE = "migrant settlement"


async def is_hungry(ctx: TickContext, community: EntityRow) -> bool:
    effects = ctx.rules.world_effects
    food = await stock(ctx.session, ctx.rules, community.id, Commodity.FOOD)
    prosperity = stat(community, "prosperity")
    return food < effects.hungry_food or (prosperity if prosperity is not None else effects.unknown_prosperity) < effects.famine_prosperity


def walkable(ctx: TickContext, ground: EnvironmentBook | None, region_id: int) -> int:
    env = ground.regions.get(region_id) if ground is not None else None
    if ground is None or env is None:
        return PERCENT
    season = ground.travel_season(env.world_id)
    return ground.footed(ctx.environment.world_seed, ctx.epoch, env, MovementMode.ON_FOOT.value, season=season, slot=f"migration.{region_id}")


async def kin_pull(ctx: TickContext, atlas: RegionAtlas, origin: EntityRow | None, region_id: int) -> float:
    if origin is None:
        return 1.0
    settled = [entity_id for entity_id in atlas.communities_in(region_id) if entity_id != origin.id]
    if not settled:
        return 1.0
    nearest = max([await closeness(ctx.session, origin.id, entity_id) for entity_id in settled])
    warmest = max([await relation(ctx.session, ctx.rules, origin.id, entity_id) for entity_id in settled])
    welcome = max(0.0, 1 + warmest / PERCENT * ctx.rules.culture_drift.migration_opinion_pct / PERCENT)
    return (1 + (nearest - 1) * ctx.rules.culture_drift.migration_kinship_pct / PERCENT) * welcome


async def town_pull(ctx: TickContext, atlas: RegionAtlas, region_id: int, origin: EntityRow | None = None, culture: PeopleCultureRow | None = None) -> float:
    best = 0.0
    for entity_id in atlas.communities_in(region_id):
        town = await ctx.session.get(SettlementProfileRow, entity_id)
        settlement = await living_entity(ctx.session, entity_id)
        if town is None or settlement is None:
            continue
        values = await culture_of(ctx.session, entity_id)
        openness = (values.get(ValueAxis.XENOPHILIA, 0) + PERCENT) / (2 * PERCENT)
        jobs = 1.0 if (stat(settlement, "population") or 0) < town.construction_capacity * PERCENT else 0.5
        pull = ((stat(settlement, "prosperity") or 0) / PERCENT + town.public_order / PERCENT + openness + jobs) / 4
        pull *= 1 + town.prestige * ctx.rules.districts.prestige_pull_pct / PERCENT / PERCENT
        best = max(best, pull)
    welcome = 1.0
    for entity_id in atlas.communities_in(region_id):
        if await law_param(ctx.session, entity_id, LawKind.FOREIGNER_RIGHTS, "level") == "citizenship":
            welcome = 1 + ctx.rules.legislation.foreigner_pull_pct / PERCENT
            break
    return (
        (1 + best * town_pull_factor(ctx.rules, culture) * ctx.rules.urban.migration_pull_pct / PERCENT)
        * welcome
        * await endemic_repel(ctx.session, ctx.rules, region_id, origin.id if origin is not None else None)
    )


async def greener_region(
    ctx: TickContext, atlas: RegionAtlas, region: EntityRow, ground: EnvironmentBook | None = None, origin: EntityRow | None = None
) -> EntityRow | None:
    effects = ctx.rules.world_effects
    own = stat(region, "fertility")
    floor = (own if own is not None else effects.unknown_fertility) + effects.famine_fertility_margin
    best: tuple[float, EntityRow] | None = None
    haunted = {atlas.top_region(place) or place for place in await haunted_regions(ctx)}
    biology, culture = await profiles_of(ctx.session, origin) if origin is not None else (None, None)
    for neighbour_id in atlas.neighbour_regions(region.id):
        if neighbour_id in haunted:
            continue
        neighbour = await living_entity(ctx.session, neighbour_id)
        if neighbour is None or neighbour.entity_type is not EntityType.REGION or neighbour.world_id != region.world_id or atlas.is_water(neighbour.id):
            continue
        passable = walkable(ctx, ground, neighbour.id)
        if passable < ctx.rules.world_effects.migration_passable_min:
            continue
        fertility = stat(neighbour, "fertility")
        value = fertility if fertility is not None else effects.unknown_fertility
        appeal = (
            value
            * (PERCENT + passable)
            / (2 * PERCENT)
            * await kin_pull(ctx, atlas, origin, neighbour.id)
            * await town_pull(ctx, atlas, neighbour.id, origin, culture)
        )
        env = ground.regions.get(neighbour.id) if ground is not None else None
        appeal *= climate_fit(ctx.rules, biology, env.temperature_band if env is not None else None)
        if value > floor and (best is None or appeal > best[0]):
            best = (appeal, neighbour)
    return best[1] if best is not None else None


async def migrate(ctx: TickContext, atlas: RegionAtlas, source: EntityRow, target: EntityRow, *, migrants: int, reason: str) -> tuple[EntityRow, bool]:
    effects = ctx.rules.world_effects
    floor, cap = headcount_bounds(ctx.rules, source)
    set_stats(source, population=max(floor, min(cap, (stat(source, "population") or 0) - migrants)))
    ruin = await resettle_ruin(ctx, target, source, migrants, reason, atlas=atlas)
    if ruin is not None:
        settlement = ruin
    else:
        name = await Namer(ctx.session, ctx.rules).from_speaker(source.id, seed_of(source.id, ctx.epoch, "migration"), NameKind.PLACE)
        settlement = await open_record(
            ctx.session,
            ctx.epoch,
            RecordSpec(
                entity_type=EntityType.SETTLEMENT,
                name=name or f"{source.name} Migrants",
                body=f"{migrants} people fleeing {reason} from {source.name} migrated to the lands of {target.name} and founded a new settlement.",
                stats=SettlementStats(population=migrants, prosperity=effects.migrant_prosperity, defense=effects.migrant_defense, piety=effects.migrant_piety),
                power=max(effects.split_min_power, source.power_level - 1),
                location_id=target.id,
                world_id=target.world_id,
                subtype=MIGRANT_SUBTYPE,
                flags=[EntityFlag.NAME_FROM_LANGUAGE] if name else [],
            ),
        )
        await connect(ctx.session, settlement.id, source.id, BondKind.DESCENDS_FROM, ctx.epoch, description="migrants")
        atlas.remember(settlement)
        await bind_language_and_faith(ctx, settlement, atlas, source)
    await connect(ctx.session, source.id, settlement.id, BondKind.MIGRATED_TO, ctx.epoch, description=f"{reason}: {migrants} people")
    return settlement, ruin is not None


@reads(
    "people.population",
    "region.fertility",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.calendars",
    "table.community_societies",
    "table.endemic_diseases",
    "table.forced_weather",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.immunities",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.legend_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.place_environment",
    "table.polity_members",
    "table.pressures",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sky_events",
    "table.world_maps",
    "table.world_seasons",
)
@writes(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
    "table.nodes",
)
async def famine_migration(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    ground = await EnvironmentBook.load(ctx.session, rules, ctx.epoch, atlas)
    moved = 0
    for community in await canon(ctx.session, [EntityType.SETTLEMENT, EntityType.PEOPLE]):
        if moved >= effects.famine_migration_cap:
            return
        population = stat(community, "population") or 0
        if community.status is not EntityStatus.CANON or population <= effects.famine_migration_min_population:
            continue
        level = await hunger(ctx.session, community.id) if await pressures_of(ctx.session, community.id) else None
        starving = level >= rules.needs.migration_hunger if level is not None else await is_hungry(ctx, community)
        weight = level / rules.needs.migration_hunger if level is not None and rules.needs.migration_hunger else 1
        if not starving or not rng.chance(rules.world_engine.famine_migration_chance * weight):
            continue
        region = await living_entity(ctx.session, atlas.top_region(community.id))
        target = await greener_region(ctx, atlas, region, ground, community) if region is not None else None
        if target is None:
            continue
        leaving = round_half_up(population * rules.deep_world.famine_migration_share_pct / PERCENT)
        lost = round_half_up(leaving * (PERCENT - walkable(ctx, ground, target.id)) * effects.migration_road_loss_pct / PERCENT / PERCENT)
        migrants = max(1, leaving - lost)
        if lost:
            floor, cap = headcount_bounds(rules, community)
            with flowing(FlowCategory.DEATH):
                set_stats(community, population=max(floor, min(cap, population - lost)))
        settlement, rebuilt = await migrate(ctx, atlas, community, target, migrants=migrants, reason="famine")
        moved += 1
        if rebuilt:
            text = f"Famine drove {migrants} people from {community.name} to the lands of {target.name}; they rebuilt the ruin of {settlement.name}."
        else:
            text = f"Famine drove {migrants} people from {community.name} to the lands of {target.name}; there they founded a new settlement."
        await note(ctx, text, key="migration.famine", ids=[community.id, settlement.id, target.id])


PHASES = (Phase("famine_migration", famine_migration),)
