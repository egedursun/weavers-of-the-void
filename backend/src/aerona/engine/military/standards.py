from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.military import OutcomeClass
from aerona.engine.body.variants import fear_of
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import hand_over
from aerona.engine.lore.items import standard_item
from aerona.engine.military.battle import BattleResult
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat

BROKEN_FIELDS = frozenset({OutcomeClass.ROUT, OutcomeClass.MASSACRE})


async def capture_standard(ctx: TickContext, war: WarRow, result: BattleResult, *, attacker_id: int) -> int | None:
    table = ctx.rules.army_depth
    winner, loser = result.winner, result.loser
    if winner is None or loser is None or result.refused or result.outcome not in BROKEN_FIELDS:
        return None
    armies = sorted({stack.row.army_entity_id for stack in loser.stacks})
    item_id = await standard_item(ctx, [loser.entity.id, *armies])
    if item_id is None or held(item_id):
        return None
    if not ctx.rng(f"standard.{war.id}.{war.battles}.{item_id}").chance(table.standard_capture_pct):
        return None
    await hand_over(ctx, item_id, winner.entity.id, ItemDeed.CAPTURED, f"standard taken on the field from {loser.entity.name}")
    profile = await ctx.session.get(ItemProfileRow, item_id)
    if profile is not None and "renown" not in profile.locked:
        profile.renown = clamp_int(profile.renown + table.standard_renown, 0, PERCENT)
    fear = await fear_of(ctx.session, loser.entity)
    for army_id in armies:
        army = await living_entity(ctx.session, army_id)
        if army is not None and not held(army_id):
            shift_stat(army, "morale", -table.standard_shock * fear)
    for stack in loser.stacks:
        if not held(stack.row.army_entity_id) and "morale" not in stack.row.locked:
            stack.row.morale = clamp_int(stack.row.morale - round_half_up(table.standard_shock * fear), 0, PERCENT)
    war.score += (1 if winner.entity.id == attacker_id else -1) * table.standard_score
    result.standard_taken = item_id
    return item_id
