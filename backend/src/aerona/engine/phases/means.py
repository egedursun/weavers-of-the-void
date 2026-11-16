from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.means.containers import ContainerTally, keep_containers
from aerona.engine.means.media import MediaTally, keep_media
from aerona.engine.means.navigation import NavigationTally, keep_navigation
from aerona.engine.means.security import SecurityTally, keep_security
from aerona.engine.means.water import WaterTally, build_lifts
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.artwork_profiles",
    "table.book_contents",
    "table.community_stocks",
    "table.holder_levels",
    "table.holder_techniques",
    "table.item_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.region_environment",
    "table.writing_customs",
    "table.written_works",
)
@writes("table.writing_customs", "table.written_works")
async def written_media(ctx: TickContext) -> None:
    tally = MediaTally()
    await keep_media(ctx, tally)
    count(ctx, "written_media", tally)


@reads("table.securities", "table.skills", "table.structure_profiles")
@writes("table.securities")
async def vaults(ctx: TickContext) -> None:
    tally = SecurityTally()
    await keep_security(ctx, tally)
    count(ctx, "vaults", tally)


@reads("table.polity_members", "table.polity_profiles", "table.region_environment", "table.resource_profiles", "table.water_lifts")
@writes("table.chronicle", "table.chronicle_entities", "table.epoch_year_cursors", "table.incident_participants", "table.incidents", "table.water_lifts")
async def water_lifting(ctx: TickContext) -> None:
    tally = WaterTally()
    await build_lifts(ctx, tally)
    count(ctx, "water_lifting", tally)


@reads("table.navigation_kits", "table.skills", "table.trade_route_profiles", "table.worlds")
@writes("table.navigation_kits")
async def pilots(ctx: TickContext) -> None:
    tally = NavigationTally()
    await keep_navigation(ctx, tally)
    count(ctx, "pilots", tally)


@reads("table.community_stocks", "table.container_stocks", "table.skills")
@writes("table.community_stocks", "table.container_stocks", "table.goods_flows")
async def vessels_of_trade(ctx: TickContext) -> None:
    tally = ContainerTally()
    await keep_containers(ctx, tally)
    count(ctx, "containers", tally)


PHASES = (
    Phase("written_media", written_media),
    Phase("vaults", vaults),
    Phase("water_lifting", water_lifting),
    Phase("pilots", pilots),
    Phase("containers", vessels_of_trade),
)
