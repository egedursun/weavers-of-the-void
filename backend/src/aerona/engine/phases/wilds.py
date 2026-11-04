from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import champions, deify, fallen, lair_cycle, living_beasts
from aerona.engine.ecology.domestication import husbandry
from aerona.engine.ecology.profiles import typed_nature_backfill
from aerona.engine.ecology.totems import adopt_totems, hunt_gods
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.records import retire_in


@reads(
    "table.applied_fixups",
    "table.bodies",
    "table.bonds",
    "table.community_stocks",
    "table.herds",
    "table.skills",
    "table.sons",
    "table.species_custom_uses",
    "table.species_profiles",
    "table.species_use_kinds",
    "table.species_uses",
    "table.species_yields",
    "table.tradition_profiles",
    "table.world_maps",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.community_stocks",
    "table.entities",
    "table.entity_traits",
    "table.herds",
    "table.species_profiles",
    "table.species_uses",
    "table.species_yields",
    "table.tradition_profiles",
)
async def husbandry_cycles(ctx: TickContext) -> None:
    ctx.count("typed_nature", await typed_nature_backfill(ctx))
    for key, value in (await husbandry(ctx)).items():
        ctx.count(key, value)
    ctx.count("totems", await adopt_totems(ctx))
    ctx.count("animal_gods", await hunt_gods(ctx))


@reads(
    "beast.strength",
    "beast.terror",
    "region.danger",
    "settlement.defense",
    "settlement.population",
    "species.danger",
    "table.beast_profiles",
    "table.bonds",
    "table.community_societies",
    "table.currencies",
    "table.entity_flags",
    "table.house_members",
    "table.memories",
    "table.region_environment",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_yields",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.war_sides",
    "table.world_maps",
)
@writes(
    "beast.renown",
    "beast.terror",
    "region.danger",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "table.beast_profiles",
    "table.bonds",
    "table.chronicle",
    "table.community_stocks",
    "table.currencies",
    "table.entities",
    "table.item_history",
    "table.item_profiles",
    "table.memories",
    "table.species_ranges",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
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
