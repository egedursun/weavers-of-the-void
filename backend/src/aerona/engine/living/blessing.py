from sqlalchemy import select

from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow, LivingProfileRow, SymbiontRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.living import Fertility
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect


async def line_in_world(ctx: TickContext, line_id: int, world_id: int | None) -> LivingLineRow | None:
    line = await ctx.session.get(LivingLineRow, line_id)
    if line is None or world_id is None:
        return None
    for node in (line.species_entity_id, line.owner_node_id, line.maker_node_id):
        entity = await ctx.session.get(EntityRow, node) if node is not None else None
        if entity is not None and entity.world_id == world_id:
            return line
    return None


async def bless_line(ctx: TickContext, line: LivingLineRow, god_id: int) -> LivingLineRow:
    table = ctx.rules.living_methods
    if "stability" not in line.locked:
        line.stability = clamp_percent(line.stability + table.unstable_drift * 2)
    if "fertility" not in line.locked and line.fertility is Fertility.STERILE:
        line.fertility = Fertility.BREEDS_TRUE
    for row in list(await ctx.session.scalars(select(LivingProfileRow).where(LivingProfileRow.line_id == line.id))):
        if not held(row.thing_node_id) and "health" not in row.locked:
            row.health = clamp_percent(row.health + ctx.rules.living.hunger_harm)
    if line.species_entity_id is not None:
        await connect(ctx.session, god_id, line.species_entity_id, BondKind.BLESSED, ctx.epoch, description=f"blessed the line {line.name}")
    await note(ctx, f"A god blessed the line {line.name}.", key="living.line_blessed", ids=[])
    return line


async def curse_line(ctx: TickContext, line: LivingLineRow, god_id: int) -> LivingLineRow:
    table = ctx.rules.living
    if "stability" not in line.locked:
        line.stability = clamp_percent(line.stability - ctx.rules.living_methods.unstable_drift * 2)
    for row in list(await ctx.session.scalars(select(LivingProfileRow).where(LivingProfileRow.line_id == line.id))):
        if not held(row.thing_node_id) and "health" not in row.locked:
            row.health = clamp_percent(row.health - table.blight_harm)
    for planting in list(await ctx.session.scalars(select(PerennialRow).where(PerennialRow.line_id == line.id))):
        if not held(planting.region_entity_id) and "condition" not in planting.locked:
            planting.condition = clamp_percent(planting.condition - table.blight_harm)
    for symbiont in list(await ctx.session.scalars(select(SymbiontRow).where(SymbiontRow.line_id == line.id))):
        if held(symbiont.host_node_id) or symbiont.locked:
            continue
        symbiont.strength = clamp_percent(symbiont.strength - table.blight_harm)
        if symbiont.strength <= 0:
            await ctx.session.delete(symbiont)
    if line.species_entity_id is not None:
        await connect(ctx.session, god_id, line.species_entity_id, BondKind.CURSED, ctx.epoch, description=f"cursed the line {line.name}")
    await note(ctx, f"A god cursed the line {line.name}.", key="living.line_cursed", ids=[])
    return line
