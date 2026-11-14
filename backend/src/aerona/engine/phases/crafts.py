from aerona.engine.context import TickContext
from aerona.engine.crafts.aids import AidTally, keep_aids
from aerona.engine.crafts.chemistry import ChemistryTally, keep_chemistry
from aerona.engine.crafts.clocks import ClockTally, keep_clocks
from aerona.engine.crafts.games import GameTally, keep_games
from aerona.engine.crafts.grounds import GroundTally, keep_grounds
from aerona.engine.crafts.insurance import InsuranceTally, keep_insurance
from aerona.engine.crafts.numbers import NumberTally, keep_numbers
from aerona.engine.crafts.rights import RightsTally, keep_rights
from aerona.engine.crafts.spirits import SpiritTally, keep_spirits
from aerona.engine.crafts.sympathy import SympathyTally, keep_sympathy
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.catch_grounds",
    "table.chemical_works",
    "table.cooperatives",
    "table.holder_techniques",
    "table.house_members",
    "table.incorporeal_rights",
    "table.insurers",
    "table.public_clocks",
    "table.resource_profiles",
    "table.species_ranges",
)
@writes("table.incorporeal_rights")
async def trades(ctx: TickContext) -> None:
    grounds, chemistry, insurance, rights, clocks = GroundTally(), ChemistryTally(), InsuranceTally(), RightsTally(), ClockTally()
    await keep_grounds(ctx, grounds)
    await keep_chemistry(ctx, chemistry)
    await keep_insurance(ctx, insurance)
    await keep_rights(ctx, rights)
    await keep_clocks(ctx, clocks)
    count(ctx, "grounds", grounds)
    count(ctx, "chemistry", chemistry)
    count(ctx, "insurance", insurance)
    count(ctx, "incorporeal", rights)
    count(ctx, "clocks", clocks)


@reads(
    "table.assistive_aids",
    "table.conditions",
    "table.epoch_year_cursors",
    "table.game_followings",
    "table.games",
    "table.holder_techniques",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.number_systems",
    "table.offices",
    "table.skills",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.game_followings",
    "table.games",
    "table.incident_participants",
    "table.incidents",
    "table.number_systems",
)
async def learning_aids(ctx: TickContext) -> None:
    aids, games, numbers = AidTally(), GameTally(), NumberTally()
    await keep_aids(ctx, aids)
    await keep_games(ctx, games)
    await keep_numbers(ctx, numbers)
    count(ctx, "aids", aids)
    count(ctx, "games", games)
    count(ctx, "numeracy", numbers)


@reads(
    "region.magic",
    "table.accusations",
    "table.emotion_spirits",
    "table.material_affinities",
    "table.rite_effects",
    "table.sympathetic_links",
    "table.thoughts",
    "table.world_materials",
)
async def sympathies(ctx: TickContext) -> None:
    sympathy, spirits = SympathyTally(), SpiritTally()
    await keep_sympathy(ctx, sympathy)
    await keep_spirits(ctx, spirits)
    count(ctx, "sympathy", sympathy)
    count(ctx, "emotion_spirits", spirits)


PHASES = (
    Phase("trades", trades),
    Phase("learning_aids", learning_aids),
    Phase("sympathies", sympathies),
)
