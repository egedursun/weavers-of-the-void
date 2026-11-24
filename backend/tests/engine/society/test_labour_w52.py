from sqlalchemy import select

from aerona.catalog.labour import JOB_BRANCH, REASONS
from aerona.catalog.needs import JOB_GOODS, OUTER_SHORTFALLS, SHORTFALLS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society_depth import CommunityShortfallRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.settlement import SizeTier, WaterSupply
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.society_depth import LabourReason, ShortfallEffect
from aerona.engine.demography.basket import apply_shortfalls
from aerona.engine.demography.labour import Plan, law_pin, price_pull, skill_pull
from aerona.engine.demography.shortfalls import kept_shortfalls, shelter_of, thirst_of
from aerona.engine.demography.society_control import hold_shortfall
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, settlement

RULES = Rules()


def workers(**counts: int) -> Plan:
    plan = Plan()
    for name, count in counts.items():
        plan.workers[Job(name)] = count
        plan.note(Job(name), LabourReason.CLASS, count)
    return plan


def test_nine_reasons_and_eleven_shortfalls_have_their_words() -> None:
    assert len(LabourReason) == 11 and set(REASONS) == set(LabourReason)
    assert not REASONS[LabourReason.LAW].chosen and REASONS[LabourReason.SKILL].chosen
    assert (
        len(ShortfallEffect) == 13 and {ShortfallEffect.THIRST, ShortfallEffect.SHELTER, ShortfallEffect.JUSTICE, ShortfallEffect.LEARNING} == OUTER_SHORTFALLS
    )
    assert SHORTFALLS[ShortfallEffect.THIRST].want == "water" and set(JOB_BRANCH) == set(Job)


def test_law_keeps_its_share_of_a_trade_against_dear_prices() -> None:
    plan = workers(farming=1000, mining=100)
    kept = law_pin(RULES, plan, frozenset({Job.FARMING}))
    assert kept == 700 and plan.reasons[(Job.FARMING, LabourReason.LAW)].workers == 700
    price_pull(RULES, plan, {kind: 10 for kind in JOB_GOODS[Job.FARMING]} | {kind: 400 for kind in JOB_GOODS[Job.MINING]})
    assert plan.workers[Job.FARMING] >= 700 and plan.workers[Job.MINING] > 100


def test_skill_draws_workers_to_what_their_people_know() -> None:
    plan = workers(farming=1000, mining=0)
    moved = skill_pull(RULES, plan, {KnowledgeBranch.METALLURGY: 4, KnowledgeBranch.AGRICULTURE: 1})
    assert moved > 0 and plan.workers[Job.MINING] > 0
    assert plan.reasons[(Job.MINING, LabourReason.SKILL)].workers > 0


def test_skill_never_moves_workers_the_law_keeps() -> None:
    plan = workers(farming=1000, mining=0)
    law_pin(Rules(), plan, frozenset({Job.FARMING}))
    skill_pull(RULES, plan, {KnowledgeBranch.METALLURGY: 5, KnowledgeBranch.AGRICULTURE: 1})
    assert plan.workers[Job.FARMING] >= 700


async def test_a_dry_land_with_no_water_works_goes_thirsty_and_stored_water_eases_it(realm: Realm) -> None:
    town = await settlement(realm, "Dust", population=1000)
    ground = RegionEnvironmentRow(entity_id=realm.region.id, rainfall=0)
    realm.session.add(SettlementInfrastructureRow(settlement_entity_id=town.id, water=WaterSupply.NONE))
    await realm.session.flush()
    ctx = context(realm.session, RULES)
    dry = await thirst_of(ctx, town, ground)
    assert dry == RULES.shortfall.dry_thirst_pct
    works = await realm.session.get(SettlementInfrastructureRow, town.id)
    assert works is not None
    works.water = WaterSupply.AQUEDUCT
    assert await thirst_of(ctx, town, ground) == 0


async def test_thirst_kills_and_a_want_of_roofs_sickens(realm: Realm) -> None:
    town = await settlement(realm, "Ruin", population=1000)
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, homeless=500, locked=[], foreigners={}))
    await realm.session.flush()
    ctx = context(realm.session, RULES)
    assert await shelter_of(ctx, town) == 50
    done = await apply_shortfalls(ctx, town, {ShortfallEffect.THIRST: 100}, None)
    assert done[ShortfallEffect.THIRST] == 200 and stat(town, "population") == 800
    assert "consumption.thirst_deaths" in await chronicle_keys(realm.session)


async def test_a_shortfall_is_told_once_and_a_held_want_is_kept(realm: Realm) -> None:
    town = await settlement(realm, "Keep", population=1000)
    ctx = context(realm.session, RULES)
    kept = await kept_shortfalls(ctx, town, {ShortfallEffect.THIRST: 60})
    assert kept[ShortfallEffect.THIRST] == 60 and set(kept) == set(ShortfallEffect)
    assert (await chronicle_keys(realm.session)).count("community.shortfall") == 1
    await kept_shortfalls(ctx, town, {ShortfallEffect.THIRST: 70})
    assert (await chronicle_keys(realm.session)).count("community.shortfall") == 1
    await hold_shortfall(ctx, town.id, ShortfallEffect.SHELTER, 40)
    again = await kept_shortfalls(ctx, town, {ShortfallEffect.SHELTER: 0})
    assert again[ShortfallEffect.SHELTER] == 40
    await hold_shortfall(ctx, town.id, ShortfallEffect.SHELTER, None)
    row = await realm.session.scalar(
        select(CommunityShortfallRow).where(CommunityShortfallRow.community_entity_id == town.id, CommunityShortfallRow.effect == ShortfallEffect.SHELTER)
    )
    assert row is not None and row.locked == []
