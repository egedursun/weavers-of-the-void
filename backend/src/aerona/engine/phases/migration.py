from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.settlements import resettle_ruin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.society import stock
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat
from aerona.language.generator import NameKind

MIGRANT_SUBTYPE = "migrant settlement"


async def is_hungry(ctx: TickContext, community: EntityRow) -> bool:
    effects = ctx.rules.world_effects
    food = await stock(ctx.session, ctx.rules, community.id, Commodity.FOOD)
    prosperity = stat(community, "prosperity")
    return food < effects.hungry_food or (prosperity if prosperity is not None else effects.unknown_prosperity) < effects.famine_prosperity


async def greener_region(ctx: TickContext, atlas: RegionAtlas, region: EntityRow) -> EntityRow | None:
    effects = ctx.rules.world_effects
    own = stat(region, "fertility")
    floor = (own if own is not None else effects.unknown_fertility) + effects.famine_fertility_margin
    best: EntityRow | None = None
    for neighbour_id in atlas.neighbour_regions(region.id):
        neighbour = await living_entity(ctx.session, neighbour_id)
        if neighbour is None or neighbour.entity_type is not EntityType.REGION or neighbour.world_id != region.world_id or atlas.is_water(neighbour.id):
            continue
        fertility = stat(neighbour, "fertility")
        value = fertility if fertility is not None else effects.unknown_fertility
        if value > floor and (best is None or value > (stat(best, "fertility") or effects.unknown_fertility)):
            best = neighbour
    return best


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


async def famine_migration(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    moved = 0
    for community in await canon(ctx.session, [EntityType.SETTLEMENT, EntityType.PEOPLE]):
        if moved >= effects.famine_migration_cap:
            return
        population = stat(community, "population") or 0
        if community.status is not EntityStatus.CANON or population <= effects.famine_migration_min_population:
            continue
        if not await is_hungry(ctx, community) or not rng.chance(rules.world_engine.famine_migration_chance):
            continue
        region = await living_entity(ctx.session, atlas.top_region(community.id))
        target = await greener_region(ctx, atlas, region) if region is not None else None
        if target is None:
            continue
        migrants = round_half_up(population * rules.deep_world.famine_migration_share_pct / PERCENT)
        settlement, rebuilt = await migrate(ctx, atlas, community, target, migrants=migrants, reason="famine")
        moved += 1
        if rebuilt:
            text = f"Famine drove {migrants} people from {community.name} to the lands of {target.name}; they rebuilt the ruin of {settlement.name}."
        else:
            text = f"Famine drove {migrants} people from {community.name} to the lands of {target.name}; there they founded a new settlement."
        await note(ctx, text, key="migration.famine", ids=[community.id, settlement.id, target.id])


PHASES = (Phase("famine_migration", famine_migration),)
