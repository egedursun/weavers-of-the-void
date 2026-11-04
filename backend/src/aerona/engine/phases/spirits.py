from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import add_flag, canon, living_entity
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import set_stats, stat


async def land_of_the_dead(ctx: TickContext) -> WorldRow | None:
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        if WORLD_TYPES[world.world_type].realm_of_dead:
            return world
    return None


async def lay_to_rest(ctx: TickContext, spirit: EntityRow, reason: str) -> None:
    await retire(ctx.session, spirit, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", close_bonds=True)


@reads("spirit.unrest", "table.bonds", "table.entity_flags", "table.epoch_year_cursors", "table.nodes", "table.routes")
@writes("spirit.unrest", "table.bonds", "table.chronicle", "table.entities", "table.entity_flags", "table.epoch_year_cursors", "table.incidents")
async def spirits_rest(ctx: TickContext) -> None:
    rules = ctx.rules
    life = rules.deep_life
    world_rules = rules.deep_world
    rng = ctx.rng()
    dead_world = await land_of_the_dead(ctx)
    dead_regions = await canon(ctx.session, [EntityType.REGION], dead_world.id) if dead_world is not None else []
    rested = 0
    crossed = 0
    by_place: dict[int | None, list[EntityRow]] = defaultdict(list)
    for spirit in await canon(ctx.session, [EntityType.SPIRIT]):
        if spirit.origin is not EntityOrigin.ENGINE or spirit.engine_kind is EngineKind.GOD_SHADE:
            continue
        current = stat(spirit, "unrest")
        unrest = clamp_int((current if current is not None else life.spirit_default_unrest) - world_rules.spirit_unrest_decay, 0, PERCENT)
        set_stats(spirit, unrest=unrest)
        age = ctx.epoch - spirit.birth_epoch
        if age >= life.spirit_rest_min_age and unrest < world_rules.spirit_rest_threshold and rng.chance(world_rules.spirit_rest_chance):
            await lay_to_rest(ctx, spirit, "came to rest; no longer wanders")
            rested += 1
            continue
        if (
            dead_world is not None
            and dead_regions
            and spirit.world_id != dead_world.id
            and age >= life.spirit_passage_min_age
            and rng.chance(world_rules.spirit_passage_chance)
        ):
            await EntityRepository(ctx.session).move(spirit, rng.pick(dead_regions).id, ctx.epoch)
            spirit.map_x = None
            spirit.map_y = None
            await add_flag(ctx.session, spirit.id, EntityFlag.CROSSED_TO_THE_DEAD, ctx.epoch)
            crossed += 1
            continue
        by_place[spirit.location_id].append(spirit)
    for place, spirits in by_place.items():
        if place is None or len(spirits) <= world_rules.spirits_per_place_cap:
            continue
        ordered = sorted(spirits, key=lambda item: (stat(item, "unrest") or 0, item.birth_epoch, item.id))
        for spirit in ordered[: len(spirits) - world_rules.spirits_per_place_cap]:
            await lay_to_rest(ctx, spirit, "came to rest among the crowd of spirits")
            rested += 1
    parts = []
    if rested:
        parts.append(f"{rested} spirits came to rest")
    if crossed and dead_world is not None:
        parts.append(f"{crossed} spirits crossed to {dead_world.name}, the land of the dead")
    if parts:
        await note(ctx, "; ".join(parts) + ".", key="spirits.rest")
    ctx.count("rested", rested)
    ctx.count("crossed", crossed)


@reads("settlement.prosperity", "spirit.unrest", "table.bonds", "table.epoch_year_cursors", "table.spirit_profiles", "table.world_maps")
@writes(
    "settlement.prosperity",
    "spirit.unrest",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def hauntings(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    settlements = await canon(ctx.session, [EntityType.SETTLEMENT])
    for spirit in await canon(ctx.session, [EntityType.SPIRIT]):
        unrest = stat(spirit, "unrest") or 0
        if unrest < rules.apocalypse.restless_threshold:
            continue
        avenged = await killers_home(ctx, spirit)
        haunted = next((settlement for settlement in settlements if settlement.id == avenged), None) or next(
            (settlement for settlement in settlements if atlas.same_region(spirit.id, settlement.id)), None
        )
        if haunted is None or not rng.chance(rules.world_engine.spirit_haunt_chance):
            continue
        prosperity = stat(haunted, "prosperity")
        set_stats(
            haunted, prosperity=clamp_int((prosperity if prosperity is not None else effects.unknown_prosperity) - effects.haunt_prosperity_loss, 0, PERCENT)
        )
        set_stats(spirit, unrest=clamp_int(unrest - effects.haunt_unrest_drop, 0, PERCENT))
        await note(
            ctx, f"{spirit.name} haunted {haunted.name}; no one goes out into the streets at night.", key="spirits.haunting", ids=[spirit.id, haunted.id]
        )


async def killers_home(ctx: TickContext, spirit: EntityRow) -> int | None:
    profile = await ctx.session.get(SpiritProfileRow, spirit.id)
    if profile is None or profile.origin_mortal_id is None:
        return None
    killer_id = await ctx.session.scalar(
        select(BondRow.source_node_id).where(BondRow.target_node_id == profile.origin_mortal_id, BondRow.kind == BondKind.KILLED).order_by(BondRow.id).limit(1)
    )
    if killer_id is None:
        return None
    heir_id = await ctx.session.scalar(
        select(BondRow.target_node_id).where(BondRow.source_node_id == killer_id, BondRow.kind == BondKind.PARENT_OF).order_by(BondRow.id.desc()).limit(1)
    )
    kin = await ctx.session.get(EntityRow, heir_id or killer_id)
    return kin.location_id if kin is not None else None


async def lay_spirit_to_rest(ctx: TickContext, spirit_id: int) -> EntityRow:
    spirit = await living_entity(ctx.session, spirit_id)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT:
        raise ValidationFailedError("Only a wandering spirit can be laid to rest.")
    await lay_to_rest(ctx, spirit, "was laid to rest by the gods")
    await note(ctx, f"{spirit.name} was laid to rest; it wanders no more.", key="spirits.laid_to_rest", ids=[spirit.id])
    return spirit


REST_PHASES = (Phase("spirits_rest", spirits_rest),)
HAUNT_PHASES = (Phase("hauntings", hauntings),)
PHASES = REST_PHASES + HAUNT_PHASES
