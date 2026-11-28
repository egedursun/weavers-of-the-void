from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life.cosmos import CAUSE_END, END_REMNANT, END_WORLD_WORLD_ENDS
from aerona.catalog.life_traits import WORLD_END_TRAITS, having
from aerona.catalog.planetary_cycles import CYCLES
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.divine import BreachPointRow, OuterBeingProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import WorldCycleRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.made import ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.evolution import CycleEffect
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.life_traits import WorldEndTrait
from aerona.domain.enums.made import ReplicatorStage
from aerona.domain.enums.mass_weapons import MassReach
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.outer import OuterFate
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery, SkyEventKind, StarType, WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.enums.world_view import WorldLight
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import planet_of
from aerona.engine.cosmos.world_views import reset_view, view_of
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record

E = WorldEnd
LIFELESS = having(WORLD_END_TRAITS, WorldEndTrait.LIFELESS)
GONE_FROM_SKY = having(WORLD_END_TRAITS, WorldEndTrait.GONE_FROM_SKY)
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

FERTILITY_KEY = "fertility"


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
        await die(ctx, mortal, cause=f"died when {world.name} was {spoken(state)}")
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
        await retire_in(ctx, life, f"it ended when {world.name} was {spoken(state)}", close_bonds=True)
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


async def end_world(
    ctx: TickContext, world: WorldRow, state: WorldEnd, cause: WorldEndCause, new_type: WorldType | None = None, *, source_node_id: int | None = None
) -> WorldEndRow:
    row = await ctx.session.get(WorldEndRow, world.id)
    if row is None:
        row = WorldEndRow(world_id=world.id, state=state, cause=cause, epoch=ctx.epoch, former_type=world.world_type, locked=[])
        ctx.session.add(row)
    row.state, row.cause, row.epoch, row.source_node_id = state, cause, ctx.epoch, source_node_id
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
    remnant = END_REMNANT[state]
    if remnant is not None:
        world.world_type = remnant
    if state is E.TRANSFIGURED and new_type is not None:
        row.new_type = new_type
        world.world_type = new_type
    if state in END_WORLD_WORLD_ENDS:
        await reset_view(ctx.session, ctx.rules, world, ctx.epoch)
    await record(
        ctx,
        f"world_end.{state.value}",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: source_node_id},
        facts={
            "end": state,
            "cause": cause,
            "lives": row.lives_ended,
            "homeless": row.homeless,
            "routes": row.routes_closed,
            "anchors": row.anchors_lost,
        },
        steps=(StepDraft(StepAction.END, target=world.id, outcome=StepOutcome.DESTROYED if state in LIFELESS else StepOutcome.SUCCESS),),
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


Sign = Callable[[TickContext, WorldRow], Awaitable[bool]]


CAUSE_SIGN: Handlers[WorldEndCause, Sign] = Handlers(WorldEndCause)


@CAUSE_SIGN.on(WorldEndCause.STAR_DEATH)
async def frozen_under(ctx: TickContext, world: WorldRow) -> bool:
    star = await star_of(ctx, world)
    if star is None or star.star_type not in EXTINGUISHED_STAR_TYPES:
        return False
    if (await view_of(ctx.session, ctx.rules, world.id)).light is not WorldLight.STAR:
        return False
    return ctx.epoch - await dark_since(ctx, star) >= ctx.rules.world_ends.frozen_epochs


GIANTS = frozenset({StarType.RED_GIANT, StarType.YELLOW_GIANT, StarType.RED_SUPERGIANT, StarType.BLUE_SUPERGIANT, StarType.HYPERGIANT})
SOCIETIES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL)


@CAUSE_SIGN.on(WorldEndCause.STAR_GIANT)
async def swallowed_by_giant(ctx: TickContext, world: WorldRow) -> bool:
    star = await star_of(ctx, world)
    if star is None or star.star_type not in GIANTS or ctx.epoch - star.created_epoch < ctx.rules.world_ends.giant_epochs:
        return False
    planet = await planet_of(ctx.session, world)
    return planet.orbit * PERCENT <= ctx.rules.world_ends.giant_reach_pct


@CAUSE_SIGN.on(WorldEndCause.IMPACT)
async def struck(ctx: TickContext, world: WorldRow) -> bool:
    comet = await ctx.session.scalar(
        select(SkyEventRow.id).where(SkyEventRow.world_id == world.id, SkyEventRow.kind == SkyEventKind.COMET, SkyEventRow.epoch == ctx.epoch).limit(1)
    )
    return comet is not None and ctx.rng(f"world_end.impact.{world.id}.{ctx.epoch}").chance(ctx.rules.world_ends.impact_pct)


@CAUSE_SIGN.on(WorldEndCause.VOID)
async def torn_open(ctx: TickContext, world: WorldRow) -> bool:
    rifts = await ctx.session.scalar(select(func.count()).select_from(RiftRow).where(RiftRow.world_id == world.id, RiftRow.state.in_(list(OPEN_RIFT_STATES))))
    return int(rifts or 0) >= ctx.rules.world_ends.void_rifts


@CAUSE_SIGN.on(WorldEndCause.OBLIVION)
async def forsaken(ctx: TickContext, world: WorldRow) -> bool:
    if ctx.epoch - world.created_epoch < ctx.rules.world_ends.forgotten_epochs:
        return False
    society = select(EntityRow.id).where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(SOCIETIES))
    living = await ctx.session.scalar(society.where(EntityRow.status == EntityStatus.CANON).limit(1))
    once = await ctx.session.scalar(society.where(EntityRow.status != EntityStatus.CANON).limit(1))
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    return living is None and once is not None and world.id != cosmos.primary_world_id


def runaway_end(ctx: TickContext, world: WorldRow, row: WorldCycleRow) -> WorldEnd | None:
    spec = CYCLES[row.cycle]
    if CycleEffect.GREENHOUSE in spec.moves:
        return E.BURNED
    if CycleEffect.SEA_LEVEL not in spec.moves:
        return None
    if spec.inverse:
        return E.FROZEN_DEAD
    return E.DROWNED if world.terrain_sea * PERCENT >= ctx.rules.world_ends.drowned_sea_pct else None


def past_its_band(ctx: TickContext, physics: WorldPhysicsRow | None, end: WorldEnd | None) -> bool:
    if end is None or physics is None:
        return end is not None
    table = ctx.rules.orbits
    if end is E.FROZEN_DEAD:
        return physics.surface_temperature < table.livable_low_kelvin
    if end is E.BURNED:
        return physics.surface_temperature > table.livable_high_kelvin
    return True


async def runaway_cycle(ctx: TickContext, world: WorldRow) -> WorldCycleRow | None:
    cycles = select(WorldCycleRow).where(WorldCycleRow.world_id == world.id, WorldCycleRow.stock >= ctx.rules.world_ends.runaway_stock)
    physics = await ctx.session.get(WorldPhysicsRow, world.id)
    return next(
        (row for row in await ctx.session.scalars(cycles.order_by(WorldCycleRow.cycle)) if past_its_band(ctx, physics, runaway_end(ctx, world, row))), None
    )


@CAUSE_SIGN.on(WorldEndCause.RUNAWAY_CLIMATE)
async def run_away(ctx: TickContext, world: WorldRow) -> bool:
    return await runaway_cycle(ctx, world) is not None


async def world_weapons(ctx: TickContext, world: WorldRow) -> list[MassWeaponRow]:
    holders = select(EntityRow.id).where(EntityRow.world_id == world.id)
    statement = select(MassWeaponRow).where(
        MassWeaponRow.reach == MassReach.WORLD, MassWeaponRow.used_epoch == ctx.epoch, MassWeaponRow.holder_entity_id.in_(holders)
    )
    return list(await ctx.session.scalars(statement.order_by(MassWeaponRow.id)))


@CAUSE_SIGN.on(WorldEndCause.WAR)
async def unmade_by_war(ctx: TickContext, world: WorldRow) -> bool:
    return len(await world_weapons(ctx, world)) >= ctx.rules.world_ends.war_weapons


async def starving_being(ctx: TickContext, world: WorldRow) -> int | None:
    table = ctx.rules.world_ends
    breached = select(BreachPointRow.outer_entity_id).where(BreachPointRow.world_id == world.id)
    statement = select(OuterBeingProfileRow.outer_entity_id).where(
        OuterBeingProfileRow.outer_entity_id.in_(breached),
        OuterBeingProfileRow.fate == OuterFate.ACTIVE,
        OuterBeingProfileRow.reach >= table.hunger_reach,
        OuterBeingProfileRow.unfed_epochs >= table.hunger_unfed_epochs,
    )
    found: int | None = await ctx.session.scalar(statement.order_by(OuterBeingProfileRow.outer_entity_id).limit(1))
    return found


@CAUSE_SIGN.on(WorldEndCause.OUTER_HUNGER)
async def devoured(ctx: TickContext, world: WorldRow) -> bool:
    return await starving_being(ctx, world) is not None


@CAUSE_SIGN.on(WorldEndCause.DIVINE_WRATH)
@CAUSE_SIGN.on(WorldEndCause.BELIEF_DRIFT)
async def never_by_itself(_ctx: TickContext, _world: WorldRow) -> bool:
    return False


@CAUSE_SIGN.on(WorldEndCause.PLAGUE)
async def emptied_by_plague(ctx: TickContext, world: WorldRow) -> bool:
    society = select(EntityRow.id).where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(SOCIETIES))
    living = await ctx.session.scalar(society.where(EntityRow.status == EntityStatus.CANON).limit(1))
    if living is not None or await ctx.session.scalar(society.where(EntityRow.status != EntityStatus.CANON).limit(1)) is None:
        return False
    regions = select(EntityRow.id).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.REGION)
    struck = await ctx.session.scalar(
        select(OutbreakRow.id)
        .where(
            OutbreakRow.region_entity_id.in_(regions), OutbreakRow.started_epoch >= ctx.epoch - ctx.rules.world_ends.epochs(ctx.rules.world_ends.plague_years)
        )
        .limit(1)
    )
    return struck is not None


async def runaway_lines(ctx: TickContext, world: WorldRow) -> list[ReplicatorLineRow]:
    places = select(EntityRow.id).where(EntityRow.world_id == world.id)
    lines = select(ReplicatorPresenceRow.line_id).where(ReplicatorPresenceRow.place_node_id.in_(places))
    return list(
        await ctx.session.scalars(
            select(ReplicatorLineRow).where(ReplicatorLineRow.id.in_(lines), ReplicatorLineRow.stage == ReplicatorStage.RUNAWAY).order_by(ReplicatorLineRow.id)
        )
    )


@CAUSE_SIGN.on(WorldEndCause.RUNAWAY_MAKING)
async def unmade_by_making(ctx: TickContext, world: WorldRow) -> bool:
    places = select(EntityRow.id).where(EntityRow.world_id == world.id)
    mass = await ctx.session.scalar(select(func.sum(ReplicatorPresenceRow.mass)).where(ReplicatorPresenceRow.place_node_id.in_(places)))
    return bool(await runaway_lines(ctx, world)) and int(mass or 0) >= ctx.rules.world_ends.runaway_making_mass


@CAUSE_SIGN.on(WorldEndCause.STRUCTURE_FAILURE)
async def structure_failed(ctx: TickContext, world: WorldRow) -> bool:
    if world.world_type is not WorldType.MEGASTRUCTURE:
        return False
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    if not regions:
        return False
    worn = sum(stat_or(region, FERTILITY_KEY, 0) for region in regions) / len(regions)
    return worn <= ctx.rules.world_ends.failure_fertility


CAUSE_SIGN.seal()


async def source_of(ctx: TickContext, world: WorldRow, cause: WorldEndCause) -> int | None:
    if cause is WorldEndCause.WAR:
        weapons = await world_weapons(ctx, world)
        return weapons[-1].holder_entity_id if weapons else None
    if cause is WorldEndCause.OUTER_HUNGER:
        return await starving_being(ctx, world)
    if cause is WorldEndCause.RUNAWAY_MAKING:
        lines = await runaway_lines(ctx, world)
        return lines[0].maker_node_id if lines else None
    return None


def ending_of(ctx: TickContext, world: WorldRow, cause: WorldEndCause, runaway: WorldCycleRow | None = None) -> WorldEnd:
    found = runaway_end(ctx, world, runaway) if runaway is not None else None
    if found is not None:
        return found
    if cause is WorldEndCause.IMPACT and world.parent_world_id is not None:
        return E.MERGED
    return CAUSE_END[cause]


async def keep_world_ends(ctx: TickContext, tally: EndingTally) -> None:
    ended = set(await ctx.session.scalars(select(WorldEndRow.world_id)))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id in ended or held(world.id):
            continue
        for cause, sign in CAUSE_SIGN.items():
            if CAUSE_END[cause] is E.TRANSFIGURED or not await sign(ctx, world):
                continue
            runaway = await runaway_cycle(ctx, world) if cause is WorldEndCause.RUNAWAY_CLIMATE else None
            await end_world(ctx, world, ending_of(ctx, world, cause, runaway), cause, source_node_id=await source_of(ctx, world, cause))
            tally.frozen += int(cause is WorldEndCause.STAR_DEATH)
            tally.ended += 1
            break
