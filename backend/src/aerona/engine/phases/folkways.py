from aerona.engine.context import TickContext
from aerona.engine.folkways.biases import BiasTally, keep_biases
from aerona.engine.folkways.mishaps import MishapTally, keep_mishaps
from aerona.engine.folkways.nutrition import NutritionTally, keep_nutrition
from aerona.engine.folkways.purity import PurityTally, keep_purity
from aerona.engine.folkways.witchcraft import WitchTally, keep_witchcraft
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.community_stocks",
    "table.diets",
    "table.holder_levels",
    "table.irregular_seasons",
    "table.mind_attributes",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.nutrient_needs",
    "table.nutrition_scores",
    "table.pressures",
)
@writes(
    "mortal.endurance",
    "mortal.strength",
    "table.diets",
    "table.entities",
    "table.mind_attributes",
    "table.mortal_profiles",
    "table.nutrient_needs",
    "table.nutrition_scores",
)
async def nutrition(ctx: TickContext) -> None:
    tally = NutritionTally()
    await keep_nutrition(ctx, tally)
    count(ctx, "nutrition", tally)


@reads("table.bias_weights", "table.bonds", "table.mortal_profiles")
@writes("table.bias_weights")
async def biases(ctx: TickContext) -> None:
    tally = BiasTally()
    await keep_biases(ctx, tally)
    count(ctx, "biases", tally)


@reads("table.culture_values", "table.impurity_sources")
async def purity(ctx: TickContext) -> None:
    tally = PurityTally()
    await keep_purity(ctx, tally)
    count(ctx, "purity", tally)


@reads(
    "table.castings",
    "table.charms",
    "table.goods_flows",
    "table.holder_levels",
    "table.impurity_sources",
    "table.luck_beliefs",
    "table.mishaps",
    "table.mortal_profiles",
    "table.notable_years",
    "table.outbreaks",
    "table.war_sides",
)
@writes("table.mishaps", "table.mortal_profiles")
async def mishaps(ctx: TickContext) -> None:
    tally = MishapTally()
    await keep_mishaps(ctx, tally)
    count(ctx, "mishaps", tally)


@reads("table.accusations", "table.mishaps", "table.witch_hunts")
async def witchcraft(ctx: TickContext) -> None:
    tally = WitchTally()
    await keep_witchcraft(ctx, tally)
    count(ctx, "witchcraft", tally)


PHASES = (
    Phase("nutrition", nutrition),
    Phase("biases", biases),
    Phase("purity", purity),
    Phase("mishaps", mishaps),
    Phase("witchcraft", witchcraft),
)
