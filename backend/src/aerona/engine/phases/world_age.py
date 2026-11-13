from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityFlag
from aerona.domain.enums.war import WarStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.holds import GOLDEN_AGE_KEY, is_held
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.stats import set_stats, stat
from aerona.prompts.filters import ordinal
from aerona.rules.registry import Rules

DECADENT_KEYS = ("martiality", "defense")


@dataclass(frozen=True)
class WorldAge:
    golden_worlds: int
    relief: int


async def world_at_war(ctx: TickContext, world: WorldRow, new_epoch: int) -> bool:
    for bond in await active_bonds(ctx.session, [BondKind.ENEMY]):
        source = await living_entity(ctx.session, bond.source_node_id)
        target = await living_entity(ctx.session, bond.target_node_id)
        if source is not None and target is not None and source.world_id == world.id and {source.entity_type, target.entity_type} <= COMMUNITY_TYPES:
            return True
    peace = ctx.rules.deep_world.golden_age_peace_epochs
    recent = await ctx.session.scalar(
        select(WarRow.id).where(WarRow.world_id == world.id, or_(WarRow.status != WarStatus.ENDED, WarRow.ended_epoch > new_epoch - peace)).limit(1)
    )
    return recent is not None


def average_prosperity(ctx: TickContext, communities: list[EntityRow]) -> float:
    default = ctx.rules.society.default_stat
    values = [value if (value := stat(community, "prosperity")) is not None else default for community in communities]
    return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True)
class GoldenAgeEffect:
    prosperity: int
    decadence: int


def golden_age_effect(rules: Rules, since_epoch: int | None, epoch: int) -> GoldenAgeEffect:
    life = rules.deep_life
    lasted = max(0, epoch - since_epoch) if since_epoch is not None else 0
    steps = min(life.golden_age_deepening_steps, lasted // life.golden_age_deepening_epochs)
    soft = life.golden_age_decadence_epochs > 0 and lasted >= life.golden_age_decadence_epochs
    return GoldenAgeEffect(
        prosperity=life.golden_age_prosperity_gain + steps * life.golden_age_deepening_gain, decadence=life.golden_age_decadence_loss if soft else 0
    )


def wear_softness(community: EntityRow, loss: int) -> None:
    for key in DECADENT_KEYS:
        value = stat(community, key)
        if value is not None:
            set_stats(community, **{key: clamp_int(value - loss, 0, PERCENT)})


async def enter_golden_age(ctx: TickContext, world: WorldRow, communities: list[EntityRow], announce: bool) -> None:
    rules = ctx.rules
    golden = await flags_by_entity(ctx.session, EntityFlag.GOLDEN_AGE)
    newly = not any(community.id in golden for community in communities)
    softened = 0
    for community in communities:
        await add_flag(ctx.session, community.id, EntityFlag.GOLDEN_AGE, ctx.epoch)
        society = await ctx.session.get(CommunitySocietyRow, community.id)
        if society is not None and society.golden_age_since_epoch is None:
            society.golden_age_since_epoch = ctx.epoch
        effect = golden_age_effect(rules, society.golden_age_since_epoch if society is not None else ctx.epoch, ctx.epoch)
        add_prosperity(rules, community, effect.prosperity)
        if effect.decadence:
            wear_softness(community, effect.decadence)
            softened += 1
    ctx.count("golden_age_softened", softened)
    if newly and announce:
        links = [community.id for community in communities[: rules.deep_life.golden_age_record_links]]
        await note(
            ctx,
            f"{world.name} entered a golden age: wars are forgotten, granaries are full, masters are doing their finest work.",
            key="world_age.golden_age",
            ids=links,
            kind=ChronicleKind.WORLD_AGE,
        )


async def end_golden_age_in(ctx: TickContext, world: WorldRow, communities: list[EntityRow]) -> bool:
    ended = False
    began: list[int] = []
    for community in communities:
        ended = await remove_flag(ctx.session, community.id, EntityFlag.GOLDEN_AGE) or ended
        society = await ctx.session.get(CommunitySocietyRow, community.id)
        if society is not None and society.golden_age_since_epoch is not None:
            began.append(society.golden_age_since_epoch)
            society.golden_age_since_epoch = None
    if ended:
        span = f" It lasted {ctx.epoch - min(began)} epochs." if began and ctx.epoch > min(began) else ""
        await note(
            ctx,
            f"{world.name}'s golden age has ended.{span}",
            key="world_age.golden_age_ended",
            ids=[community.id for community in communities[:1]],
            kind=ChronicleKind.WORLD_AGE,
        )
    return ended


@dataclass(frozen=True)
class WorldVerdict:
    world: WorldRow
    age: int
    old: bool
    communities: list[EntityRow]
    golden: bool
    held: bool


@dataclass(frozen=True)
class AgeReading:
    turning: bool
    verdicts: list[WorldVerdict]
    golden_worlds: int
    relief: int


async def read_world_age(ctx: TickContext, new_epoch: int) -> AgeReading:
    rules = ctx.rules
    world_rules = rules.deep_world
    turning = new_epoch % world_rules.era_turn_interval == 0
    relief = world_rules.era_turn_apocalypse_push if turning else 0
    verdicts: list[WorldVerdict] = []
    flagged = await flags_by_entity(ctx.session, EntityFlag.GOLDEN_AGE)
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        age = new_epoch - (world.created_epoch or 1)
        old = age > 0 and age % world_rules.world_age_step == 0
        if old:
            relief += rules.deep_life.world_age_apocalypse_push
        communities = await canon(ctx.session, SOCIETY_TYPES, world.id)
        if not communities:
            verdicts.append(WorldVerdict(world=world, age=age, old=old, communities=[], golden=False, held=False))
            continue
        if await is_held(ctx.session, world.id, GOLDEN_AGE_KEY, ctx.epoch):
            golden = any(community.id in flagged for community in communities)
            verdicts.append(WorldVerdict(world=world, age=age, old=old, communities=communities, golden=golden, held=True))
            continue
        golden = (
            not await world_at_war(ctx, world, new_epoch)
            and average_prosperity(ctx, communities) >= world_rules.golden_age_prosperity
            and age >= rules.deep_life.golden_age_min_world_age
        )
        verdicts.append(WorldVerdict(world=world, age=age, old=old, communities=communities, golden=golden, held=False))
    return AgeReading(turning=turning, verdicts=verdicts, golden_worlds=sum(1 for verdict in verdicts if verdict.golden), relief=relief)


def age_of(reading: AgeReading) -> WorldAge:
    return WorldAge(golden_worlds=reading.golden_worlds, relief=reading.relief)


async def world_age(ctx: TickContext, new_epoch: int) -> WorldAge:
    reading = await read_world_age(ctx, new_epoch)
    if reading.turning:
        await note(
            ctx,
            f"Epoch turning: the world entered its {ordinal(new_epoch)} epoch. The seers closed the old accounts; fears subsided for a while.",
            key="world_age.epoch_turning",
            kind=ChronicleKind.WORLD_AGE,
        )
    for verdict in reading.verdicts:
        world = verdict.world
        if verdict.old:
            await note(
                ctx,
                f"{world.name} is {verdict.age} epochs old: its mountains have worn down, its rivers have changed their beds; it is an old world now.",
                key="world_age.old_world",
                kind=ChronicleKind.WORLD_AGE,
                world_id=world.id,
            )
        if not verdict.communities:
            continue
        if verdict.held:
            if verdict.golden:
                await enter_golden_age(ctx, world, verdict.communities, announce=False)
            continue
        if verdict.golden:
            await enter_golden_age(ctx, world, verdict.communities, announce=True)
        else:
            await end_golden_age_in(ctx, world, verdict.communities)
    return age_of(reading)


async def proclaim_golden_age(ctx: TickContext, world_id: int) -> int:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    communities = await canon(ctx.session, SOCIETY_TYPES, world.id)
    if not communities:
        raise ValidationFailedError(f"{world.name} has no peoples or settlements to enjoy a golden age.")
    await enter_golden_age(ctx, world, communities, announce=True)
    return len(communities)


async def end_golden_age(ctx: TickContext, world_id: int) -> bool:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return await end_golden_age_in(ctx, world, await canon(ctx.session, SOCIETY_TYPES, world.id))


@dataclass(frozen=True)
class GoldenAgeStatus:
    active: bool
    since_epoch: int | None
    epochs: int
    prosperity_gain: int
    decadence: int
    held: bool
    communities: int
    golden_communities: int


async def golden_age_status(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> GoldenAgeStatus:
    communities = await canon(session, SOCIETY_TYPES, world_id)
    flagged = await flags_by_entity(session, EntityFlag.GOLDEN_AGE)
    golden = [community for community in communities if community.id in flagged]
    starts = [
        society.golden_age_since_epoch
        for community in golden
        if (society := await session.get(CommunitySocietyRow, community.id)) is not None and society.golden_age_since_epoch is not None
    ]
    since = min(starts) if starts else None
    effect = golden_age_effect(rules, since, epoch) if golden else GoldenAgeEffect(prosperity=0, decadence=0)
    return GoldenAgeStatus(
        active=bool(golden),
        since_epoch=since,
        epochs=max(0, epoch - since) if since is not None else 0,
        prosperity_gain=effect.prosperity,
        decadence=effect.decadence,
        held=await is_held(session, world_id, GOLDEN_AGE_KEY, epoch),
        communities=len(communities),
        golden_communities=len(golden),
    )


async def date_golden_age(session: AsyncSession, world_id: int, since_epoch: int) -> int:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    flagged = await flags_by_entity(session, EntityFlag.GOLDEN_AGE)
    dated = 0
    for community in await canon(session, SOCIETY_TYPES, world.id):
        society = await session.get(CommunitySocietyRow, community.id) if community.id in flagged else None
        if society is not None:
            society.golden_age_since_epoch = since_epoch
            dated += 1
    if not dated:
        raise ValidationFailedError(f"{world.name} is not in a golden age; proclaim one first.")
    await session.flush()
    return dated
