from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.population import PopulationPolicyRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.fertility_means import FertilityMeans, MeansSource
from aerona.domain.enums.intimacy import NormStance
from aerona.domain.enums.population import PopulationAim
from aerona.domain.models.entity_stats import PeopleStats, RiteStats, TradeRouteStats
from aerona.engine.fertility_means.factor import people_factor, user_factor
from aerona.engine.fertility_means.tend import MeansTally, discover, expose, follow_policies, people_of_towns, peoples, spread
from aerona.engine.mortal.standing import standing_of
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules

F = FertilityMeans


async def homeland(session: AsyncSession, world: CoreWorld, people: EntityRow, name: str, region: int = 0) -> EntityRow:
    town = await settlement(session, name, world, world.regions[region])
    await BondRepository(session).connect(BondDraft(people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    return town


def known(people: EntityRow, means: FertilityMeans, **values: object) -> FertilityMeansRow:
    defaults: dict[str, object] = {"source": MeansSource.FOLK, "reliability": 60, "risk": 5, "stance": NormStance.TOLERATED, "use_pct": 50, "locked": []}
    return FertilityMeansRow(people_entity_id=people.id, means=means, **(defaults | values))


async def test_a_people_finds_simple_means_by_folk_knowledge_and_one_without_conception_finds_none(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "find", tuned_rules(fertility_means={"discover_pct": 100}))
    await homeland(session, world, world.people, "Findby")
    barren = await entity(session, "The Unborn", EntityType.PEOPLE, PeopleStats(population=100), world_id=world.world.id)
    session.add(BodySystemRow(holder_entity_id=barren.id, system=BodySystem.REPRODUCTION, present=False, locked=[]))
    await session.flush()
    kinds = await peoples(ctx)
    assert barren.id not in {people.id for people in kinds}
    await discover(ctx, world.people, MeansTally())
    rows = list(await session.scalars(select(FertilityMeansRow).where(FertilityMeansRow.people_entity_id == world.people.id)))
    assert {row.means for row in rows} == {F.PREVENTION, F.REMEDY_FOR_BARRENNESS, F.ENDING_PREGNANCY}
    assert all(row.source is MeansSource.FOLK for row in rows)
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "birth.means_found")) is not None


async def test_means_in_use_change_the_births_of_a_people_and_of_one_who_uses_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "births", tuned_rules())
    town = await homeland(session, world, world.people, "Birthby")
    session.add(known(world.people, F.PREVENTION, reliability=80, use_pct=50))
    user = await mortal(session, "Wren Shut", world, town.id)
    session.add(FertilityUseRow(user_entity_id=user.id, people_entity_id=world.people.id, means=F.PREVENTION, locked=[]))
    await session.flush()
    assert abs(await people_factor(session, ctx.rules, world.people.id) - 0.6) < 1e-9
    assert abs(await user_factor(session, ctx.rules, user) - 0.2) < 1e-9


async def test_a_policy_to_grow_forbids_prevention_and_pushes_its_use_down(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "policy", tuned_rules(fertility_means={"ban_force_pct": 50, "policy_push": 20}))
    town = await homeland(session, world, world.people, "Growby")
    row = known(world.people, F.PREVENTION, use_pct=40)
    session.add(row)
    session.add(PopulationPolicyRow(holder_node_id=town.id, aim=PopulationAim.GROW, strength=100, enforcement=100, baseline=0, locked=[]))
    await session.flush()
    tally = MeansTally()
    await follow_policies(ctx, await people_of_towns(ctx, await peoples(ctx)), tally)
    assert row.stance is NormStance.FORBIDDEN and row.use_pct == 20 and tally.banned == 1


async def test_hidden_use_comes_to_light_and_shames_the_user(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "exposed", tuned_rules())
    town = await homeland(session, world, world.people, "Hushby")
    session.add(known(world.people, F.ENDING_PREGNANCY, stance=NormStance.FORBIDDEN, risk=100))
    user = await mortal(session, "Moss Quiet", world, town.id)
    use = FertilityUseRow(user_entity_id=user.id, people_entity_id=world.people.id, means=F.ENDING_PREGNANCY, hidden=True, locked=[])
    session.add(use)
    await session.flush()
    tally = MeansTally()
    await expose(ctx, tally)
    assert use.exposed and tally.exposed == 1 and (await standing_of(session, user, "infamy") or 0) > 0


async def test_a_means_passes_along_a_trade_route_to_a_people_that_lacks_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "spread", tuned_rules(fertility_means={"spread_pct": 100}))
    home = await homeland(session, world, world.people, "Spreadby")
    other = await entity(session, "The Far Folk", EntityType.PEOPLE, PeopleStats(population=100), world_id=world.world.id)
    far = await homeland(session, world, other, "Farport", region=1)
    road = await entity(session, "Long Road", EntityType.TRADE_ROUTE, TradeRouteStats(capacity=40), world_id=world.world.id)
    route = {"mode": TradeMode.ROAD, "status": TradeRouteStatus.OPEN, "length": 2, "founded_epoch": 0, "locked": []}
    session.add(TradeRouteProfileRow(route_entity_id=road.id, first_market_id=home.id, second_market_id=far.id, **route))
    session.add(known(world.people, F.PREVENTION, use_pct=40))
    await session.flush()
    tally = MeansTally()
    await spread(ctx, await peoples(ctx), tally)
    passed = await session.get(FertilityMeansRow, (other.id, F.PREVENTION))
    assert passed is not None and passed.reliability == 50 and tally.spread == 1


async def test_a_people_that_keeps_rites_finds_its_means_by_rite_without_bodily_risk(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "rite", tuned_rules(fertility_means={"discover_pct": 100, "risk_pct": 20}))
    town = await homeland(session, world, world.people, "Riteby")
    rite = await entity(session, "The Turning Rite", EntityType.RITE, RiteStats(), world_id=world.world.id)
    await BondRepository(session).connect(BondDraft(town.id, rite.id, BondKind.CELEBRATES, 0))
    await discover(ctx, world.people, MeansTally())
    rows = list(await session.scalars(select(FertilityMeansRow).where(FertilityMeansRow.people_entity_id == world.people.id)))
    assert rows and all(row.source is MeansSource.RITE and row.risk == 0 for row in rows)
