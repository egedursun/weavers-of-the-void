from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.ecology.anatomy import ensure_anatomy
from aerona.engine.ecology.beasts import champions, deify, fallen, lair_cycle, living_beasts
from aerona.engine.ecology.biochemistry import seed_world_life
from aerona.engine.ecology.domestication import husbandry
from aerona.engine.ecology.flora import CropBook, blight, breed_cultivars, flora_backfill, gather_wild, link_pests, plant_backfill, sow
from aerona.engine.ecology.monsters import emerge_from_deep, roam_void
from aerona.engine.ecology.necromancy import necromancy
from aerona.engine.ecology.pets import adopt_pets, tend_pets
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
    "table.applied_fixups",
    "table.beast_profiles",
    "table.bonds",
    "table.community_societies",
    "table.creature_anatomy",
    "table.currencies",
    "table.entity_flags",
    "table.entity_traits",
    "table.house_members",
    "table.memories",
    "table.region_environment",
    "table.resource_profiles",
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
    "table.applied_fixups",
    "table.beast_profiles",
    "table.bonds",
    "table.chronicle",
    "table.community_stocks",
    "table.creature_anatomy",
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
    ctx.count("anatomies", await ensure_anatomy(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    ctx.count("monsters_emerged", await emerge_from_deep(ctx, atlas))
    for beast, row in await living_beasts(ctx):
        if held(beast.id):
            continue
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
    ctx.count("void_roamed", await roam_void(ctx, atlas))


@reads(
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.crop_pests",
    "table.entity_traits",
    "table.outbreaks",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_yields",
    "table.world_biochemistries",
    "table.world_seasons",
)
@writes("table.applied_fixups", "table.plant_profiles", "table.region_crops", "table.world_biochemistries")
async def flora_cycles(ctx: TickContext) -> None:
    ctx.count("world_life", await seed_world_life(ctx.session))
    for key, value in (await flora_backfill(ctx)).items():
        ctx.count(f"backfill_{key}", value)
    ctx.count("plant_profiles", await plant_backfill(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    book = await CropBook.load(ctx.session, ctx.rules)
    for key, value in (await gather_wild(ctx, book, atlas)).items():
        ctx.count(key, value)
    for key, value in (await sow(ctx, book, atlas)).items():
        ctx.count(key, value)
    ctx.count("cultivars", await breed_cultivars(ctx, book, atlas))
    ctx.count("pests_linked", await link_pests(ctx, book))
    ctx.count("crops_blighted", await blight(ctx, book))


HUSBANDRY_PHASES = (Phase("husbandry", husbandry_cycles), Phase("flora_cycles", flora_cycles))


@reads("table.bonds", "table.herds")
async def pet_cycles(ctx: TickContext) -> None:
    ctx.count("pets_taken", await adopt_pets(ctx))
    tally = await tend_pets(ctx)
    for key in ("mourned", "orphaned", "comforted", "hunted"):
        ctx.count(f"pets_{key}", getattr(tally, key))


@reads("table.bonds")
async def necromancy_cycles(ctx: TickContext) -> None:
    tally = await necromancy(ctx)
    for key in ("towers", "hosts", "sieges"):
        ctx.count(f"necromancy_{key}", getattr(tally, key))


BEAST_PHASES = (Phase("beast_cycles", beast_cycles), Phase("pet_cycles", pet_cycles), Phase("necromancy_cycles", necromancy_cycles))
PHASES = HUSBANDRY_PHASES + BEAST_PHASES
