from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.economy import CommunityStockRow, GoodsFlowRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.faith import CultHoldingRow, CultOfficeRow, HeresyRow, RelicRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import PlaceCover, WaterSource
from aerona.domain.enums.faith import ClergyFunction, HoldingKind, TenetKind
from aerona.domain.enums.mind import MemoryKind, PressureKind, TraitKind, TraitSource
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.son import Passion
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import ItemStats, LanguageStats, PolityStats
from aerona.engine.body.conditions import condition_of, gain_condition
from aerona.engine.environment.places import holy_place_ids
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.church import clergy_sway
from aerona.engine.faith.doctrine import divine_king, liturgy_reach, passion_tenets, staff, wanted_tenets
from aerona.engine.faith.works import alms, canonise, credit, devotion, pilgrimage, survey_holdings, tithe
from aerona.engine.faith.zeal import doom_omens, scandals
from aerona.engine.faith.zealotry import heretics, inquisition, investiture
from aerona.engine.lore.items import relic_year
from aerona.engine.mind.book import add_trait, write_pressures
from aerona.engine.phases.faith import human_sacrifice
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.faith.factories import faithful, mortal, tick
from tests.engine.gods.factories import GodsWorld, add_world, bond, make_entity


async def church_of(session: AsyncSession, cult_id: int):
    return (await FaithBook.load(session)).churches[cult_id]


async def test_tithes_are_taken_from_the_goods_of_the_lands(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    church = await church_of(session, faith.cult.id)
    await survey_holdings(ctx, church)
    session.add(GoodsFlowRow(epoch=ctx.epoch, community_entity_id=faith.town.id, commodity=CommodityKind.GRAIN, flow=GoodsFlow.HARVEST, quantity=10000))
    stock = CommunityStockRow(community_entity_id=faith.town.id, commodity=CommodityKind.GRAIN, quantity=10000, quality=50)
    session.add(stock)
    await session.flush()
    income = await tithe(ctx, church, await LawBook.load(session))
    expected = round(10000 * faith.doctrine.tithe_rate / 100 * rules.tithes.voluntary_pct / 100)
    assert stock.quantity == 10000 - expected
    assert income == expected // rules.tithes.units_per_treasury
    assert faith.doctrine.treasury == income


async def test_churches_sharing_a_land_share_its_tithe_instead_of_each_taking_it_whole(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    church = await church_of(session, faith.cult.id)
    await survey_holdings(ctx, church)
    rival = await make_entity(session, "Second Rite", EntityType.CULT, world_id=faith.town.world_id, location_id=faith.town.id)
    session.add(CultHoldingRow(cult_entity_id=rival.id, holding_entity_id=faith.town.id, kind=HoldingKind.LAND, since_epoch=ctx.epoch))
    session.add(GoodsFlowRow(epoch=ctx.epoch, community_entity_id=faith.town.id, commodity=CommodityKind.GRAIN, flow=GoodsFlow.HARVEST, quantity=10000))
    stock = CommunityStockRow(community_entity_id=faith.town.id, commodity=CommodityKind.GRAIN, quantity=10000, quality=50)
    session.add(stock)
    await session.flush()
    await tithe(ctx, church, await LawBook.load(session))
    whole = round(10000 * faith.doctrine.tithe_rate / 100 * rules.tithes.voluntary_pct / 100)
    assert stock.quantity == 10000 - round(whole / 2)


async def test_a_held_treasury_takes_no_income(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    faith.doctrine.treasury, faith.doctrine.locked = 40, ["treasury"]
    assert credit(faith.doctrine, 25) == 0
    church = await church_of(session, faith.cult.id)
    await pilgrimage(ctx, church)
    assert faith.doctrine.treasury == 40


async def test_alms_ease_poverty_and_win_goodwill(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    await write_pressures(session, faith.town.id, {PressureKind.POVERTY: 40})
    church = await church_of(session, faith.cult.id)
    assert await alms(ctx, church) == 1
    goodwill = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == faith.town.id, MemoryRow.subject_node_id == faith.cult.id))
    assert goodwill is not None and goodwill.kind is MemoryKind.FAMINE_AID and goodwill.magnitude > 0


async def test_a_saints_bones_become_a_relic_item(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    saint = await mortal(session, world, faith.town, "Blessed Iro", dead=True, role=MortalRole.PRIEST)
    church = await church_of(session, faith.cult.id)
    relic = await canonise(ctx, church, saint)
    bones = await session.get(ItemProfileRow, relic.item_entity_id)
    assert relic.item_entity_id != saint.id and relic.saint_entity_id == saint.id
    assert bones is not None and bones.item_class is ItemClass.HOLY_RELIC
    assert await session.get(CultHoldingRow, (faith.cult.id, relic.item_entity_id)) is not None
    assert (await canonise(ctx, church, saint)).item_entity_id == relic.item_entity_id


async def test_the_inquisition_hunts_the_members_of_suppressed_heresies(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, replace(rules, inquisition=replace(rules.inquisition, execution_chance=0)))
    faith = await faithful(session, world)
    sect = await make_entity(session, "The Grey Sect", EntityType.CULT, world_id=world.world.id, location_id=faith.town.id)
    session.add(HeresyRow(heresy_entity_id=sect.id, parent_entity_id=faith.cult.id, distance=40, declared_epoch=1, suppressed=True, tolerated=False))
    believer = await mortal(session, world, faith.town, "Loyal Wen")
    await bond(session, believer.id, faith.god.id, BondKind.WORSHIPS)
    heretic = await mortal(session, world, faith.town, "Heretic Sul")
    await bond(session, heretic.id, faith.god.id, BondKind.WORSHIPS)
    await bond(session, heretic.id, sect.id, BondKind.MEMBER_OF)
    await session.flush()
    church = await church_of(session, faith.cult.id)
    found = await heretics(ctx, church)
    assert heretic in found and believer not in found
    line = await inquisition(ctx, church)
    assert line is not None and line.key == "faith.inquisition_question" and heretic.id in line.ids


async def seat_realm(session: AsyncSession, world: GodsWorld, faith, ruler) -> PolityProfileRow:
    polity = await make_entity(session, "Kingdom of Ash", EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    realm = PolityProfileRow(
        polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), state_religion_id=faith.cult.id
    )
    session.add(realm)
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id))
    await session.flush()
    return realm


async def test_divine_rule_fuses_the_crown_and_the_leadership_of_the_faith(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world, tenets=(TenetKind.DIVINE_RULE,))
    king = await mortal(session, world, faith.town, "King Oru")
    await mortal(session, world, faith.town, "Priest Ama", role=MortalRole.PRIEST)
    realm = await seat_realm(session, world, faith, king)
    church = await church_of(session, faith.cult.id)
    assert (await divine_king(ctx, church)) == king
    await staff(ctx, church)
    high = await session.scalar(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == faith.cult.id, CultOfficeRow.kind == ClergyFunction.LEADER))
    assert high is not None and high.holder_entity_id == king.id
    assert await clergy_sway(session, rules, realm.polity_entity_id) == 0
    assert await investiture(ctx, church) is None


async def test_investiture_is_a_typed_incident_driven_by_sway(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, replace(rules, inquisition=replace(rules.inquisition, investiture_chance=100)))
    faith = await faithful(session, world)
    faith.doctrine.clergy_count = 500
    ruler = await mortal(session, world, faith.town, "Queen Tal")
    realm = await seat_realm(session, world, faith, ruler)
    assert await clergy_sway(session, rules, realm.polity_entity_id) > 0
    line = await investiture(ctx, await church_of(session, faith.cult.id))
    assert line is not None and line.key.startswith("faith.investiture_") and ruler.id in line.ids


async def test_a_held_office_is_not_refilled(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    await mortal(session, world, faith.town, "Priest Lo", role=MortalRole.PRIEST)
    session.add(CultOfficeRow(cult_entity_id=faith.cult.id, kind=ClergyFunction.LEADER, holder_entity_id=None, since_epoch=1, locked=True))
    await session.flush()
    await staff(ctx, await church_of(session, faith.cult.id))
    high = await session.scalar(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == faith.cult.id, CultOfficeRow.kind == ClergyFunction.LEADER))
    assert high is not None and high.holder_entity_id is None


async def test_doom_omens_and_vicious_clergy_move_the_zeal(session: AsyncSession, world: GodsWorld) -> None:

    rules = Rules()
    ctx = tick(session, replace(rules, zeal=replace(rules.zeal, scandal_chance=100)))
    faith = await faithful(session, world)
    session.add(SkyEventRow(kind=SkyEventKind.ECLIPSE, epoch=ctx.epoch, world_id=world.world.id))
    priest = await mortal(session, world, faith.town, "Greedy Mal", role=MortalRole.PRIEST)
    await add_trait(session, priest.id, TraitKind.GREEDY, TraitSource.BIRTH, 1)
    await session.flush()
    church = await church_of(session, faith.cult.id)
    assert await doom_omens(ctx, church) == 1
    assert await scandals(ctx, church) == [priest]


async def test_devotion_gathers_and_feeds_the_living_god(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    before = faith.god.faith
    church = await church_of(session, faith.cult.id)
    gain = await devotion(ctx, church, faith.god.id)
    assert gain > 0 and faith.god.faith > before
    assert (faith.cult.stats.devotion or 0) > 0


async def test_human_sacrifice_takes_people_and_appals_every_other_people(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world, tenets=(TenetKind.HUMAN_SACRIFICE,))
    others = [
        await make_entity(session, f"Watchers {index}", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id) for index in range(7)
    ]
    before = faith.town.stats.population or 0
    book = await FaithBook.load(session)
    given = await human_sacrifice(ctx, book.churches[faith.cult.id], book)
    assert given >= rules.doctrine.sacrifice_cohort
    assert (faith.town.stats.population or 0) == before - rules.doctrine.sacrifice_cohort
    appalled = set(await session.scalars(select(MemoryRow.holder_node_id).where(MemoryRow.subject_node_id == faith.cult.id)))
    assert {other.id for other in others} <= appalled


async def test_passions_seed_tenets_and_the_holy_place_is_in_the_cults_world(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:

    ctx = tick(session, rules)
    faith = await faithful(session, world)
    faith.god.wrath = 95
    church = await church_of(session, faith.cult.id)
    assert TenetKind.HOLY_WAR in passion_tenets(church, rules.doctrine.passion_tenet)
    assert Passion.WRATH
    assert TenetKind.HOLY_WAR in wanted_tenets(rules, church, {})
    elsewhere = await add_world(session, "Far Shore")
    far = await make_entity(session, "Far Spring", EntityType.PLACE, world_id=elsewhere.id)
    near = await make_entity(session, "Near Spring", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    for place in (far, near):
        session.add(
            PlaceEnvironmentRow(entity_id=place.id, cover=PlaceCover.OPEN, water_source=WaterSource.NONE, nexus=True, height_advantage=0, soil_fertility=40)
        )
        session.add(PlaceProfileRow(entity_id=place.id, kind=PlaceKind.SPRING))
    await session.flush()
    holy = await holy_place_ids(session, rules, world.world.id)
    assert near.id in holy and far.id not in holy
    assert ctx.epoch >= 0


async def test_a_foreign_liturgy_dims_the_preaching(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    tongue = await make_entity(session, "Old Chant", EntityType.LANGUAGE, world_id=world.world.id, stats=LanguageStats())
    faith.doctrine.liturgical_language_id = tongue.id
    church = await church_of(session, faith.cult.id)
    assert await liturgy_reach(ctx, church) == rules.doctrine.liturgy_preaching_pct
    for member in church.members:
        await bond(session, member.id, tongue.id, BondKind.SPEAKS)
    assert await liturgy_reach(ctx, church) == 100


async def test_relics_heal_the_sick_at_their_shrine_first(session: AsyncSession, world: GodsWorld) -> None:

    rules = Rules()
    ctx = tick(session, replace(rules, relics=replace(rules.relics, healing_chance=100, theft_chance=0)))
    faith = await faithful(session, world)
    elsewhere = await make_entity(session, "Far Town", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    far_sick = [await mortal(session, world, elsewhere, f"Far {index}") for index in range(3)]
    pilgrim = await mortal(session, world, faith.town, "Pilgrim")
    for person in (*far_sick, pilgrim):
        await gain_condition(ctx, person, ConditionKind.CHRONIC_ILLNESS, HarmCause.AGE)
    relic_item = await make_entity(session, "Holy Finger", EntityType.ITEM, world_id=world.world.id, location_id=faith.town.id, stats=ItemStats())
    session.add(
        RelicRow(
            item_entity_id=relic_item.id, cult_entity_id=faith.cult.id, shrine_entity_id=faith.town.id, sanctity=50, pilgrims=0, canonised_epoch=1, locked=[]
        )
    )
    await session.flush()
    counts = await relic_year(ctx, await RegionAtlas.load(session))
    assert counts["healed"] == 1
    assert await condition_of(ctx, pilgrim.id, ConditionKind.CHRONIC_ILLNESS) is None
    assert await condition_of(ctx, far_sick[0].id, ConditionKind.CHRONIC_ILLNESS) is not None
    assert faith.cult.status is EntityStatus.CANON
    assert HoldingKind.RELIC
