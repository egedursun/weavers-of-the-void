from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.session import Database
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow
from aerona.db.tables.economy import MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import GoodCategory, KindConcept, KindSpread, KindStance
from aerona.domain.models.entity_stats import LanguageStats, PeopleStats, SettlementStats
from aerona.engine.kinds.acts import make_kind
from aerona.engine.kinds.derive import DeriveTally, derive_kinds, tend_prestige
from aerona.engine.kinds.genesis import KindSeed, found_kinds
from aerona.engine.kinds.legacy import LEGACY_FIXUP, legacy_holdings
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, seed_cosmos, tick, tuned
from tests.tools.factories import connect


@pytest.fixture
async def session(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[AsyncSession]:
    database: Database = open_database(tmp_path / "growth.db")
    async with database.write() as found:
        yield found
    await database.dispose()


@pytest.fixture
async def cosmos(session: AsyncSession) -> Cosmos:
    return await seed_cosmos(session)


async def town(session: AsyncSession, cosmos: Cosmos, name: str = "Orrin Ford") -> EntityRow:
    found = await make_entity(session, name, EntityType.SETTLEMENT, SettlementStats(population=3000), world_id=cosmos.home.id)
    tongue = await make_entity(session, f"{name} Speech", EntityType.LANGUAGE, LanguageStats(spread=30), world_id=cosmos.home.id)
    await connect(session, found.id, tongue.id, BondKind.SPEAKS)
    return found


async def holdings_of(session: AsyncSession, holder: EntityRow) -> list[KindHoldingRow]:
    return list(await session.scalars(select(KindHoldingRow).where(KindHoldingRow.holder_node_id == holder.id).order_by(KindHoldingRow.id)))


def held(concept: KindConcept, kind_id: int, holder_id: int, stance: KindStance, strength: int) -> KindHoldingRow:
    return KindHoldingRow(concept=concept, kind_id=kind_id, holder_node_id=holder_id, stance=stance, strength=strength, since_epoch=0, locked=[])


def quiet(rules: Rules, **values: int) -> Rules:
    base = {"substitution_pct": 0, "fusion_pct": 0, "prestige_gain": 0, "prestige_fade": 0}
    return tuned(rules, "kinds", **{**base, **values})


async def price(session: AsyncSession, market: EntityRow, commodity: CommodityKind, value: int) -> None:
    session.add(MarketPriceRow(market_entity_id=market.id, commodity=commodity, epoch=EPOCH, price=value, supply=10, demand=10))
    await session.flush()


async def test_a_people_founds_its_kinds_and_a_wrong_category_is_skipped(session: AsyncSession, cosmos: Cosmos) -> None:
    people = await make_entity(session, "Orrin", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    seeds = [
        KindSeed(KindConcept.GOOD, "grain", "Hollow Barley", "A grain the Orrin sow in wet ground."),
        KindSeed(KindConcept.GOOD, "no such category", "Nothing", ""),
    ]
    made = await found_kinds(session, Rules(), seeds, holder_id=people.id, world_id=cosmos.home.id, epoch=EPOCH, spread=KindSpread.GENESIS)
    held = await holdings_of(session, people)
    assert [row.name for row in made] == ["Hollow Barley"]
    assert isinstance(made[0], GoodKindRow) and made[0].category is GoodCategory.GRAIN and made[0].origin_node_id == people.id
    assert [(row.stance, row.spread) for row in held] == [(KindStance.MAKES, KindSpread.GENESIS)]


async def test_every_registered_concept_can_be_founded_from_a_seed(session: AsyncSession, cosmos: Cosmos) -> None:
    people = await make_entity(session, "Vessa", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    seeds = [KindSeed(concept, next(iter(spec.category_labels)), f"First {spec.label}", "") for concept, spec in CONCEPTS.items()]
    made = await found_kinds(
        session, tuned(Rules(), "kinds", founded_per_people=200), seeds, holder_id=people.id, world_id=cosmos.home.id, epoch=EPOCH, spread=KindSpread.GENESIS
    )
    assert len(made) == len(CONCEPTS)


async def test_old_worlds_give_their_towns_the_dishes_they_cook_once(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    dish = DishRow(name="Ash Bread", method=CookingMethod.BAKED, world_id=cosmos.home.id, created_epoch=0, locked=[])
    session.add(dish)
    await session.flush()
    session.add(CommunityDishRow(community_entity_id=home.id, dish_id=dish.id, popularity=70, since_epoch=0, locked=[]))
    await session.flush()
    ctx = tick(session, Rules())
    result = await legacy_holdings(ctx)
    held = await holdings_of(session, home)
    assert result["dishes"] == 1
    assert [(row.concept, row.kind_id, row.strength) for row in held] == [(KindConcept.DISH, dish.id, 70)]
    assert await session.get(AppliedFixupRow, LEGACY_FIXUP) is not None
    assert await legacy_holdings(ctx) == {}


async def held_good(session: AsyncSession, cosmos: Cosmos, holder: EntityRow, commodity: CommodityKind, **values: int) -> GoodKindRow:
    good = GoodKindRow(
        name="Hollow Barley",
        category=GoodCategory.GRAIN,
        world_id=cosmos.home.id,
        origin_node_id=holder.id,
        stocked_as=commodity,
        created_epoch=0,
        locked=[],
        **values,
    )
    session.add(good)
    await session.flush()
    session.add(held(KindConcept.GOOD, good.id, holder.id, KindStance.MAKES, 80))
    await session.flush()
    return good


async def test_a_good_that_stays_dear_gives_way_to_a_substitute_from_a_cheaper_good(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    good = await held_good(session, cosmos, home, CommodityKind.GRAIN, base_value=100, prestige=40)
    await price(session, home, CommodityKind.GRAIN, 300)
    await price(session, home, CommodityKind.TUBERS, 70)
    tally = await derive_kinds(tick(session, quiet(Rules(), substitution_pct=100)))
    goods = list(await session.scalars(select(GoodKindRow).where(GoodKindRow.derived_from_id == good.id)))
    original = next(row for row in await holdings_of(session, home) if row.kind_id == good.id)
    assert tally.substituted == 1 and len(goods) == 1
    assert goods[0].stocked_as is CommodityKind.TUBERS and goods[0].base_value == 75 and goods[0].prestige == 30
    assert original.strength == 80 - Rules().kinds.substitution_fade


async def test_a_good_at_its_usual_price_keeps_its_kind(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    good = await held_good(session, cosmos, home, CommodityKind.GRAIN)
    await price(session, home, CommodityKind.GRAIN, 100)
    await price(session, home, CommodityKind.TUBERS, 70)
    tally = await derive_kinds(tick(session, quiet(Rules(), substitution_pct=100)))
    assert tally.substituted == 0
    assert await session.scalar(select(GoodKindRow.id).where(GoodKindRow.derived_from_id == good.id)) is None


async def test_a_dish_of_a_dear_good_is_left_to_its_kitchens(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    dish = DishRow(name="Ash Bread", method=CookingMethod.BAKED, world_id=cosmos.home.id, origin_node_id=home.id, created_epoch=0, locked=[])
    session.add(dish)
    await session.flush()
    session.add(DishIngredientRow(dish_id=dish.id, commodity=CommodityKind.GRAIN, share=80))
    session.add(held(KindConcept.DISH, dish.id, home.id, KindStance.MAKES, 80))
    await session.flush()
    await price(session, home, CommodityKind.GRAIN, 300)
    await price(session, home, CommodityKind.TUBERS, 70)
    tally = await derive_kinds(tick(session, quiet(Rules(), substitution_pct=100, fusion_pct=100)))
    assert tally.substituted == 0 and tally.fused == 0
    assert await session.scalar(select(DishRow.id).where(DishRow.derived_from_id == dish.id)) is None


async def test_two_kinds_of_one_category_from_different_makers_fuse(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    other = await make_entity(session, "Vessa", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    first = await held_good(session, cosmos, home, CommodityKind.GRAIN, prestige=20)
    second = GoodKindRow(
        name="Red Millet", category=GoodCategory.GRAIN, world_id=cosmos.home.id, origin_node_id=other.id, prestige=60, created_epoch=0, locked=[]
    )
    session.add(second)
    await session.flush()
    session.add(held(KindConcept.GOOD, second.id, home.id, KindStance.USES, 60))
    await session.flush()
    tally = await derive_kinds(tick(session, quiet(Rules(), fusion_pct=100)))
    fused = await session.scalar(select(GoodKindRow).where(GoodKindRow.derived_from_id == first.id))
    assert tally.fused == 1 and fused is not None and fused.prestige == 40


async def test_a_spreading_kind_gains_prestige_until_everyone_holds_it(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    good = await held_good(session, cosmos, home, CommodityKind.GRAIN, prestige=20)
    rules = quiet(Rules(), prestige_gain=6, prestige_fade=4, prestige_saturation=3)
    await tend_prestige(tick(session, rules), DeriveTally())
    assert good.prestige == 22
    for index in range(3):
        holder = await make_entity(session, f"Far Folk {index}", EntityType.PEOPLE, PeopleStats(population=1000), world_id=cosmos.home.id)
        session.add(held(KindConcept.GOOD, good.id, holder.id, KindStance.USES, 30))
    await session.flush()
    await tend_prestige(tick(session, rules), DeriveTally())
    assert good.prestige == 18


async def test_every_concept_can_be_made_from_a_name_and_a_category_alone(session: AsyncSession, cosmos: Cosmos) -> None:
    ctx = tick(session, Rules())
    for spec in CONCEPTS.values():
        made = await make_kind(ctx, spec, {"name": f"Plain {spec.label}", "category": spec.category(next(iter(spec.category_labels)))})
        assert made.id is not None


async def test_a_dear_good_yields_one_substitute_that_other_holders_take_up(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    other = await town(session, cosmos, "Vessa Ford")
    good = await held_good(session, cosmos, home, CommodityKind.GRAIN, base_value=100, prestige=40)
    session.add(held(KindConcept.GOOD, good.id, other.id, KindStance.USES, 80))
    await session.flush()
    for market in (home, other):
        await price(session, market, CommodityKind.GRAIN, 300)
        await price(session, market, CommodityKind.TUBERS, 70)
    rules = quiet(Rules(), substitution_pct=100)
    await derive_kinds(tick(session, rules))
    await derive_kinds(tick(session, rules))
    goods = list(await session.scalars(select(GoodKindRow).where(GoodKindRow.derived_from_id == good.id)))
    assert len(goods) == 1
    holders = {row.holder_node_id for row in await session.scalars(select(KindHoldingRow).where(KindHoldingRow.kind_id == goods[0].id))}
    assert holders == {home.id, other.id}


async def test_two_kinds_fuse_once_for_a_holder_however_long_they_stay_strong(session: AsyncSession, cosmos: Cosmos) -> None:
    home = await town(session, cosmos)
    other = await make_entity(session, "Vessa", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    first = await held_good(session, cosmos, home, CommodityKind.GRAIN, prestige=20)
    second = GoodKindRow(
        name="Red Millet", category=GoodCategory.GRAIN, world_id=cosmos.home.id, origin_node_id=other.id, prestige=60, created_epoch=0, locked=[]
    )
    session.add(second)
    await session.flush()
    session.add(held(KindConcept.GOOD, second.id, home.id, KindStance.USES, 60))
    await session.flush()
    rules = quiet(Rules(), fusion_pct=100)
    for _ in range(3):
        await derive_kinds(tick(session, rules))
    fused = list(await session.scalars(select(GoodKindRow).where(GoodKindRow.derived_from_id.in_([first.id, second.id]))))
    assert len(fused) == 1
