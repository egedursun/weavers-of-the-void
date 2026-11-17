from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.drink_roles import DRINK_ROLES
from aerona.db.tables.food_kinds import DrinkKindRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.kinds import DrinkCategory, DrinkRole, KindConcept, KindSpread, KindStance
from aerona.engine.cuisine.drinks import keep_drinks
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_foodways_w48 import people_with_town


async def keeps_drink(session: AsyncSession, people_id: int, role: DrinkRole, name: str) -> DrinkKindRow:
    drink = DrinkKindRow(name=name, category=DrinkCategory.INFUSION, role=role, origin_node_id=people_id, created_epoch=0, locked=[])
    session.add(drink)
    await session.flush()
    session.add(
        KindHoldingRow(
            concept=KindConcept.DRINK, kind_id=drink.id, holder_node_id=people_id, stance=KindStance.MAKES, strength=100, spread=KindSpread.INVENTED, locked=[]
        )
    )
    await session.flush()
    return drink


def test_every_drink_role_names_a_real_rule() -> None:
    rules = Rules().drink
    assert all(effect.rule is None or isinstance(getattr(rules, effect.rule), int) for effect in DRINK_ROLES.values())


async def test_a_drink_kept_for_rites_raises_piety_and_one_for_feasts_calms_unrest(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "foodways")
    rite_folk, rite_town = await people_with_town(session, world, "Ardan")
    feast_folk, feast_town = await people_with_town(session, world, "Belis", region=1)
    await keeps_drink(session, rite_folk.id, DrinkRole.RITE, "First")
    await keeps_drink(session, feast_folk.id, DrinkRole.FEAST, "Second")
    piety = stat(rite_town, "piety") or 0
    await keep_drinks(ctx)
    assert (stat(rite_town, "piety") or 0) > piety
    profile = await session.get(SettlementProfileRow, feast_town.id)
    assert profile is not None and profile.unrest < 40


async def test_peoples_that_keep_one_drink_for_making_bonds_grow_closer(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "foodways")
    first, _ = await people_with_town(session, world, "Ardan")
    second, _ = await people_with_town(session, world, "Belis", region=1)
    drink = await keeps_drink(session, first.id, DrinkRole.BOND_MAKING, "Shared")
    session.add(
        KindHoldingRow(
            concept=KindConcept.DRINK, kind_id=drink.id, holder_node_id=second.id, stance=KindStance.USES, strength=100, spread=KindSpread.TRADE, locked=[]
        )
    )
    await session.flush()
    tally = await keep_drinks(ctx)
    assert tally.shared == 1
    assert await session.scalar(select(KindHoldingRow.id).where(KindHoldingRow.holder_node_id == second.id)) is not None
