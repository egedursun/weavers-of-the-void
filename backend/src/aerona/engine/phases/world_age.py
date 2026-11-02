from dataclasses import dataclass

from sqlalchemy import or_, select

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
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.stats import stat
from aerona.prompts.filters import ordinal


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


async def enter_golden_age(ctx: TickContext, world: WorldRow, communities: list[EntityRow], announce: bool) -> None:
    rules = ctx.rules
    golden = await flags_by_entity(ctx.session, EntityFlag.GOLDEN_AGE)
    newly = not any(community.id in golden for community in communities)
    for community in communities:
        await add_flag(ctx.session, community.id, EntityFlag.GOLDEN_AGE, ctx.epoch)
        add_prosperity(rules, community, rules.deep_life.golden_age_prosperity_gain)
        society = await ctx.session.get(CommunitySocietyRow, community.id)
        if society is not None and society.golden_age_since_epoch is None:
            society.golden_age_since_epoch = ctx.epoch
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


async def world_age(ctx: TickContext, new_epoch: int) -> WorldAge:
    rules = ctx.rules
    world_rules = rules.deep_world
    relief = 0
    golden_worlds = 0
    if new_epoch % world_rules.era_turn_interval == 0:
        relief += world_rules.era_turn_apocalypse_push
        await note(
            ctx,
            f"Epoch turning: the world entered its {ordinal(new_epoch)} epoch. The seers closed the old accounts; fears subsided for a while.",
            key="world_age.epoch_turning",
            kind=ChronicleKind.WORLD_AGE,
        )
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        age = new_epoch - (world.created_epoch or 1)
        if age > 0 and age % world_rules.world_age_step == 0:
            relief += rules.deep_life.world_age_apocalypse_push
            await note(
                ctx,
                f"{world.name} is {age} epochs old: its mountains have worn down, its rivers have changed their beds; it is an old world now.",
                key="world_age.old_world",
                kind=ChronicleKind.WORLD_AGE,
                world_id=world.id,
            )
        communities = await canon(ctx.session, SOCIETY_TYPES, world.id)
        if not communities:
            continue
        golden = (
            not await world_at_war(ctx, world, new_epoch)
            and average_prosperity(ctx, communities) >= world_rules.golden_age_prosperity
            and age >= rules.deep_life.golden_age_min_world_age
        )
        if golden:
            golden_worlds += 1
            await enter_golden_age(ctx, world, communities, announce=True)
        else:
            await end_golden_age_in(ctx, world, communities)
    return WorldAge(golden_worlds=golden_worlds, relief=relief)


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
