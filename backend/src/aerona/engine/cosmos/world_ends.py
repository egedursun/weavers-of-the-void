from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery, SkyEventKind, StarType, WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.enums.world_view import WorldLight
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import planet_of
from aerona.engine.cosmos.world_views import reset_view, view_of
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.notes import note
from aerona.engine.primitives.records import retire_in

E = WorldEnd
LIFELESS = frozenset({E.SHATTERED, E.CONSUMED, E.FROZEN_DEAD, E.SUNK_INTO_VOID})
GONE_FROM_SKY = frozenset({E.CONSUMED, E.SUNK_INTO_VOID, E.FORGOTTEN})
LIVES = frozenset(
    {
        EntityType.PEOPLE,
        EntityType.SETTLEMENT,
        EntityType.SPECIES,
        EntityType.CULT,
        EntityType.FACTION,
        EntityType.ARMY,
        EntityType.BEAST,
    }
)
HOME_BONDS = (BondKind.LIVES_IN, BondKind.DESCENDS_FROM)


@dataclass
class EndingTally:
    ended: int = 0
    frozen: int = 0


async def lives_end(ctx: TickContext, world: WorldRow, state: WorldEnd) -> int:
    ended = 0
    for mortal in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        )
    ):
        if held(mortal.id):
            continue
        await die(ctx, mortal, cause=f"died when {world.name} was {state.value.replace('_', ' ')}")
        ended += 1
    for life in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(list(LIVES)), EntityRow.status == EntityStatus.CANON)
        )
    ):
        if held(life.id):
            continue
        if state is E.FROZEN_DEAD and life.entity_type is EntityType.SETTLEMENT:
            await EntityRepository(ctx.session).add_flag(life.id, EntityFlag.RUIN, ctx.epoch)
        await retire_in(ctx, life, f"it ended when {world.name} was {state.value.replace('_', ' ')}", close_bonds=True)
        ended += 1
    return ended


async def peoples_abroad(ctx: TickContext, world: WorldRow) -> int:
    here = select(EntityRow.id).where(EntityRow.world_id == world.id)
    abroad = select(EntityRow.id).where(EntityRow.world_id != world.id, EntityRow.status == EntityStatus.CANON)
    bonds = list(
        await ctx.session.scalars(
            select(BondRow).where(
                BondRow.kind.in_(list(HOME_BONDS)),
                BondRow.state == BondState.ACTIVE,
                BondRow.target_node_id.in_(here),
                BondRow.source_node_id.in_(abroad),
            )
        )
    )
    cut = 0
    for bond in bonds:
        if held(bond.source_node_id):
            continue
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, f"{world.name} came to its end")
        cut += 1
    return cut


async def anchors_lost(ctx: TickContext, world: WorldRow) -> int:
    lost = 0
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    primary = cosmos.primary_world_id if cosmos.primary_world_id != world.id else None
    for son in list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id))):
        if held(son.id):
            continue
        anchor = await ctx.session.get(EntityRow, son.anchor_entity_id) if son.anchor_entity_id is not None else None
        if anchor is not None and anchor.world_id == world.id:
            son.anchor_entity_id = None
            lost += 1
        if son.current_world_id == world.id:
            son.current_world_id = primary
    for god in list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.world_id == world.id, ForeignGodRow.status == ForeignGodStatus.AWAKE))):
        if held(god.id):
            continue
        god.status = ForeignGodStatus.ASLEEP
        lost += 1
    return lost


async def end_world(ctx: TickContext, world: WorldRow, state: WorldEnd, cause: WorldEndCause, new_type: WorldType | None = None) -> WorldEndRow:
    row = await ctx.session.get(WorldEndRow, world.id)
    if row is None:
        row = WorldEndRow(world_id=world.id, state=state, cause=cause, epoch=ctx.epoch, former_type=world.world_type, locked=[])
        ctx.session.add(row)
    row.state, row.cause, row.epoch = state, cause, ctx.epoch
    repository = WorldRepository(ctx.session)
    if state in LIFELESS:
        row.lives_ended += await lives_end(ctx, world, state)
        row.anchors_lost += await anchors_lost(ctx, world)
        row.homeless += await peoples_abroad(ctx, world)
    if state in LIFELESS or state in GONE_FROM_SKY:
        for route in await repository.routes_touching(world.id, active_only=True):
            route.active = False
            row.routes_closed += 1
    if state in GONE_FROM_SKY:
        await repository.set_discovery(world, Discovery.FORGOTTEN)
    if state is E.SHATTERED:
        world.world_type = WorldType.SHATTERED
    if state is E.TRANSFIGURED and new_type is not None:
        row.new_type = new_type
        world.world_type = new_type
    if state in {E.SHATTERED, E.TRANSFIGURED}:
        await reset_view(ctx.session, ctx.rules, world, ctx.epoch)
    told = state.value.replace("_", " ")
    await note(
        ctx,
        f"{world.name} was {told} ({cause.value.replace('_', ' ')}): {row.lives_ended} lives ended, {row.homeless} homeward ties cut abroad.",
        key=f"world_end.{state.value}",
        kind=ChronicleKind.COSMIC,
        world_id=world.id,
    )
    await ctx.session.flush()
    return row


async def star_of(ctx: TickContext, world: WorldRow) -> StarRow | None:
    star_id = world.star_id
    if star_id is None and world.parent_world_id is not None:
        parent = await ctx.session.get(WorldRow, world.parent_world_id)
        star_id = parent.star_id if parent is not None else None
    return await ctx.session.get(StarRow, star_id) if star_id is not None else None


async def dark_since(ctx: TickContext, star: StarRow) -> int:
    fell = await ctx.session.scalar(
        select(func.max(SkyEventRow.epoch)).where(SkyEventRow.star_id == star.id, SkyEventRow.kind.in_([SkyEventKind.SUPERNOVA, SkyEventKind.BLACK_SUN]))
    )
    return int(fell) if fell is not None else star.created_epoch


async def frozen_under(ctx: TickContext, world: WorldRow) -> bool:
    star = await star_of(ctx, world)
    if star is None or star.star_type not in EXTINGUISHED_STAR_TYPES:
        return False
    if (await view_of(ctx.session, ctx.rules, world.id)).light is not WorldLight.STAR:
        return False
    return ctx.epoch - await dark_since(ctx, star) >= ctx.rules.world_ends.frozen_epochs


GIANTS = frozenset({StarType.RED_GIANT, StarType.YELLOW_GIANT, StarType.RED_SUPERGIANT, StarType.BLUE_SUPERGIANT, StarType.HYPERGIANT})
SOCIETIES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL)
Sign = Callable[[TickContext, WorldRow], Awaitable[bool]]


async def swallowed_by_giant(ctx: TickContext, world: WorldRow) -> bool:
    star = await star_of(ctx, world)
    if star is None or star.star_type not in GIANTS or ctx.epoch - star.created_epoch < ctx.rules.world_ends.giant_epochs:
        return False
    planet = await planet_of(ctx.session, world)
    return planet.orbit * PERCENT <= ctx.rules.world_ends.giant_reach_pct


async def struck(ctx: TickContext, world: WorldRow) -> bool:
    comet = await ctx.session.scalar(
        select(SkyEventRow.id).where(SkyEventRow.world_id == world.id, SkyEventRow.kind == SkyEventKind.COMET, SkyEventRow.epoch == ctx.epoch).limit(1)
    )
    return comet is not None and ctx.rng(f"world_end.impact.{world.id}.{ctx.epoch}").chance(ctx.rules.world_ends.impact_pct)


async def torn_open(ctx: TickContext, world: WorldRow) -> bool:
    rifts = await ctx.session.scalar(select(func.count()).select_from(RiftRow).where(RiftRow.world_id == world.id, RiftRow.state.in_(list(OPEN_RIFT_STATES))))
    return int(rifts or 0) >= ctx.rules.world_ends.void_rifts


async def forsaken(ctx: TickContext, world: WorldRow) -> bool:
    if ctx.epoch - world.created_epoch < ctx.rules.world_ends.forgotten_epochs:
        return False
    society = select(EntityRow.id).where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(SOCIETIES))
    living = await ctx.session.scalar(society.where(EntityRow.status == EntityStatus.CANON).limit(1))
    once = await ctx.session.scalar(society.where(EntityRow.status != EntityStatus.CANON).limit(1))
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    return living is None and once is not None and world.id != cosmos.primary_world_id


async def never_by_itself(_ctx: TickContext, _world: WorldRow) -> bool:
    return False


CAUSE_END: Mapping[WorldEndCause, WorldEnd] = total(
    WorldEndCause,
    {
        WorldEndCause.IMPACT: E.SHATTERED,
        WorldEndCause.DIVINE_WRATH: E.SHATTERED,
        WorldEndCause.STAR_GIANT: E.CONSUMED,
        WorldEndCause.STAR_DEATH: E.FROZEN_DEAD,
        WorldEndCause.VOID: E.SUNK_INTO_VOID,
        WorldEndCause.OBLIVION: E.FORGOTTEN,
        WorldEndCause.BELIEF_DRIFT: E.TRANSFIGURED,
    },
)
CAUSE_SIGN: Mapping[WorldEndCause, Sign] = total(
    WorldEndCause,
    {
        WorldEndCause.IMPACT: struck,
        WorldEndCause.DIVINE_WRATH: never_by_itself,
        WorldEndCause.STAR_GIANT: swallowed_by_giant,
        WorldEndCause.STAR_DEATH: frozen_under,
        WorldEndCause.VOID: torn_open,
        WorldEndCause.OBLIVION: forsaken,
        WorldEndCause.BELIEF_DRIFT: never_by_itself,
    },
)


async def keep_world_ends(ctx: TickContext, tally: EndingTally) -> None:
    ended = set(await ctx.session.scalars(select(WorldEndRow.world_id)))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id in ended or held(world.id):
            continue
        for cause, sign in CAUSE_SIGN.items():
            if CAUSE_END[cause] is E.TRANSFIGURED or not await sign(ctx, world):
                continue
            await end_world(ctx, world, CAUSE_END[cause], cause)
            tally.frozen += int(cause is WorldEndCause.STAR_DEATH)
            tally.ended += 1
            break
