from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext

HIDDEN_DISCOVERY = {Discovery.LEGEND: "only a legend", Discovery.UNKNOWN: "unknown"}


async def mark_world_discovered(ctx: TickContext, world: WorldRow, reason: str) -> bool:
    previous = world.discovery
    if previous not in HIDDEN_DISCOVERY:
        return False
    await WorldRepository(ctx.session).set_discovery(world, Discovery.KNOWN)
    await ctx.chronicle(
        ChronicleKind.COSMIC,
        f"{world.name} is no longer {HIDDEN_DISCOVERY[previous]}: {reason}.",
        template_key="cosmos.world_discovered",
        world_id=world.id,
        feed_category=FeedCategory.WORLD,
    )
    ctx.count("worlds_discovered")
    return True
