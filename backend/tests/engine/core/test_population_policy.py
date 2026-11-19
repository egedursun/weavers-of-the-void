from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.population import PopulationAim, PopulationInstrument
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.numbers.book import PolicyBook
from aerona.engine.numbers.policies import NumbersTally, keep_numbers, keep_policy
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def town(session: AsyncSession, world: CoreWorld, name: str, population: int = 1000) -> EntityRow:
    found = await settlement(session, name, world, world.regions[0], population=population)
    await bond(session, found.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=found.id, size_tier=SizeTier.TOWN, unrest=10, sanitation=20, locked=[], foreigners={}))
    await session.flush()
    return found


async def policy(session: AsyncSession, holder_id: int, aim: PopulationAim, *instruments: PopulationInstrument, **values: int) -> PopulationPolicyRow:
    row = PopulationPolicyRow(
        holder_node_id=holder_id, aim=aim, strength=values.get("strength", 50), enforcement=100, baseline=values.get("baseline", 0), locked=[]
    )
    session.add(row)
    await session.flush()
    session.add_all(PopulationInstrumentRow(policy_id=row.id, instrument=kind, holder_node_id=holder_id, strength=100, locked=[]) for kind in instruments)
    await session.flush()
    return row


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(population_policy=values)))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("population.")).order_by(IncidentRow.id)))


async def test_birth_rewards_raise_the_chance_of_births_and_a_child_limit_holds_them(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world, "Ardun")
    await policy(session, world.people.id, PopulationAim.GROW, PopulationInstrument.BIRTH_REWARD, PopulationInstrument.CHILD_LIMIT)
    book = await PolicyBook.load(ctx)
    assert book.birth_factor(home.id) == 1 + ctx.rules.population_policy.birth_reward_pct / 100
    assert book.child_limit(home.id) == 1
    assert book.birth_factor(None) == 1.0


async def test_expulsion_drives_people_out_and_a_child_limit_meets_resistance(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world, "Ardun")
    row = await policy(session, world.people.id, PopulationAim.KEEP_KIND, PopulationInstrument.EXPULSION, PopulationInstrument.CHILD_LIMIT)
    tally = NumbersTally()
    await keep_policy(tuned(ctx, child_limit_resistance=100, enforcement_cost_per_point=0, review_years=1000), row, tally)
    profile = await session.get(SettlementProfileRow, home.id)
    assert stat_or(home, "population", 0) < 1000 and profile is not None and profile.unrest > 10
    assert tally.expelled == 1 and tally.resisted == 2 and row.enforcement < 100
    assert {"population.expulsion", "population.resisted", "population.instrument_enforced"} <= set(await kinds_of(session))


async def test_resettlement_moves_people_from_the_crowded_town_to_the_empty_one(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    crowded, empty = await town(session, world, "Ardun", 2000), await town(session, world, "Lowmere", 200)
    row = await policy(session, world.people.id, PopulationAim.SETTLE_LAND, PopulationInstrument.RESETTLEMENT)
    await keep_policy(tuned(ctx, enforcement_cost_per_point=0, review_years=1000), row, NumbersTally())
    assert stat_or(crowded, "population", 0) < 2000 and stat_or(empty, "population", 0) > 200
    assert "population.resettlement" in await kinds_of(session)


async def test_a_policy_grows_stronger_when_its_numbers_go_against_it_and_is_repealed_at_nothing(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    await town(session, world, "Ardun", 900)
    row = await policy(session, world.people.id, PopulationAim.GROW, PopulationInstrument.HEALTH_CAMPAIGN, baseline=1000)
    await keep_policy(tuned(ctx, enforcement_cost_per_point=0, review_years=1), row, NumbersTally())
    assert row.strength == 60
    row.strength, row.reviewed_epoch = 0, ctx.epoch
    tally = NumbersTally()
    await keep_policy(tuned(ctx, enforcement_cost_per_point=0, review_years=1000), row, tally)
    assert tally.repealed == 1 and "population.policy_repealed" in await kinds_of(session)


async def test_a_sparse_realm_takes_up_a_policy_to_grow(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world, "Ardun", 100)
    realm = await entity(session, "Crown of Ardun", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[], emblem={}))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=home.id))
    await session.flush()
    tally = await keep_numbers(tuned(ctx, adopt_pct=100))
    adopted = await session.scalar(select(PopulationPolicyRow).where(PopulationPolicyRow.holder_node_id == realm.id))
    assert tally.adopted == 1 and adopted is not None and adopted.aim is PopulationAim.GROW
    assert "population.policy_adopted" in await kinds_of(session)


async def test_the_grievance_of_towns_under_a_harsh_policy_takes_strength_from_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    home = await town(session, world, "Ardun")
    profile = await session.get(SettlementProfileRow, home.id)
    assert profile is not None
    profile.unrest = 90
    row = await policy(session, world.people.id, PopulationAim.KEEP_KIND, PopulationInstrument.EXPULSION)
    tuned_ctx = tuned(ctx, enforcement_cost_per_point=0, review_years=1000)
    await keep_policy(tuned_ctx, row, NumbersTally())
    assert row.strength == 50 - tuned_ctx.rules.population_policy.review_step
