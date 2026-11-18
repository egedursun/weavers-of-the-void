from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.lore import LEGEND_MORALS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.context import TickContext
from aerona.engine.dominion.effects import scale_here
from aerona.engine.environment.perils import haunt_factor
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import add_flag, canon, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record


async def land_of_the_dead(ctx: TickContext) -> WorldRow | None:
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        if WORLD_TYPES[world.world_type].realm_of_dead:
            return world
    return None


async def lay_to_rest(ctx: TickContext, spirit: EntityRow, reason: str) -> None:
    await retire(ctx.session, spirit, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", close_bonds=True)


@reads("spirit.unrest", "table.bonds", "table.entities", "table.entity_flags", "table.nodes", "table.routes", "table.worlds")
@writes("spirit.unrest", "table.bonds", "table.chronicle", "table.entities", "table.entity_flags", "table.incident_facts", "table.incidents")
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
        death = max(0, -await scale_here(ctx, spirit.id, DivineScale.GROWTH)) * rules.dominion.spirit_unrest_per_step
        unrest = clamp_int((current if current is not None else life.spirit_default_unrest) - world_rules.spirit_unrest_decay + death, 0, PERCENT)
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
    if rested or (crossed and dead_world is not None):
        await record(
            ctx,
            "spirits.rest",
            roles={IncidentRole.DESTINATION: dead_world.id if crossed and dead_world is not None else None},
            facts={
                "rested": rested,
                "crossed": crossed if dead_world is not None else 0,
                "told": "; ".join(
                    part
                    for part in (
                        f"{several(rested, 'spirit', 'spirits')} came to rest" if rested else "",
                        f"{several(crossed, 'spirit', 'spirits')} crossed to {dead_world.name}, the land of the dead"
                        if crossed and dead_world is not None
                        else "",
                    )
                    if part
                ),
            },
        )
    ctx.count("rested", rested)
    ctx.count("crossed", crossed)


@reads(
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.region_environment",
    "table.region_memories",
    "table.spirit_profiles",
    "table.world_maps",
)
@writes(
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.name_registry",
)
async def hauntings(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    settlements = unheld(await canon(ctx.session, [EntityType.SETTLEMENT]))
    for spirit in unheld(await canon(ctx.session, [EntityType.SPIRIT])):
        unrest = stat(spirit, "unrest") or 0
        if unrest < rules.apocalypse.restless_threshold:
            continue
        avenged = await killers_home(ctx, spirit)
        haunted = next((settlement for settlement in settlements if settlement.id == avenged), None) or next(
            (settlement for settlement in settlements if atlas.same_region(spirit.id, settlement.id)), None
        )
        if haunted is None or not rng.chance(rules.world_engine.spirit_haunt_chance * await haunt_factor(ctx.session, rules, atlas.top_region(haunted.id))):
            continue
        prosperity = stat(haunted, "prosperity")
        set_stats(
            haunted, prosperity=clamp_int((prosperity if prosperity is not None else effects.unknown_prosperity) - effects.haunt_prosperity_loss, 0, PERCENT)
        )
        set_stats(spirit, unrest=clamp_int(unrest - effects.haunt_unrest_drop, 0, PERCENT))
        await record(
            ctx, "spirits.haunting", roles={IncidentRole.SUBJECT: [spirit.id, haunted.id]}, facts={"spirit": str(spirit.name), "haunted": str(haunted.name)}
        )
        legend, born = await ghost_legend(ctx, spirit, haunted)
        if born:
            await record(
                ctx,
                "spirits.ghost_legend",
                roles={IncidentRole.SUBJECT: [legend.id, spirit.id, haunted.id]},
                facts={"haunted": str(haunted.name), "spirit": str(spirit.name), "legend": str(legend.name)},
            )


async def ghost_legend(ctx: TickContext, spirit: EntityRow, haunted: EntityRow) -> tuple[EntityRow, bool]:
    table = ctx.rules.spirits
    row = await ctx.session.scalar(
        select(LegendProfileRow)
        .join(EntityRow, EntityRow.id == LegendProfileRow.legend_entity_id)
        .where(
            LegendProfileRow.archetype == LegendArchetype.HAUNTED_PLACE,
            LegendProfileRow.subject_node_id == spirit.id,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(LegendProfileRow.legend_entity_id)
        .limit(1)
    )
    if row is not None:
        if "credence" not in row.locked:
            row.credence = clamp_int(row.credence + table.haunt_legend_gain, 0, PERCENT)
        if haunted.id not in row.tellers:
            row.tellers = [*row.tellers, haunted.id]
            await connect(ctx.session, haunted.id, row.legend_entity_id, BondKind.CELEBRATES, ctx.epoch, description="tells the ghost story")
        legend = await ctx.session.get(EntityRow, row.legend_entity_id)
        if legend is not None:
            return legend, False
    legend = await create_record(
        ctx,
        RecordSpec(
            name=f"The Haunting of {haunted.name}",
            entity_type=EntityType.LEGEND,
            stats=LegendStats(spread=table.haunt_legend_credence),
            body=f"The people of {haunted.name} tell how {spirit.name} haunts them.",
            power=max(1, spirit.power_level),
            world_id=haunted.world_id,
            location_id=haunted.id,
        ),
    )
    await connect(ctx.session, legend.id, spirit.id, BondKind.TELLS_OF, ctx.epoch, description="a ghost story")
    await connect(ctx.session, haunted.id, legend.id, BondKind.CELEBRATES, ctx.epoch, description="tells the ghost story")
    ctx.session.add(
        LegendProfileRow(
            legend_entity_id=legend.id,
            archetype=LegendArchetype.HAUNTED_PLACE,
            credence=table.haunt_legend_credence,
            distortion=0,
            subject_node_id=spirit.id,
            moral={axis.value: value for axis, value in LEGEND_MORALS[LegendArchetype.HAUNTED_PLACE].items()},
            tellers=[haunted.id],
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    return legend, True


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
    await record(ctx, "spirits.laid_to_rest", roles={IncidentRole.SUBJECT: spirit.id})
    return spirit


REST_PHASES = (Phase("spirits_rest", spirits_rest),)
HAUNT_PHASES = (Phase("hauntings", hauntings),)
PHASES = REST_PHASES + HAUNT_PHASES
