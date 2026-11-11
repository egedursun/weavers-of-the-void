from aerona.engine.arcana.grammar import ensure_all
from aerona.engine.arcana.items import ChargeTally, recharge_all
from aerona.engine.arcana.labs import StudyTally, study
from aerona.engine.arcana.longevity import LongevityTally, tend_longevity
from aerona.engine.arcana.vis import VisTally, flow_vis
from aerona.engine.arcana.warping import WarpTally, warp_world
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.lab_texts", "table.rite_grammar", "table.rite_profiles")
@writes("table.rite_grammar")
async def spell_grammar(ctx: TickContext) -> None:
    ctx.count("grammar_shaped", await ensure_all(ctx))
    tally = StudyTally()
    await study(ctx, tally)
    count(ctx, "lab", tally)


@reads("table.item_enchantments", "table.magic_sites", "table.vis_stocks")
@writes("table.vis_stocks")
async def vis(ctx: TickContext) -> None:
    tally = VisTally()
    await flow_vis(ctx, tally)
    count(ctx, "vis", tally)
    charges = ChargeTally()
    await recharge_all(ctx, charges)
    count(ctx, "charges", charges)


@reads("table.ley_lines", "table.warping")
async def warping(ctx: TickContext) -> None:
    tally = WarpTally()
    await warp_world(ctx, tally)
    count(ctx, "warp", tally)


@reads("table.longevity")
async def longevity(ctx: TickContext) -> None:
    tally = LongevityTally()
    await tend_longevity(ctx, tally)
    count(ctx, "longevity", tally)


PHASES = (
    Phase("spell_grammar", spell_grammar),
    Phase("vis", vis),
    Phase("warping", warping),
    Phase("longevity", longevity),
)
