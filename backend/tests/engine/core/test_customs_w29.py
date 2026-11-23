from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.customs_lines import mortal_customs_lines, son_customs_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import (
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    BorderControlRow,
    CommuteRow,
    CooperativeRow,
    EvidenceRow,
    GradeDutyRow,
    IntoxicantCustomRow,
    MarkCustomRow,
    MeasureStandardRow,
    MembershipCategoryRow,
    MembershipRow,
    NameFormRow,
    NamingCustomRow,
    PoorReliefRow,
    RevivalRow,
    TimeBudgetRow,
    WelfareRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.mind import CultureValueRow, GriefRow, PressureRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, DriftCauseRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.customs import (
    AgeGrade,
    CoopPurpose,
    EvidenceKind,
    GradeDuty,
    Intoxicant,
    IntoxicantUse,
    MarkKind,
    MarkMeaning,
    MemberRight,
    Membership,
    NamingPattern,
    ReliefKind,
    RevivalGoal,
    RevivalStage,
    RevivalWay,
)
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.justice import CaseStage, Deposition
from aerona.domain.enums.mind import GriefStage, PressureKind, Profession, ValueAxis
from aerona.domain.enums.mortal import CrimeKind, LifeStage, PunishmentKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats, StructureStats
from aerona.engine.body.afflictions import active
from aerona.engine.context import TickContext
from aerona.engine.customs.age_sets import AgeSetTally, keep_age_sets
from aerona.engine.customs.civics import CivicsTally, keep_civics
from aerona.engine.customs.grades import too_young_to_wed
from aerona.engine.customs.intoxicants import IntoxicationTally, keep_intoxication
from aerona.engine.customs.marks import MarkTally, keep_marks
from aerona.engine.customs.naming import NamingTally, keep_naming
from aerona.engine.customs.relief import commute_share, poverty_relief
from aerona.engine.customs.revival import RevivalTally, keep_revivals
from aerona.engine.customs.rights import crossing, has_right, unarmed, unwed_by_law
from aerona.engine.customs.taboo import name_tabooed
from aerona.engine.customs.time_budgets import TimeTally, keep_time_budgets, leisure_odds, rested_fertility
from aerona.engine.customs.town_life import TownLifeTally, keep_town_life
from aerona.engine.mortal.justice import sentence
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.services.integrity.customs_links import mend_customs_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "customs", rules=tuned_rules(**rules))


async def home(session: AsyncSession, world: CoreWorld, name: str, **values: int) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    for axis, value in values.items():
        session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis(axis), value=value))
    await session.flush()
    return town, world.people


def profile(mortal_id: int, **values: object) -> MortalProfileRow:
    return MortalProfileRow(entity_id=mortal_id, locked=[], **values)


async def realm_of(session: AsyncSession, world: CoreWorld, name: str, *towns: int) -> EntityRow:
    found = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    for town in towns:
        session.add(PolityMemberRow(polity_entity_id=found.id, member_entity_id=town))
    await session.flush()
    return found


async def test_a_pressed_people_raises_a_movement_that_passes_its_stages(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Oldwell", tradition=60)
    session.add(DriftCauseRow(community_entity_id=town.id, cause=DriftCause.CONQUEST, axis=ValueAxis.TRADITION, amount=-40, total=-40, epoch=3))
    await session.flush()
    tally = RevivalTally()
    await keep_revivals(await at(session, 3), tally)
    row = await session.scalar(select(RevivalRow).where(RevivalRow.people_entity_id == folk.id))
    assert row is not None and row.way in RevivalWay and row.stage is RevivalStage.STRESS and tally.begun == 1
    for epoch in range(4, 8):
        await keep_revivals(await at(session, epoch, revivals={"stage_gain": 100}), tally)
    row = await session.scalar(select(RevivalRow).where(RevivalRow.people_entity_id == folk.id))
    assert row is not None and row.stage is RevivalStage.NEW_STEADY and row.ended_epoch is not None and tally.settled == 1


async def test_daily_intoxicants_breed_dependence(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Tapwick")
    drinker = await mortal(session, "Sot", world, town.id)
    session.add(profile(drinker.id))
    session.add(IntoxicantCustomRow(people_entity_id=folk.id, intoxicant=Intoxicant.SPIRITS, use=IntoxicantUse.DAILY, acceptance=100, locked=[]))
    await session.flush()
    tally = IntoxicationTally()
    await keep_intoxication(await at(session, 3, intoxication={"habit_chance": 100}), tally)
    afflictions = await active(session, drinker.id)
    assert tally.habits == 1 and any(row.package is PackageKind.DRINK_DEPENDENCE for row in afflictions)


async def test_a_deed_is_marked_and_read_as_renown_and_a_brand_shames(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Inkhold")
    hero = await mortal(session, "Ravel", world, town.id)
    foe = await mortal(session, "Grim", world, town.id)
    session.add_all([profile(hero.id, renown=10), profile(foe.id, honour=50)])
    session.add(MarkCustomRow(people_entity_id=folk.id, kind=MarkKind.TATTOO, meaning=MarkMeaning.DEED, locked=[]))
    await bond(session, hero.id, foe.id, BondKind.KILLED, epoch=3)
    await session.flush()
    tally = MarkTally()
    await keep_marks(await at(session, 3), tally)
    await sentence(await at(session, 4), foe, CrimeKind.THEFT, PunishmentKind.BRANDING)
    marks = list(await session.scalars(select(BodyMarkRow).where(BodyMarkRow.holder_node_id == hero.id)))
    hero_profile = await session.get(MortalProfileRow, hero.id)
    foe_profile = await session.get(MortalProfileRow, foe.id)
    assert [mark.meaning for mark in marks] == [MarkMeaning.DEED] and hero_profile is not None and hero_profile.renown > 10
    assert foe_profile is not None and foe_profile.honour < 50


async def test_a_year_of_more_work_and_worship_raises_output_and_piety(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Toilby")
    shares = {f"share_{item.value}": 0.0 for item in SocialClass}
    shares["share_farmer"] = 100.0
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            **shares,
            **{f"satisfaction_{item.value}": 50 for item in SocialClass},
            stock_food=0,
            stock_ore=0,
            stock_goods=0,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    session.add(
        TimeBudgetRow(people_entity_id=folk.id, social_class=SocialClass.FARMER, work=85, rest=0, worship=15, leisure=0, travel=0, service=0, locked=[])
    )
    await session.flush()
    before = (stat(town, "prosperity") or 0, stat(town, "piety") or 0)
    await keep_time_budgets(await at(session, 3, time_budgets={"worship_piety": 50}), TimeTally())
    assert (stat(town, "prosperity") or 0) > before[0] and (stat(town, "piety") or 0) > before[1]


async def test_a_secret_name_is_the_true_name_and_the_dead_go_unnamed(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Hushford")
    child = await mortal(session, "Wren", world, town.id)
    child.birth_epoch = 3
    session.add(profile(child.id))
    session.add(NamingCustomRow(people_entity_id=folk.id, pattern=NamingPattern.GIVEN, secret_names=True, taboo_epochs=3, locked=[]))
    await session.flush()
    await keep_naming(await at(session, 3), NamingTally())
    forms = {row.form.value: row.name for row in await session.scalars(select(NameFormRow).where(NameFormRow.holder_node_id == child.id))}
    true = await session.get(TrueNameRow, child.id)
    assert forms.get("birth") == "Wren" and "secret" in forms and true is not None and true.name == forms["secret"]
    child.status, child.end_epoch = EntityStatus.DEAD, 4
    await session.flush()
    assert await name_tabooed(session, child.id, 5) and not await name_tabooed(session, child.id, 8)


async def test_youths_form_an_age_set_that_may_not_wed_and_rises_to_warriors(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Ringstead", tradition=60)
    first = await mortal(session, "Kel", world, town.id)
    second = await mortal(session, "Isa", world, town.id)
    session.add_all([profile(first.id, life_stage=LifeStage.YOUTH), profile(second.id, life_stage=LifeStage.YOUTH)])
    await session.flush()
    tally = AgeSetTally()
    await keep_age_sets(await at(session, 3), tally)
    member = await session.get(AgeSetMemberRow, first.id)
    assert member is not None and tally.initiated == 2 and await too_young_to_wed(session, first, second)
    await keep_age_sets(await at(session, 6, age_sets={"span_years": 50, "grade_years": 50}), tally)
    found = await session.get(AgeSetRow, member.age_set_id)
    assert found is not None and found.grade is AgeGrade.YOUNG_ADULTS
    ceremony = await session.scalar(select(GatheringRow).where(GatheringRow.host_node_id == folk.id, GatheringRow.kind == GatheringKind.MILESTONE))
    assert ceremony is not None


async def test_town_life_eases_poverty_loses_labour_on_the_way_and_pools_means(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Almsby")
    house = await entity(session, "The Open Door", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=house.id, kind=StructureKind.ALMSHOUSE, host_entity_id=town.id))
    guild = await entity(session, "The Fishers", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add_all([DistrictRow(settlement_entity_id=town.id, kind=kind, built_epoch=1) for kind in list(DistrictKind)[:4]])
    session.add(PressureRow(entity_id=town.id, pressure=PressureKind.POVERTY, value=80))
    await session.flush()
    await keep_town_life(await at(session, 3, cooperatives={"found_from": 50}, welfare={"upkeep_per_inmate": 0}), TownLifeTally())
    assert await session.get(WelfareRow, house.id) is not None and await poverty_relief(session, tuned_rules(), town.id) > 0
    commute = await session.get(CommuteRow, town.id)
    assert commute is not None and commute.labour_lost > 0 and await commute_share(session, town.id) < 1
    pool = await session.get(CooperativeRow, guild.id)
    assert pool is not None and pool.purpose in tuple(CoopPurpose)
    pool.purpose = CoopPurpose.CREDIT
    pool.locked = ["purpose"]
    await session.flush()
    empty = await poverty_relief(session, tuned_rules(), town.id)
    member = await mortal(session, "Net-Mender", world, town.id)
    session.add(profile(member.id, wealth=60))
    await bond(session, member.id, guild.id, BondKind.MEMBER_OF)
    await keep_town_life(await at(session, 4, welfare={"upkeep_per_inmate": 0}), TownLifeTally())
    assert pool.members == 1 and await poverty_relief(session, tuned_rules(), town.id) > empty


async def test_evidence_weighs_a_case_and_fades_as_it_waits(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Courtby")
    accused = await mortal(session, "Dov", world, town.id)
    witness = await mortal(session, "Ula", world, town.id)
    case = CrimeCaseRow(
        settlement_entity_id=town.id,
        crime=CrimeKind.THEFT,
        accused_entity_id=accused.id,
        culprit_entity_id=accused.id,
        stage=CaseStage.TRIAL,
        opened_epoch=3,
        locked=[],
    )
    session.add(case)
    await session.flush()
    session.add(CaseWitnessRow(case_id=case.id, witness_entity_id=witness.id, testimony=Deposition.ACCUSES, reliability=80))
    await session.flush()
    await keep_civics(await at(session, 3), CivicsTally())
    rows = list(await session.scalars(select(EvidenceRow).where(EvidenceRow.case_id == case.id)))
    first = case.evidence
    assert EvidenceKind.WITNESS in {row.kind for row in rows} and len(rows) >= 2 and first > 0
    await keep_civics(await at(session, 4), CivicsTally())
    assert case.evidence < first


async def test_citizenship_decides_rights_and_borders_and_measures_shape_trade(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Lawmere")
    other = await settlement(session, "Farport", world, world.regions[1])
    ruler = await mortal(session, "Queen Ama", world, town.id)
    stranger = await mortal(session, "Tov", world, town.id)
    realm = await realm_of(session, world, "Lawmere Realm", town.id)
    abroad = await realm_of(session, world, "Far Realm", other.id)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id))
    session.add_all([profile(ruler.id, polity_id=realm.id), profile(stranger.id, polity_id=realm.id)])
    stranger.affiliated_entity_id = None
    await session.flush()
    await keep_civics(await at(session, 3), CivicsTally())
    assert await session.get(MembershipCategoryRow, (realm.id, Membership.BOUND)) is not None
    membership = await session.get(MembershipRow, ruler.id)
    assert membership is not None
    membership.category = Membership.BOUND
    await session.flush()
    assert not await has_right(session, ruler.id, MemberRight.OFFICE) and await unwed_by_law(session, ruler, stranger)
    assert Profession.SOLDIER.value in await unarmed(session, ruler.id)
    session.add(BorderControlRow(polity_entity_id=abroad.id, fee=100, delay=2, enforcement=100, corruption=0, locked=[]))
    session.add_all([MeasureStandardRow(polity_entity_id=realm.id, locked=[]), MeasureStandardRow(polity_entity_id=abroad.id, locked=[])])
    await session.flush()
    factor, fee, toll = await crossing(session, tuned_rules(), (town.id, other.id))
    assert toll == abroad.id and fee > 0 and factor < 1
    assert folk is not None


async def test_customs_reach_minds_and_integrity_ends_movements_of_vanished_peoples(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Telltale")
    reader = await mortal(session, "Mira", world, town.id)
    session.add(profile(reader.id))
    session.add(BodyMarkRow(holder_node_id=reader.id, kind=MarkKind.SCAR, meaning=MarkMeaning.DEED, placed_epoch=1, locked=[]))
    session.add(NamingCustomRow(people_entity_id=folk.id, pattern=NamingPattern.CLAN, locked=[]))
    session.add(GradeDutyRow(people_entity_id=folk.id, duty=GradeDuty.HERDING, grade=AgeGrade.YOUTHS, locked=[]))
    session.add(
        RevivalRow(
            people_entity_id=folk.id, way=RevivalWay.RESTORE, goal=RevivalGoal.REVIVE_LANGUAGE, stage=RevivalStage.DISTORTION, started_epoch=1, locked=[]
        )
    )
    session.add(
        PoorReliefRow(
            polity_entity_id=(await realm_of(session, world, "Telltale Realm", town.id)).id,
            kind=ReliefKind.ALMS,
            budget=100,
            reach=100,
            locked=[],
        )
    )
    await session.flush()
    scope = await load_scope(session, tuned_rules())
    lines = await mortal_customs_lines(scope, reader)
    assert any("scar" in line for line in lines) and any("revive the language" in line for line in lines)
    assert "how your people name: named for the clan" in lines
    assert "among your people the grade of youths carries the duty of herding" in lines
    assert any("revive the language" in line for line in await son_customs_lines(scope, world.son))
    assert await poverty_relief(session, tuned_rules(), town.id) > 0
    folk.status, folk.end_epoch = EntityStatus.DESTROYED, 4
    await session.flush()
    assert await mend_customs_links(session, 4) >= 1


async def test_a_movement_restores_the_old_god_or_is_put_down_by_the_realm_that_presses_on_it(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Oldshrine", tradition=60)
    realm = await realm_of(session, world, "The Pressing Crown", town.id)
    await bond(session, folk.id, world.son.id, BondKind.WORSHIPS, epoch=1)
    old = await session.scalar(select(BondRow).where(BondRow.source_node_id == folk.id, BondRow.kind == BondKind.WORSHIPS))
    assert old is not None
    old.state = BondState.PAST
    await session.flush()
    row = RevivalRow(
        people_entity_id=folk.id,
        way=RevivalWay.RESTORE,
        stage=RevivalStage.REVITALISATION,
        goal=RevivalGoal.RESTORE_GOD,
        strength=0,
        started_epoch=2,
        locked=[],
    )
    session.add(row)
    await session.flush()
    await keep_revivals(await at(session, 3, revivals={"restore_chance": 100, "suppress_chance": 0, "stage_gain": 0}), RevivalTally())
    assert await patron_node(session, folk) == world.son.id
    row.dominant_entity_id = realm.id
    await session.flush()
    tally = RevivalTally()
    await keep_revivals(await at(session, 4, revivals={"suppress_chance": 100}), tally)
    assert row.stage is RevivalStage.SUPPRESSED and row.ended_epoch == 4 and tally.suppressed == 1


async def test_forbidden_drink_shames_its_takers_and_drink_in_mourning_and_brew_ease_the_town(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Drywell")
    taker = await mortal(session, "Lusk", world, town.id)
    mourner = await mortal(session, "Hale", world, town.id)
    session.add_all([profile(taker.id, infamy=0), profile(mourner.id, stress=50)])
    session.add(IntoxicantCustomRow(people_entity_id=folk.id, intoxicant=Intoxicant.LEAF, use=IntoxicantUse.FORBIDDEN, acceptance=100, locked=[]))
    session.add(IntoxicantCustomRow(people_entity_id=folk.id, intoxicant=Intoxicant.BREW, use=IntoxicantUse.MOURNING, acceptance=100, locked=[]))
    session.add(
        GriefRow(mourner_node_id=mourner.id, deceased_node_id=taker.id, stage=GriefStage.MOURNING, strength=50, started_epoch=2, stage_epoch=2, length_epochs=5)
    )
    await session.flush()
    rules = {"habit_chance": 100, "forbidden_pct": 100, "forbidden_infamy": 7, "mourning_calm": 10}
    await keep_intoxication(await at(session, 3, intoxication=rules), IntoxicationTally())
    shamed = await session.get(MortalProfileRow, taker.id)
    eased = await session.get(MortalProfileRow, mourner.id)
    assert shamed is not None and shamed.infamy == 7 and eased is not None and eased.stress == 40


async def test_a_corvee_turns_work_into_service_rest_breeds_children_and_youths_bear_no_arms(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Levyham")
    shares = {f"share_{item.value}": 0.0 for item in SocialClass}
    shares["share_farmer"] = 100.0
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            **shares,
            **{f"satisfaction_{item.value}": 50 for item in SocialClass},
            stock_food=0,
            stock_ore=0,
            stock_goods=0,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    session.add(
        TimeBudgetRow(people_entity_id=folk.id, social_class=SocialClass.FARMER, work=55, rest=40, worship=0, leisure=5, travel=0, service=0, locked=[])
    )
    session.add(CorveeRow(community_entity_id=town.id, share_pct=100))
    await session.flush()
    before = stat(town, "defense") or 0
    await keep_time_budgets(await at(session, 3, time_budgets={"service_defense": 10, "usual_service": 0}), TimeTally())
    assert (stat(town, "defense") or 0) > before
    farmer = await mortal(session, "Tamsin", world, town.id)
    farmer.social_class = SocialClass.FARMER
    await session.flush()
    assert await rested_fertility(session, tuned_rules(time_budgets={"rest_fertility_pct": 50}), farmer) == 2.0
    assert await leisure_odds(session, tuned_rules(time_budgets={"leisure_attendance": 10}), farmer) == -5
    youth = await mortal(session, "Pell", world, town.id)
    session.add(profile(youth.id, life_stage=LifeStage.YOUTH))
    young_set = AgeSetRow(people_entity_id=folk.id, name="The Young Set", initiated_from=3, grade=AgeGrade.YOUTHS, promoted_epoch=3, locked=[])
    session.add(young_set)
    await session.flush()
    session.add(AgeSetMemberRow(mortal_entity_id=youth.id, age_set_id=young_set.id, locked=[]))
    await session.flush()
    assert Profession.SOLDIER.value in await unarmed(session, youth.id)
    young_set.grade = AgeGrade.YOUNG_ADULTS
    await session.flush()
    assert await unarmed(session, youth.id) == frozenset()


async def test_a_house_of_welfare_unpaid_turns_its_poor_away_and_cooperative_dues_come_from_members(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Bareby")
    house = await entity(session, "The Last Door", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    patron = await mortal(session, "Penniless", world, town.id)
    session.add(profile(patron.id, wealth=0))
    session.add(StructureProfileRow(structure_entity_id=house.id, kind=StructureKind.ALMSHOUSE, host_entity_id=town.id, builder_entity_id=patron.id))
    session.add(PressureRow(entity_id=town.id, pressure=PressureKind.POVERTY, value=80))
    guild = await entity(session, "The Pooled", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(CooperativeRow(faction_entity_id=guild.id, purpose=CoopPurpose.CREDIT, locked=["purpose"]))
    member = await mortal(session, "Saver", world, town.id)
    session.add(profile(member.id, wealth=50))
    await bond(session, member.id, guild.id, BondKind.MEMBER_OF)
    await session.flush()
    await keep_town_life(await at(session, 3), TownLifeTally())
    welfare = await session.get(WelfareRow, house.id)
    pool = await session.get(CooperativeRow, guild.id)
    paid = await session.get(MortalProfileRow, member.id)
    assert welfare is not None and welfare.inmates == 0
    assert pool is not None and pool.pool > 0 and paid is not None and paid.wealth < 50
