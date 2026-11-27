from aerona.engine.context import TickContext
from aerona.engine.dominion.core import DominionTally, weigh_dominion
from aerona.engine.dominion.creatures import CreatureTally, act_creatures
from aerona.engine.dominion.image import ImageTally, shape_gods
from aerona.engine.dominion.sites import SiteTally, meet_and_fail, search_sites, seed_sites, seed_thrones, tend_thrones, yield_sites
from aerona.engine.dominion.worship import WorshipTally, view_worship
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas


def count(ctx: TickContext, prefix: str, tally: object) -> None:
    for key, value in vars(tally).items():
        ctx.count(f"{prefix}_{key}", value)


@reads(
    "table.bonds",
    "table.creator",
    "table.dimensions",
    "table.divine_standing",
    "table.dominions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.place_profiles",
    "table.region_dominion",
    "table.sons",
    "table.stars",
    "table.thrones",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.divine_standing",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.sons",
    "table.thrones",
)
async def thrones(ctx: TickContext) -> None:
    tally = SiteTally()
    await seed_thrones(ctx, tally)
    await tend_thrones(ctx, tally)
    count(ctx, "throne", tally)


@reads(
    "table.community_stocks",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.magic_sites",
    "table.node_births",
    "table.nodes",
    "table.place_profiles",
    "table.routes",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.magic_sites",
    "table.place_profiles",
)
async def magic_sites(ctx: TickContext) -> None:
    tally = SiteTally()
    await seed_sites(ctx, tally)
    await search_sites(ctx, await RegionAtlas.load(ctx.session), tally)
    await yield_sites(ctx, tally)
    await meet_and_fail(ctx, tally)
    count(ctx, "magic_site", tally)


@reads(
    "mortal.age",
    "mortal.lifespan",
    "people.population",
    "settlement.population",
    "table.action_records",
    "table.bonds",
    "table.creator",
    "table.cult_holdings",
    "table.dimensions",
    "table.dominions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.incident_participants",
    "table.incidents",
    "table.mind_facets",
    "table.minds",
    "table.miracle_records",
    "table.modifiers",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.place_profiles",
    "table.region_dominion",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.thoughts",
    "table.thrones",
    "table.traits",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.dominions",
    "table.god_designs",
    "table.god_scales",
    "table.incident_participants",
    "table.incidents",
    "table.modifiers",
    "table.mortal_profiles",
    "table.node_births",
    "table.region_dominion",
    "table.thoughts",
)
async def dominion(ctx: TickContext) -> None:
    tally = DominionTally()
    await weigh_dominion(ctx, tally)
    count(ctx, "dominion", tally)


@reads(
    "people.piety",
    "settlement.piety",
    "table.culture_values",
    "table.divine_standing",
    "table.entities",
    "table.messages",
    "table.nodes",
    "table.structure_profiles",
)
@writes("people.piety", "settlement.piety", "table.divine_standing", "table.entities")
async def worship_views(ctx: TickContext) -> None:
    tally = WorshipTally()
    await view_worship(ctx, tally)
    count(ctx, "worship", tally)


@reads(
    "table.bonds",
    "table.divine_standing",
    "table.entities",
    "table.folk_beliefs",
    "table.foreign_gods",
    "table.god_images",
    "table.incidents",
    "table.mind_facets",
    "table.miracle_records",
    "table.modifiers",
    "table.nodes",
    "table.pressures",
    "table.sons",
    "table.war_sides",
    "table.wars",
)
@writes("table.god_images", "table.sons")
async def god_images(ctx: TickContext) -> None:
    tally = ImageTally()
    await shape_gods(ctx, tally)
    count(ctx, "image", tally)


@reads("table.bonds", "table.deep_passages", "table.divine_creatures")
async def divine_creatures(ctx: TickContext) -> None:
    tally = CreatureTally()
    await act_creatures(ctx, tally)
    count(ctx, "creature", tally)


PHASES = (
    Phase("thrones", thrones),
    Phase("magic_sites", magic_sites),
    Phase("dominion", dominion),
    Phase("worship_views", worship_views),
    Phase("god_images", god_images),
    Phase("divine_creatures", divine_creatures),
)
