from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_causes import DEATH_CAUSES, LOOSE_CAUSES, death_cause_of
from aerona.catalog.invariants import TYPED, GenericCheck, InvariantSpec, Remedy
from aerona.catalog.long_seasons import CAUSES
from aerona.catalog.market_kinds import ANIMAL_CLUBS, CLUBS
from aerona.catalog.plants import PARTS
from aerona.catalog.revivals import REVIVAL_WAYS
from aerona.db.record_context import RecordScope, scoped
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.session import Database
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.arts import ClubRow
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.childhood import ChildStandingRow, SocializationRow
from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow
from aerona.db.tables.commerce import LeaseRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.crafts import IncorporealRightRow, NumberSystemRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.culture import HolderTechniqueRow, TraditionProfileRow
from aerona.db.tables.customs import BodyMarkRow, IntoxicantCustomRow, RevivalRow, TimeBudgetRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleCultureRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.divine_conceptions import GodReadingRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.economy import CurrencyRow, WorldMaterialRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgGovernanceRow, OrgMergerRow, OrgSeatRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow
from aerona.db.tables.households import DwellingRow, HouseholdRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow
from aerona.db.tables.intimacy import IntimacyNormRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow, WillHeirRow, WillRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinDynamicRow, KinFavourRow, KinRivalryRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow, WorkerBodyRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow, WarRemnantRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationMeasureRow, OccupationRegimeRow
from aerona.db.tables.orders import EconomicOrderRow, OrderTransitionRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.plants import PlantPartRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.relations import ContestRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, SecurityPriceRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.db.tables.warfare import CaptiveRow, WarRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.ages import SeasonSpell, SeasonSpellShape
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyPart, BodyPlan, ConditionKind, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.constructs import OrderKind
from aerona.domain.enums.crafts import RightKind
from aerona.domain.enums.creator import CovenantDuty, CreatorPromise
from aerona.domain.enums.creature_groups import GroupForm
from aerona.domain.enums.culture import Technique, TraditionFunction
from aerona.domain.enums.customs import Intoxicant, MarkKind, MarkMeaning, RevivalGoal
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import AgeBand, CohortCondition, FuneralCustom, InheritanceCustom, Job, MartialStyle, SexKind
from aerona.domain.enums.departures import DepartureKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine_conceptions import GodReading
from aerona.domain.enums.ecology import YieldProduct
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, MaterialOrigin, MoneyForm
from aerona.domain.enums.endowments import EndowmentState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.faction import FactionKind, MovementCause
from aerona.domain.enums.fertility_means import FertilityMeans
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.governance import GoverningBody
from aerona.domain.enums.interworld import CampaignStage
from aerona.domain.enums.intimacy import RelationContext
from aerona.domain.enums.kinds import GoodCategory, KindConcept
from aerona.domain.enums.leagues import LeagueDecisionKind, LeagueOrgan
from aerona.domain.enums.mass_weapons import MassHarm, MassReach
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.occupation_regimes import CollaborationFate
from aerona.domain.enums.orders import TransitionKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.reckoning import ReckoningMeasure
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.enums.records import FactUnit, StepAction, WitnessMode
from aerona.domain.enums.referendums import Franchise, ReferendumResult, ReferendumSubject
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake
from aerona.domain.enums.restoration import RestorationStage
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.war import CaptiveStatus, WarCause
from aerona.domain.models.entity_stats import (
    ArmyStats,
    BeastStats,
    CultStats,
    DiseaseStats,
    EventStats,
    FactionStats,
    HouseStats,
    LeagueStats,
    PeopleStats,
    PolityStats,
    SpeciesStats,
    TraditionStats,
)
from aerona.engine.households.dwelling_kinds import built_in_dwelling
from aerona.engine.recording.checkpoints import take_checkpoint
from aerona.services.integrity.invariants import CHECKS, findings, resolve, sweep
from aerona.services.integrity.record_links import absent_witnesses
from tests.conftest import OpenDatabase
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, seed_core_world, settlement
from tests.engine.core.test_arcana_w15 import foreign_caster

Breaker = Callable[[AsyncSession, CoreWorld], Awaitable[None]]
PHASE_KIND = "phase.statecraft"


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "integrity.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> CoreWorld:
    return await seed_core_world(session)


async def captor_dies(session: AsyncSession, world: CoreWorld) -> None:
    captor = await mortal(session, "Holder", world, world.regions[0].id)
    held = await mortal(session, "Held", world, world.regions[0].id)
    session.add(CaptiveRow(captive_entity_id=held.id, captor_entity_id=captor.id, status=CaptiveStatus.HELD, taken_epoch=1))
    captor.status, captor.end_epoch = EntityStatus.DEAD, 1


async def species_dies_in_its_lands(session: AsyncSession, world: CoreWorld) -> None:
    kind = await entity(session, "Last Herd", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SpeciesRangeRow(species_entity_id=kind.id, region_entity_id=world.regions[0].id, abundance=40, locked=[]))
    kind.status, kind.end_epoch = EntityStatus.DEAD, 1


async def order_loses_target(session: AsyncSession, world: CoreWorld) -> None:
    owner = await mortal(session, "Keeper", world, world.regions[0].id)
    orders = InstructionSetRow(owner_entity_id=owner.id, locked=[])
    session.add(orders)
    await session.flush()
    session.add(InstructionOrderRow(set_id=orders.id, kind=OrderKind.GUARD, target_node_id=None, locked=[]))


async def construct_makes_itself(session: AsyncSession, world: CoreWorld) -> None:
    body = await mortal(session, "Vessel", world, world.regions[0].id)
    session.add(ConstructRow(entity_id=body.id, maker_entity_id=body.id, locked=[]))


async def ruler_dies(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Seat", world, world.regions[0])
    ruler = await mortal(session, "Ruler", world, town.id)
    await bond(session, ruler.id, town.id, BondKind.RULES)
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, 1


async def covenant_without_people(session: AsyncSession, world: CoreWorld) -> None:
    keeper = await mortal(session, "Lone", world, world.regions[0].id)
    session.add(CovenantRow(people_entity_id=keeper.id, duty=CovenantDuty.WORSHIP, promise=CreatorPromise.PLENTY, locked=[]))


async def seat_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(DivineSeatRow(god_node_id=world.people.id, locked=[]))


async def tie_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(PantheonTieRow(god_node_id=world.son.id, other_node_id=world.people.id, locked=[]))


async def joining_without_people(session: AsyncSession, world: CoreWorld) -> None:
    god = await foreign_caster(session, world)
    session.add(SyncretismRow(foreign_god_id=god.id, son_id=world.son.id, people_entity_id=world.species.id, locked=[]))


async def holding_without_kind(session: AsyncSession, world: CoreWorld) -> None:
    session.add(KindHoldingRow(concept=KindConcept.GOOD, kind_id=987654, holder_node_id=world.people.id, locked=[]))


async def kind_derived_from_itself(session: AsyncSession, world: CoreWorld) -> None:
    kind = GoodKindRow(name="Loop Bread", category=GoodCategory.GRAIN, world_id=world.world.id, locked=[])
    session.add(kind)
    await session.flush()
    kind.derived_from_id = kind.id


async def kind_out_of_range(session: AsyncSession, world: CoreWorld) -> None:
    session.add(GoodKindRow(name="Dear Salt", category=GoodCategory.MINERAL_SEASONING, world_id=world.world.id, base_value=5000, locked=[]))


async def paper_made_of_metal(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Mint", world, world.regions[0])
    session.add(
        CurrencyRow(issuer_entity_id=town.id, name="Notes", metal=MaterialKind.SILVER, purity=100, supply=0, trust=50, minted_epoch=0, form=MoneyForm.PAPER)
    )


async def genome_with_unknown_allele(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Odd Blood", world, world.regions[0].id)
    session.add(GenomeRow(holder_node_id=holder.id, genes={"muscle": ["vast", "high"]}, potential={}, likeness={}, marks=[], locked=[]))


async def star_stuff_from_a_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forge", world, world.regions[0])
    session.add(
        WorldMaterialRow(
            world_id=world.world.id,
            origin=MaterialOrigin.STAR,
            source_node_id=town.id,
            family=MaterialFamily.EXOTIC,
            hardness=50,
            toughness=50,
            weight=50,
            edge=50,
            conductivity=50,
            sanctity=0,
            corruption=0,
            rarity=50,
            base_value=10,
            decay=0,
            created_epoch=0,
        )
    )


async def happening(session: AsyncSession, *, kind: str = "uncatalogued.happening", year: int | None = None, place: int | None = None) -> IncidentRow:
    row = IncidentRow(kind=kind, epoch=1, year=year, place_entity_id=place, magnitude=0, locked=[])
    session.add(row)
    await session.flush()
    return row


async def happening_of_a_retired_kind(session: AsyncSession, world: CoreWorld) -> None:
    await happening(session, kind="retired.happening")


async def fact_of_no_kind(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session)
    session.add(IncidentFactRow(incident_id=incident.id, key="amount", number=3.0, unit=FactUnit.COUNT))


async def step_inside_itself(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND)
    step = IncidentStepRow(incident_id=incident.id, position=0, action=StepAction.BEGIN)
    session.add(step)
    await session.flush()
    step.parent_step_id = step.id


async def step_of_no_kind(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session)
    session.add(IncidentStepRow(incident_id=incident.id, position=0, action=StepAction.STRIKE))


async def effect_before_cause(session: AsyncSession, world: CoreWorld) -> None:
    cause = await happening(session, kind=PHASE_KIND, year=40)
    effect = await happening(session, kind=PHASE_KIND, year=12)
    effect.cause_incident_id = cause.id


async def world_made_late(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind="genesis.world", year=7)
    made.epoch = 1


async def people_before_its_world(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind=PHASE_KIND, year=31)
    session.add(IncidentParticipantRow(incident_id=made.id, node_id=world.regions[0].id, role=IncidentRole.PRODUCT, position=0))
    woke = await happening(session, kind=PHASE_KIND, year=0)
    session.add(IncidentParticipantRow(incident_id=woke.id, node_id=world.regions[0].id, role=IncidentRole.SUBJECT, position=0))


async def undated_birth(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind=PHASE_KIND, year=9)
    session.add(IncidentParticipantRow(incident_id=made.id, node_id=world.people.id, role=IncidentRole.PRODUCT, position=0))


async def steps_running_back(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, year=30)
    session.add(IncidentStepRow(incident_id=incident.id, position=0, year=30, action=StepAction.BEGIN))
    session.add(IncidentStepRow(incident_id=incident.id, position=1, year=20, action=StepAction.END))


async def witness_far_away(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    onlooker = await mortal(session, "Far Onlooker", world, world.regions[1].id)
    session.add(
        IncidentParticipantRow(incident_id=incident.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.SAW, fidelity=90)
    )


async def time_budget_over_the_year(session: AsyncSession, world: CoreWorld) -> None:
    session.add(TimeBudgetRow(people_entity_id=world.people.id, social_class=SocialClass.FARMER, life_stage=LifeStage.ADULT, work=90, rest=40, locked=[]))


async def wedding_before_naming(session: AsyncSession, world: CoreWorld) -> None:
    session.add(ChildStandingRow(people_entity_id=world.people.id, naming_age=20, marriage_age=10, locked=[]))


async def upbringing_past_the_whole(session: AsyncSession, world: CoreWorld) -> None:
    session.add(SocializationRow(people_entity_id=world.people.id, play=90, example=90, locked=[]))


async def sexed_norm_for_a_sexless_people(session: AsyncSession, world: CoreWorld) -> None:
    session.add(PeopleReproductionRow(people_entity_id=world.people.id, system=ReproductiveSystem.ASEXUAL, locked=[]))
    session.add(IntimacyNormRow(people_entity_id=world.people.id, context=RelationContext.BETWEEN_ANY_SEXES, locked=[]))


async def elder_in_a_youth_group(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Youthford", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(YouthStandingRow(people_entity_id=world.people.id, youth_from=12, youth_to=20, locked=[]))
    elder = await mortal(session, "Old Brann", world, town.id, age=60)
    group = YouthGroupRow(settlement_entity_id=town.id, name="the youth of the ford", locked=[])
    session.add(group)
    await session.flush()
    session.add(YouthGroupMemberRow(group_id=group.id, member_node_id=elder.id, locked=[]))


async def policy_held_by_a_single_being(session: AsyncSession, world: CoreWorld) -> None:
    being = await mortal(session, "Lone Planner", world, world.regions[0].id)
    session.add(PopulationPolicyRow(holder_node_id=being.id, locked=[]))


async def instrument_of_another_holder(session: AsyncSession, world: CoreWorld) -> None:
    policy = PopulationPolicyRow(holder_node_id=world.people.id, locked=[])
    session.add(policy)
    await session.flush()
    session.add(PopulationInstrumentRow(policy_id=policy.id, instrument=PopulationInstrument.BIRTH_REWARD, holder_node_id=world.regions[0].id, locked=[]))


async def lease_of_a_thing_not_owned(session: AsyncSession, world: CoreWorld) -> None:
    owner = await mortal(session, "False Landlord", world, world.regions[0].id)
    tenant = await mortal(session, "Tenant", world, world.regions[0].id)
    session.add(LeaseRow(owner_node_id=owner.id, lessee_node_id=tenant.id, thing_node_id=world.regions[1].id, locked=[]))


async def works_on_foreign_ground(session: AsyncSession, world: CoreWorld) -> None:
    home = await settlement(session, "Homeford", world, world.regions[0])
    away = await settlement(session, "Farford", world, world.regions[1])
    await bond(session, home.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(PublicWorksRow(polity_entity_id=home.id, place_node_id=away.id, locked=[]))


async def item_beyond_its_outlet(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Criers Ford", world, world.regions[0])
    owner = await mortal(session, "Crier", world, town.id)
    outlet = MediaOutletRow(owner_node_id=owner.id, seat_entity_id=town.id, name="The Ford Crier", reach=10, locked=[])
    session.add(outlet)
    await session.flush()
    session.add(MediaItemRow(outlet_id=outlet.id, owner_node_id=owner.id, reach=90, locked=[]))


async def governed_guild(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, f"{name} Town", world, world.regions[0])
    head = await mortal(session, f"{name} Head", world, town.id)
    guild = await entity(session, name, EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, influence_over={}, cohort_share={}, locked=[]))
    session.add(FactionMembershipRow(faction_entity_id=guild.id, mortal_entity_id=head.id, locked=[]))
    session.add(OrgGovernanceRow(org_node_id=guild.id, decision_body=GoverningBody.ASSEMBLY_OF_MEMBERS, head_node_id=head.id, locked=[]))
    await session.flush()
    return guild, head


async def seat_held_by_a_stranger(session: AsyncSession, world: CoreWorld) -> None:
    guild, head = await governed_guild(session, world, "The Stranger Hall")
    stranger = await mortal(session, "Stranger", world, world.regions[0].id)
    session.add(OrgSeatRow(org_node_id=guild.id, member_node_id=head.id, vote_weight=60, locked=[]))
    session.add(OrgSeatRow(org_node_id=guild.id, member_node_id=stranger.id, vote_weight=40, locked=[]))


async def votes_that_miss_a_hundred(session: AsyncSession, world: CoreWorld) -> None:
    guild, head = await governed_guild(session, world, "The Short Hall")
    session.add(OrgSeatRow(org_node_id=guild.id, member_node_id=head.id, vote_weight=70, locked=[]))


async def bid_for_a_vanished_house(session: AsyncSession, world: CoreWorld) -> None:
    buyer, _head = await governed_guild(session, world, "The Buyer Hall")
    gone, _other = await governed_guild(session, world, "The Gone Hall")
    gone.status, gone.end_epoch = EntityStatus.DEAD, world.cosmos.epoch
    session.add(OrgMergerRow(acquirer_node_id=buyer.id, target_node_id=gone.id, price=10, locked=[]))


async def creditor_who_never_lent(session: AsyncSession, world: CoreWorld) -> None:
    debtor, head = await governed_guild(session, world, "The Debt Hall")
    session.add(InsolvencyCaseRow(debtor_node_id=debtor.id, creditors=[head.id], owed=50, locked=[]))


async def reading_of_no_god(session: AsyncSession, world: CoreWorld) -> None:
    cult = await entity(session, "Odd Faith", EntityType.CULT, CultStats(followers=10), world_id=world.world.id)
    session.add(GodReadingRow(cult_entity_id=cult.id, god_node_id=world.people.id, reading=GodReading.TRUE, locked=[]))


async def pack_led_by_another_kind(session: AsyncSession, world: CoreWorld) -> None:
    other = await entity(session, "Other Kind", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id)
    beast = await entity(session, "Strange Leader", EntityType.BEAST, BeastStats(danger=30), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(BeastProfileRow(beast_entity_id=beast.id, species_entity_id=other.id, locked=[]))
    region = world.regions[0].id
    session.add(
        CreatureGroupRow(species_entity_id=world.species.id, region_entity_id=region, form=GroupForm.PACK, size=100, leader_node_id=beast.id, locked=[])
    )


async def wave_on_a_dry_coast(session: AsyncSession, world: CoreWorld) -> None:
    wave = SeaWaveRow(world_id=world.world.id, origin=WaveOrigin.QUAKE, sea_region_id=world.regions[2].id, strength=50, locked=[])
    session.add(wave)
    await session.flush()
    session.add(SeaWaveCoastRow(wave_id=wave.id, region_entity_id=world.regions[0].id, height=40, locked=[]))


async def honour_past_its_limit(session: AsyncSession, world: CoreWorld) -> None:
    kind = HonourKindRow(conferrer_node_id=world.people.id, name="Order of One", rank=1, holder_limit=1, locked=[])
    session.add(kind)
    await session.flush()
    town = await settlement(session, "Honourby", world, world.regions[0])
    for name in ("First Holder", "Second Holder"):
        holder = await mortal(session, name, world, town.id)
        session.add(HonourHeldRow(holder_node_id=holder.id, kind_id=kind.id, epoch=0, locked=[]))


async def honour_with_an_odd_privilege(session: AsyncSession, world: CoreWorld) -> None:
    session.add(HonourKindRow(conferrer_node_id=world.people.id, name="Order of Odds", rank=1, privileges=["title", "not a privilege"], locked=[]))


async def means_of_a_people_without_conception(session: AsyncSession, world: CoreWorld) -> None:
    session.add(BodySystemRow(holder_entity_id=world.people.id, system=BodySystem.REPRODUCTION, present=False, locked=[]))
    session.add(FertilityMeansRow(people_entity_id=world.people.id, means=FertilityMeans.PREVENTION, locked=[]))


async def use_of_an_unknown_means(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Unknowing", world, world.regions[0])
    being = await mortal(session, "Odd User", world, town.id)
    session.add(FertilityUseRow(user_entity_id=being.id, people_entity_id=world.people.id, means=FertilityMeans.SURROGACY, locked=[]))


async def condition_of_an_absent_system(session: AsyncSession, world: CoreWorld) -> None:
    kind = AgentlessConditionRow(world_id=world.world.id, name="A wearing of the breath", cause=ConditionCause.AGE, system=BodySystem.BREATH, locked=[])
    session.add(kind)
    session.add(BodySystemRow(holder_entity_id=world.people.id, system=BodySystem.BREATH, present=False, locked=[]))
    town = await settlement(session, "Breathless", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    being = await mortal(session, "No Breath", world, town.id)
    await session.flush()
    session.add(ConditionRow(bearer_node_id=being.id, kind=ConditionKind.CHRONIC_ILLNESS, severity=1, source=HarmCause.AGE, since_epoch=0, kind_id=kind.id))


async def grave_with_a_stray_thing(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Barrow Town", world, world.regions[0])
    dead = await mortal(session, "Old Bones", world, town.id)
    session.add(GraveGoodsRow(dead_entity_id=dead.id, grave_entity_id=town.id, items=[town.id], locked=[]))


async def exchange_with_itself(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lone Tongue", world, world.regions[0])
    session.add(InterpretationRow(first_party_id=town.id, second_party_id=town.id, fidelity=50, epoch=0, locked=[]))


async def mood_with_a_stray_feeling(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Moody Town", world, world.regions[0])
    session.add(FeelingSpreadRow(settlement_entity_id=town.id, feelings={"joy": 150, "not a feeling": 20}, locked=[]))


async def dynamic_of_nothing(session: AsyncSession, world: CoreWorld) -> None:
    del world
    session.add(KinDynamicRow(locked=[]))


async def kin_dynamic(session: AsyncSession, world: CoreWorld) -> KinDynamicRow:
    house = await entity(session, "Breaker House", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    row = KinDynamicRow(house_entity_id=house.id, locked=[])
    session.add(row)
    await session.flush()
    return row


async def favour_for_oneself(session: AsyncSession, world: CoreWorld) -> None:
    dynamic = await kin_dynamic(session, world)
    vain = await mortal(session, "Vain One", world, None)
    session.add(KinFavourRow(dynamic_id=dynamic.id, parent_node_id=vain.id, child_node_id=vain.id, locked=[]))


async def rivalry_backwards(session: AsyncSession, world: CoreWorld) -> None:
    dynamic = await kin_dynamic(session, world)
    first, second = await mortal(session, "Elder Rival", world, None), await mortal(session, "Younger Rival", world, None)
    session.add(KinRivalryRow(dynamic_id=dynamic.id, first_node_id=max(first.id, second.id), second_node_id=min(first.id, second.id), locked=[]))


async def sway_of_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    dynamic = await kin_dynamic(session, world)
    gone = await mortal(session, "Gone Elder", world, None)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 0
    session.add(ElderSwayRow(dynamic_id=dynamic.id, elder_node_id=gone.id, locked=[]))


async def protected_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Guarded Town", world, world.regions[0])
    session.add(ProtectedAreaRow(region_entity_id=town.id, banned_uses=[], locked=[]))


async def protected_region_as_kind(session: AsyncSession, world: CoreWorld) -> None:
    session.add(SpeciesProtectionRow(species_entity_id=world.regions[0].id, measures=[], locked=[]))


async def aims_of_another_movement(session: AsyncSession, world: CoreWorld) -> None:
    movement = await entity(session, "Peace Movement", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(MovementProfileRow(faction_entity_id=movement.id, cause=MovementCause.PEACE, locked=[]))
    session.add(ConservationMovementRow(movement_entity_id=movement.id, aims=[], cohort_support={}, locked=[]))


async def rule_on_anothers_district(session: AsyncSession, world: CoreWorld) -> None:
    first = await settlement(session, "Rulehome", world, world.regions[0])
    other = await settlement(session, "Otherhome", world, world.regions[0])
    district = DistrictRow(settlement_entity_id=other.id, kind=DistrictKind.MARKET, level=1, built_epoch=0, locked=[])
    session.add(district)
    await session.flush()
    session.add(LandUseRuleRow(settlement_entity_id=first.id, district_id=district.id, values={}, locked=[]))


async def city_with_itself_as_quarter(session: AsyncSession, world: CoreWorld) -> None:
    core = await settlement(session, "Selfcity", world, world.regions[0])
    session.add(ConurbationRow(core_entity_id=core.id, members=[core.id], imposed_laws=[], locked=[]))


async def campaign_on_a_stray_way(session: AsyncSession, world: CoreWorld) -> None:
    attacker = await entity(session, "Lost Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    other, _regions = await add_empty_world(session, "Strayworld")
    third, _more = await add_empty_world(session, "Thirdworld")
    route = RouteRow(world_a_id=world.world.id, world_b_id=third.id, method=TravelMethod.DIVINE_BRIDGE, duration_epochs=1, danger=0, created_epoch=0)
    session.add(route)
    await session.flush()
    session.add(InterworldCampaignRow(attacker_entity_id=attacker.id, from_world_id=world.world.id, target_world_id=other.id, route_id=route.id, locked=[]))


async def landed_host_elsewhere(session: AsyncSession, world: CoreWorld) -> None:
    attacker = await entity(session, "Strayed Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    other, _regions = await add_empty_world(session, "Farland")
    host = await entity(session, "Strayed Host", EntityType.ARMY, ArmyStats(size=100), world_id=world.world.id)
    holding = CampaignStage.HOLDING
    session.add(
        InterworldCampaignRow(
            attacker_entity_id=attacker.id, from_world_id=world.world.id, target_world_id=other.id, army_entity_id=host.id, stage=holding, locked=[]
        )
    )


async def movement_to_its_own_world(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Restless Town", world, world.regions[0])
    session.add(InterworldMigrationRow(community_entity_id=town.id, from_world_id=world.world.id, to_world_id=world.world.id, journey_ids=[], locked=[]))


async def weapon_beyond_its_means(session: AsyncSession, world: CoreWorld) -> None:
    holder = await entity(session, "Unlearned Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(HolderTechniqueRow(holder_entity_id=holder.id, technique=Technique.BRONZE))
    session.add(MassWeaponRow(holder_entity_id=holder.id, harm=MassHarm.RADIATION, reach=MassReach.WORLD, count=3, seen_by=[], locked=[]))


async def remnant_of_a_war_still_fought(session: AsyncSession, world: CoreWorld) -> None:
    event = await entity(session, "Unending War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOSTILITY, started_epoch=0)
    session.add(war)
    await session.flush()
    session.add(WarRemnantRow(region_entity_id=world.regions[0].id, war_id=war.id, locked=[]))


async def remnant_in_land_and_orbit(session: AsyncSession, world: CoreWorld) -> None:
    session.add(WarRemnantRow(region_entity_id=world.regions[0].id, orbit_world_id=world.world.id, locked=[]))


async def posture_toward_itself(session: AsyncSession, world: CoreWorld) -> None:
    holder = await entity(session, "Inward Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(DeterrencePostureRow(holder_entity_id=holder.id, toward_entity_id=holder.id, locked=[]))


async def occupier_of(session: AsyncSession, world: CoreWorld, name: str) -> EntityRow:
    return await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)


async def regime_without_an_occupation(session: AsyncSession, world: CoreWorld) -> None:
    occupier = await occupier_of(session, world, "Gone Occupier")
    session.add(OccupationRegimeRow(region_entity_id=world.regions[0].id, occupier_entity_id=occupier.id, administrators=[], imposed_laws=[], locked=[]))


async def held_regime(session: AsyncSession, world: CoreWorld, name: str) -> OccupationRegimeRow:
    occupier = await occupier_of(session, world, name)
    session.add(OccupationRow(region_entity_id=world.regions[0].id, occupier_entity_id=occupier.id, since_epoch=0, locked=[]))
    regime = OccupationRegimeRow(region_entity_id=world.regions[0].id, occupier_entity_id=occupier.id, administrators=[], imposed_laws=[], locked=[])
    session.add(regime)
    await session.flush()
    return regime


async def collaborator_from_afar(session: AsyncSession, world: CoreWorld) -> None:
    regime = await held_regime(session, world, "Far Occupier")
    stranger = await mortal(session, "Far Servant", world, None)
    session.add(CollaborationRow(regime_id=regime.id, collaborator_node_id=stranger.id, locked=[]))


async def killed_collaborator_without_an_end(session: AsyncSession, world: CoreWorld) -> None:
    regime = await held_regime(session, world, "Grim Occupier")
    town = await settlement(session, "Grim Town", world, world.regions[0])
    servant = await mortal(session, "Grim Servant", world, town.id)
    session.add(CollaborationRow(regime_id=regime.id, collaborator_node_id=servant.id, fate=CollaborationFate.KILLED, locked=[]))


async def measure_of_an_ended_regime(session: AsyncSession, world: CoreWorld) -> None:
    occupier = await occupier_of(session, world, "Ended Occupier")
    regime = OccupationRegimeRow(
        region_entity_id=world.regions[0].id, occupier_entity_id=occupier.id, ended_epoch=1, administrators=[], imposed_laws=[], locked=[]
    )
    session.add(regime)
    await session.flush()
    session.add(OccupationMeasureRow(regime_id=regime.id, region_entity_id=world.regions[0].id, locked=[]))


async def measure_in_another_land(session: AsyncSession, world: CoreWorld) -> None:
    regime = await held_regime(session, world, "Wandering Occupier")
    session.add(OccupationMeasureRow(regime_id=regime.id, region_entity_id=world.regions[1].id, locked=[]))


async def restoration_of_a_standing_realm(session: AsyncSession, world: CoreWorld) -> None:
    standing = await entity(session, "Standing Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(RestorationRow(fallen_polity_id=standing.id, territories=[], bases=[], locked=[]))


async def fallen_crown(session: AsyncSession, world: CoreWorld, name: str) -> EntityRow:
    fallen = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 0
    return fallen


async def restored_without_a_link(session: AsyncSession, world: CoreWorld) -> None:
    fallen = await fallen_crown(session, world, "Unlinked Fallen Crown")
    heir = await entity(session, "Unlinked Heir Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    restored = RestorationStage.RESTORED
    session.add(RestorationRow(fallen_polity_id=fallen.id, restored_polity_id=heir.id, stage=restored, ended_epoch=1, territories=[], bases=[], locked=[]))


async def open_restoration_with_an_end(session: AsyncSession, world: CoreWorld) -> None:
    fallen = await fallen_crown(session, world, "Ended Fallen Crown")
    session.add(RestorationRow(fallen_polity_id=fallen.id, ended_epoch=2, territories=[], bases=[], locked=[]))


async def cult_of_a_settlement(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Worshipped Town", world, world.regions[0])
    session.add(LeaderCultRow(leader_node_id=town.id, promoters=[], instruments=[], locked=[]))


async def cult_with_a_lost_promoter(session: AsyncSession, world: CoreWorld) -> None:
    leader = await mortal(session, "Cult Leader", world, None)
    session.add(LeaderCultRow(leader_node_id=leader.id, promoters=[987654321], instruments=[], locked=[]))


async def living_cult_with_an_end(session: AsyncSession, world: CoreWorld) -> None:
    leader = await mortal(session, "Ended Leader", world, None)
    session.add(LeaderCultRow(leader_node_id=leader.id, promoters=[], instruments=[], ended_epoch=3, locked=[]))


async def reckoning_in(session: AsyncSession, world: CoreWorld, name: str) -> ReckoningRow:
    realm = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    row = ReckoningRow(polity_entity_id=realm.id, fallen_epoch=1, opened_epoch=2, locked=[])
    session.add(row)
    await session.flush()
    return row


async def case_naming_an_unrecorded_deed(session: AsyncSession, world: CoreWorld) -> None:
    row = await reckoning_in(session, world, "The Unrecorded Realm")
    accused = await mortal(session, "Nameless Servant", world, None)
    session.add(ReckoningCaseRow(reckoning_id=row.id, accused_node_id=accused.id, incident_ids=[987654321], locked=[]))


async def reckoning_before_its_fall(session: AsyncSession, world: CoreWorld) -> None:
    row = await reckoning_in(session, world, "The Early Realm")
    row.fallen_epoch = 9


async def measure_of_another_realm(session: AsyncSession, world: CoreWorld) -> None:
    row = await reckoning_in(session, world, "The Measured Realm")
    other = await entity(session, "The Other Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(ReckoningMeasureRow(reckoning_id=row.id, polity_entity_id=other.id, measure=ReckoningMeasure.MEMORIAL, locked=[]))


async def vote_of(session: AsyncSession, world: CoreWorld, name: str) -> ReferendumRow:
    realm = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    row = ReferendumRow(holder_node_id=realm.id, subject=ReferendumSubject.WAR, target_node_id=realm.id, called_epoch=2, locked=[])
    session.add(row)
    await session.flush()
    return row


async def vote_open_to_the_wrong_people(session: AsyncSession, world: CoreWorld) -> None:
    row = await vote_of(session, world, "The Misfranchised Realm")
    row.franchise = Franchise.ALL


async def vote_on_nothing(session: AsyncSession, world: CoreWorld) -> None:
    row = await vote_of(session, world, "The Aimless Realm")
    row.target_node_id = None


async def vote_held_before_it_was_called(session: AsyncSession, world: CoreWorld) -> None:
    row = await vote_of(session, world, "The Hasty Realm")
    row.result, row.held_epoch = ReferendumResult.PASSED, 0


async def leaving_of(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, DepartureRow]:
    town = await settlement(session, f"{name} Town", world, world.regions[0])
    holder = await mortal(session, name, world, town.id)
    row = DepartureRow(holder_node_id=holder.id, kind=DepartureKind.ABDICATION, epoch=2, conditions=[], locked=[])
    session.add(row)
    await session.flush()
    return holder, row


async def office_handed_to_oneself(session: AsyncSession, world: CoreWorld) -> None:
    holder, row = await leaving_of(session, world, "Self Hander")
    row.in_favour_of_node_id = holder.id


async def leaving_of_a_stray_office(session: AsyncSession, world: CoreWorld) -> None:
    _holder, row = await leaving_of(session, world, "Stray Leaver")
    realm = await entity(session, "The Office Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    office = OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.MARSHAL, since_epoch=0, powers=[])
    session.add(office)
    await session.flush()
    row.office_id, row.office_kind = office.id, OfficeKind.RULER


async def return_before_leaving(session: AsyncSession, world: CoreWorld) -> None:
    _holder, row = await leaving_of(session, world, "Early Returner")
    row.returned_epoch = 0


async def realm_with_two_orders(session: AsyncSession, world: CoreWorld) -> None:
    realm = await entity(session, "The Doubled Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add_all([EconomicOrderRow(polity_entity_id=realm.id, locked=[]), EconomicOrderRow(polity_entity_id=realm.id, locked=[])])


async def change_of_unknown_axes(session: AsyncSession, world: CoreWorld) -> None:
    realm = await entity(session, "The Muddled Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(OrderTransitionRow(polity_entity_id=realm.id, kind=TransitionKind.LAND_REFORM, from_axes={"weather": "fair"}, to_axes={}, locked=[]))


async def change_of_a_fallen_realm(session: AsyncSession, world: CoreWorld) -> None:
    realm = await entity(session, "The Fallen Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(OrderTransitionRow(polity_entity_id=realm.id, kind=TransitionKind.EMANCIPATION, from_axes={}, to_axes={}, locked=[]))
    realm.status, realm.end_epoch = EntityStatus.DEAD, world.cosmos.epoch


async def league_of(session: AsyncSession, world: CoreWorld, name: str, aims: list[str], organs: list[str]) -> EntityRow:
    league = await entity(session, name, EntityType.LEAGUE, LeagueStats(), world_id=world.world.id)
    session.add(PolityLeagueRow(league_entity_id=league.id, aims=aims, organs=organs, locked=[]))
    await session.flush()
    return league


async def guild_in_a_league(session: AsyncSession, world: CoreWorld) -> None:
    league = await league_of(session, world, "The Odd League", ["trade"], ["assembly"])
    guild, _head = await governed_guild(session, world, "The Leagued Guild")
    session.add(LeagueMemberRow(league_entity_id=league.id, polity_entity_id=guild.id, locked=[]))


async def currency_union_with_no_money(session: AsyncSession, world: CoreWorld) -> None:
    await league_of(session, world, "The Moneyless League", ["currency_union"], ["assembly"])


async def ruling_with_no_court(session: AsyncSession, world: CoreWorld) -> None:
    league = await league_of(session, world, "The Courtless League", ["trade"], ["assembly"])
    session.add(LeagueDecisionRow(league_entity_id=league.id, organ=LeagueOrgan.COURT, kind=LeagueDecisionKind.RULING, locked=[]))


async def security_of(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, IssuedSecurityRow]:
    guild, _head = await governed_guild(session, world, name)
    security = IssuedSecurityRow(name=f"the shares of {name}", issuer_node_id=guild.id, amount=10, locked=[])
    session.add(security)
    await session.flush()
    return guild, security


async def holdings_beyond_the_amount(session: AsyncSession, world: CoreWorld) -> None:
    guild, security = await security_of(session, world, "The Overheld")
    session.add(SecurityHoldingRow(holder_node_id=guild.id, security_id=security.id, amount=25, locked=[]))


async def listed_claim_of_a_gone_issuer(session: AsyncSession, world: CoreWorld) -> None:
    guild, _security = await security_of(session, world, "The Gone Issuer")
    guild.status, guild.end_epoch = EntityStatus.DEAD, world.cosmos.epoch


async def price_naming_a_stranger(session: AsyncSession, world: CoreWorld) -> None:
    _guild, security = await security_of(session, world, "The Priced")
    stranger, _head = await governed_guild(session, world, "The Stranger House")
    session.add(SecurityPriceRow(security_id=security.id, issuer_node_id=stranger.id, epoch=0, price=5, locked=[]))


async def currency_with_authority(session: AsyncSession, world: CoreWorld, name: str) -> tuple[CurrencyRow, MonetaryAuthorityRow]:
    town = await settlement(session, f"{name} Town", world, world.regions[0])
    currency = CurrencyRow(issuer_entity_id=town.id, name=name, purity=100, supply=100, trust=60, minted_epoch=0)
    session.add(currency)
    await session.flush()
    authority = MonetaryAuthorityRow(currency_id=currency.id, holder_node_id=town.id, issuer_node_id=town.id, locked=[])
    session.add(authority)
    await session.flush()
    return currency, authority


async def peg_on_its_own_coin(session: AsyncSession, world: CoreWorld) -> None:
    currency, authority = await currency_with_authority(session, world, "Selfmark")
    authority.peg_currency_id = currency.id


async def authority_naming_a_stranger_issuer(session: AsyncSession, world: CoreWorld) -> None:
    _currency, authority = await currency_with_authority(session, world, "Straymark")
    stranger = await settlement(session, "Strayholm", world, world.regions[0])
    authority.issuer_node_id = stranger.id


async def contract_of_a_body_that_is_gone(session: AsyncSession, world: CoreWorld) -> None:
    guild, _head = await governed_guild(session, world, "The Bodiless Hirer")
    session.add(LabourContractRow(hirer_node_id=guild.id, body_node_id=guild.id, trade=Job.CRAFTING, locked=[]))


async def dispute_with_too_many_out(session: AsyncSession, world: CoreWorld) -> None:
    guild, _head = await governed_guild(session, world, "The Crowded Hirer")
    town = await settlement(session, "Crowdford", world, world.regions[0])
    session.add(LabourRow(community_entity_id=town.id, job=Job.CRAFTING, workers=10, output_pct=100, epoch=0, held=False))
    session.add(LabourDisputeRow(hirer_node_id=guild.id, settlement_entity_id=town.id, trade=Job.CRAFTING, workers_out=500, locked=[]))


async def body_of_unknown_trades(session: AsyncSession, world: CoreWorld) -> None:
    guild, _head = await governed_guild(session, world, "The Unknown Trades")
    session.add(WorkerBodyRow(faction_node_id=guild.id, trades=["crafting", "nothing_known"], locked=[]))


async def shares_that_miss_a_hundred(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Shortmarket", world, world.regions[0])
    guild, _head = await governed_guild(session, world, "The Short Seller")
    session.add(MarketStructureRow(market_entity_id=town.id, commodity=CommodityKind.GRAIN, sellers={str(guild.id): 70}, small_sellers_pct=0, locked=[]))


async def compact_with_an_outsider(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Compactford", world, world.regions[0])
    guild, head = await governed_guild(session, world, "The Compact Seller")
    session.add(MarketStructureRow(market_entity_id=town.id, commodity=CommodityKind.GRAIN, sellers={str(guild.id): 100}, locked=[]))
    session.add(CartelRow(name="the outsiders' compact", members=[guild.id, head.id], markets=[town.id], commodity=CommodityKind.GRAIN, locked=[]))


async def price_war_in_a_lost_market(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lostmarket", world, world.regions[0])
    guild, _head = await governed_guild(session, world, "The Lost Seller")
    session.add(PriceWarRow(aggressor_node_id=guild.id, market_entity_id=town.id, commodity=CommodityKind.GRAIN, locked=[]))
    town.status, town.end_epoch = EntityStatus.DEAD, world.cosmos.epoch


async def sermon_in_a_town_without_a_temple(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Templeless", world, world.regions[0])
    speaker = await mortal(session, "Preacher", world, town.id)
    session.add(SpeechRow(speaker_node_id=speaker.id, place_entity_id=town.id, venue=SpeechVenue.TEMPLE, locked=[]))


async def class_of_animals_pointing_at_a_region(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        FolkClassRow(
            people_entity_id=world.people.id,
            domain=FolkDomain.ANIMALS,
            name="Beasts of the hills",
            grouped_node_id=world.regions[0].id,
            locked=[],
        )
    )


async def stage_set_down_by_another_realm(session: AsyncSession, world: CoreWorld) -> None:
    builder = await entity(session, "Builders", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    stranger = await entity(session, "Strangers", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    works = PublicWorksRow(polity_entity_id=builder.id, place_node_id=world.regions[0].id, locked=[])
    session.add(works)
    await session.flush()
    session.add(PublicWorkStageRow(works_id=works.id, polity_entity_id=stranger.id, stage=1, locked=[]))


async def endowment_held_captive_by_a_mortal(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Almsford", world, world.regions[0])
    keeper = await mortal(session, "Keeper", world, town.id)
    session.add(EndowmentRow(founder_node_id=keeper.id, beneficiary_node_id=town.id, trustee_node_id=keeper.id, state=EndowmentState.CAPTURED, locked=[]))


async def practice_of_a_mortal(session: AsyncSession, world: CoreWorld) -> None:
    lone = await mortal(session, "Lone", world, world.regions[0].id)
    session.add(FacetPracticeRow(community_entity_id=lone.id, facet=FacetKind.MASONRY, level=40, locked=[]))
    await session.flush()


async def remains_the_rite_forbids(session: AsyncSession, world: CoreWorld) -> None:
    culture = await session.get(PeopleCultureRow, world.people.id)
    if culture is None:
        culture = PeopleCultureRow(
            people_entity_id=world.people.id,
            cohesion=50,
            literacy=10,
            urbanisation=10,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            locked=[],
        )
        session.add(culture)
    culture.funeral_rite = FuneralCustom.CREMATION
    culture.remains_treatment = RemainsTreatment.EXPOSURE


async def reading_beyond_the_base(session: AsyncSession, world: CoreWorld) -> None:
    session.add(NumberSystemRow(people_entity_id=world.people.id, base=5, numerology={"7": "lucky", "2": "sacred"}, locked=[]))


async def kin_group_headed_by_a_stranger(session: AsyncSession, world: CoreWorld) -> None:
    stranger = await mortal(session, "Stray Head", world, world.regions[0].id)
    session.add(KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", head_node_id=stranger.id, locked=[]))


async def stranger_in_a_descent_group(session: AsyncSession, world: CoreWorld) -> None:
    other = await entity(session, "Far Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    town = await settlement(session, "Farhold", world, world.regions[1])
    await bond(session, town.id, other.id, BondKind.DESCENDS_FROM)
    stranger = await mortal(session, "Far Kin", world, town.id)
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", locked=[])
    session.add(group)
    await session.flush()
    session.add(KinGroupMemberRow(group_id=group.id, member_node_id=stranger.id, locked=[]))


async def witness_who_does_not_say_how(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    onlooker = await mortal(session, "Silent Onlooker", world, world.regions[0].id)
    session.add(IncidentParticipantRow(incident_id=incident.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0))


async def engine_change_of_no_happening(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        StateChangeRow(
            epoch=1,
            table_name="entities",
            row_key=f'{{"id": {world.people.id}}}',
            node_id=world.people.id,
            operation=LedgerOperation.UPDATE,
            field="power_level",
            before_number=1.0,
            after_number=2.0,
            actor_kind=ActorKind.ENGINE,
            phase="statecraft",
        )
    )


async def checkpoint_that_lies(session: AsyncSession, world: CoreWorld) -> None:
    await take_checkpoint(session, 1)
    found = await session.scalar(select(StateCheckpointRow).where(StateCheckpointRow.table_name == "entities"))
    assert found is not None
    found.digest = "not the digest of anything"


async def chronicle_kept_by_a_people(session: AsyncSession, world: CoreWorld) -> None:
    session.add(RecordKeeperRow(kind=RecordKeeperKind.CHRONICLER, scope_node_id=world.creator.id, keeper_entity_id=world.people.id, since_epoch=1, locked=[]))


async def year_that_misses_a_hundred(session: AsyncSession, world: CoreWorld) -> None:
    seasons = list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world.world.id).order_by(WorldSeasonRow.position)))
    if seasons:
        seasons[0].share_pct += 7
        return
    for position in range(2):
        session.add(
            WorldSeasonRow(
                world_id=world.world.id,
                position=position,
                name=f"Turn {position}",
                temperature_shift=0,
                rain_shift=0,
                growth=50,
                travel=50,
                campaign=50,
                share_pct=30,
            )
        )


async def spell_of_a_shape_its_cause_forbids(session: AsyncSession, world: CoreWorld) -> None:
    cause, shape = next((cause, shape) for cause, spec in CAUSES.items() for shape in SeasonSpellShape if shape not in spec.shapes)
    session.add(IrregularSeasonRow(world_id=world.world.id, cause=cause, shape=shape, spell=SeasonSpell.WINTER, locked=[]))


async def forecast_on_another_world(session: AsyncSession, world: CoreWorld) -> None:
    other, _ = await add_empty_world(session, "Farshore")
    spell = IrregularSeasonRow(world_id=world.world.id, spell=SeasonSpell.WINTER, locked=[])
    session.add(spell)
    await session.flush()
    session.add(WinterForecastRow(long_season_id=spell.id, world_id=other.id, people_entity_id=world.people.id, locked=[]))


async def sexless_cohort_in_a_two_kinded_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Twofold", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex_kind=SexKind.NONE,
            social_class=SocialClass.FARMER,
            condition=CohortCondition.NONE,
            count=50,
        )
    )


async def product_of_a_missing_part(session: AsyncSession, world: CoreWorld) -> None:
    part, missing = next((part, other) for part, spec in PARTS.items() for other in ProductPart if other not in spec.yields)
    session.add(PlantPartRow(species_entity_id=world.species.id, part=part, locked=[]))
    session.add(SpeciesProductRow(species_entity_id=world.species.id, product=YieldProduct.MEAT.value, part=missing, locked=[]))


async def will_that_leaves_too_little(session: AsyncSession, world: CoreWorld) -> None:
    testator = await mortal(session, "Old Testator", world, world.regions[0].id)
    heir = await mortal(session, "Young Heir", world, world.regions[0].id)
    will = WillRow(testator_node_id=testator.id, locked=[])
    session.add(will)
    await session.flush()
    session.add(WillHeirRow(will_id=will.id, heir_node_id=heir.id, share=40))


async def nest_of_a_grounded_household(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Low Eaves", world, world.regions[0])
    head = await mortal(session, "Walker", world, town.id)
    nest = await built_in_dwelling(session, "nest")
    household = HouseholdRow(name="the house of Walker", head_node_id=head.id, settlement_node_id=town.id, locked=[])
    session.add(household)
    await session.flush()
    session.add(DwellingRow(household_id=household.id, dwelling_kind_id=nest.id, settlement_node_id=town.id, locked=[]))


async def identity_pointing_at_nothing(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Tongue Holder", world, world.regions[0].id)
    await session.execute(text("PRAGMA defer_foreign_keys=ON"))
    session.add(HeldIdentityRow(holder_entity_id=holder.id, layer=IdentityLayer.LANGUAGE, value_node_id=987654321, locked=[]))


async def movement_seeking_beyond_its_way(session: AsyncSession, world: CoreWorld) -> None:
    way, goal = next((way, goal) for way, spec in REVIVAL_WAYS.items() for goal in RevivalGoal if goal not in spec.goals)
    session.add(RevivalRow(people_entity_id=world.people.id, way=way, goal=goal, locked=[]))


async def implant_mark_with_no_implant(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Marked One", world, world.regions[0].id)
    session.add(BodyMarkRow(holder_node_id=bearer.id, kind=MarkKind.IMPLANT, meaning=MarkMeaning.STATUS, augment_id=None, locked=[]))


async def festival_kept_at_no_time(session: AsyncSession, world: CoreWorld) -> None:
    rite = await entity(session, "Gathering of Plenty", EntityType.TRADITION, TraditionStats(), world_id=world.world.id)
    session.add(TraditionProfileRow(tradition_entity_id=rite.id, kind=TraditionFunction.FESTIVAL, calendar_slot=None, locked=[]))


async def beast_borne_outbreak_of_no_beast(session: AsyncSession, world: CoreWorld) -> None:
    sickness = await entity(session, "Marsh Ague", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(OutbreakRow(disease_entity_id=sickness.id, region_entity_id=world.regions[0].id, path=SpreadPath.WILDLIFE, severity=40, started_epoch=1))


async def wound_on_a_part_the_body_lacks(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Dry Walker", world, world.regions[0].id)
    session.add(BodyRow(node_id=bearer.id, plan=BodyPlan.HUMANOID, fingers=10))
    session.add(
        InjuryRow(
            bearer_node_id=bearer.id,
            part=BodyPart.GILLS,
            kind=InjuryKind.CUT,
            damage_type=DamageType.CUT,
            severity=2,
            state=InjuryState.FRESH,
            function_loss=10,
            cause_kind=HarmCause.ACCIDENT,
            epoch=1,
        )
    )


async def promise_to_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    promised = await mortal(session, "Promised", world, world.regions[0].id)
    gone = await mortal(session, "Gone Before", world, world.regions[0].id)
    await bond(session, promised.id, gone.id, BondKind.BETROTHED_TO)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1


async def contest_for_land_staking_a_person(session: AsyncSession, world: CoreWorld) -> None:
    first = await mortal(session, "Claimant", world, world.regions[0].id)
    second = await mortal(session, "Holder Of Field", world, world.regions[0].id)
    session.add(
        ContestRow(
            kind=ContestKind.RIDDLE_GAME,
            stake=ContestStake.LAND,
            challenger_node_id=first.id,
            defender_node_id=second.id,
            stake_node_id=second.id,
            outcome=ContestEnd.DRAWN,
            epoch=1,
        )
    )


async def made_intoxicant_of_an_unknowing_people(session: AsyncSession, world: CoreWorld) -> None:
    session.add(IntoxicantCustomRow(people_entity_id=world.people.id, intoxicant=Intoxicant.SYNTHETIC, locked=[]))


async def partnership_with_no_partner(session: AsyncSession, world: CoreWorld) -> None:
    row = await session.get(BiologyRow, world.people.id)
    if row is None:
        row = BiologyRow(holder_entity_id=world.people.id, variants=[], locked=[])
        session.add(row)
    row.variants, row.partner_species_id = [*row.variants, BiologyVariant.SYMBIOTIC.value], None


async def death_blamed_on_the_wrong_cause(session: AsyncSession, world: CoreWorld) -> None:
    damage, cause = next((damage, cause) for damage in DamageType if DEATH_CAUSES[cause := death_cause_of(None, damage)].damage is not None)
    dead = await mortal(session, "Fallen One", world, world.regions[0].id)
    wrong = next(loose for loose in sorted(LOOSE_CAUSES) if loose is not cause)
    session.add(MortalProfileRow(entity_id=dead.id, cause_of_death=wrong, locked=[]))
    session.add(
        InjuryRow(
            bearer_node_id=dead.id,
            part=BodyPart.TORSO,
            kind=InjuryKind.CUT,
            damage_type=damage,
            severity=5,
            state=InjuryState.LETHAL,
            function_loss=100,
            cause_kind=HarmCause.ACCIDENT,
            epoch=1,
        )
    )


async def charm_with_no_object(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Charmed", world, world.regions[0].id)
    session.add(
        AfflictionRow(
            bearer_node_id=bearer.id,
            package=PackageKind.CHARM,
            since_epoch=1,
            stage_since_epoch=1,
            transmission=Transmission.CONTACT,
            charm_target_node_id=None,
            charm_strength=50,
            locked=[],
        )
    )


async def change_of_form_into_nothing(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Changing One", world, world.regions[0].id)
    session.add(
        AfflictionRow(
            bearer_node_id=bearer.id,
            package=PackageKind.TRANSFORMATION,
            since_epoch=1,
            stage_since_epoch=1,
            transmission=Transmission.CONTACT,
            transform_plan=None,
            locked=[],
        )
    )


async def fortune_neither_good_nor_ill(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Unmarked", world, world.regions[0].id)
    session.add(
        AfflictionRow(
            bearer_node_id=bearer.id,
            package=PackageKind.FORTUNE,
            since_epoch=1,
            stage_since_epoch=1,
            transmission=Transmission.CONTACT,
            fortune_sign=None,
            fortune_strength=None,
            locked=[],
        )
    )


async def right_to_no_technique(session: AsyncSession, world: CoreWorld) -> None:
    session.add(IncorporealRightRow(holder_node_id=world.people.id, kind=RightKind.TECHNIQUE, name="An empty right", technique=None, locked=[]))


async def beast_club_with_no_beasts(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Racing Ground", world, world.regions[0])
    club = await entity(session, "The Swift Riders", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=club.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=town.id, locked=[]))
    session.add(ClubRow(faction_entity_id=club.id, kind=sorted(ANIMAL_CLUBS)[0], locked=[]))


async def fixing_with_no_winner(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fixed Field", world, world.regions[0])
    fixer = await mortal(session, "Fixer", world, town.id)
    club = await entity(session, "The Bought Side", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    plain = next(kind for kind, spec in CLUBS.items() if not spec.keeps_animals)
    session.add(ClubRow(faction_entity_id=club.id, kind=plain, fixed_by_entity_id=fixer.id, fixed_winner_entity_id=None, locked=[]))


BREAKERS: dict[str, Breaker] = {
    "season_shares": year_that_misses_a_hundred,
    "long_season_source": spell_of_a_shape_its_cause_forbids,
    "forecast_world": forecast_on_another_world,
    "cohort_sex_kinds": sexless_cohort_in_a_two_kinded_town,
    "plant_product_part": product_of_a_missing_part,
    "will_shares_whole": will_that_leaves_too_little,
    "dwelling_fits_body": nest_of_a_grounded_household,
    "identity_value_target": identity_pointing_at_nothing,
    "revival_way_goal": movement_seeking_beyond_its_way,
    "implant_mark_augment": implant_mark_with_no_implant,
    "tradition_slot_fit": festival_kept_at_no_time,
    "outbreak_path_carrier": beast_borne_outbreak_of_no_beast,
    "wound_part_in_plan": wound_on_a_part_the_body_lacks,
    "betrothal_living": promise_to_the_dead,
    "contest_stake_named": contest_for_land_staking_a_person,
    "intoxicant_source": made_intoxicant_of_an_unknowing_people,
    "symbiotic_partner": partnership_with_no_partner,
    "death_cause_last_wound": death_blamed_on_the_wrong_cause,
    "charm_names_living_target": charm_with_no_object,
    "transformation_target_valid": change_of_form_into_nothing,
    "fortune_has_sign": fortune_neither_good_nor_ill,
    "right_sources": right_to_no_technique,
    "club_sport_animals": beast_club_with_no_beasts,
    "fixing_names_match": fixing_with_no_winner,
    "fact_schema": fact_of_no_kind,
    "kind_known": happening_of_a_retired_kind,
    "keeper_mortal": chronicle_kept_by_a_people,
    "step_nesting": step_inside_itself,
    "step_action": step_of_no_kind,
    "moment_after_cause": effect_before_cause,
    "genesis_at_start": world_made_late,
    "moment_after_births": people_before_its_world,
    "birth_dated": undated_birth,
    "step_moment_order": steps_running_back,
    "witness_present": witness_far_away,
    "witness_mode": witness_who_does_not_say_how,
    "time_shares": time_budget_over_the_year,
    "child_ages": wedding_before_naming,
    "upbringing_shares": upbringing_past_the_whole,
    "norm_sexes": sexed_norm_for_a_sexless_people,
    "youth_years": elder_in_a_youth_group,
    "policy_holder": policy_held_by_a_single_being,
    "lease_owner": lease_of_a_thing_not_owned,
    "works_place": works_on_foreign_ground,
    "media_reach": item_beyond_its_outlet,
    "god_reading_real": reading_of_no_god,
    "creature_group_one_kind": pack_led_by_another_kind,
    "wave_coast_on_sea": wave_on_a_dry_coast,
    "honour_holder_limit": honour_past_its_limit,
    "honour_privileges": honour_with_an_odd_privilege,
    "fertility_means_conceive": means_of_a_people_without_conception,
    "fertility_use_known": use_of_an_unknown_means,
    "condition_body_system": condition_of_an_absent_system,
    "grave_goods_held": grave_with_a_stray_thing,
    "interpretation_reader": exchange_with_itself,
    "feeling_spread_values": mood_with_a_stray_feeling,
    "kin_dynamic_scope": dynamic_of_nothing,
    "kin_favour_other": favour_for_oneself,
    "kin_rivalry_pair": rivalry_backwards,
    "elder_sway_living": sway_of_the_dead,
    "protected_area_region": protected_town,
    "species_protection_kind": protected_region_as_kind,
    "conservation_movement_cause": aims_of_another_movement,
    "land_use_rule_district": rule_on_anothers_district,
    "conurbation_members": city_with_itself_as_quarter,
    "interworld_campaign_route": campaign_on_a_stray_way,
    "interworld_campaign_landed": landed_host_elsewhere,
    "interworld_migration_route": movement_to_its_own_world,
    "mass_weapon_technique": weapon_beyond_its_means,
    "war_remnant_war": remnant_of_a_war_still_fought,
    "war_remnant_place": remnant_in_land_and_orbit,
    "deterrence_posture_self": posture_toward_itself,
    "occupation_regime_open": regime_without_an_occupation,
    "collaboration_place": collaborator_from_afar,
    "collaboration_end": killed_collaborator_without_an_end,
    "occupation_measure_regime": measure_of_an_ended_regime,
    "occupation_measure_region": measure_in_another_land,
    "restoration_fallen": restoration_of_a_standing_realm,
    "restoration_predecessor": restored_without_a_link,
    "restoration_end": open_restoration_with_an_end,
    "leader_cult_leader": cult_of_a_settlement,
    "leader_cult_promoters": cult_with_a_lost_promoter,
    "leader_cult_end": living_cult_with_an_end,
    "reckoning_case_acts": case_naming_an_unrecorded_deed,
    "reckoning_after_fall": reckoning_before_its_fall,
    "reckoning_measure_realm": measure_of_another_realm,
    "referendum_franchise": vote_open_to_the_wrong_people,
    "referendum_subject": vote_on_nothing,
    "referendum_held": vote_held_before_it_was_called,
    "departure_successor": office_handed_to_oneself,
    "departure_office": leaving_of_a_stray_office,
    "departure_return": return_before_leaving,
    "economic_order_single": realm_with_two_orders,
    "order_transition_axes": change_of_unknown_axes,
    "order_transition_realm": change_of_a_fallen_realm,
    "league_members_polities": guild_in_a_league,
    "league_currency_union": currency_union_with_no_money,
    "league_decision_organ": ruling_with_no_court,
    "security_holdings_within": holdings_beyond_the_amount,
    "security_issuer_living": listed_claim_of_a_gone_issuer,
    "security_price_issuer": price_naming_a_stranger,
    "monetary_peg_target": peg_on_its_own_coin,
    "monetary_issuer": authority_naming_a_stranger_issuer,
    "labour_contract_body": contract_of_a_body_that_is_gone,
    "labour_dispute_workers": dispute_with_too_many_out,
    "worker_body_trades": body_of_unknown_trades,
    "market_shares_whole": shares_that_miss_a_hundred,
    "cartel_sellers": compact_with_an_outsider,
    "price_war_market": price_war_in_a_lost_market,
    "org_seats_members": seat_held_by_a_stranger,
    "org_votes_whole": votes_that_miss_a_hundred,
    "org_merger_parties": bid_for_a_vanished_house,
    "insolvency_claims": creditor_who_never_lent,
    "speech_venue": sermon_in_a_town_without_a_temple,
    "folk_class_kind": class_of_animals_pointing_at_a_region,
    "stage_builder": stage_set_down_by_another_realm,
    "endowment_capture": endowment_held_captive_by_a_mortal,
    "remains_rite": remains_the_rite_forbids,
    "practice_holder": practice_of_a_mortal,
    "numerology_keys": reading_beyond_the_base,
    "instrument_policy": instrument_of_another_holder,
    "kin_head_member": kin_group_headed_by_a_stranger,
    "kin_member_rule": stranger_in_a_descent_group,
    "change_in_scope": engine_change_of_no_happening,
    "checkpoint_holds": checkpoint_that_lies,
    "genome_alleles": genome_with_unknown_allele,
    "money_metal": paper_made_of_metal,
    "material_source": star_stuff_from_a_town,
    "living_captor": captor_dies,
    "living_range": species_dies_in_its_lands,
    "order_target": order_loses_target,
    "maker_not_self": construct_makes_itself,
    "living_ruler": ruler_dies,
    "covenant_people": covenant_without_people,
    "seat_god": seat_without_god,
    "tie_gods": tie_without_god,
    "syncretism_kinds": joining_without_people,
    "holding_kind": holding_without_kind,
    "kind_lineage": kind_derived_from_itself,
    "kind_ranges": kind_out_of_range,
}


@pytest.mark.parametrize("spec", TYPED, ids=lambda spec: spec.key)
async def test_each_invariant_finds_what_breaks_it_and_mends_it(session: AsyncSession, world: CoreWorld, spec: InvariantSpec) -> None:
    key = spec.key
    find, _ = CHECKS[key]
    assert await find(session) == []
    await BREAKERS[key](session, world)
    await session.flush()
    broken = await find(session)
    assert broken
    if spec.remedy is Remedy.REPAIR:
        await sweep(session)
    else:
        for finding in [item for item in await findings(session) if item.invariant == key]:
            await resolve(session, finding)
    assert await find(session) == []


async def test_every_typed_invariant_has_a_breaker() -> None:
    assert {spec.key for spec in TYPED} == set(BREAKERS) == set(CHECKS)


async def test_the_generic_checks_mend_ranges_epochs_and_report_stray_holds(session: AsyncSession, world: CoreWorld) -> None:
    session.add(TechnologyProfileRow(holder_node_id=world.people.id, family=TechFamily.ENERGY, level=3, updated_epoch=500, locked=["level", "nothing_here"]))
    await session.flush()
    swept = await sweep(session)
    assert swept.repaired[GenericCheck.PAST_EPOCHS.value] >= 1
    row = await session.get(TechnologyProfileRow, (world.people.id, TechFamily.ENERGY))
    assert row is not None
    await session.refresh(row)
    assert row.updated_epoch <= world.cosmos.epoch
    stray = [item for item in await findings(session) if item.check is GenericCheck.LOCKED_NAMES and item.table == "technology_profiles"]
    assert stray
    await resolve(session, stray[0])
    await session.refresh(row)
    assert row.locked == ["level"]


async def test_one_who_heard_from_afar_or_moved_later_is_not_called_absent(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    heard = await mortal(session, "Far Listener", world, world.regions[1].id)
    moved = await mortal(session, "Later Traveller", world, world.regions[0].id)
    session.add_all(
        [
            IncidentParticipantRow(
                incident_id=incident.id, node_id=heard.id, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.HEARD, fidelity=60
            ),
            IncidentParticipantRow(incident_id=incident.id, node_id=moved.id, role=IncidentRole.WITNESS, position=1, witness_mode=WitnessMode.SAW, fidelity=90),
        ]
    )
    await session.flush()
    with scoped(RecordScope(key="test.move", epoch=incident.epoch + 1)):
        moved.location_id = world.regions[1].id
        await session.flush()
    assert await absent_witnesses(session) == []
