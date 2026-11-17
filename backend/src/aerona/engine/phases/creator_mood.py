from dataclasses import replace

from aerona.engine.context import TickContext
from aerona.engine.divine.creator import passion_sign, taboo_wrath
from aerona.engine.gods.mood import compute_mood_update, gather_mood_inputs, mood_of, store_breakdown, store_mood
from aerona.engine.gods.queries import cosmos_row, creator_row
from aerona.engine.gods.signs import estranged_turn, grace_sign, lonely_dream, silence, wrath_sign
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_percent


@reads(
    "knowledge.spread",
    "people.prosperity",
    "settlement.prosperity",
    "table.action_records",
    "table.bonds",
    "table.cosmos",
    "table.creator",
    "table.creator_mood_inputs",
    "table.creator_taboos",
    "table.entities",
    "table.entity_flags",
    "table.messages",
    "table.nodes",
    "table.resurrection_orders",
    "table.sons",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.creator",
    "table.creator_mood_inputs",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.sons",
)
async def creator_mood(ctx: TickContext) -> None:
    creator = await creator_row(ctx.session)
    cosmos = await cosmos_row(ctx.session)
    if creator is None or cosmos is None:
        return
    rules = ctx.rules.creator
    rng = ctx.rng("signs")
    gathered = await gather_mood_inputs(ctx.session, ctx.rules, ctx.epoch - 1, cosmos.doom_clock)
    temper = ctx.rng("temperament")
    inputs = replace(gathered, temperament_roll=temper.random(), anger_roll=temper.random(), content_roll=temper.random())
    update = compute_mood_update(ctx.rules, mood_of(creator), inputs)
    store_mood(creator, update.state)
    await store_breakdown(ctx.session, ctx.epoch, update.breakdown)
    if creator.mood_anger >= rules.wrath_threshold and rng.chance(rules.wrath_sign_chance):
        await wrath_sign(ctx, creator)
    if creator.mood_contentment >= rules.content_threshold and rng.chance(rules.content_sign_chance) and await grace_sign(ctx, creator) is not None:
        creator.mood_contentment = clamp_percent(creator.mood_contentment - rules.content_discharge)
    if creator.mood_interest <= rules.indifferent_threshold:
        await silence(ctx, creator, rng.chance(rules.silence_sign_chance))
    if creator.mood_loneliness >= rules.lonely_threshold and rng.chance(rules.loneliness_sign_chance):
        await lonely_dream(ctx, creator)
    await estranged_turn(ctx, creator)
    await passion_sign(ctx, creator)
    await taboo_wrath(ctx, creator)
    await ctx.session.flush()


PHASES = (Phase("creator_mood", creator_mood),)
