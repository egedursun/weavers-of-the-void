from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.regime_lines import mortal_regime_lines, son_regime_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.cycles import AsabiyyaRow, GiftRow, LongPlanRow, PolityStressRow
from aerona.db.tables.dominion import MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mind import CultureValueRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.regime import (
    AcademicFreedomRow,
    BreedingPlanRow,
    CoalitionMemberRow,
    CredentialRow,
    ExaminationRow,
    ExamSittingRow,
    LineageSegmentRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolLineageRow,
    SchoolMemberRow,
    VenalOfficeRow,
)
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.cycles import CyclePhase, GiftOccasion, GiftState, LongPlanKind, LongPlanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.intrigue import FavourOrigin, IntrigueSecret
from aerona.domain.enums.military import FeudParty, FeudStatus
from aerona.domain.enums.mind import SkillKind, SkillSource, TraitKind, TraitSource, ValueAxis
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.regime import CredentialKind, LeadershipMode, PowerStance, Routinisation, SegmentLevel, SelectorateKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import FactionStats, HouseStats, PeopleStats, PolityStats, StructureStats
from aerona.engine.collective.roles import career_open
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import AsabiyyaTally, keep_asabiyya
from aerona.engine.cycles.stress import StressTally, read_stress
from aerona.engine.intrigue.favours import owe
from aerona.engine.mind.book import add_trait
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.offices import usurper_for
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from aerona.engine.regime.book import (
    appointment_weights,
    corruption_pull,
    coup_factor,
    credential_rank,
    extraction_of,
    feud_swell,
    freedom_factor,
    inquiry_factor,
    legitimacy_kinds,
    morale_factor,
    patron_pull,
    schooled,
)
from aerona.engine.regime.control import edit_record, found_school, set_freedom
from aerona.engine.regime.learning import LearningTally, keep_learning
from aerona.engine.regime.lineages import LineageTally, keep_lineages
from aerona.engine.regime.patronage import PatronageTally, keep_patronage, purge_subject
from aerona.engine.regime.rule import RegimeTally, keep_regimes
from aerona.services.integrity.regime_links import mend_regime_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules

POPULATION = 2000


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "regime", rules=tuned_rules(**namespaces))


async def at_epoch(session: AsyncSession, epoch: int, **namespaces: dict[str, int]) -> TickContext:
    cosmos = await session.scalar(select(CosmosRow).limit(1))
    assert cosmos is not None
    cosmos.epoch = epoch
    await session.flush()
    return await context(session, **namespaces)


async def town_of(session: AsyncSession, world: CoreWorld, name: str, region: int = 0) -> EntityRow:
    town = await settlement(session, name, world, world.regions[region], population=POPULATION)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=500, militia=10, locked=[], foreigners={}))
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            share_farmer=60.0,
            share_artisan=10.0,
            share_merchant=5.0,
            share_priest=5.0,
            share_warrior=5.0,
            share_scribe=5.0,
            share_noble=10.0,
            share_serf_or_slave=0.0,
            share_outcast=0.0,
            share_monastic=0.0,
            **{f"satisfaction_{item.value}": 60 for item in SocialClass},
            stock_food=500,
            stock_ore=100,
            stock_goods=100,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    await session.flush()
    return town


async def realm_of(
    session: AsyncSession,
    world: CoreWorld,
    towns: list[EntityRow],
    ruler: EntityRow | None = None,
    *,
    government: GovernmentKind = GovernmentKind.MONARCHY,
    rule: DecisionRule = DecisionRule.AUTOCRATIC,
    treasury: int = 2000,
    debt: int = 0,
) -> EntityRow:
    polity = await entity(session, f"Crown of {towns[0].name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=government,
            decision_rule=rule,
            capital_entity_id=towns[0].id,
            core_entity_id=polity.id,
            legitimacy=50,
            stability=50,
            treasury=treasury,
            debt=debt,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    for town in towns:
        session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity


def skilled(session: AsyncSession, mortal_id: int, skill: SkillKind, level: int) -> None:
    session.add(SkillRow(holder_node_id=mortal_id, skill=skill, level=level, xp=0, peak=level, last_used_epoch=1, source=SkillSource.PRACTICE))


async def test_a_narrow_coalition_buys_loyalty_and_a_wide_one_builds(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    other = await town_of(session, world, "Farside", region=1)
    ruler = await mortal(session, "Ruler", world, town.id)
    lord = await mortal(session, "Lord", world, town.id)
    lord.social_class = SocialClass.NOBLE
    lord.importance = 80
    narrow = await realm_of(session, world, [town], ruler, rule=DecisionRule.AUTOCRATIC)
    wide = await realm_of(session, world, [other], None, government=GovernmentKind.REPUBLIC, rule=DecisionRule.ASSEMBLY)
    ctx = await context(session)
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    small, large = await session.get(RegimeRow, narrow.id), await session.get(RegimeRow, wide.id)
    assert small is not None and large is not None
    assert small.selectorate is SelectorateKind.NOBLES and large.selectorate is SelectorateKind.CITIZENS
    assert small.public_share < large.public_share
    member = await session.get(CoalitionMemberRow, (narrow.id, lord.id))
    assert member is not None and member.reward > 0
    assert tally.public_goods > 0 and tally.private_goods > 0
    assert stat_or(other, "prosperity", 0) > stat_or(town, "prosperity", 0) or tally.public_goods > 0
    member.loyalty = 0
    member.reward = 0
    small.coalition_loyalty = 0
    ctx = await context(session, selectorate={"purge_pct": 100, "purge_at": 90})
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    assert tally.purged == 1 and await session.get(CoalitionMemberRow, (narrow.id, lord.id)) is None


async def test_a_founders_death_brings_a_crisis_then_turns_charisma(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    founder = await mortal(session, "Founder", world, town.id, charisma=95)
    founder.importance = 95
    heir = await mortal(session, "Heir", world, town.id)
    realm = await realm_of(session, world, [town], founder)
    ctx = await context(session, legitimacy_types={"drift_pct": 100}, charisma_routinisation={"schism_pct": 0})
    await keep_regimes(ctx, RegimeTally())
    row = await session.get(RegimeRow, realm.id)
    assert row is not None and row.founder_entity_id == founder.id
    row.charismatic, row.traditional, row.rational = 90, 10, 0
    row.locked = ["charismatic", "traditional", "rational"]
    founder.status = EntityStatus.DEAD
    founder.end_epoch = 1
    seat = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER))
    assert seat is not None
    seat.holder_entity_id = heir.id
    await session.flush()
    await keep_regimes(ctx, RegimeTally())
    assert row.routinisation is Routinisation.PENDING and row.crisis_epoch is not None
    row.locked = []
    ctx = await at_epoch(session, 5, charisma_routinisation={"schism_pct": 0})
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    assert row.routinisation is Routinisation.DYNASTY and tally.routinised == 1
    parts = await legitimacy_kinds(session, ctx.rules, realm.id)
    assert parts


async def test_an_insecure_ruler_plunders_and_guards_the_throne(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Old Ruler", world, town.id, age=68, lifespan=70)
    realm = await realm_of(session, world, [town], ruler)
    session.add(
        PolityStressRow(
            polity_entity_id=realm.id,
            pressure=90,
            immiseration=90,
            elite_overproduction=90,
            fiscal_distress=90,
            psi=90,
            aspirants=0,
            positions=0,
            challenge=0,
            phase=CyclePhase.CRISIS,
            updated_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    ctx = await context(session, coup_proofing={"adopt_pct": 100})
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    row = await session.get(RegimeRow, realm.id)
    assert row is not None and row.horizon < 50 and row.extraction > 100
    assert await extraction_of(session, realm.id) > 1
    assert tally.measures == 1 and row.rotation
    before = await coup_factor(session, ctx.rules, realm.id)
    row.parallel_guard = row.hostages = True
    assert await coup_factor(session, ctx.rules, realm.id) < before
    assert await morale_factor(session, ctx.rules, town.id) < 1


async def test_clients_win_appointments_and_votes_where_institutions_are_weak(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    client = await mortal(session, "Client", world, town.id)
    stranger = await mortal(session, "Stranger", world, town.id)
    realm = await realm_of(session, world, [town], ruler)
    ctx = await context(session)
    await keep_regimes(ctx, RegimeTally())
    await owe(ctx, client.id, ruler.id, FavourOrigin.GIFT, 60)
    await session.flush()
    await keep_patronage(ctx, PatronageTally())
    tie = await session.scalar(select(PatronageTieRow).where(PatronageTieRow.client_entity_id == client.id))
    assert tie is not None and tie.patron_node_id == ruler.id
    row = await session.get(RegimeRow, realm.id)
    assert row is not None
    row.institutions = 0
    weights = await appointment_weights(session, ctx.rules, realm.id, ruler.id, [client.id, stranger.id])
    assert weights[client.id] > weights[stranger.id]
    assert await patron_pull(session, ctx.rules, realm.id, ruler.id, client.id) > 0


async def test_an_indebted_realm_sells_a_seat_that_repays_its_buyer(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    buyer = await mortal(session, "Buyer", world, town.id)
    session.add(MortalProfileRow(entity_id=buyer.id, wealth=100, locked=[]))
    realm = await realm_of(session, world, [town], ruler, debt=5000)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.TREASURER, holder_entity_id=None, powers=[], locked=[]))
    await session.flush()
    ctx = await context(session, venality={"sell_pct": 100, "base_price": 100})
    await keep_regimes(ctx, RegimeTally())
    tally = PatronageTally()
    await keep_patronage(ctx, tally)
    venal = await session.scalar(select(VenalOfficeRow))
    assert tally.sold == 1 and venal is not None and venal.buyer_entity_id == buyer.id
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    assert await corruption_pull(session, ctx.rules, realm.id) > 0
    await keep_patronage(ctx, PatronageTally())
    assert venal.recouped > 0


async def test_a_great_subject_plots_and_leads_the_coup(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    far = await town_of(session, world, "Farside", region=1)
    ruler = await mortal(session, "Ruler", world, town.id)
    governor = await mortal(session, "Governor", world, far.id)
    governor.importance = 90
    session.add(MortalProfileRow(entity_id=governor.id, wealth=100, locked=[]))
    await add_trait(session, governor.id, TraitKind.AMBITIOUS, TraitSource.BIRTH, 0)
    realm = await realm_of(session, world, [town, far], ruler)
    session.add(
        OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.GOVERNOR, holder_entity_id=governor.id, region_entity_id=world.regions[1].id, powers=[], locked=[])
    )
    await session.flush()
    ctx = await context(session, power_bases={"plot_at": 40})
    await keep_regimes(ctx, RegimeTally())
    await keep_patronage(ctx, PatronageTally())
    base = await session.get(PowerBaseRow, governor.id)
    assert base is not None and base.threat >= 40 and base.stance is PowerStance.PLOTTING
    book = await RealmBook.load(session)
    usurper, _ = await usurper_for(ctx, book.realms[realm.id])
    assert usurper is not None and usurper.id == governor.id


async def test_a_big_mans_following_breaks_apart_at_the_death(session: AsyncSession, world: CoreWorld) -> None:
    towns = [await town_of(session, world, f"Camp {index}", region=index % 3) for index in range(3)]
    big_man = await mortal(session, "Big Man", world, towns[0].id)
    heir = await mortal(session, "Heir", world, towns[0].id)
    realm = await realm_of(session, world, towns, big_man, government=GovernmentKind.CHIEFDOM)
    session.add(GiftRow(giver_node_id=big_man.id, receiver_node_id=heir.id, value=10, occasion=GiftOccasion.FEAST, state=GiftState.OPEN, epoch=0, locked=[]))
    await session.flush()
    ctx = await context(session, charisma_routinisation={"fragment_pct": 100}, leadership_modes={"chief_pct": 0})
    await keep_regimes(ctx, RegimeTally())
    row = await session.get(RegimeRow, realm.id)
    assert row is not None and row.leadership is LeadershipMode.ACHIEVED
    big_man.status = EntityStatus.DEAD
    big_man.end_epoch = 1
    seat = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER))
    assert seat is not None
    seat.holder_entity_id = heir.id
    await session.flush()
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    assert tally.fragmented == 2


async def test_lines_take_sides_in_a_feud_by_their_kinship(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    founder = await mortal(session, "Elder", world, town.id)
    houses = []
    for name, parent in (("Root", None), ("Elder Branch", 0), ("Younger Branch", 0), ("Cadet", 1)):
        house = await entity(session, f"House {name}", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
        session.add(
            HouseProfileRow(
                house_entity_id=house.id,
                founder_entity_id=founder.id,
                parent_house_id=houses[parent].id if parent is not None else None,
                emblem={},
                traits=[],
                seats=[],
                locked=[],
            )
        )
        houses.append(house)
    await session.flush()
    feud = FeudRow(first_entity_id=houses[1].id, second_entity_id=houses[2].id, party=FeudParty.HOUSE, status=FeudStatus.ACTIVE, since_epoch=0, locked=[])
    session.add(feud)
    await session.flush()
    ctx = await context(session)
    tally = LineageTally()
    await keep_lineages(ctx, tally)
    cadet = await session.get(LineageSegmentRow, houses[3].id)
    root = await session.get(LineageSegmentRow, houses[0].id)
    assert cadet is not None and cadet.backs_entity_id == houses[1].id
    assert root is not None and root.level is SegmentLevel.CLAN and root.backs_entity_id is None
    assert await feud_swell(session, ctx.rules, feud) > 1


async def test_a_breeding_design_marries_the_house_to_carriers(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    house = await entity(session, "House Line", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    heir = await mortal(session, "Heir", world, town.id, age=20)
    carrier = await mortal(session, "Carrier", world, town.id, age=20)
    session.add(HouseProfileRow(house_entity_id=house.id, founder_entity_id=heir.id, head_entity_id=heir.id, emblem={}, traits=[], seats=[], locked=[]))
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=heir.id))
    session.add(GenomeRow(holder_node_id=carrier.id, genes={"height": ["tall", "tall"]}))
    design = LongPlanRow(
        holder_node_id=house.id,
        target_node_id=house.id,
        kind=LongPlanKind.BLOODLINE,
        name="The Tall Line",
        steps=4,
        progress=0,
        step_cost=0,
        secrecy=50,
        locked=[],
    )
    session.add(design)
    await session.flush()
    plan = BreedingPlanRow(plan_id=design.id, house_entity_id=house.id, locus="height", allele="tall", target_share=50, locked=[])
    session.add(plan)
    await session.flush()
    ctx = await context(session, breeding_plans={"love_pct": 0, "conceal_pct": 100})
    tally = LineageTally()
    await keep_lineages(ctx, tally)
    assert tally.matches == 1 and plan.matches == 1 and plan.concealed == 1
    ctx = await context(session, breeding_plans={"love_pct": 100})
    plan_two = await session.get(BreedingPlanRow, design.id)
    assert plan_two is not None and design.status is LongPlanStatus.ACTIVE


async def test_examinations_grant_credentials_that_open_office_and_swell_the_aspirants(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    scholar = await mortal(session, "Scholar", world, town.id)
    dunce = await mortal(session, "Dunce", world, town.id)
    skilled(session, scholar.id, SkillKind.LAW, 60)
    realm = await realm_of(session, world, [town], ruler)
    session.add(HolderTechniqueRow(holder_entity_id=realm.id, technique=Technique.EXAMINATIONS, since_epoch=0, secret=False))
    await session.flush()
    ctx = await context(session, examinations={"pass_rate": 100, "graduate_weight": 100})
    tally = LearningTally()
    await keep_learning(ctx, tally)
    sitting = await session.scalar(select(ExamSittingRow))
    assert await session.get(ExaminationRow, realm.id) is not None and sitting is not None and sitting.passed > 0
    gathered = await session.scalar(select(GatheringRow).where(GatheringRow.kind == GatheringKind.EXAMINATION))
    assert gathered is not None and gathered.host_node_id == realm.id
    credential = await session.scalar(select(CredentialRow).where(CredentialRow.mortal_entity_id == scholar.id))
    assert credential is not None and credential.kind is CredentialKind.EXAMINATION
    assert await career_open(session, ctx.rules, scholar, CareerPath.OFFICE)
    assert not await career_open(session, ctx.rules, dunce, CareerPath.OFFICE)
    reading = (await read_stress(ctx, StressTally()))[0][2]
    assert reading.aspirants >= sitting.passed


async def test_suppressed_learning_drives_scholars_to_a_freer_house(session: AsyncSession, world: CoreWorld) -> None:
    stifled = await town_of(session, world, "Ashby")
    free = await town_of(session, world, "Farside", region=1)
    for host, name in ((stifled, "Old Academy"), (free, "Open Academy")):
        hall = await entity(session, name, EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=host.id)
        session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.ACADEMY, host_entity_id=host.id, effect_pct=100, locked=[]))
    scholar = await mortal(session, "Scholar", world, stifled.id)
    skilled(session, scholar.id, SkillKind.LORE, 80)
    session.add(HolderTechniqueRow(holder_entity_id=stifled.id, technique=Technique.LOGIC, since_epoch=0, secret=False))
    await session.flush()
    ctx = await context(session, academic_freedom={"migrate_pct": 100, "drift_pct": 100})
    await keep_learning(ctx, LearningTally())
    rows = {row.structure_entity_id: row for row in await session.scalars(select(AcademicFreedomRow))}
    assert len(rows) == 2
    stifled_row = next(row for row in rows.values() if row.level == min(item.level for item in rows.values()))
    stifled_row.level, stifled_row.suppressed, stifled_row.locked = 5, True, ["level", "suppressed"]
    await session.flush()
    assert await freedom_factor(session, ctx.rules, stifled.id) < await freedom_factor(session, ctx.rules, free.id)
    tally = LearningTally()
    await keep_learning(ctx, tally)
    assert tally.migrated == 1 and scholar.location_id == free.id
    credentials = {row.kind for row in await session.scalars(select(CredentialRow).where(CredentialRow.mortal_entity_id == scholar.id))}
    assert CredentialKind.MASTER in credentials and CredentialKind.DOCTOR in credentials


async def test_a_master_gathers_a_school_that_teaches_and_keeps_its_learning(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    hall = await entity(session, "Hall", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.SCHOOL, host_entity_id=town.id, effect_pct=100, locked=[]))
    master = await mortal(session, "Master", world, town.id)
    skilled(session, master.id, SkillKind.LORE, 80)
    disciples = []
    for index in range(2):
        pupil = await mortal(session, f"Pupil {index}", world, town.id)
        skilled(session, pupil.id, SkillKind.LORE, 10)
        disciples.append(pupil)
    await session.flush()
    ctx = await context(session, school_lineages={"teach_xp": 500})
    tally = LearningTally()
    await keep_learning(ctx, tally)
    school = await session.scalar(select(SchoolLineageRow))
    assert school is not None and school.founder_entity_id == master.id and tally.schools == 1
    members = list(await session.scalars(select(SchoolMemberRow).where(SchoolMemberRow.school_id == school.id)))
    assert len(members) == 3 and tally.taught == 2
    assert await schooled(session, town.id)
    master.status = EntityStatus.DEAD
    master.end_epoch = 1
    await session.flush()
    await keep_learning(ctx, LearningTally())
    led = [row for row in await session.scalars(select(SchoolMemberRow).where(SchoolMemberRow.school_id == school.id))]
    assert all(row.master_entity_id != master.id for row in led)


async def test_mortals_and_sons_hear_of_rule_patrons_and_learning(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    me = await mortal(session, "Me", world, town.id)
    realm = await realm_of(session, world, [town], ruler)
    ctx = await context(session)
    await keep_regimes(ctx, RegimeTally())
    session.add(PatronageTieRow(patron_node_id=ruler.id, client_entity_id=me.id, strength=40, since_epoch=0, locked=[]))
    session.add(CredentialRow(mortal_entity_id=me.id, kind=CredentialKind.MASTER, epoch=0, locked=[]))
    row = await session.get(RegimeRow, realm.id)
    assert row is not None
    row.routinisation = Routinisation.SCHISM
    world.son.current_world_id = world.world.id
    await session.flush()
    scope = await load_scope(session, ctx.rules)
    text = " ".join(await mortal_regime_lines(scope, me))
    assert "your patron is Ruler" in text and "credential of master" in text and "chosen by its nobles" in text
    session.add(PowerBaseRow(mortal_entity_id=me.id, polity_entity_id=realm.id, threat=90, stance=PowerStance.PLOTTING, locked=[]))
    await session.flush()
    lines = await son_regime_lines(scope, world.son)
    assert any(f"(polity {realm.id}) is torn" in line for line in lines)
    assert any(f"(mortal {me.id}) plots to take power in" in line for line in lines)
    throne = " ".join(await mortal_regime_lines(scope, ruler))
    assert f"(mortal {me.id}) stands plotting toward your rule" in throne


async def test_integrity_lets_the_dead_leave_circles_and_ties(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    gone = await mortal(session, "Gone", world, town.id)
    realm = await realm_of(session, world, [town], ruler)
    session.add(CoalitionMemberRow(polity_entity_id=realm.id, mortal_entity_id=gone.id, locked=[]))
    session.add(PatronageTieRow(patron_node_id=ruler.id, client_entity_id=gone.id, strength=40, since_epoch=0, locked=[]))
    gone.status = EntityStatus.DEAD
    gone.end_epoch = 1
    await session.flush()
    assert await mend_regime_links(session) == 2
    assert await session.get(CoalitionMemberRow, (realm.id, gone.id)) is None


async def test_story_19_the_soft_dynasty(session: AsyncSession, world: CoreWorld) -> None:
    capital = await town_of(session, world, "River Seat")
    frontier_town = await settlement(session, "Far Camps", world, world.regions[1])
    raiders = await entity(session, "Far Riders", EntityType.PEOPLE, PeopleStats(population=3000), world_id=world.world.id, location_id=world.regions[1].id)
    await BondRepository(session).connect(BondDraft(raiders.id, frontier_town.id, BondKind.LIVES_IN, 0))
    for axis, mine, theirs in ((ValueAxis.MARTIAL, 90, -90), (ValueAxis.MERCY, -90, 90), (ValueAxis.PIETY, 80, -80)):
        session.add(CultureValueRow(entity_id=world.people.id, axis=axis, value=mine))
        session.add(CultureValueRow(entity_id=raiders.id, axis=axis, value=theirs))
    khan = await mortal(session, "Khan", world, capital.id, charisma=95)
    khan.importance = 95
    heir = await mortal(session, "Heir", world, capital.id)
    scholar = await mortal(session, "Scholar", world, capital.id)
    skilled(session, scholar.id, SkillKind.LAW, 70)
    realm = await realm_of(session, world, [capital], khan)
    ctx = await context(session, legitimacy_types={"drift_pct": 100}, charisma_routinisation={"schism_pct": 0})
    await keep_regimes(ctx, RegimeTally())
    rule = await session.get(RegimeRow, realm.id)
    assert rule is not None and rule.founder_entity_id == khan.id
    rule.charismatic, rule.traditional, rule.rational = 90, 10, 0
    rule.locked = ["charismatic", "traditional", "rational"]
    khan.status = EntityStatus.DEAD
    khan.end_epoch = 1
    seat = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER))
    assert seat is not None
    seat.holder_entity_id = heir.id
    await session.flush()
    await keep_regimes(ctx, RegimeTally())
    rule.locked = []
    ctx = await at_epoch(session, 3, charisma_routinisation={"schism_pct": 0}, examinations={"pass_rate": 100})
    await keep_regimes(ctx, RegimeTally())
    assert rule.routinisation is Routinisation.DYNASTY
    before = (await read_stress(ctx, StressTally()))[0][2]
    aspirants, overproduction = before.aspirants, before.elite_overproduction
    session.add(HolderTechniqueRow(holder_entity_id=realm.id, technique=Technique.EXAMINATIONS, since_epoch=3, secret=False))
    await session.flush()
    await keep_learning(ctx, LearningTally())
    after = (await read_stress(ctx, StressTally()))[0][2]
    assert after.aspirants > aspirants and after.elite_overproduction >= overproduction
    society = await session.get(CommunitySocietyRow, capital.id)
    assert society is not None
    for social_class in SocialClass:
        setattr(society, f"satisfaction_{social_class.value}", 95)
    session.add(AsabiyyaRow(holder_entity_id=realm.id, value=80, frontier=0, luxury_generations=5, locked=[]))
    await session.flush()
    ctx = await at_epoch(session, 4, asabiyya={"frontier_floor": 10, "frontier_ratio_pct": 100, "frontier_gain": 5})
    await keep_asabiyya(ctx, AsabiyyaTally())
    dynasty = await session.get(AsabiyyaRow, realm.id)
    frontier_people = await session.get(AsabiyyaRow, raiders.id)
    assert dynasty is not None and dynasty.value < 80
    assert frontier_people is not None and frontier_people.frontier >= 1 and frontier_people.value > 50


async def test_wealth_and_renown_alone_never_extort_the_throne(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    magnate = await mortal(session, "Magnate", world, town.id)
    magnate.importance = 100
    session.add(MortalProfileRow(entity_id=magnate.id, wealth=100, locked=[]))
    realm = await realm_of(session, world, [town], None, treasury=0)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.TREASURER, holder_entity_id=magnate.id, powers=[], locked=[]))
    await session.flush()
    ctx = await context(session)
    await keep_regimes(ctx, RegimeTally())
    await keep_patronage(ctx, PatronageTally())
    base = await session.get(PowerBaseRow, magnate.id)
    assert base is not None and base.holdings == 0 and base.troops == 0
    assert base.stance in {PowerStance.LOYAL, PowerStance.DEFIANT}


async def test_a_school_named_with_an_article_is_never_doubled(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    founder = await mortal(session, "Founder", world, town.id)
    ctx = await context(session)
    school = await found_school(ctx, founder.id, "The Old Count", None)
    text = " ".join(await mortal_regime_lines(await load_scope(session, ctx.rules), founder))
    assert school.name == "The Old Count" and "you belong to The Old Count" in text and "the The" not in text


async def test_a_realm_without_its_choosing_class_is_chosen_by_its_other_elites(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    society = await session.get(CommunitySocietyRow, town.id)
    assert society is not None
    society.share_noble = 0.0
    society.share_farmer = 70.0
    priest = await mortal(session, "Priest", world, town.id)
    priest.social_class = SocialClass.PRIEST
    realm = await realm_of(session, world, [town], None)
    await keep_regimes(await context(session), RegimeTally())
    row = await session.get(RegimeRow, realm.id)
    assert row is not None and row.selectorate is SelectorateKind.NOBLES and row.selectorate_size > 0 and row.coalition_size > 0
    assert await session.get(CoalitionMemberRow, (realm.id, priest.id)) is not None


async def test_setting_learning_below_the_mark_suppresses_it_at_once(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    hall = await entity(session, "Hall", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.ACADEMY, host_entity_id=town.id, effect_pct=100, locked=[]))
    await session.flush()
    ctx = await context(session)
    row = await set_freedom(ctx, hall.id, {"level": 10})
    assert row.suppressed
    await edit_record(ctx, "academic_freedom", hall.id, {"level": 90}, [])
    assert not row.suppressed


async def test_power_balance_public_contentment_and_regard_shape_the_circle(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    friend = await mortal(session, "Friend", world, town.id)
    rival = await mortal(session, "Rival", world, town.id)
    for lord in (friend, rival):
        lord.social_class = SocialClass.NOBLE
        lord.importance = 70
    realm = await realm_of(session, world, [town], ruler, rule=DecisionRule.ASSEMBLY, treasury=20000)
    ctx = await context(session)
    await keep_regimes(ctx, RegimeTally())
    row = await session.get(RegimeRow, realm.id)
    assert row is not None
    wide = row.coalition_size
    society = await session.get(CommunitySocietyRow, town.id)
    assert society is not None and society.satisfaction_farmer > 60
    guild = await entity(session, "Grain Guild", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=town.id, influence_over={str(realm.id): 90}))
    session.add(RelationshipRow(holder_node_id=friend.id, subject_node_id=ruler.id, friendship=90, since_epoch=0, last_epoch=0))
    session.add(RelationshipRow(holder_node_id=rival.id, subject_node_id=ruler.id, rivalry=90, since_epoch=0, last_epoch=0))
    await session.flush()
    await keep_regimes(ctx, RegimeTally())
    assert row.coalition_size < wide
    liked, disliked = await session.get(CoalitionMemberRow, (realm.id, friend.id)), await session.get(CoalitionMemberRow, (realm.id, rival.id))
    assert liked is not None and disliked is not None and liked.loyalty > disliked.loyalty


async def test_miracles_feed_charisma_and_a_schism_raises_a_rival_claim(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    founder = await mortal(session, "Founder", world, town.id, charisma=90)
    child = await mortal(session, "Child", world, town.id)
    heir = await mortal(session, "Heir", world, town.id)
    await BondRepository(session).connect(BondDraft(founder.id, child.id, BondKind.PARENT_OF, 0))
    realm = await realm_of(session, world, [town], founder)
    ctx = await context(session, legitimacy_types={"drift_pct": 100}, charisma_routinisation={"schism_pct": 100})
    await keep_regimes(ctx, RegimeTally())
    row = await session.get(RegimeRow, realm.id)
    assert row is not None
    plain = row.charismatic
    session.add(MiracleRecordRow(god_node_id=world.son.id, kind="healing", epoch=1, credited_node_id=founder.id, locked=[]))
    await session.flush()
    await keep_regimes(ctx, RegimeTally())
    assert row.charismatic > plain
    row.founder_entity_id = founder.id
    row.charismatic, row.traditional, row.rational = 90, 10, 0
    row.locked = ["charismatic", "traditional", "rational"]
    founder.status = EntityStatus.DEAD
    founder.end_epoch = 1
    seat = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER))
    assert seat is not None
    seat.holder_entity_id = heir.id
    await session.flush()
    await keep_regimes(ctx, RegimeTally())
    row.locked = []
    ctx = await at_epoch(session, 4, charisma_routinisation={"schism_pct": 100})
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    claim = await session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == child.id, ClaimRow.polity_entity_id == realm.id))
    assert tally.schisms == 1 and row.routinisation is Routinisation.SCHISM and claim is not None


async def test_a_ruler_answers_a_plotter_by_marriage_then_split_command_then_purge(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    far = await town_of(session, world, "Farside", region=1)
    ruler = await mortal(session, "Ruler", world, town.id)
    daughter = await mortal(session, "Ruler's Child", world, town.id, age=20)
    await BondRepository(session).connect(BondDraft(ruler.id, daughter.id, BondKind.PARENT_OF, 0))
    plotter = await mortal(session, "Plotter", world, far.id, age=30)
    plotter.importance = 90
    session.add(MortalProfileRow(entity_id=plotter.id, wealth=100, locked=[]))
    await add_trait(session, plotter.id, TraitKind.AMBITIOUS, TraitSource.BIRTH, 0)
    realm = await realm_of(session, world, [town, far], ruler, treasury=0)
    session.add(
        OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.GOVERNOR, holder_entity_id=plotter.id, region_entity_id=world.regions[1].id, powers=[], locked=[])
    )
    await session.flush()
    ctx = await context(session, power_bases={"plot_at": 30, "counter_pct": 100})
    await keep_regimes(ctx, RegimeTally())
    tally = PatronageTally()
    await keep_patronage(ctx, tally)
    assert tally.married == 1
    base = await session.get(PowerBaseRow, plotter.id)
    assert base is not None and base.stance is PowerStance.LOYAL
    book = await RealmBook.load(session)
    assert await purge_subject(ctx, book.realms[realm.id], plotter)
    assert await session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == plotter.id)) is None


async def test_concealed_parentage_becomes_a_secret_and_credentials_put_their_holder_first(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    house = await entity(session, "House Line", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    heir = await mortal(session, "Heir", world, town.id, age=20)
    carrier = await mortal(session, "Carrier", world, town.id, age=20)
    session.add(HouseProfileRow(house_entity_id=house.id, founder_entity_id=heir.id, head_entity_id=heir.id, emblem={}, traits=[], seats=[], locked=[]))
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=heir.id))
    session.add(GenomeRow(holder_node_id=carrier.id, genes={"height": ["tall", "tall"]}))
    design = LongPlanRow(
        holder_node_id=house.id,
        target_node_id=house.id,
        kind=LongPlanKind.BLOODLINE,
        name="The Tall Line",
        steps=4,
        progress=0,
        step_cost=0,
        secrecy=50,
        locked=[],
    )
    session.add(design)
    await session.flush()
    session.add(BreedingPlanRow(plan_id=design.id, house_entity_id=house.id, locus="height", allele="tall", target_share=50, locked=[]))
    session.add(CredentialRow(mortal_entity_id=carrier.id, kind=CredentialKind.DOCTOR, epoch=0, locked=[]))
    await session.flush()
    ctx = await context(session, breeding_plans={"love_pct": 0, "conceal_pct": 100})
    await keep_lineages(ctx, LineageTally())
    secret = await session.scalar(select(SecretRow).where(SecretRow.holder_node_id == heir.id, SecretRow.kind == IntrigueSecret.TRUE_PARENTAGE))
    assert secret is not None and secret.about_node_id == house.id
    assert await credential_rank(session, carrier.id, 2, 0) == 0
    assert await credential_rank(session, heir.id, 2, 0) == 2


async def test_free_inquiry_weighs_evidence_more_than_stifled_inquiry(session: AsyncSession, world: CoreWorld) -> None:
    free = await town_of(session, world, "Openhall")
    stifled = await town_of(session, world, "Closedhall", region=1)
    for host, level in ((free, 90), (stifled, 10)):
        hall = await entity(session, f"Hall of {host.name}", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=host.id)
        session.add(StructureProfileRow(structure_entity_id=hall.id, kind=StructureKind.ACADEMY, host_entity_id=host.id, effect_pct=100, locked=[]))
        session.add(AcademicFreedomRow(structure_entity_id=hall.id, level=level, suppressed=level < 30, locked=[]))
    await session.flush()
    rules = (await context(session)).rules
    assert await inquiry_factor(session, rules, free.id) > 1 > await inquiry_factor(session, rules, stifled.id)
