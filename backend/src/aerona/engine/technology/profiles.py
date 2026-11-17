from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.technology import ERA_LEVEL, FAMILY_BRANCHES, FAMILY_TECHNIQUES
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.technology import TECH_LEVEL_MAX, TechnologyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import chosen_levels, world_start
from aerona.engine.lore.research import techniques_of
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.terms import explaining_alone, term


def derived(levels: dict[KnowledgeBranch, int], known: set[Technique], family: TechFamily) -> int:
    branch = max((levels.get(item, 0) for item in FAMILY_BRANCHES[family]), default=0)
    craft = sum(1 for technique in FAMILY_TECHNIQUES[family] if technique in known)
    return clamp_int(branch + craft // 2, 0, TECH_LEVEL_MAX)


async def family_level(session: AsyncSession, holder_id: int | None, family: TechFamily) -> int:
    if holder_id is None:
        return 0
    entity = await session.get(EntityRow, holder_id)
    people = await people_of(session, entity) if entity is not None else None
    for owner in (holder_id, people.id if people is not None else None, entity.world_id if entity is not None else None):
        if owner is None:
            continue
        row = await session.get(TechnologyProfileRow, (owner, family))
        if row is not None:
            return row.level
    levels = (await known_levels(session, [holder_id])).get(holder_id, {})
    return derived(levels, await techniques_of(session, holder_id), family)


async def keep_peoples(ctx: TickContext) -> int:
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    levels = await known_levels(ctx.session, peoples)
    moved = 0
    for people in peoples:
        if held(people):
            continue
        known = await techniques_of(ctx.session, people)
        for family in TechFamily:
            level = derived(levels.get(people, {}), known, family)
            row = await ctx.session.get(TechnologyProfileRow, (people, family))
            if row is None:
                ctx.session.add(TechnologyProfileRow(holder_node_id=people, family=family, level=level, updated_epoch=ctx.epoch, locked=[]))
                moved += 1
            elif "level" not in row.locked and row.level != level:
                with explaining_alone():
                    term("technology.known_level", level, source_node_id=people)
                    row.level, row.updated_epoch = level, ctx.epoch
                moved += 1
    return moved


async def seed_worlds(ctx: TickContext) -> int:
    baseline = ERA_LEVEL[await world_start(ctx.session)]
    chosen = await chosen_levels(ctx.session)
    seeded = 0
    for world in list(await ctx.session.scalars(select(WorldRow.id).order_by(WorldRow.id))):
        if held(world) or await ctx.session.get(TechnologyProfileRow, (world, TechFamily.AGRICULTURE)) is not None:
            continue
        for family in TechFamily:
            level = chosen.get(family, baseline)
            ctx.session.add(TechnologyProfileRow(holder_node_id=world, family=family, level=level, updated_epoch=ctx.epoch, locked=[]))
        seeded += 1
    return seeded


async def keep_technology(ctx: TickContext) -> None:
    ctx.count("technology_worlds_seeded", await seed_worlds(ctx))
    ctx.count("technology_profiles_moved", await keep_peoples(ctx))
    await ctx.session.flush()
