import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.cycle_lines import mortal_cycle_lines, son_cycle_lines
from aerona.agents.context.scope import load_scope
from aerona.catalog.genetics import GIFT_LOCI_ORDER
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.collective import AccountRow, DiasporaRow, FoundingMythRow, RoleNormRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.cycles import (
    AsabiyyaRow,
    CampRow,
    ChallengeRow,
    CircuitRow,
    ConfederationRow,
    DivineDebtRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LegacyTraitRow,
    LongPlanRow,
    ManumissionRow,
    MarriageAllianceRow,
    MortalCasteRow,
    PeopleReproductionRow,
    PolityStressRow,
    SlaveMarketRow,
    StressReadingRow,
)
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleCultureRow
from aerona.db.tables.discovery import ArtFormPractitionerRow, ArtFormProfileRow
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.genetics import AllelePoolRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mind import CultureEthicRow, CultureValueRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, LabourReasonRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow
from aerona.db.tables.warfare import TributeRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.collective import AccountKind, RoleEligibility, RoleKind
from aerona.domain.enums.culture import ArtMode, Technique
from aerona.domain.enums.cycles import (
    ChallengeKind,
    ChallengeResponse,
    CyclePhase,
    GiftOccasion,
    GiftState,
    KinshipDescent,
    LabourRegime,
    LegacyKind,
    LongPlanKind,
    LongPlanStatus,
    ManumissionPath,
    MobilityMode,
    ReproductiveCaste,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.demography import AgeBand, CohortCondition, InheritanceCustom, Job, MartialStyle, Sex
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.mind import ActKind, EthicalStance, ValueAxis
from aerona.domain.enums.mortal import CareerPath, MarriageEnd
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import LabourReason
from aerona.domain.enums.structure import ConstructionStatus, StructureKind
from aerona.domain.enums.unions import UnionExchange, UnionPurpose
from aerona.domain.models.entity_stats import ArtFormStats, HouseStats, MortalStats, PeopleStats, PolityStats, StructureStats
from aerona.engine.collective.roles import career_open, combat_sexes, role_rank
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import AsabiyyaTally, homeland_psi, keep_asabiyya
from aerona.engine.cycles.bondage import BondageTally, bind_migrants, keep_markets, lay_corvees, raise_freed, serve_terms, work_corvees
from aerona.engine.cycles.breeding import born_sex, caste_for
from aerona.engine.cycles.challenge import ChallengeTally, meet_challenges
from aerona.engine.cycles.control import free_bound, new_plan, set_kinship, set_legacy, set_union
from aerona.engine.cycles.gifts import GiftTally, balance, give, keep_offerings, return_gift, settle_due
from aerona.engine.cycles.hospitality import circuit_partners, circuit_stops
from aerona.engine.cycles.indenture import freed_stigma
from aerona.engine.cycles.kinship import KinshipTally, keep_kinship
from aerona.engine.cycles.legacy import LegacyTally, keep_legacies
from aerona.engine.cycles.lineage import breeds, descent_heirs, kin_bars
from aerona.engine.cycles.nomads import NomadTally, keep_nomads
from aerona.engine.cycles.plans import PlanTally, advance_plans
from aerona.engine.cycles.reproduction import ReproductionTally, keep_reproduction
from aerona.engine.cycles.seeding import SeedTally, seed_peoples
from aerona.engine.cycles.stress import StressTally, psi, read_stress, realm_capacity
from aerona.engine.demography.kinship import inheritance_of, may_wed
from aerona.engine.economy.purse import coin_of
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import HEADCOUNT_KEY
from aerona.engine.lore.taboos import guest_killed
from aerona.engine.mortal.kinship import add_parent, marry
from aerona.engine.phases.cycles import structural_demography
from aerona.engine.primitives.capacity import CapacityModel
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.rules.registry import Rules
from aerona.services.integrity.cycle_links import mend_cycle_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules

POPULATION = 2000


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "cycles", rules=tuned_rules(**namespaces))


async def at_epoch(session: AsyncSession, epoch: int, **namespaces: dict[str, int]) -> TickContext:
    cosmos = await session.scalar(select(CosmosRow).limit(1))
    assert cosmos is not None
    cosmos.epoch = epoch
    await session.flush()
    return await context(session, **namespaces)


async def town_of(
    session: AsyncSession, world: CoreWorld, name: str, region: int = 0, *, population: int = POPULATION, tier: SizeTier = SizeTier.TOWN
) -> EntityRow:
    town = await settlement(session, name, world, world.regions[region], population=population)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=tier, treasury=500, militia=10, locked=[], foreigners={}))
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            share_farmer=70.0,
            share_artisan=10.0,
            share_merchant=5.0,
            share_priest=3.0,
            share_warrior=4.0,
            share_scribe=2.0,
            share_noble=6.0,
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
    session: AsyncSession, world: CoreWorld, town: EntityRow, ruler: EntityRow | None = None, *, treasury: int = 500, debt: int = 0
) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            capital_entity_id=town.id,
            legitimacy=50,
            stability=50,
            treasury=treasury,
            debt=debt,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, locked=[]))
    await session.flush()
    return polity


async def society_of(session: AsyncSession, town: EntityRow) -> CommunitySocietyRow:
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None
    return row


def wages(society: CommunitySocietyRow, pressure: int) -> None:
    content = max(0, 90 - pressure)
    for social_class in (SocialClass.FARMER, SocialClass.ARTISAN, SocialClass.OUTCAST):
        setattr(society, f"satisfaction_{social_class.value}", content)


async def test_the_stress_index_rises_into_crisis_and_falls_back_in_a_closed_world(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby", population=300)
    realm = await realm_of(session, world, town, debt=600, treasury=100)
    society = await society_of(session, town)
    model = await CapacityModel.load(session, Rules())
    capacity = realm_capacity(model, [town])
    set_stats(town, population=round(capacity * 0.45))
    wages(society, 0)
    namespaces = {"structural_demography": {"elite_fall_pct": 30, "counter_elite_pct": 0, "overproduction_scale": 40, "positions_per_town": 10}}
    phases: list[CyclePhase] = []
    for epoch in range(1, 41):
        ctx = await at_epoch(session, epoch, **namespaces)
        await structural_demography(ctx)
        row = await session.get(PolityStressRow, realm.id)
        assert row is not None
        phases.append(row.phase)
        misery = row.immiseration / 100
        population = stat_or(town, "population", 0)
        set_stats(town, population=max(50, round(population * (1.18 - misery * 0.6))))
        wages(society, row.pressure)
        if row.phase is not CyclePhase.CRISIS:
            society.share_noble = min(30.0, society.share_noble + 1.5)
            society.share_farmer = max(10.0, 100.0 - sum(getattr(society, f"share_{item.value}") for item in SocialClass if item is not SocialClass.FARMER))
        await session.flush()
    readings = list(await session.scalars(select(StressReadingRow).where(StressReadingRow.polity_entity_id == realm.id).order_by(StressReadingRow.epoch)))
    assert len(readings) == 40
    assert CyclePhase.CRISIS in phases
    first_crisis = phases.index(CyclePhase.CRISIS)
    assert phases[0] in {CyclePhase.GROWTH, CyclePhase.STAGFLATION}
    assert any(phase is not CyclePhase.CRISIS for phase in phases[first_crisis:])
    peak = max(reading.psi for reading in readings)
    assert min(reading.psi for reading in readings[first_crisis:]) < peak


async def test_aspirants_are_counted_from_shares_and_gather_as_counter_elites(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ruler = await mortal(session, "Ruler", world, town.id)
    realm = await realm_of(session, world, town, ruler)
    aspirant = await mortal(session, "Aspirant", world, town.id)
    aspirant.social_class = SocialClass.NOBLE
    aspirant.importance = 90
    ctx = await context(session, structural_demography={"counter_elite_at": 0, "counter_elite_pct": 100})
    tally = StressTally()
    found = await read_stress(ctx, tally)
    row = found[0][2]
    expected = POPULATION * (6.0 + 5.0 * 0.5 + 2.0 * 0.5) / 100
    assert row.aspirants == round(expected)
    await structural_demography(ctx)
    leadership = await session.scalar(select(FactionMembershipRow).where(FactionMembershipRow.mortal_entity_id == aspirant.id))
    assert leadership is not None and leadership.rank is FactionRank.LEADER
    assert realm.id == found[0][0].id
    assert psi(100, 100, 100) == 100 and psi(0, 100, 100) == 0


async def test_solidarity_rises_on_a_frontier_and_softens_with_ease(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby", region=0)
    others = await entity(session, "Strangers", EntityType.PEOPLE, PeopleStats(population=3000), world_id=world.world.id, location_id=world.regions[1].id)
    other_town = await settlement(session, "Farside", world, world.regions[1])
    await BondRepository(session).connect(BondDraft(others.id, other_town.id, BondKind.LIVES_IN, 0))
    for axis, mine, theirs in ((ValueAxis.MARTIAL, 90, -90), (ValueAxis.MERCY, -90, 90), (ValueAxis.PIETY, 80, -80)):
        session.add(CultureValueRow(entity_id=world.people.id, axis=axis, value=mine))
        session.add(CultureValueRow(entity_id=others.id, axis=axis, value=theirs))
    await session.flush()
    ctx = await context(session, asabiyya={"frontier_floor": 10, "frontier_ratio_pct": 100, "frontier_gain": 5})
    await keep_asabiyya(ctx, AsabiyyaTally())
    row = await session.get(AsabiyyaRow, world.people.id)
    assert row is not None and row.frontier >= 1 and row.value > 50
    high = row.value
    row.frontier = 0
    row.luxury_generations = 5
    ctx = await context(session, asabiyya={"frontier_floor": 200, "luxury_decay": 10})
    society = await society_of(session, town)
    for social_class in SocialClass:
        setattr(society, f"satisfaction_{social_class.value}", 95)
    await keep_asabiyya(ctx, AsabiyyaTally())
    assert row.value < high
    assert town.id


async def test_a_challenge_in_the_band_is_answered_and_one_beyond_it_breaks_the_realm(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town)
    ctx = await context(session, challenge_response={"severity_scale": 1000, "band_low": 5, "band_high": 60})
    ctx.environment.stats.flows[("epidemics", HEADCOUNT_KEY, town.id, FlowCategory.PLAGUE.value)] = -10
    await meet_challenges(ctx, ChallengeTally())
    challenge = await session.scalar(select(ChallengeRow).where(ChallengeRow.holder_entity_id == realm.id))
    assert challenge is not None and challenge.kind is ChallengeKind.PLAGUE and challenge.response is ChallengeResponse.RESPONSE
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    stability = profile.stability
    ctx = await context(session, challenge_response={"severity_scale": 2000, "band_low": 5, "band_high": 30})
    ctx.environment.stats.flows[("war_casualties", HEADCOUNT_KEY, town.id, FlowCategory.CASUALTY.value)] = -1500
    await meet_challenges(ctx, ChallengeTally())
    kinds = {row.kind: row.response for row in await session.scalars(select(ChallengeRow).where(ChallengeRow.holder_entity_id == realm.id))}
    assert kinds[ChallengeKind.INVASION] is ChallengeResponse.COLLAPSE
    assert profile.stability < stability


async def test_a_long_plan_passes_to_the_next_ruler_and_raises_its_wonder(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    founder = await mortal(session, "Founder", world, town.id)
    realm = await realm_of(session, world, town, founder, treasury=10_000)
    ctx = await context(session, long_plans={"expose_pct": 0})
    plan = await new_plan(ctx, realm.id, LongPlanKind.WONDER, "The Great Spire", target_id=town.id, carrier_id=founder.id, steps=2, step_cost=10, secrecy=100)
    founder.status = EntityStatus.DEAD
    founder.end_epoch = 1
    heir = await mortal(session, "Heir", world, town.id)
    office = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id))
    assert office is not None
    office.holder_entity_id = heir.id
    await session.flush()
    tally = PlanTally()
    await advance_plans(ctx, tally)
    assert plan.carrier_node_id == heir.id and tally.carried == 1 and plan.progress == 1
    await advance_plans(ctx, tally)
    assert plan.status is LongPlanStatus.COMPLETED
    work = await session.scalar(select(ConstructionRow).where(ConstructionRow.site_entity_id == town.id, ConstructionRow.kind == StructureKind.WONDER))
    assert work is not None and work.funds > 0
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None and profile.treasury == 10_000 - 20


async def test_the_gift_ledger_balances_returns_and_costs_face_when_unanswered(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    other = await town_of(session, world, "Farside", region=1)
    first = await realm_of(session, world, town, treasury=1000)
    second = await realm_of(session, world, other, treasury=1000)
    ctx = await context(session, reciprocity={"return_epochs": 1, "refuse_below": -100, "outgive_pct": 0})
    gift = await give(ctx, first.id, second.id, 100, GiftOccasion.COURTESY)
    assert gift is not None and gift.state is GiftState.OPEN
    assert balance([gift], first.id) == 100 and balance([gift], second.id) == -100
    answer = await return_gift(ctx, gift)
    assert answer is not None and gift.state is GiftState.RETURNED and answer.value == 100
    returned = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "gifts.returned"))
    assert returned is not None
    assert await session.scalar(select(IncidentStepRow.action).where(IncidentStepRow.incident_id == returned.id)) is StepAction.RETURN_GIFT
    giver = await session.get(PolityProfileRow, first.id)
    receiver = await session.get(PolityProfileRow, second.id)
    assert giver is not None and receiver is not None
    assert giver.treasury == 1000 and receiver.treasury == 1000
    unanswered = await give(ctx, first.id, second.id, 200, GiftOccasion.COURTESY)
    assert unanswered is not None
    receiver.treasury = 0
    standing = receiver.legitimacy
    ctx = await at_epoch(session, ctx.epoch + 5, reciprocity={"return_epochs": 1, "refuse_below": -100, "lapse_prestige": 50})
    await settle_due(ctx, GiftTally())
    assert unanswered.state is GiftState.LAPSED
    assert receiver.legitimacy < standing


async def test_competitive_gifts_escalate_until_one_side_is_ruined(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    other = await town_of(session, world, "Farside", region=1)
    first = await realm_of(session, world, town, treasury=5000)
    second = await realm_of(session, world, other, treasury=600)
    namespaces = {"reciprocity": {"return_epochs": 1, "refuse_below": -100, "outgive_pct": 50}}
    ctx = await context(session, **namespaces)
    claim = await give(ctx, first.id, second.id, 200, GiftOccasion.FEAST)
    assert claim is not None
    for _ in range(1, 8):
        ctx = await at_epoch(session, ctx.epoch + 2, **namespaces)
        await settle_due(ctx, GiftTally())
    states = [row.state for row in await session.scalars(select(GiftRow).order_by(GiftRow.id))]
    assert GiftState.LAPSED in states and len(states) >= 2


async def test_unanswered_offerings_breed_neglect(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    await BondRepository(session).connect(BondDraft(town.id, world.son.id, BondKind.WORSHIPS, 0))
    await session.flush()
    ctx = await context(session, sacrifice_exchange={"offering_per_piety": 200, "debt_at": 10, "debt_neglect": 100})
    await keep_offerings(ctx, GiftTally())
    await keep_offerings(ctx, GiftTally())
    debt = await session.get(DivineDebtRow, (world.son.id, town.id))
    standing = await session.get(DivineStandingRow, (town.id, world.son.id))
    assert debt is not None and debt.offered > debt.answered
    assert standing is not None and standing.neglect > 0
    lines = await son_cycle_lines(await load_scope(session, ctx.rules), world.son)
    assert any(f"community {town.id}" in line for line in lines)


async def test_second_line_kin_inherit_through_the_second_line_and_couples_move(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    far = await town_of(session, world, "Farside", region=1)
    session.add(
        PeopleCultureRow(
            people_entity_id=world.people.id,
            cohesion=50,
            literacy=10,
            urbanisation=10,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            locked=[],
        )
    )
    ctx = await context(session)
    await set_kinship(
        ctx,
        world.people.id,
        {"descent": KinshipDescent.THROUGH_SECOND_LINE.value, "residence": ResidenceRule.WITH_SECOND_FAMILY.value, "sibling_union_first": True},
    )
    grand = await mortal(session, "Grand", world, town.id, sex=Sex.FEMALE.value)
    uncle = await mortal(session, "Uncle", world, town.id, sex=Sex.MALE.value)
    sister = await mortal(session, "Sister", world, town.id, sex=Sex.FEMALE.value)
    nephew = await mortal(session, "Nephew", world, town.id, sex=Sex.MALE.value)
    son = await mortal(session, "Own", world, town.id, sex=Sex.MALE.value)
    for parent, child in ((grand, uncle), (grand, sister), (sister, nephew), (uncle, son)):
        await add_parent(session, parent.id, child.id, 0)
    for mortal_row in (grand, uncle, sister, nephew, son):
        await BondRepository(session).connect(BondDraft(mortal_row.id, world.people.id, BondKind.MEMBER_OF, 0))
    await session.flush()
    assert await inheritance_of(session, uncle) is InheritanceCustom.THROUGH_SECOND_LINE
    heirs = await descent_heirs(session, uncle, [son])
    assert [heir.id for heir in heirs] == [nephew.id]
    bride = await mortal(session, "Bride", world, far.id, sex=Sex.FEMALE.value)
    groom = await mortal(session, "Groom", world, town.id, sex=Sex.MALE.value)
    await BondRepository(session).connect(BondDraft(groom.id, world.people.id, BondKind.MEMBER_OF, 0))
    ctx = await at_epoch(session, 3)
    await marry(session, groom, bride, ctx.epoch)
    await keep_kinship(ctx, KinshipTally())
    assert groom.location_id == far.id


async def test_a_first_side_sibling_union_weds_the_widow_to_a_sibling_of_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ctx = await context(session)
    await set_kinship(ctx, world.people.id, {"sibling_union_first": True})
    elder = await mortal(session, "Elder", world, town.id, sex=Sex.FEMALE.value)
    dead = await mortal(session, "Fallen", world, town.id, sex=Sex.MALE.value)
    sibling = await mortal(session, "Sibling", world, town.id, sex=Sex.MALE.value)
    widow = await mortal(session, "Widow", world, town.id, sex=Sex.FEMALE.value)
    for child in (dead, sibling):
        await add_parent(session, elder.id, child.id, 0)
    for row in (elder, dead, sibling, widow):
        await BondRepository(session).connect(BondDraft(row.id, world.people.id, BondKind.MEMBER_OF, 0))
    ctx = await at_epoch(session, 4)
    marriage = await marry(session, dead, widow, 1)
    dead.status = EntityStatus.DEAD
    dead.end_epoch = 1
    marriage.end_epoch = ctx.epoch
    marriage.cause_end = MarriageEnd.DEATH
    await session.flush()
    tally = KinshipTally()
    await keep_kinship(ctx, tally)
    assert tally.sibling_union_first == 1
    wed = await session.scalar(select(MarriageRow).where(MarriageRow.first_id == widow.id, MarriageRow.second_id == sibling.id))
    assert wed is not None


async def test_marriages_between_lines_build_an_alliance_and_rank(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ctx = await context(session)
    await set_kinship(ctx, world.people.id, {"residence": ResidenceRule.WITH_FIRST_FAMILY.value})
    await set_union(ctx, world.people.id, {"exchange": UnionExchange.FROM_ONE_FAMILY.value, "exchange_value": 10})
    houses = []
    for name, sex in (("Ward", Sex.FEMALE), ("Vane", Sex.MALE)):
        member = await mortal(session, f"{name} heir", world, town.id, sex=sex.value)
        await BondRepository(session).connect(BondDraft(member.id, world.people.id, BondKind.MEMBER_OF, 0))
        house = await entity(session, name, EntityType.HOUSE, HouseStats(), world_id=world.world.id)
        session.add(HouseProfileRow(house_entity_id=house.id, prestige=20, emblem={}, traits=[], seats=[], locked=[]))
        session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id, joined_epoch=0, by_marriage=False))
        houses.append((house, member))
    await session.flush()
    ctx = await at_epoch(session, 5)
    await marry(session, houses[0][1], houses[1][1], ctx.epoch, purpose=UnionPurpose.ALLIANCE)
    await keep_kinship(ctx, KinshipTally())
    alliance = await session.get(MarriageAllianceRow, (houses[0][0].id, houses[1][0].id))
    assert alliance is not None and alliance.marriages == 1
    giver = await session.get(HouseProfileRow, houses[0][0].id)
    assert giver is not None and giver.prestige > 20


async def test_reproductive_systems_steer_births_castes_and_sexes(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    ctx = await context(session)
    session.add(
        PeopleReproductionRow(people_entity_id=world.people.id, system=ReproductiveSystem.CASTE, breeder_pct=50, soldier_pct=50, worker_pct=0, locked=[])
    )
    first = await mortal(session, "Worker", world, town.id)
    second = await mortal(session, "Queen", world, town.id)
    for row in (first, second):
        await BondRepository(session).connect(BondDraft(row.id, world.people.id, BondKind.MEMBER_OF, 0))
    await session.flush()
    await keep_reproduction(ctx, ReproductionTally())
    castes = {row.mortal_entity_id: row.caste for row in await session.scalars(select(MortalCasteRow))}
    assert set(castes) == {first.id, second.id}
    for row in await session.scalars(select(MortalCasteRow)):
        row.caste = ReproductiveCaste.WORKER if row.mortal_entity_id == first.id else ReproductiveCaste.BREEDER
    await session.flush()
    assert not await breeds(session, first, first)
    assert await breeds(session, first, second)
    assert not await may_wed(session, ctx.rules, first, second)
    rng = ctx.rng("born")
    assert born_sex(ctx.rules, ReproductiveSystem.CASTE, rng) is Sex.OTHER
    row = await session.get(PeopleReproductionRow, world.people.id)
    assert row is not None and caste_for(row, rng) in {ReproductiveCaste.BREEDER, ReproductiveCaste.SOLDIER}
    row.system = ReproductiveSystem.SEQUENTIAL
    row.change_age = 30
    changer = await mortal(session, "Changer", world, town.id, sex=Sex.FEMALE.value, age=30)
    await BondRepository(session).connect(BondDraft(changer.id, world.people.id, BondKind.MEMBER_OF, 0))
    await session.flush()
    await keep_reproduction(ctx, ReproductionTally())
    assert isinstance(changer.stats, MortalStats) and changer.stats.sex == Sex.MALE.value


async def test_peoples_read_their_ways_of_kin_and_birth_from_their_customs(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    tally = SeedTally()
    await seed_peoples(ctx, tally)
    assert tally.kinship == 1 and tally.reproduction == 1
    kin = await session.get(KinshipSystemRow, world.people.id)
    assert kin is not None and kin.descent is KinshipDescent.BILATERAL
    await seed_peoples(ctx, SeedTally())
    assert await kin_bars(session, await mortal(session, "A", world, world.regions[0].id), await mortal(session, "B", world, world.regions[0].id)) is False


async def test_a_herding_village_takes_to_the_move_and_its_riders_take_tribute(session: AsyncSession, world: CoreWorld) -> None:
    camp_town = await town_of(session, world, "Tents", region=0, population=3000, tier=SizeTier.VILLAGE)
    farm = await town_of(session, world, "Fields", region=1, population=500)
    session.add(LabourRow(community_entity_id=camp_town.id, job=Job.HERDING, workers=900, output_pct=100, epoch=0, held=False))
    session.add(LabourRow(community_entity_id=camp_town.id, job=Job.FARMING, workers=100, output_pct=100, epoch=0, held=False))
    farm_profile = await session.get(SettlementProfileRow, farm.id)
    assert farm_profile is not None
    farm_profile.militia = 5
    await session.flush()
    ctx = await context(session, nomadism={"raid_pct": 0, "tribute_ratio": 2})
    tally = NomadTally()
    await keep_nomads(ctx, tally)
    camp = await session.get(CampRow, camp_town.id)
    assert camp is not None and camp.mode is MobilityMode.NOMADIC and camp.circuit
    assert tally.tributes >= 1
    assert await session.scalar(select(TributeRow).where(TributeRow.payer_entity_id == farm.id, TributeRow.receiver_entity_id == camp_town.id)) is not None
    leader = await mortal(session, "Khagan", world, camp_town.id, charisma=95)
    leader.importance = 99
    second = await town_of(session, world, "Yurts", region=1, population=800, tier=SizeTier.VILLAGE)
    session.add(CampRow(settlement_entity_id=second.id, mode=MobilityMode.NOMADIC, circuit=[world.regions[1].id], locked=[]))
    session.add(CampRow(settlement_entity_id=farm.id, mode=MobilityMode.NOMADIC, circuit=[world.regions[1].id], locked=[]))
    await session.flush()
    ctx = await context(session, nomadism={"raid_pct": 0, "confederation_min": 2, "leader_charisma": 50})
    await keep_nomads(ctx, NomadTally())
    league = await session.scalar(select(ConfederationRow))
    assert league is not None and league.leader_entity_id == leader.id
    leader.status = EntityStatus.DEAD
    leader.end_epoch = 1
    await session.flush()
    tally = NomadTally()
    await keep_nomads(ctx, tally)
    assert tally.fragmented == 1 and league.dissolved_epoch is not None


async def test_a_successor_people_keeps_its_legacies_and_names_its_forebear(session: AsyncSession, world: CoreWorld) -> None:
    successor = await entity(session, "Heirs", EntityType.PEOPLE, PeopleStats(population=2000), world_id=world.world.id, location_id=world.regions[1].id)
    for people, style in ((world.people, MartialStyle.HORSE_ARCHER), (successor, MartialStyle.PHALANX)):
        session.add(
            PeopleCultureRow(
                people_entity_id=people.id,
                cohesion=50,
                literacy=10,
                urbanisation=10,
                martial_style=style,
                inheritance=InheritanceCustom.PRIMOGENITURE,
                locked=[],
            )
        )
    await BondRepository(session).connect(BondDraft(successor.id, world.people.id, BondKind.DESCENDS_FROM, 1))
    account = AccountRow(holder_entity_id=successor.id, kind=AccountKind.FOUNDING_MYTH, fidelity=50, credence=60, defaced=False, epoch=1, locked=[])
    session.add(account)
    await session.flush()
    session.add(FoundingMythRow(holder_entity_id=successor.id, account_id=account.id, credence=60, since_epoch=1, locked=[]))
    await session.flush()
    ctx = await context(session, legacy_traits={"keep_pct": 100})
    tally = LegacyTally()
    await keep_legacies(ctx, tally)
    culture = await session.get(PeopleCultureRow, successor.id)
    assert culture is not None and culture.martial_style is MartialStyle.HORSE_ARCHER
    kept = {row.kind for row in await session.scalars(select(LegacyTraitRow).where(LegacyTraitRow.people_entity_id == successor.id))}
    assert LegacyKind.MARTIAL_STYLE in kept and tally.myths == 1
    again = LegacyTally()
    await keep_legacies(ctx, again)
    assert again.kept == 0


async def test_forced_labour_raises_a_great_work_and_the_town_remembers(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town)
    work = await entity(session, "Long Wall", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    construction = ConstructionRow(
        structure_entity_id=work.id, site_entity_id=town.id, kind=StructureKind.WALL, status=ConstructionStatus.ACTIVE, cost=100, started_epoch=1, locked=[]
    )
    session.add(construction)
    session.add(StructureProfileRow(structure_entity_id=work.id, kind=StructureKind.WALL, host_entity_id=town.id, locked=[]))
    session.add(
        CorveeRow(community_entity_id=town.id, share_pct=20, polity_entity_id=realm.id, work_entity_id=work.id, laboured_epochs=0, since_epoch=1, by_hand=False)
    )
    session.add(LabourReasonRow(community_entity_id=town.id, job=Job.BUILDING, reason=LabourReason.CORVEE, workers=150, price_pct=100, epoch=1))
    await session.flush()
    ctx = await context(session, corvee={"work_output": 100})
    tally = BondageTally()
    await work_corvees(ctx, tally)
    assert construction.status is ConstructionStatus.FINISHED and tally.corvee_work >= 100
    await work_corvees(ctx, tally)
    await session.flush()
    memory = await session.scalar(select(AccountRow).where(AccountRow.holder_entity_id == town.id, AccountRow.structure_entity_id == work.id))
    assert memory is not None and tally.suffering == 1
    assert await session.get(CorveeRow, town.id) is None


async def test_bondage_markets_and_the_ways_to_freedom(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    buyer = await town_of(session, world, "Buyer", region=1, tier=SizeTier.VILLAGE)
    await realm_of(session, world, buyer, treasury=100_000)
    session.add(
        PeopleCultureRow(
            people_entity_id=world.people.id,
            cohesion=50,
            literacy=10,
            urbanisation=10,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            slavery_lawful=True,
            locked=[],
        )
    )
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex=Sex.FEMALE,
            social_class=SocialClass.SERF_OR_SLAVE,
            condition=CohortCondition.ENSLAVED,
            count=200,
        )
    )
    bond = IndentureRow(community_entity_id=town.id, regime=LabourRegime.PEONAGE, count=10, term_epochs=0, debt=100, exploitation=100, since_epoch=0, locked=[])
    session.add(bond)
    await session.flush()
    ctx = await context(session, indenture={"inflate_share": 100, "inflate_pct": 50, "repay_per_head": 1})
    await serve_terms(ctx, BondageTally())
    assert bond.debt > 100
    ctx = await context(session, slave_markets={"sale_pct": 50})
    tally = BondageTally()
    await keep_markets(ctx, tally)
    market = await session.get(SlaveMarketRow, town.id)
    assert market is not None and market.open and market.price > 0 and market.stock == 100
    assert await session.get(SlaveMarketRow, buyer.id) is None
    assert tally.sold > 0
    moved = await session.scalar(select(CohortRow).where(CohortRow.community_entity_id == buyer.id, CohortRow.social_class == SocialClass.SERF_OR_SLAVE))
    assert moved is not None and moved.count == tally.sold
    freeing = await free_bound(ctx, town.id, 50, ManumissionPath.PURCHASE)
    assert freeing is not None and freeing.count > 0
    artisans = await session.scalar(select(CohortRow).where(CohortRow.community_entity_id == town.id, CohortRow.social_class == SocialClass.ARTISAN))
    assert artisans is not None and artisans.count == freeing.count
    assert await session.scalar(select(ManumissionRow).where(ManumissionRow.path == ManumissionPath.PURCHASE)) is not None


async def test_a_mortal_knows_its_gifts_kin_and_bonds(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    me = await mortal(session, "Iska", world, town.id)
    await BondRepository(session).connect(BondDraft(me.id, world.people.id, BondKind.MEMBER_OF, 0))
    ctx = await context(session)
    await set_union(ctx, world.people.id, {"exchange": UnionExchange.TO_ONE_FAMILY.value})
    session.add(
        GiftRow(
            giver_node_id=world.son.id, receiver_node_id=me.id, value=30, occasion=GiftOccasion.FEAST, state=GiftState.OPEN, due_epoch=4, epoch=1, locked=[]
        )
    )
    session.add(
        IndentureRow(
            community_entity_id=town.id,
            regime=LabourRegime.INDENTURE,
            count=12,
            term_epochs=2,
            debt=40,
            exploitation=20,
            origin_entity_id=world.people.id,
            since_epoch=0,
            locked=[],
        )
    )
    session.add(ManumissionRow(community_entity_id=town.id, count=9, path=ManumissionPath.WILL, standing=40, epoch=1, locked=[]))
    await session.flush()
    lines = await mortal_cycle_lines(await load_scope(session, ctx.rules), me)
    text = " ".join(lines)
    assert "you owe" in text and "exchange to one family worth 10" in text and "bound in indenture, newcomers of" in text
    assert "9 freed by will here stand at 40 of 100 among the freeborn" in text


async def test_integrity_lets_gone_stops_and_holders_go(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    other = await town_of(session, world, "Farside", region=1)
    third = await town_of(session, world, "Thirdwell", region=2)
    circuit = CircuitRow(name="The First Round", stops=[town.id, other.id, third.id], position=2, passes=0, started_epoch=0, locked=[])
    plan = LongPlanRow(holder_node_id=other.id, kind=LongPlanKind.CONVERSION, name="The Turning", steps=5, progress=0, step_cost=0, secrecy=50, locked=[])
    session.add_all([circuit, plan])
    other.status = EntityStatus.DEAD
    other.end_epoch = 1
    await session.flush()
    mended = await mend_cycle_links(session, 6)
    assert mended >= 2 and circuit.stops == [town.id, third.id] and plan.status is LongPlanStatus.ABANDONED


async def test_peoples_of_different_values_read_different_ways_of_kin(session: AsyncSession, world: CoreWorld) -> None:
    peoples = [world.people]
    for index in range(7):
        peoples.append(
            await entity(session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=1000), world_id=world.world.id, location_id=world.regions[0].id)
        )
    spreads = (-20, -10, -2, 0, 3, 9, 18, 30)
    for people, kin in zip(peoples, spreads, strict=True):
        for axis, value in ((ValueAxis.KINSHIP, kin), (ValueAxis.FAMILY, -kin), (ValueAxis.HIERARCHY, kin // 2), (ValueAxis.WEALTH, kin % 7 * 3)):
            session.add(CultureValueRow(entity_id=people.id, axis=axis, value=value))
    await session.flush()
    await seed_peoples(await context(session), SeedTally())
    systems = {(row.descent, row.descent_group, row.kin_terms) for row in await session.scalars(select(KinshipSystemRow))}
    assert len(systems) >= 4


async def great_work(session: AsyncSession, world: CoreWorld, town: EntityRow) -> ConstructionRow:
    work = await entity(session, "Sky Stair", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    construction = ConstructionRow(
        structure_entity_id=work.id, site_entity_id=town.id, kind=StructureKind.WONDER, status=ConstructionStatus.ACTIVE, cost=500, started_epoch=1, locked=[]
    )
    session.add(construction)
    session.add(StructureProfileRow(structure_entity_id=work.id, kind=StructureKind.WONDER, host_entity_id=town.id, locked=[]))
    await session.flush()
    return construction


async def test_a_realm_whose_people_hold_forced_labour_unthinkable_will_not_summon_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    await realm_of(session, world, town)
    await great_work(session, world, town)
    ethic = CultureEthicRow(holder_entity_id=world.people.id, act=ActKind.FORCED_LABOUR, stance=EthicalStance.UNTHINKABLE, since_epoch=0, locked=[])
    session.add(ethic)
    await session.flush()
    ctx = await context(session, corvee={"lay_pct": 100})
    tally = BondageTally()
    await lay_corvees(ctx, tally)
    assert tally.refused == 1 and await session.get(CorveeRow, town.id) is None
    ethic.stance = EthicalStance.ACCEPTABLE
    await session.flush()
    tally = BondageTally()
    await lay_corvees(ctx, tally)
    assert tally.corvee_laid == 1 and await session.get(CorveeRow, town.id) is not None


async def test_newcomers_sign_contracts_harder_the_further_their_ways(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    near = await entity(session, "Neighbours", EntityType.PEOPLE, PeopleStats(population=1000), world_id=world.world.id, location_id=world.regions[1].id)
    far = await entity(session, "Strangers", EntityType.PEOPLE, PeopleStats(population=1000), world_id=world.world.id, location_id=world.regions[2].id)
    for people, value in ((world.people, 60), (near, 60), (far, -60)):
        session.add(CultureValueRow(entity_id=people.id, axis=ValueAxis.MERCY, value=value))
    session.add(DiasporaRow(people_entity_id=near.id, host_entity_id=town.id, population=100, ties=60, since_epoch=0, locked=[]))
    session.add(DiasporaRow(people_entity_id=far.id, host_entity_id=town.id, population=100, ties=60, since_epoch=0, locked=[]))
    await session.flush()
    ctx = await context(session, indenture={"migrant_pct": 100, "migrant_share_pct": 20, "exploitation_spread": 0})
    tally = BondageTally()
    await bind_migrants(ctx, tally)
    bonds = {row.origin_entity_id: row for row in await session.scalars(select(IndentureRow).where(IndentureRow.community_entity_id == town.id))}
    assert set(bonds) == {near.id, far.id} and tally.contracted == 40
    assert bonds[far.id].exploitation > bonds[near.id].exploitation and bonds[far.id].regime is LabourRegime.INDENTURE
    again = BondageTally()
    await bind_migrants(ctx, again)
    assert again.contracted == 0


async def test_the_freed_start_low_are_kept_from_office_and_rise_to_equals(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    origin = await entity(session, "Taken", EntityType.PEOPLE, PeopleStats(population=1000), world_id=world.world.id, location_id=world.regions[1].id)
    session.add(CaptiveCohortRow(captor_entity_id=town.id, origin_entity_id=origin.id, count=0, since_epoch=0, locked=[]))
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex=Sex.FEMALE,
            social_class=SocialClass.SERF_OR_SLAVE,
            condition=CohortCondition.ENSLAVED,
            count=200,
        )
    )
    bound = await mortal(session, "Unchained", world, town.id)
    bound.social_class = SocialClass.SERF_OR_SLAVE
    freeborn = await mortal(session, "Freeborn", world, town.id)
    await session.flush()
    ctx = await context(session, manumission={"freed_standing": 40, "standing_rise": 30, "office_at": 70, "hierarchy_drag": 0})
    row = await free_bound(ctx, town.id, 100, ManumissionPath.PURCHASE)
    assert row is not None and row.standing == 40 and row.origin_entity_id == origin.id
    assert bound.social_class is SocialClass.ARTISAN
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.foreigners.get(str(origin.id), 0) > 0
    assert not await career_open(session, ctx.rules, bound, CareerPath.OFFICE)
    assert await career_open(session, ctx.rules, freeborn, CareerPath.OFFICE)
    assert await freed_stigma(session, town) > 0
    tally = BondageTally()
    await raise_freed(ctx, tally)
    await raise_freed(ctx, tally)
    assert row.standing == 100 and tally.equal == row.count
    assert await career_open(session, ctx.rules, bound, CareerPath.OFFICE) and await freed_stigma(session, town) == 0


async def test_a_guest_come_along_the_circuit_is_under_its_duty_of_hospitality(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    other = await town_of(session, world, "Farside", region=1)
    stranger = await town_of(session, world, "Elsewhere", region=2)
    session.add(CircuitRow(name="The Round", stops=[town.id, other.id], position=0, passes=0, started_epoch=0, locked=[]))
    guest = await mortal(session, "Guest", world, town.id)
    wanderer = await mortal(session, "Wanderer", world, town.id)
    killer = await mortal(session, "Host", world, town.id)
    await BondRepository(session).connect(BondDraft(guest.id, other.id, BondKind.LIVES_IN, 0))
    await BondRepository(session).connect(BondDraft(wanderer.id, stranger.id, BondKind.LIVES_IN, 0))
    await session.flush()
    assert await circuit_partners(session, town.id) == {other.id} and set(await circuit_stops(session)) == {town.id, other.id}
    ctx = await context(session)
    assert await guest_killed(ctx, killer.id, guest) == 2
    assert await guest_killed(ctx, killer.id, wanderer) == 0


async def test_a_son_hears_of_the_troubled_realms_of_its_world(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town)
    world.son.current_world_id = world.world.id
    session.add(
        PolityStressRow(
            polity_entity_id=realm.id,
            pressure=80,
            immiseration=70,
            elite_overproduction=90,
            fiscal_distress=60,
            psi=75,
            aspirants=300,
            positions=100,
            challenge=20,
            phase=CyclePhase.CRISIS,
            updated_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    ctx = await context(session)
    lines = await son_cycle_lines(await load_scope(session, ctx.rules), world.son)
    assert any(f"(polity {realm.id}) is in crisis" in line for line in lines)


async def test_sexless_peoples_open_every_role_and_castes_prefer_their_own(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    session.add(PeopleReproductionRow(people_entity_id=world.people.id, system=ReproductiveSystem.CASTE, locked=[]))
    session.add(RoleNormRow(holder_entity_id=world.people.id, role=RoleKind.COMBAT, eligibility=RoleEligibility.MALE_ONLY, min_age=0, classes=[], locked=[]))
    soldier = await mortal(session, "Soldier", world, town.id)
    worker = await mortal(session, "Worker", world, town.id)
    session.add(MortalCasteRow(mortal_entity_id=soldier.id, caste=ReproductiveCaste.SOLDIER, locked=[]))
    session.add(MortalCasteRow(mortal_entity_id=worker.id, caste=ReproductiveCaste.WORKER, locked=[]))
    await session.flush()
    assert await combat_sexes(session, town) == set(Sex)
    soldier_rank = await role_rank(session, soldier, RoleKind.COMBAT)
    worker_rank = await role_rank(session, worker, RoleKind.COMBAT)
    assert soldier_rank is not None and worker_rank is not None and soldier_rank < worker_rank


async def test_a_people_loses_solidarity_while_its_homeland_realm_is_in_crisis(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town)
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
    ctx = await context(session)
    assert await homeland_psi(ctx, {town.id}) == 90
    await keep_asabiyya(ctx, AsabiyyaTally())
    row = await session.get(AsabiyyaRow, world.people.id)
    assert row is not None and row.value < 50


async def test_a_bloodline_plan_on_a_people_raises_its_gift(session: AsyncSession, world: CoreWorld) -> None:
    locus = GIFT_LOCI_ORDER[0].value
    pool = AllelePoolRow(people_node_id=world.people.id, frequencies={locus: {"dormant": 70, "gifted": 20, "wild": 10}}, gifted_share=10, locked=[])
    plan = LongPlanRow(
        holder_node_id=world.son.id,
        target_node_id=world.people.id,
        kind=LongPlanKind.BLOODLINE,
        name="The Long Breeding",
        steps=1,
        progress=0,
        step_cost=0,
        secrecy=50,
        locked=[],
    )
    session.add_all([pool, plan])
    await session.flush()
    ctx = await context(session, long_plans={"bloodline_gift_pct": 50, "expose_pct": 0})
    await advance_plans(ctx, PlanTally())
    assert plan.status is LongPlanStatus.COMPLETED and pool.frequencies[locus]["gifted"] > 20


async def test_a_camp_on_bare_pasture_sets_out_anew_and_trades_with_its_neighbours(session: AsyncSession, world: CoreWorld) -> None:
    camp_town = await town_of(session, world, "Tents", region=0, population=3000, tier=SizeTier.VILLAGE)
    farm = await town_of(session, world, "Fields", region=1, population=500)
    await realm_of(session, world, farm, treasury=1000)
    session.add(LabourRow(community_entity_id=camp_town.id, job=Job.HERDING, workers=900, output_pct=100, epoch=0, held=False))
    camp = CampRow(settlement_entity_id=camp_town.id, mode=MobilityMode.NOMADIC, circuit=[world.regions[2].id], herd=500, grazing=0, water=50, locked=[])
    session.add(camp)
    farm_profile = await session.get(SettlementProfileRow, farm.id)
    assert farm_profile is not None
    farm_profile.militia = 100_000
    await session.flush()
    ctx = await context(session, nomadism={"reroute_at": 25, "raid_pct": 0, "trade_pct": 100, "trade_per_herd": 10})
    tally = NomadTally()
    await keep_nomads(ctx, tally)
    assert tally.rerouted == 1 and camp.circuit != [world.regions[2].id]
    assert tally.trades >= 1 and await coin_of(session, ctx.rules, camp_town) > 0


async def test_a_people_keeps_the_techniques_and_arts_of_those_it_came_from_and_took_in(session: AsyncSession, world: CoreWorld) -> None:
    successor = await entity(session, "Heirs", EntityType.PEOPLE, PeopleStats(population=2000), world_id=world.world.id, location_id=world.regions[1].id)
    absorbed = await entity(session, "Taken In", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id, location_id=world.regions[2].id)
    technique = next(iter(Technique))
    session.add(HolderTechniqueRow(holder_entity_id=world.people.id, technique=technique, since_epoch=0, secret=False))
    form = await entity(session, "Night Song", EntityType.ART_FORM, ArtFormStats(), world_id=world.world.id)
    session.add(ArtFormProfileRow(art_form_entity_id=form.id, discipline=ArtMode.MUSICAL, origin_culture_id=absorbed.id, locked=[]))
    await BondRepository(session).connect(BondDraft(successor.id, world.people.id, BondKind.DESCENDS_FROM, 1))
    await BondRepository(session).connect(BondDraft(absorbed.id, successor.id, BondKind.PART_OF, 1))
    await session.flush()
    ctx = await context(session, legacy_traits={"keep_pct": 100, "absorbed_keep_pct": 100})
    await keep_legacies(ctx, LegacyTally())
    kept = {
        (row.kind, row.predecessor_entity_id) for row in await session.scalars(select(LegacyTraitRow).where(LegacyTraitRow.people_entity_id == successor.id))
    }
    assert (LegacyKind.INNOVATION, world.people.id) in kept and (LegacyKind.ART_FORM, absorbed.id) in kept
    assert await session.get(HolderTechniqueRow, (successor.id, technique)) is not None
    assert await session.get(ArtFormPractitionerRow, (form.id, successor.id)) is not None


async def test_every_kind_of_legacy_refuses_a_key_that_names_nothing(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    for kind in LegacyKind:
        with pytest.raises(ValidationFailedError):
            await set_legacy(ctx, world.people.id, kind, "999999", None)
