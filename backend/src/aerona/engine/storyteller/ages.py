from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.genesis import TURNING_CYCLES
from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import AgeEchoRow, AgeRow, ArcRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountKind
from aerona.domain.enums.cosmography import ApocalypseVariant
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.phases.civilization import reveal_previous_creation
from aerona.engine.primitives.queries import add_flag, connect
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record as record_incident
from aerona.engine.storyteller.arcs import open_arc

CARRIED_KINDS = (EntityType.LEGEND, EntityType.PROPHECY)


@dataclass
class AgeTally:
    opened: int = 0
    reborn: int = 0
    turned: int = 0


async def current_age(ctx: TickContext) -> AgeRow | None:
    return await ctx.session.scalar(select(AgeRow).where(AgeRow.ended_epoch.is_(None)).order_by(AgeRow.number.desc()).limit(1))


async def ensure_age(ctx: TickContext, tally: AgeTally) -> AgeRow:
    row = await current_age(ctx)
    if row is not None:
        return row
    last = await ctx.session.scalar(select(AgeRow.number).order_by(AgeRow.number.desc()).limit(1))
    row = AgeRow(number=(last or 0) + 1, began_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    tally.opened += 1
    return row


def faded(value: int | None, carried: int) -> int:
    return (value or 0) * carried // PERCENT


async def carry_lore(ctx: TickContext, carried: int) -> int:
    count = 0
    lore = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_(CARRIED_KINDS), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.power_level.desc(), EntityRow.id)
    )
    for item in list(lore):
        holder = item.affiliated_entity_id or item.location_id
        if holder is None or held(item.id):
            continue
        ctx.session.add(
            AccountRow(
                holder_entity_id=holder, kind=AccountKind.FOLK_MEMORY, subject_node_id=item.id, fidelity=carried, credence=carried, epoch=ctx.epoch, locked=[]
            )
        )
        if item.entity_type is EntityType.LEGEND:
            set_stats(item, spread=faded(stat(item, "spread"), carried))
        else:
            set_stats(item, certainty=faded(stat(item, "certainty"), carried))
        count += 1
    return count


async def lose_knowledge(ctx: TickContext, world_ids: list[int], carried: int) -> int:
    lost = 0
    knowledge = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON, EntityRow.world_id.in_(world_ids))
        .order_by(EntityRow.id)
    )
    for item in list(knowledge):
        if held(item.id) or ctx.rng(f"age.lost.{item.id}.{ctx.epoch}").chance(carried):
            continue
        if await add_flag(ctx.session, item.id, EntityFlag.LOST, ctx.epoch):
            lost += 1
    return lost


async def seed_echoes(ctx: TickContext, ended: AgeRow, opened: AgeRow) -> int:
    table = ctx.rules.ages
    made = 0
    great = await ctx.session.scalars(select(MortalProfileRow).order_by(MortalProfileRow.renown.desc(), MortalProfileRow.entity_id))
    for profile in great:
        if made >= table.echoes_per_age:
            break
        arc = await ctx.session.scalar(
            select(ArcRow).where(ArcRow.subject_node_id == profile.entity_id, ArcRow.started_epoch >= ended.began_epoch).order_by(ArcRow.id.desc()).limit(1)
        )
        if arc is None:
            continue
        ctx.session.add(AgeEchoRow(age_id=opened.id, template=arc.template, source_node_id=profile.entity_id, weight=table.echo_weight, locked=[]))
        made += 1
    await ctx.session.flush()
    return made


async def turn_age(ctx: TickContext, variant: ApocalypseVariant | None) -> AgeRow:
    tally = AgeTally()
    ended = await ensure_age(ctx, tally)
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    carried = PERCENT - ctx.rules.ages.spiral_change_pct if cosmos.age_cycle is AgeCycle.SPIRAL else ctx.rules.ages.carry_pct
    ended.ended_epoch = ctx.epoch
    ended.variant = variant
    ended.carried = carried
    opened = AgeRow(number=ended.number + 1, began_epoch=ctx.epoch, locked=[])
    ctx.session.add(opened)
    await ctx.session.flush()
    worlds = [world for world in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)) if not held(world.id)]
    for world in worlds:
        await reveal_previous_creation(ctx, world)
    lore = await carry_lore(ctx, carried)
    lost = await lose_knowledge(ctx, [world.id for world in worlds], carried)
    echoes = await seed_echoes(ctx, ended, opened)
    await record_incident(
        ctx,
        "ages.turned",
        roles={IncidentRole.SUBJECT: tuple(world.id for world in worlds)},
        facts={"age": opened.number, "tales": lore, "arts_lost": lost, "echoes": echoes},
    )
    return opened


async def newborns(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.birth_epoch >= ctx.epoch - 1)
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def rebirth(ctx: TickContext, age: AgeRow, tally: AgeTally) -> None:
    table = ctx.rules.ages
    waiting = list(await ctx.session.scalars(select(AgeEchoRow).where(AgeEchoRow.age_id == age.id, AgeEchoRow.echo_node_id.is_(None)).order_by(AgeEchoRow.id)))
    taken: set[int] = set(await ctx.session.scalars(select(AgeEchoRow.echo_node_id).where(AgeEchoRow.echo_node_id.is_not(None))))
    for born in await newborns(ctx):
        if not waiting:
            return
        if born.id in taken or not ctx.rng(f"age.rebirth.{born.id}").chance(table.rebirth_chance):
            continue
        echo = waiting.pop(0)
        echo.echo_node_id = born.id
        taken.add(born.id)
        await open_arc(ctx, born.id, echo.template, echo_id=echo.id)
        if echo.source_node_id is not None and echo.source_node_id != born.id:
            await connect(ctx.session, echo.source_node_id, born.id, BondKind.SOUL_DESCENDED_TO, ctx.epoch, description="echoed into a new age")
        tally.reborn += 1
        await record_incident(
            ctx,
            "ages.echo",
            roles={IncidentRole.SUBJECT: born.id, IncidentRole.PREDECESSOR: echo.source_node_id},
            facts={
                "template": echo.template,
            },
        )


async def keep_ages(ctx: TickContext, tally: AgeTally) -> None:
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    if cosmos.age_cycle not in TURNING_CYCLES:
        return
    age = await ensure_age(ctx, tally)
    period = ctx.rules.ages.period_epochs
    if period and ctx.epoch - age.began_epoch >= period and "ended_epoch" not in age.locked:
        age = await turn_age(ctx, None)
        tally.turned += 1
    await rebirth(ctx, age, tally)
    await ctx.session.flush()
