from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import champions, deify, fallen, lair_cycle, living_beasts
from aerona.engine.ecology.domestication import husbandry
from aerona.engine.ecology.totems import adopt_totems
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.records import retire_in


@reads(
    "table.bonds",
    "table.community_stocks",
    "table.herds",
    "table.skills",
    "table.species_profiles",
    "table.species_uses",
    "table.species_yields",
    "table.world_maps",
)
@writes("table.bonds", "table.community_stocks", "table.entities", "table.herds", "table.species_profiles", "table.species_uses", "table.species_yields")
async def husbandry_cycles(ctx: TickContext) -> None:
    for key, value in (await husbandry(ctx)).items():
        ctx.count(key, value)
    ctx.count("totems", await adopt_totems(ctx))


@reads(
    "beast.strength",
    "beast.terror",
    "settlement.defense",
    "settlement.population",
    "species.danger",
    "table.beast_profiles",
    "table.entity_flags",
    "table.memories",
    "table.species_profiles",
    "table.species_ranges",
    "table.world_maps",
)
@writes(
    "beast.renown",
    "beast.terror",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "table.beast_profiles",
    "table.bonds",
    "table.community_stocks",
    "table.entities",
)
async def beast_cycles(ctx: TickContext) -> None:
    ctx.count("beasts_risen", await champions(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    for beast, row in await living_beasts(ctx):
        worshipped = await deify(ctx, atlas, beast, row)
        if worshipped:
            ctx.count("beasts_worshipped")
            await note(ctx, f"{worshipped[0].upper()}{worshipped[1:]}.", key="beasts.worshipped", ids=[beast.id])
        text = await lair_cycle(ctx, atlas, beast, row)
        if text == "old age":
            await retire_in(ctx, beast, "died of great age in its lair")
            ctx.count("beasts_aged_out")
        elif text:
            ctx.count("beast_deeds")
            await note(ctx, f"{text[0].upper()}{text[1:]}.", key="beasts.deed", ids=[beast.id])
    for told in await fallen(ctx):
        ctx.count("beasts_fallen")
        await note(ctx, f"{told}.", key="beasts.fallen", ids=[])


HUSBANDRY_PHASES = (Phase("husbandry", husbandry_cycles),)
BEAST_PHASES = (Phase("beast_cycles", beast_cycles),)
PHASES = HUSBANDRY_PHASES + BEAST_PHASES
