from dataclasses import replace
from types import SimpleNamespace

from sqlalchemy import func, select

from aerona.catalog.effect_packages import PACKAGES
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.cycles import CircuitRow, GiftRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import GriefRow, MemoryRow, ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.orders import SavingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.affliction import CureKind, ForgetScope, PackageKind, SleepUntil, Transmission
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.economy import TradeLoss, TradeMode
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.mind import GriefStage, MemoryKind, MoodArousal, ThoughtKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.tongues import LanguageStage
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.body.afflictions import afflict, forget, recognised, release_cure, wakes_by
from aerona.engine.body.packages_w52 import Shape
from aerona.engine.collective.crowds import hear_petition
from aerona.engine.cycles.gifts import hoard
from aerona.engine.economy.route_dangers import Dangers, pirate_danger
from aerona.engine.industry.pollution import fish_factor
from aerona.engine.mind.grief import GriefTally, advance
from aerona.engine.mind.memories import remember
from aerona.engine.mind.opinion import relation_floor
from aerona.engine.mind.thoughts import settle_mood, think
from aerona.engine.mortal.course import decline
from aerona.engine.orders.savings import tend_held
from aerona.engine.phases.lore import endanger
from aerona.engine.phases.w52_agent_l import time_shares, world_thoughts
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement

RULES = Rules()


async def kinds_recorded(realm: Realm, key: str) -> int:
    return int(await realm.session.scalar(select(func.count()).select_from(IncidentRow).where(IncidentRow.kind == key)) or 0)


async def test_an_answered_petition_eases_unrest(realm: Realm) -> None:
    town = await settlement(realm, "Gate")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=40, locked=[]))
    rules = replace(RULES, collective=replace(RULES.collective, petition_heard_pct=100))
    ctx = context(realm.session, rules)
    assert await hear_petition(ctx, town, SimpleNamespace(participants=30), ctx.rng("petition"))
    profile = await realm.session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.unrest == 40 - rules.collective.petition_relief
    assert await kinds_recorded(realm, "petition.answered") == 1


async def test_a_circuit_gift_kept_back_is_hoarded_and_costs_standing(realm: Realm) -> None:
    here, there = await settlement(realm, "Here"), await settlement(realm, "There")
    circuit = CircuitRow(name="Ring", stops=[here.id, there.id], locked=[])
    realm.session.add(circuit)
    await realm.session.flush()
    gift = GiftRow(giver_node_id=there.id, receiver_node_id=here.id, occasion=GiftOccasion.CIRCUIT, state=GiftState.OPEN, circuit_id=circuit.id, locked=[])
    realm.session.add(gift)
    await realm.session.flush()
    rules = replace(RULES, gifts=replace(RULES.gifts, hoard_chance_pct=100))
    assert await hoard(context(realm.session, rules), circuit, here.id)
    assert gift.state is GiftState.HOARDED
    assert await kinds_recorded(realm, "gift.hoarded") == 1


async def test_a_tongue_with_few_speakers_comes_near_its_end_and_recovers(realm: Realm) -> None:
    tongue = await make(realm.session, "Old Speech", EntityType.LANGUAGE, LanguageStats(spread=5), world_id=realm.world.id)
    profile = await language_profile(realm.session, tongue)
    hamlet = await settlement(realm, "Hamlet", population=120)
    await link(realm.session, hamlet.id, tongue.id, BondKind.SPEAKS)
    ctx = context(realm.session)
    await endanger(ctx, tongue)
    assert profile.stage is LanguageStage.ENDANGERED
    assert await kinds_recorded(realm, "language.endangered") == 1
    big = await settlement(realm, "Burgh", population=9000)
    await link(realm.session, big.id, tongue.id, BondKind.SPEAKS)
    await endanger(ctx, tongue)
    assert profile.stage is LanguageStage.NATURAL


def test_pirates_haunt_lawless_coasts_and_breakage_is_kept_as_it_is() -> None:
    coast = SimpleNamespace(coast_kind=next(kind for kind in CoastKind if kind is not CoastKind.NONE))
    inland = SimpleNamespace(coast_kind=CoastKind.NONE)
    book = SimpleNamespace(ground=SimpleNamespace(regions={1: coast, 2: inland, 3: coast}))
    assert pirate_danger(RULES, book, TradeMode.SEA, [1, 2, 3], frozenset()) == 2 * RULES.route_dangers.pirate_haven_danger
    assert pirate_danger(RULES, book, TradeMode.SEA, [1, 2, 3], frozenset({1})) == RULES.route_dangers.pirate_haven_danger
    assert pirate_danger(RULES, book, TradeMode.ROAD, [1, 3], frozenset()) == 0
    dangers = Dangers(pirates=10, breakage=5).reckon(RULES)
    assert dangers.parts()[TradeLoss.BREAKAGE] == 5 and dangers.parts()[TradeLoss.PIRATES] == 10 * RULES.route_dangers.pirates_pct // 100
    assert dangers.total == dangers.pirates + dangers.breakage


async def test_ageing_moves_a_life_on_at_its_own_rate(realm: Realm) -> None:
    being = await mortal(realm, "Ivo", age=30)
    ctx = context(realm.session)
    row = await afflict(ctx, being, PackageKind.AGEING, Transmission.CURSE, shape=Shape(ageing_rate_pct=300))
    assert row is not None and row.ageing_rate_pct == 300
    assert stat(being, "age") == 30 + RULES.packages.epochs_years * 2
    assert PACKAGES[PackageKind.AGEING].stages[0].hastens


async def test_forgetting_takes_by_its_scope(realm: Realm) -> None:
    being, friend, foe = await mortal(realm, "Ana"), await mortal(realm, "Bo"), await mortal(realm, "Cy")
    for epoch, subject in ((1, friend.id), (2, foe.id), (3, foe.id)):
        await remember(realm.session, RULES, holder_id=being.id, subject_id=subject, kind=MemoryKind.HARMED_ME, magnitude=-30, epoch=epoch)
    await realm.session.flush()
    ctx = context(realm.session)
    assert await forget(ctx, being, ForgetScope.PERSON) >= 1
    left = list(await realm.session.scalars(select(MemoryRow.subject_node_id).where(MemoryRow.holder_node_id == being.id)))
    assert foe.id not in left or friend.id not in left


async def test_a_sleep_wakes_only_by_its_own_cure(realm: Realm) -> None:
    being = await mortal(realm, "Dov")
    row = await afflict(context(realm.session), being, PackageKind.SLEEP, Transmission.CURSE, shape=Shape(sleep_until=SleepUntil.TIME))
    assert row is not None and row.sleep_until is SleepUntil.TIME
    assert wakes_by(row, CureKind.TIME) and not wakes_by(row, CureKind.QUEST)


async def test_arousal_rises_with_stirring_thoughts(realm: Realm) -> None:
    being = await mortal(realm, "Eli")
    for _ in range(4):
        await think(realm.session, RULES, being.id, ThoughtKind.FLED_PLAGUE, 3)
    await settle_mood(realm.session, RULES, being, 3)
    profile = await realm.session.get(MortalProfileRow, being.id)
    assert profile is not None and profile.arousal_score != 50 and profile.arousal in set(MoodArousal)


async def test_the_mature_lose_strength(realm: Realm) -> None:
    being = await mortal(realm, "Fen", strength=60)
    decline(context(realm.session), being)
    assert (stat(being, "strength") or 0) < 60
    assert LifeStage.MATURE.value == "mature"


async def test_grief_bargains_after_anger_and_may_shorten_mourning(realm: Realm) -> None:
    mourner, lost = await mortal(realm, "Gil"), await mortal(realm, "Hal")
    row = GriefRow(mourner_node_id=mourner.id, deceased_node_id=lost.id, stage=GriefStage.ANGER, strength=80, started_epoch=1, stage_epoch=1, length_epochs=3)
    realm.session.add(row)
    await realm.session.flush()
    rules = replace(RULES, grief=replace(RULES.grief, anger_years=0, bargaining_years=200, bargaining_relief_pct=100))
    await advance(context(realm.session, rules, epoch=3), mourner, GriefTally())
    assert row.stage is GriefStage.BARGAINING and row.length_epochs == 2


async def test_herds_kept_as_savings_grow(realm: Realm) -> None:
    town = await settlement(realm, "Fold")
    household = HouseholdRow(name="Fold house", settlement_node_id=town.id, wealth=10, locked=[])
    realm.session.add(household)
    await realm.session.flush()
    row = SavingRow(household_id=household.id, livestock=100, updated_epoch=1, locked=[])
    realm.session.add(row)
    await tend_held(context(realm.session), household, row)
    assert row.livestock == 100 + 100 * (RULES.saving.herd_growth_pct - RULES.saving.herd_loss_pct) // 100


def test_heat_in_the_waters_lowers_the_catch() -> None:
    cool = RegionPollutionRow(region_node_id=1, air=0, water=0, soil=0, radiation=0, noise=0, light=0, heat=0, epoch=1, locked=[])
    warm = RegionPollutionRow(region_node_id=1, air=0, water=0, soil=0, radiation=0, noise=0, light=0, heat=80, epoch=1, locked=[])
    assert fish_factor(RULES, warm) < fish_factor(RULES, cool) == 1.0


async def test_a_storm_where_folk_live_leaves_them_a_thought(realm: Realm) -> None:
    town = await settlement(realm, "Cove")
    being = await mortal(realm, "Ira", location_id=town.id)
    realm.session.add(IncidentRow(kind="event.storm", epoch=3, place_entity_id=town.id))
    await realm.session.flush()
    await world_thoughts(context(realm.session, epoch=3))
    kinds = list(await realm.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == being.id)))
    assert ThoughtKind.STORM_SURVIVED in kinds


async def test_time_in_company_binds_a_people_and_mourning_time_eases_grief(realm: Realm) -> None:
    folk = await people(realm, "Kin")
    realm.session.add(
        PeopleCultureRow(
            people_entity_id=folk.id,
            cohesion=40,
            literacy=0,
            urbanisation=0,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            locked=[],
        )
    )
    realm.session.add(
        TimeBudgetRow(people_entity_id=folk.id, social_class=SocialClass.FARMER, life_stage=LifeStage.ADULT, socialising=10, mourning=5, locked=[])
    )
    mourner, lost = await mortal(realm, "Jo"), await mortal(realm, "Ka")
    mourner.affiliated_entity_id = folk.id
    grief = GriefRow(
        mourner_node_id=mourner.id, deceased_node_id=lost.id, stage=GriefStage.MOURNING, strength=60, started_epoch=1, stage_epoch=1, length_epochs=3
    )
    realm.session.add(grief)
    await realm.session.flush()
    await time_shares(context(realm.session))
    culture = await realm.session.get(PeopleCultureRow, folk.id)
    assert culture is not None and culture.cohesion > 40
    assert grief.strength < 60


def test_a_bond_keeps_opinion_above_its_floor_but_a_hostile_one_does_not() -> None:
    assert relation_floor(RULES, ["spouse"]) == RULES.relations.spouse_floor
    assert relation_floor(RULES, ["rival"]) is None
    assert relation_floor(RULES, []) is None


async def test_a_marked_affliction_is_read_by_those_who_know_and_a_pardon_lifts_a_curse(realm: Realm) -> None:
    being, healer, wronged = await mortal(realm, "Lu"), await mortal(realm, "Mo"), await mortal(realm, "Ny")
    rules = replace(RULES, packages=replace(RULES.packages, marked_read_pct=100))
    ctx = context(realm.session, rules)
    row = await afflict(ctx, being, PackageKind.AGEING, Transmission.CURSE)
    assert row is not None and await recognised(ctx, row, healer.id)
    assert await kinds_recorded(realm, "affliction.recognised") == 1
    assert not await release_cure(ctx, being)
    await remember(realm.session, RULES, holder_id=wronged.id, subject_id=being.id, kind=MemoryKind.APOLOGISED_TO_ME, magnitude=20, epoch=3)
    await realm.session.flush()
    assert await release_cure(ctx, being)
