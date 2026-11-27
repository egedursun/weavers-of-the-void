from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import MOURNING_RITE, REMEMBRANCE_DAY
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.lore import traditions
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, seed_core_world
from tests.engine.cosmos.factories import tick


async def test_a_rite_the_world_began_is_kept_as_what_it_was_begun_as(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, Rules())
    kinds = {}
    for subtype in (MOURNING_RITE, REMEMBRANCE_DAY, "a custom of its own"):
        rite = await entity(session, f"Rite {len(kinds)}", EntityType.TRADITION, TraditionStats(), world_id=world.world.id, origin=EntityOrigin.ENGINE)
        rite.subtype = subtype
        kinds[subtype] = (await traditions.profile_of(ctx, rite)).kind
    assert kinds == {
        MOURNING_RITE: TraditionFunction.MOURNING,
        REMEMBRANCE_DAY: TraditionFunction.COMMEMORATION,
        "a custom of its own": TraditionFunction.FESTIVAL,
    }
