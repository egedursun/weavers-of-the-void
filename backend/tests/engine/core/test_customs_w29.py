from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.customs_lines import mortal_customs_lines, son_customs_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.customs import (
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    BorderControlRow,
    CommuteRow,
    CooperativeRow,
    EvidenceRow,
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
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.mind import CultureValueRow, PressureRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import DriftCauseRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import (
    AgeGrade,
    CoopPurpose,
    Intoxicant,
    IntoxicantUse,
    MarkKind,
    MarkMeaning,
    MemberRight,
    Membership,
    NamingPattern,
    ReliefKind,
    RevivalAim,
    RevivalGoal,
    RevivalStage,
)
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.justice import CaseStage, Deposition
from aerona.domain.enums.mind import PressureKind, Profession, ValueAxis
from aerona.domain.enums.mortal import CrimeKind, LifeStage
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
from aerona.engine.customs.grades import too_young_to_wed, warriors_ready
from aerona.engine.customs.intoxicants import IntoxicationTally, keep_intoxication
from aerona.engine.customs.marks import MarkTally, keep_marks
from aerona.engine.customs.naming import NamingTally, keep_naming
from aerona.engine.customs.relief import commute_share, poverty_relief
from aerona.engine.customs.revival import RevivalTally, keep_revivals
from aerona.engine.customs.rights import crossing, has_right, unarmed, unwed_by_law
from aerona.engine.customs.taboo import name_tabooed
from aerona.engine.customs.time_budgets import TimeTally, keep_time_budgets
from aerona.engine.customs.town_life import TownLifeTally, keep_town_life
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
    town.affiliated_entity_id = world.people.id
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
    assert row is not None and row.aim is RevivalAim.RESTORE and row.stage is RevivalStage.STRESS and tally.begun == 1
    for epoch in range(4, 8):
        await keep_revivals(await at(session, epoch, revivals={"stage_gain": 100}), tally)
    assert row.stage is RevivalStage.NEW_STEADY and row.ended_epoch is not None and tally.settled == 1


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
    session.add(BodyMarkRow(holder_node_id=foe.id, kind=MarkKind.BRAND, meaning=MarkMeaning.CRIME, placed_epoch=3, locked=[]))
    await session.flush()
    tally = MarkTally()
    await keep_marks(await at(session, 3), tally)
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
    await keep_age_sets(await at(session, 6, age_sets={"span_epochs": 1, "grade_epochs": 1}), tally)
    found = await session.get(AgeSetRow, member.age_set_id)
    assert found is not None and found.grade is AgeGrade.WARRIORS and await warriors_ready(session, folk.id)


async def test_town_life_eases_poverty_loses_labour_on_the_way_and_pools_means(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Almsby")
    house = await entity(session, "The Open Door", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=house.id, kind=StructureKind.ALMSHOUSE, host_entity_id=town.id))
    guild = await entity(session, "The Fishers", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add_all([DistrictRow(settlement_entity_id=town.id, kind=kind, built_epoch=1) for kind in list(DistrictKind)[:4]])
    session.add(PressureRow(entity_id=town.id, pressure=PressureKind.POVERTY, value=80))
    await session.flush()
    await keep_town_life(await at(session, 3, cooperatives={"found_from": 50}), TownLifeTally())
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
    await bond(session, member.id, guild.id, BondKind.MEMBER_OF)
    await keep_town_life(await at(session, 4), TownLifeTally())
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
    assert len(rows) == 2 and first > 0
    await keep_civics(await at(session, 4), CivicsTally())
    assert case.evidence < first


async def test_citizenship_decides_rights_and_borders_and_measures_shape_trade(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Lawmere")
    other = await settlement(session, "Farport", world, world.regions[1])
    ruler = await mortal(session, "Queen Ama", world, town.id)
    stranger = await mortal(session, "Tov", world, town.id)
    realm = await realm_of(session, world, "Lawmere Realm", town.id)
    abroad = await realm_of(session, world, "Far Realm", other.id)
    await bond(session, ruler.id, realm.id, BondKind.RULES)
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
    session.add(
        RevivalRow(
            people_entity_id=folk.id, aim=RevivalAim.RESTORE, goal=RevivalGoal.REVIVE_LANGUAGE, stage=RevivalStage.DISTORTION, started_epoch=1, locked=[]
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
    assert any("scar" in line for line in lines) and any("revive language" in line for line in lines)
    assert any("revive language" in line for line in await son_customs_lines(scope, world.son))
    assert await poverty_relief(session, tuned_rules(), town.id) > 0
    folk.status, folk.end_epoch = EntityStatus.DESTROYED, 4
    await session.flush()
    assert await mend_customs_links(session, 4) >= 1
