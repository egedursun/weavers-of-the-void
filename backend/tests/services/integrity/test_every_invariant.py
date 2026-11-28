from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_causes import DEATH_CAUSES, LOOSE_CAUSES, death_cause_of
from aerona.catalog.invariants import TYPED, GenericCheck, InvariantSpec, Remedy
from aerona.catalog.long_seasons import CAUSES
from aerona.catalog.market_kinds import ANIMAL_CLUBS, CLUBS
from aerona.catalog.methods import METHODS
from aerona.catalog.plants import PARTS
from aerona.catalog.revivals import REVIVAL_WAYS
from aerona.catalog.stats import max_essence
from aerona.db.record_context import RecordScope, scoped
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.session import Database
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.arts import ClubRow
from aerona.db.tables.belonging import HeldIdentityRow, SanctuaryRow
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.childhood import ChildStandingRow, SocializationRow
from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow
from aerona.db.tables.collective import AccountRow, GenerationRow
from aerona.db.tables.commerce import LeaseRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, RiftRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.crafts import AssistiveAidRow, IncorporealRightRow, NumberSystemRow, SympatheticLinkRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.culture import HolderTechniqueRow, TraditionProfileRow
from aerona.db.tables.customs import BodyMarkRow, IntoxicantCustomRow, MembershipRow, RevivalRow, TimeBudgetRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.divine import CouncilRulingRow, DivineWoundRow, NaturalLawProfileRow
from aerona.db.tables.divine_conceptions import GodReadingRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.economy import CurrencyRow, TradeRouteProfileRow, WorldMaterialRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, LanguageProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.faith import ReincarnationRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.folkways import LuckBeliefRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionRow, GatheringRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgGovernanceRow, OrgMergerRow, OrgSeatRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow, NamedUnitRow, UnitHonourRow
from aerona.db.tables.households import DwellingRow, HouseholdRow
from aerona.db.tables.industry import CommunityMethodRow
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
from aerona.db.tables.means import NavigationKitRow, SecurityRow, WaterLiftRow, WrittenWorkRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow
from aerona.db.tables.military import OccupationRow, SpyNetworkRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.mythic import ServitorRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationMeasureRow, OccupationRegimeRow
from aerona.db.tables.operations import ExpeditionRow, ShipCrewRow
from aerona.db.tables.orders import EconomicOrderRow, OrderTransitionRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.physics import ImpactEventRow, StarPhysicsRow, WorldLifeRow, WorldPhysicsRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.plants import PlantPartRow
from aerona.db.tables.polity import ClaimRow, OfficeRow, PolityProfileRow, TreatyPartyRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.presence import PresenceExchangeRow, PresenceSessionRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.relations import ContestRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow, LoreTradeRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sacred import BirthSignRow, GeniusLocusRow, PetitionRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, SecurityPriceRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.sites import BattlefieldFeatureRow
from aerona.db.tables.sons import SonRelationRow, SonRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, SiegeRow, WarRow, WarSideRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.ages import SeasonSpell, SeasonSpellShape
from aerona.domain.enums.agrarian import RebuildCause, RebuildPlan
from aerona.domain.enums.arcana import SpellDuration, SpellForm, SpellRange, SpellTechnique
from aerona.domain.enums.belonging import FugitiveKind, IdentityLayer, SanctuaryKind
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyPart, BodyPlan, ConditionKind, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.collective import AccountKind
from aerona.domain.enums.constructs import CommandToken, OrderCondition, OrderKind
from aerona.domain.enums.cosmography import BeingAgenda, BeingKind, BeingPhase, BeingScale, DimensionKind, RiftCause, RiftState
from aerona.domain.enums.crafts import AssistiveAid, LinkToken, RightKind
from aerona.domain.enums.creator import CovenantDuty, CreatorPromise
from aerona.domain.enums.creature_groups import GroupForm
from aerona.domain.enums.culture import CalendarSlot, Technique, TraditionFunction
from aerona.domain.enums.customs import Intoxicant, MarkKind, MarkMeaning, Membership, Naturalisation, RevivalGoal
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import AgeBand, CohortCondition, FuneralCustom, InheritanceCustom, Job, MartialStyle, SexKind
from aerona.domain.enums.departures import DepartureKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine import CouncilMotion, DivineWoundKind, LawException, SonPunishment, WoundCause
from aerona.domain.enums.divine_conceptions import GodReading
from aerona.domain.enums.ecology import Biochemistry, YieldProduct
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, MaterialOrigin, MoneyForm, TradeMode, TradeRouteStatus
from aerona.domain.enums.endowments import EndowmentState
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.faction import FactionKind, MovementCause
from aerona.domain.enums.faith import RebirthPath, ReincarnationGate
from aerona.domain.enums.fertility_means import FertilityMeans
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.folkways import LuckReach, LuckSign
from aerona.domain.enums.gathering import CollectionKind, CollectionRole, GatheringKind, GatheringStatus
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.domain.enums.governance import GoverningBody
from aerona.domain.enums.honours import UnitHonourKind
from aerona.domain.enums.industry import ProcessKind
from aerona.domain.enums.interworld import CampaignStage
from aerona.domain.enums.intimacy import RelationContext
from aerona.domain.enums.kinds import GoodCategory, KindConcept
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.leagues import LeagueDecisionKind, LeagueOrgan
from aerona.domain.enums.mass_weapons import MassHarm, MassReach
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.means import LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.military import DefenderAction
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.domain.enums.mythic import ServitorOrigin
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.occupation_regimes import CollaborationFate
from aerona.domain.enums.operations import CarrierKind, CrewStation, ExpeditionGround
from aerona.domain.enums.orders import TransitionKind
from aerona.domain.enums.physics import AirNeed, ImpactBody, ImpactOutcome, LifeEnvironment
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind, OfficeKind, PartyRole
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.presence import PresenceExchangeStatus, PresenceGuise, PresenceRecord
from aerona.domain.enums.reckoning import ReckoningMeasure
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.enums.records import FactUnit, StepAction, WitnessMode
from aerona.domain.enums.referendums import Franchise, ReferendumResult, ReferendumSubject
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LorePrice, ReputationAxis
from aerona.domain.enums.restoration import RestorationStage
from aerona.domain.enums.sacred import GeniusLocusKind, PetitionKind, SignInfluence
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.site import BattlefieldFeature
from aerona.domain.enums.society import NaturalLaw, SocialClass
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.statecraft import CrisisDemand, CrisisState
from aerona.domain.enums.titles import TitleTier
from aerona.domain.enums.tongues import LanguageModality, LanguageStage
from aerona.domain.enums.travel import TravelMethod, VehicleKind
from aerona.domain.enums.war import BattleOutcome, CaptiveStatus, WarCause, WarSide, WarStatus
from aerona.domain.enums.world import Gravity
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.enums.world_view import SettleMode, WarTerrain
from aerona.domain.models.entity_stats import (
    ArmyStats,
    ArtworkStats,
    BeastStats,
    CosmicBeingStats,
    CultStats,
    DiseaseStats,
    EventStats,
    FactionStats,
    HouseStats,
    LanguageStats,
    LawStats,
    LeagueStats,
    MortalStats,
    NaturalLawStats,
    PeopleStats,
    PlaceStats,
    PolityStats,
    RiteStats,
    SettlementStats,
    SpeciesStats,
    SpiritStats,
    StructureStats,
    TitleStats,
    TradeRouteStats,
    TraditionStats,
    TreatyStats,
    VesselStats,
)
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.orbits import infer
from aerona.engine.cosmos.stellar import new_physics
from aerona.engine.demography.peoples import ensure_profiles
from aerona.engine.households.dwelling_kinds import built_in_dwelling
from aerona.engine.minds.profiles import profile_of
from aerona.engine.primitives.language_profile import DEFAULT_PHONOLOGY
from aerona.engine.recording.checkpoints import take_checkpoint
from aerona.rules.registry import Rules
from aerona.services.integrity.invariants import CHECKS, findings, resolve, sweep
from aerona.services.integrity.record_links import absent_witnesses
from tests.conftest import OpenDatabase
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, seed_core_world, settlement, son_draft
from tests.engine.core.test_arcana_w15 import foreign_caster


async def crisis_settled_by_no_one(session: AsyncSession, world: CoreWorld) -> None:
    first = await entity(session, "Reed Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    second = await entity(session, "Fen Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        CrisisRow(demander_entity_id=first.id, target_entity_id=second.id, demand=CrisisDemand.PAY, state=CrisisState.MEDIATED, opened_epoch=1, locked=[])
    )


async def dispute_with_no_contender(session: AsyncSession, world: CoreWorld) -> None:
    doer = await mortal(session, "Beast Slayer", world, world.regions[0].id)
    boaster = await mortal(session, "Loud Boaster", world, world.regions[0].id)
    deed = DeedRow(doer_node_id=doer.id, axis=ReputationAxis.HEROISM, magnitude=40, epoch=1, locked=[])
    session.add(deed)
    await session.flush()
    session.add(DeedClaimRow(deed_id=deed.id, claimant_node_id=boaster.id, kind=ClaimKind.FALSE, status=ClaimStatus.DISPUTED, epoch=1, locked=[]))


async def service_with_no_task(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lorehold", world, world.regions[0])
    session.add(
        LoreTradeRow(
            seller_node_id=town.id, buyer_node_id=world.people.id, kind=KnowledgeKind.TECHNIQUE, key="smelting", value=10, price=LorePrice.SERVICE, epoch=1
        )
    )


Breaker = Callable[[AsyncSession, CoreWorld], Awaitable[None]]
PHASE_KIND = "phase.statecraft"
FAR_ORBIT = 60.0
COLD_ORBIT = 1.6


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
    session.add(IncidentParticipantRow(incident_id=made.id, node_id=world.regions[0].id, role=IncidentRole.CHILD, position=0))
    session.add(NodeBirthRow(node_id=world.regions[0].id, year=31, locked=[]))
    woke = await happening(session, kind=PHASE_KIND, year=0)
    session.add(IncidentParticipantRow(incident_id=woke.id, node_id=world.regions[0].id, role=IncidentRole.SUBJECT, position=0))


async def birth_after_its_first_record(session: AsyncSession, world: CoreWorld) -> None:
    named = await mortal(session, "Late Dated", world, world.regions[0].id)
    session.add(NodeBirthRow(node_id=named.id, year=40, locked=[]))
    seen = await happening(session, kind=PHASE_KIND, year=10)
    session.add(IncidentParticipantRow(incident_id=seen.id, node_id=named.id, role=IncidentRole.SUBJECT, position=0))


async def child_older_than_its_years(session: AsyncSession, world: CoreWorld) -> None:
    child = await mortal(session, "Old Child", world, world.regions[0].id, age=40)
    session.add(NodeBirthRow(node_id=child.id, year=45, locked=[]))
    born = await happening(session, kind="births.child", year=45)
    session.add(IncidentParticipantRow(incident_id=born.id, node_id=child.id, role=IncidentRole.CHILD, position=0))


async def witness_before_birth(session: AsyncSession, world: CoreWorld) -> None:
    onlooker = await mortal(session, "Unborn Onlooker", world, world.regions[0].id)
    session.add(NodeBirthRow(node_id=onlooker.id, year=30, locked=[]))
    seen = await happening(session, kind=PHASE_KIND, year=0)
    session.add(
        IncidentParticipantRow(incident_id=seen.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.SAW, fidelity=90)
    )


async def verdict_inside_its_age(session: AsyncSession, world: CoreWorld) -> None:
    await happening(session, kind="fate.reward", year=5)


async def wake_before_the_death(session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Wake Host", world, world.regions[0].id)
    honoured = await mortal(session, "Wake Honoured", world, world.regions[0].id, death_year=30)
    honoured.status, honoured.end_epoch = EntityStatus.DEAD, 1
    session.add(
        GatheringRow(
            host_node_id=host.id,
            kind=GatheringKind.WAKE,
            status=GatheringStatus.HELD,
            honoured_node_id=honoured.id,
            world_id=world.world.id,
            epoch=1,
            year=10,
            locked=[],
        )
    )


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


async def household_mood_told_as_a_place(session: AsyncSession, world: CoreWorld) -> None:
    head = await mortal(session, "Hearth Head", world, None)
    session.add(HouseholdRow(id=head.id, name="House of the Hearth", head_node_id=head.id, locked=[]))
    told = await happening(session, kind="mood.spread", year=12)
    session.add(IncidentParticipantRow(incident_id=told.id, node_id=head.id, role=IncidentRole.SUBJECT, position=0))
    session.add(IncidentFactRow(incident_id=told.id, key="feeling", enum_name="Emotion", enum_value="joy"))
    session.add(IncidentFactRow(incident_id=told.id, key="strength", number=60.0, unit=FactUnit.PERCENT))


async def grown_one_still_called_a_child(session: AsyncSession, world: CoreWorld) -> None:
    grown = await mortal(session, "Long Grown", world, world.regions[0].id)
    grown.subtype = "child"
    session.add(MortalProfileRow(entity_id=grown.id, life_stage=LifeStage.ADULT))


async def mortal_standing_inside_a_guild(session: AsyncSession, world: CoreWorld) -> None:
    guild = await entity(session, "Rivet Guild", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=world.regions[0].id)
    hand = await mortal(session, "Guild Hand", world, world.regions[0].id)
    hand.location_id = guild.id


async def funeral_named_after_its_host(session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Keel Host", world, None)
    mourned = await mortal(session, "Mourned One", world, None)
    row = CollectionRow(kind=CollectionKind.FUNERAL, name="Funeral of Keel Host and Mourned One", world_id=world.world.id, start_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    session.add(CollectionMemberRow(collection_id=row.id, node_id=host.id, role=CollectionRole.HOST, since_epoch=1))
    session.add(CollectionMemberRow(collection_id=row.id, node_id=mourned.id, role=CollectionRole.VICTIM, since_epoch=1))


async def plague_named_before_its_naming(session: AsyncSession, world: CoreWorld) -> None:
    plague = await entity(session, "Upcegin", EntityType.EVENT, EventStats(), world_id=world.world.id)
    row = CollectionRow(kind=CollectionKind.PLAGUE, name="Plague of Ofjur Plague (Epoch 8)", world_id=world.world.id, start_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    session.add(CollectionMemberRow(collection_id=row.id, node_id=plague.id, role=CollectionRole.LEADER, since_epoch=1))


async def headship_named_by_its_label(session: AsyncSession, world: CoreWorld) -> None:
    title = await entity(session, "the Headship of an association of Ormedal", EntityType.TITLE, TitleStats(), world_id=world.world.id)
    session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleTier.GUILD, locked=[]))


async def tribute_named_for_an_old_name(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Dasmir Quay", world, world.regions[0])
    tribute = await entity(session, "the Tribute of Vorkel Quay", EntityType.TREATY, TreatyStats(), world_id=world.world.id)
    session.add(TreatyPartyRow(treaty_entity_id=tribute.id, party_node_id=town.id, role=PartyRole.SIGNATORY))
    session.add(
        StateChangeRow(
            epoch=1,
            table_name="nodes",
            row_key=f'{{"id": {town.id}}}',
            node_id=town.id,
            operation=LedgerOperation.UPDATE,
            field="name",
            before_text="Vorkel Quay",
            actor_kind=ActorKind.SYSTEM,
        )
    )


async def memory_of_a_stranger_happening(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Holds A Memory", world, world.regions[0].id)
    remembered = await mortal(session, "Is Remembered", world, world.regions[0].id)
    elsewhere = IncidentRow(kind="society.rivalry", epoch=1)
    session.add(elsewhere)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=elsewhere.id, node_id=holder.id, role=IncidentRole.ACTOR, position=0))
    session.add(
        MemoryRow(
            holder_node_id=holder.id,
            subject_node_id=remembered.id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-10,
            decay_pct=10,
            epoch=1,
            incident_id=elsewhere.id,
        )
    )


async def fact_the_kind_no_longer_tells(session: AsyncSession, world: CoreWorld) -> None:
    town = await entity(session, "Altar Town", EntityType.SETTLEMENT, SettlementStats(), world_id=world.world.id)
    incident = IncidentRow(kind="religion.syncretism", epoch=1)
    session.add(incident)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=incident.id, node_id=town.id, role=IncidentRole.SUBJECT, position=0))
    session.add(IncidentFactRow(incident_id=incident.id, key="cold", position=0, name="; the altars grew cold"))


async def mourning_kept_as_festival(session: AsyncSession, world: CoreWorld) -> None:
    rite = await entity(session, "Mourning of Ash", EntityType.TRADITION, TraditionStats(), world_id=world.world.id, origin=EntityOrigin.ENGINE)
    rite.subtype = "mourning rite"
    session.add(TraditionProfileRow(tradition_entity_id=rite.id, kind=TraditionFunction.FESTIVAL, calendar_slot=CalendarSlot.HARVEST, locked=[]))


async def kept_after_its_time_did_not_come(session: AsyncSession, world: CoreWorld) -> None:
    town = await entity(session, "Late Feast Town", EntityType.SETTLEMENT, SettlementStats(), world_id=world.world.id)
    feast = await entity(session, "Late Fires", EntityType.TRADITION, TraditionStats(), world_id=world.world.id)
    for kind, roles in (("tradition.slot_closed", (IncidentRole.SUBJECT, IncidentRole.ACTOR)), ("tradition.kept", (IncidentRole.PRODUCT, IncidentRole.PLACE))):
        told = IncidentRow(kind=kind, epoch=1)
        session.add(told)
        await session.flush()
        session.add(IncidentParticipantRow(incident_id=told.id, node_id=feast.id, role=roles[0], position=0))
        session.add(IncidentParticipantRow(incident_id=told.id, node_id=town.id, role=roles[1], position=0))


async def remembrance_of_no_one(session: AsyncSession, world: CoreWorld) -> None:
    dead = await mortal(session, "Remembered Elder", world, world.regions[0].id)
    rite = await entity(session, "Mourning of Remembered Elder", EntityType.TRADITION, TraditionStats(), world_id=world.world.id, origin=EntityOrigin.ENGINE)
    await bond(session, rite.id, dead.id, BondKind.TELLS_OF)
    session.add(TraditionProfileRow(tradition_entity_id=rite.id, kind=TraditionFunction.MOURNING, calendar_slot=CalendarSlot.REMEMBRANCE, locked=[]))


async def mourning_under_another_dead(session: AsyncSession, world: CoreWorld) -> None:
    dead = await mortal(session, "Mourned Here", world, world.regions[0].id)
    other = await mortal(session, "Mourned Elsewhere", world, world.regions[0].id)
    funeral = CollectionRow(kind=CollectionKind.FUNERAL, name="Funeral of Mourned Elsewhere", start_epoch=1, locked=[])
    session.add(funeral)
    await session.flush()
    session.add(CollectionMemberRow(collection_id=funeral.id, node_id=other.id, role=CollectionRole.VICTIM))
    session.add(CollectionMemberRow(collection_id=funeral.id, node_id=dead.id, role=CollectionRole.GUEST))
    session.add(
        GatheringRow(
            host_node_id=world.regions[0].id,
            kind=GatheringKind.MOURNING,
            status=GatheringStatus.HELD,
            honoured_node_id=dead.id,
            collection_id=funeral.id,
            epoch=1,
            locked=[],
        )
    )


async def dead_still_hale(session: AsyncSession, world: CoreWorld) -> None:
    fallen = await mortal(session, "Fallen Hale", world, world.regions[0].id, hp=60)
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 1


async def host_led_by_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    fallen = await mortal(session, "Fallen Marshal", world, world.regions[0].id)
    host = await entity(session, "Leaderless Host", EntityType.ARMY, ArmyStats(size=100), world_id=world.world.id)
    session.add(ArmyRow(entity_id=host.id, owner_entity_id=world.regions[0].id, commander_entity_id=fallen.id, raised_epoch=1))
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 1


async def war_titled_after_strangers(session: AsyncSession, world: CoreWorld) -> None:
    first = await entity(session, "Red Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    second = await entity(session, "Blue Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    event = await entity(session, "War of Nobody and Noone", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(
        event_entity_id=event.id, world_id=world.world.id, status=WarStatus.ONGOING, cause=WarCause.HOSTILITY, started_epoch=1, battles=0, score=0, locked=[]
    )
    session.add(war)
    await session.flush()
    session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=first.id, side=WarSide.ATTACKER, joined_epoch=1),
            WarSideRow(war_id=war.id, entity_id=second.id, side=WarSide.DEFENDER, joined_epoch=1),
        ]
    )


async def ruin_still_peopled(session: AsyncSession, world: CoreWorld) -> None:
    town = await entity(session, "Empty Hamlet", EntityType.SETTLEMENT, SettlementStats(population=60), world_id=world.world.id)
    session.add(EntityFlagRow(entity_id=town.id, flag=EntityFlag.RUIN, epoch=1))
    town.status, town.end_epoch = EntityStatus.DEAD, 1


async def rebuilding_a_ruin(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Emptied Quay", world, world.regions[0])
    town.status, town.end_epoch = EntityStatus.DESTROYED, 1
    session.add(ReconstructionRow(settlement_entity_id=town.id, cause=RebuildCause.FLOOD, started_epoch=1, locked=[]))


async def two_seasons_one_name(session: AsyncSession, world: CoreWorld) -> None:
    for position in (0, 1):
        session.add(
            WorldSeasonRow(
                world_id=world.world.id,
                position=position + 7,
                name="Ovmin",
                temperature_shift=0,
                rain_shift=0,
                growth=50,
                travel=50,
                campaign=50,
                share_pct=50,
                edited=False,
            )
        )


async def offshoot_named_after_a_clique(session: AsyncSession, world: CoreWorld) -> None:
    await entity(session, "Greystead under those around Varr", EntityType.FACTION, FactionStats(), world_id=world.world.id)


async def plague_named_after_its_carrier(session: AsyncSession, world: CoreWorld) -> None:
    carrier = await mortal(session, "Mamda", world, world.regions[0].id)
    sickness = await entity(session, "Grey cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    plague = CollectionRow(kind=CollectionKind.PLAGUE, name="Plague of Grey cough and Mamda", world_id=world.world.id, start_epoch=1, locked=[])
    session.add(plague)
    spread = IncidentRow(kind="disease.army_carried", epoch=1, year=20, world_id=world.world.id)
    session.add(spread)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=spread.id, node_id=carrier.id, role=IncidentRole.SUBJECT, position=0))
    session.add(IncidentParticipantRow(incident_id=spread.id, node_id=sickness.id, role=IncidentRole.INSTRUMENT, position=1))
    session.add(CollectionIncidentRow(collection_id=plague.id, incident_id=spread.id))


async def league_named_bare(session: AsyncSession, world: CoreWorld) -> None:
    await entity(session, "the league of Empire of Greystead", EntityType.LEAGUE, LeagueStats(), world_id=world.world.id)


async def two_duels_in_one_history(session: AsyncSession, world: CoreWorld) -> None:
    first, shared, later = [await mortal(session, name, world, world.regions[0].id) for name in ("Parar", "Wapnar", "Onur")]
    duel = CollectionRow(kind=CollectionKind.DUEL, name="Duel of Parar and Wapnar", world_id=world.world.id, start_epoch=1, locked=[])
    session.add(duel)
    await session.flush()
    for year, pair in ((41, (first, shared)), (85, (shared, later))):
        fought = IncidentRow(kind="duel.honour", epoch=1 if year < 50 else 2, year=year, world_id=world.world.id)
        session.add(fought)
        await session.flush()
        session.add(IncidentParticipantRow(incident_id=fought.id, node_id=pair[0].id, role=IncidentRole.ACTOR, position=0))
        session.add(IncidentParticipantRow(incident_id=fought.id, node_id=pair[1].id, role=IncidentRole.OPPONENT, position=1))
        session.add(CollectionIncidentRow(collection_id=duel.id, incident_id=fought.id))


async def lit_home(session: AsyncSession, world: CoreWorld) -> WorldPhysicsRow:
    rules = await CosmosRepository(session).rules()
    star = await session.get(StarRow, world.world.star_id)
    assert star is not None
    if await session.get(StarPhysicsRow, star.id) is None:
        session.add(new_physics(rules, star, None))
    physics = await session.get(WorldPhysicsRow, world.world.id)
    if physics is None:
        physics = infer(rules, world.world, star)
        session.add(physics)
    await session.flush()
    return physics


async def planet_far_from_its_star(session: AsyncSession, world: CoreWorld) -> None:
    await lit_home(session, world)
    world.world.orbit = COLD_ORBIT


async def divine_mind_left_behind(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 6
    mind = await profile_of(session, await CosmosRepository(session).rules(), world.son.id, 1)
    mind.run_epochs = 1


async def covenant_of_enemies(session: AsyncSession, world: CoreWorld) -> None:
    sibling = await SonRepository(session).create(son_draft("Varra", world.world.id))
    await BondRepository(session).connect(BondDraft(world.son.id, sibling.id, BondKind.ALLY, 1, "A covenant sworn before the council."))
    await SonRepository(session).change_relation(world.son.id, sibling.id, -98)


async def grudge_with_no_names(session: AsyncSession, world: CoreWorld) -> None:
    sibling = await SonRepository(session).create(son_draft("Varra", world.world.id))
    session.add(
        MemoryRow(
            holder_node_id=world.son.id,
            subject_node_id=sibling.id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-25,
            decay_pct=3,
            epoch=1,
            note="overcame it in the battle for Greystead",
        )
    )


async def bond_note_overwritten(session: AsyncSession, world: CoreWorld) -> None:
    sibling = await SonRepository(session).create(son_draft("Varra", world.world.id))
    first, second = sorted((world.son.id, sibling.id))
    session.add(SonRelationRow(son_a_id=first, son_b_id=second, value=-20, note="overcame it in the battle for Greystead"))


async def son_met_the_creator(session: AsyncSession, world: CoreWorld) -> None:
    son = await session.get(SonRow, world.son.id)
    assert son is not None
    son.reputation_epoch, son.reputation_last_contact_epoch = world.cosmos.epoch, 0
    meeting = PresenceSessionRow(node_id=son.id, guise=PresenceGuise.CREATOR, record=PresenceRecord.ON_RECORD, opened_epoch=world.cosmos.epoch)
    session.add(meeting)
    await session.flush()
    session.add(PresenceExchangeRow(session_id=meeting.id, ordinal=1, epoch=world.cosmos.epoch, player_text="Speak.", status=PresenceExchangeStatus.DONE))


async def son_overfilled(session: AsyncSession, world: CoreWorld) -> None:
    son = await session.get(SonRow, world.son.id)
    assert son is not None
    son.essence = max_essence(await CosmosRepository(session).rules(), son.might) + 14


async def star_left_dim(session: AsyncSession, world: CoreWorld) -> None:
    await lit_home(session, world)
    own = await session.get(StarPhysicsRow, world.world.star_id)
    assert own is not None
    own.luminosity = 0.001


async def grown_mortal_born_at_first_sight(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 10
    grown = await entity(session, "Grey Captain", EntityType.MORTAL, MortalStats(age=44), world_id=world.world.id)
    session.add(NodeBirthRow(node_id=grown.id, year=481, season=None, day=None, hour=None, locked=[]))


async def star_clock_set_from_birth(session: AsyncSession, world: CoreWorld) -> None:
    await lit_home(session, world)
    star = await session.get(StarRow, world.world.star_id)
    own = await session.get(StarPhysicsRow, world.world.star_id)
    assert star is not None and own is not None
    own.age_epochs = own.lifetime_epochs
    star.lifecycle_clock = own.lifetime_epochs * 2


async def planet_moved_by_an_old_repair(session: AsyncSession, world: CoreWorld) -> None:
    await lit_home(session, world)
    lived = world.world.orbit
    world.world.orbit = FAR_ORBIT
    world.world.calendar_locked = ["year_length_days"]
    for field, before, after in (("orbit", lived, FAR_ORBIT), ("calendar_locked", None, None)):
        session.add(
            StateChangeRow(
                epoch=1,
                table_name="worlds",
                row_key=f'{{"id": {world.world.id}}}',
                node_id=world.world.id,
                operation=LedgerOperation.UPDATE,
                field=field,
                before_number=before,
                after_number=after,
                before_text="[]" if field == "calendar_locked" else None,
                after_text='["year_length_days"]' if field == "calendar_locked" else None,
                actor_kind=ActorKind.SYSTEM,
            )
        )


async def strain_named_twice(session: AsyncSession, world: CoreWorld) -> None:
    await entity(session, "Grey cough, strain 2, strain 2", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)


async def generations_outnumber_their_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await entity(session, "Thin Hamlet", EntityType.SETTLEMENT, SettlementStats(population=40), world_id=world.world.id)
    session.add(GenerationRow(community_entity_id=town.id, generation_epoch=1, formative=[], value_shifts={}, alive=400, locked=[]))


async def grown_mortal_signed_at_arrival(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 4
    grown = await entity(session, "Grey Elder", EntityType.MORTAL, MortalStats(age=120), world_id=world.world.id)
    session.add(BirthSignRow(mortal_entity_id=grown.id, season=0, dreaded=False, influence=SignInfluence.BELIEVED, fortune=0, born_epoch=4, locked=[]))


async def wound_dated_outside_its_epoch(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Old Scar", world, world.regions[0].id)
    session.add(
        InjuryRow(
            bearer_node_id=bearer.id,
            part=BodyPart.LEFT_ARM,
            kind=InjuryKind.CUT,
            damage_type=DamageType.CUT,
            severity=2,
            state=InjuryState.HEALED_SCAR,
            function_loss=0,
            cause_kind=HarmCause.ACCIDENT,
            epoch=7,
            year=30,
        )
    )


async def seat_held_before_its_holder_came(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Short Stay", world, world.regions[0].id)
    session.add(NodeBirthRow(node_id=holder.id, year=330, locked=[]))
    session.add(DepartureRow(holder_node_id=holder.id, kind=DepartureKind.RETIREMENT, epoch=8, years_held=300, locked=[]))


async def law_named_twice(session: AsyncSession, world: CoreWorld) -> None:
    await entity(session, "The burial law law of Greystead", EntityType.LAW, LawStats(), world_id=world.world.id)


async def vigil_kept_at_harvest(session: AsyncSession, world: CoreWorld) -> None:
    vigil = await entity(session, "Long Watch", EntityType.TRADITION, TraditionStats(), world_id=world.world.id, origin=EntityOrigin.ENGINE)
    session.add(TraditionProfileRow(tradition_entity_id=vigil.id, kind=TraditionFunction.VIGIL, calendar_slot=CalendarSlot.HARVEST, locked=[]))


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


async def river_spirit_counted_a_mountain(session: AsyncSession, world: CoreWorld) -> None:
    ford = await entity(session, "Shallow Ford", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=ford.id, kind=PlaceKind.RIVER, locked=[]))
    keeper = await entity(session, "Ford Keeper", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=ford.id)
    session.add(GeniusLocusRow(spirit_entity_id=keeper.id, place_entity_id=ford.id, kind=GeniusLocusKind.MOUNTAIN, locked=[]))


async def settlement_in_no_cell(session: AsyncSession, world: CoreWorld) -> None:
    town = await entity(
        session,
        "Hollow Hearth",
        EntityType.SETTLEMENT,
        SettlementStats(population=100, prosperity=50, defense=30, piety=50),
        world_id=world.world.id,
        location_id=world.regions[0].id,
    )
    town.stratum = UndergroundStratum.CAVERN_LOWER


async def passage_dug_but_never_open(session: AsyncSession, world: CoreWorld) -> None:
    session.add(RegionStratumRow(region_entity_id=world.regions[0].id, stratum=UndergroundStratum.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    session.add(
        DeepPassageRow(
            world_id=world.world.id,
            first_region_entity_id=world.regions[0].id,
            first_stratum=None,
            second_region_entity_id=world.regions[0].id,
            second_stratum=UndergroundStratum.CAVERN_UPPER,
            state=DeepPassageState.OPEN,
            origin=DeepPassageOrigin.DUG,
            width=40,
            progress=30,
            opened=False,
            locked=[],
        )
    )


async def passage_into_no_cell(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        DeepPassageRow(
            world_id=world.world.id,
            first_region_entity_id=world.regions[0].id,
            first_stratum=None,
            second_region_entity_id=world.regions[0].id,
            second_stratum=UndergroundStratum.MAGMA_SEA,
            state=DeepPassageState.OPEN,
            origin=DeepPassageOrigin.NATURAL,
            width=40,
            progress=100,
            opened=True,
            locked=[],
        )
    )


async def vengeance_against_no_one(session: AsyncSession, world: CoreWorld) -> None:
    asker = await mortal(session, "Wronged One", world, world.regions[0].id)
    office = await entity(session, "Office Of Springs", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PetitionRow(petitioner_node_id=asker.id, office_spirit_id=office.id, kind=PetitionKind.VENGEANCE, filed_epoch=1, due_epoch=2, locked=[]))


async def luck_in_no_creature(session: AsyncSession, world: CoreWorld) -> None:
    session.add(LuckBeliefRow(people_entity_id=world.people.id, sign=LuckSign.ANIMAL, reach=LuckReach.TRADE, lucky=True, name="A sign of nothing", locked=[]))


async def reborn_as_no_kind(session: AsyncSession, world: CoreWorld) -> None:
    soul = await entity(session, "Wandering Soul", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ReincarnationRow(spirit_entity_id=soul.id, gate=ReincarnationGate.TENET, path=RebirthPath.KIND, epoch=1))


async def promise_to_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    promised = await mortal(session, "Promised", world, world.regions[0].id)
    gone = await mortal(session, "Gone Before", world, world.regions[0].id)
    await bond(session, promised.id, gone.id, BondKind.BETROTHED_TO)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1


async def war_between(session: AsyncSession, world: CoreWorld) -> tuple[int, EntityRow, EntityRow]:
    first = await settlement(session, "Fordham", world, world.regions[0])
    second = await settlement(session, "Weirby", world, world.regions[0])
    event = await entity(session, "The Weir War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=next(iter(WarCause)), started_epoch=1)
    session.add(war)
    await session.flush()
    return war.id, first, second


async def mole_placed_outside_the_target(session: AsyncSession, world: CoreWorld) -> None:
    _, first, second = await war_between(session, world)
    elsewhere = await settlement(session, "Farhold", world, world.regions[0])
    session.add(
        SpyNetworkRow(
            owner_entity_id=first.id, target_entity_id=second.id, agent_ids=[], since_epoch=1, revealed_aims=[], institution_entity_id=elsewhere.id, locked=[]
        )
    )


async def flood_with_no_water(session: AsyncSession, world: CoreWorld) -> None:
    war_id, first, second = await war_between(session, world)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    if ground is not None:
        ground.river_class = RiverClass.NONE
    session.add(
        SiegeRow(
            war_id=war_id,
            besieged_entity_id=second.id,
            besieger_entity_id=first.id,
            started_epoch=1,
            works={},
            last_defence=DefenderAction.FLOOD_APPROACHES,
            locked=[],
        )
    )


async def settlement_submerged_on_dry_land(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Drysend", world, world.regions[0])
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    if ground is not None:
        ground.dominant_terrain = TerrainKind.PLAIN
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, settle_mode=SettleMode.SUBMERGED, locked=[], foreigners={}))


async def battle_in_open_space_on_a_land_world(session: AsyncSession, world: CoreWorld) -> None:
    war_id, first, second = await war_between(session, world)
    session.add(
        BattleRow(
            war_id=war_id,
            epoch=1,
            sequence=1,
            winner_entity_id=first.id,
            loser_entity_id=second.id,
            outcome=BattleOutcome.FIELD_VICTORY,
            gap=1.0,
            ground=WarTerrain.SPACE,
        )
    )


async def honour_won_nowhere(session: AsyncSession, world: CoreWorld) -> None:
    unit = NamedUnitRow(name="The Weir Guard", esprit=50, formed_epoch=1, locked=[])
    session.add(unit)
    await session.flush()
    session.add(UnitHonourRow(named_unit_id=unit.id, kind=UnitHonourKind.CROSSING, note="", epoch=1, locked=[]))


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


async def hand_over_of_no_one(session: AsyncSession, world: CoreWorld) -> None:
    first = await mortal(session, "Demander Lord", world, world.regions[0].id)
    second = await mortal(session, "Target Lord", world, world.regions[0].id)
    session.add(
        CrisisRow(
            demander_entity_id=first.id,
            target_entity_id=second.id,
            demand=CrisisDemand.HAND_OVER,
            subject_node_id=world.regions[0].id,
            opened_epoch=1,
            locked=[],
        )
    )


async def union_with_no_spouse(session: AsyncSession, world: CoreWorld) -> None:
    folk = await mortal(session, "Wed Stranger", world, world.regions[0].id)
    lord = await mortal(session, "Realm Holder", world, world.regions[0].id)
    session.add(
        MembershipRow(mortal_entity_id=folk.id, polity_entity_id=lord.id, category=Membership.CITIZEN, path=Naturalisation.UNION, since_epoch=1, locked=[])
    )


async def adoption_by_no_one(session: AsyncSession, world: CoreWorld) -> None:
    heir = await mortal(session, "Taken Heir", world, world.regions[0].id)
    lord = await mortal(session, "Old Lord", world, world.regions[0].id)
    session.add(
        ClaimRow(claimant_entity_id=heir.id, polity_entity_id=lord.id, basis=ClaimBasis.ADOPTION, strength=50, backer_entity_id=None, since_epoch=1, locked=[])
    )


async def linked_rite_with_no_link(session: AsyncSession, world: CoreWorld) -> None:
    keeper = await mortal(session, "Unlinked Keeper", world, world.regions[0].id)
    rite = await entity(session, "Far Word", EntityType.RITE, RiteStats(power=1, castings=0), world_id=world.world.id)
    await bond(session, keeper.id, rite.id, BondKind.OWNS)
    session.add(RiteGrammarRow(rite_entity_id=rite.id, technique=SpellTechnique.CONTROL, form=SpellForm.MIND, range=SpellRange.LINKED, difficulty=1, locked=[]))


async def rite_until_nothing(session: AsyncSession, world: CoreWorld) -> None:
    rite = await entity(session, "Open Bond", EntityType.RITE, RiteStats(power=1, castings=0), world_id=world.world.id)
    session.add(
        RiteGrammarRow(
            rite_entity_id=rite.id, technique=SpellTechnique.BIND, form=SpellForm.MIND, duration=SpellDuration.UNTIL_CONDITION, difficulty=1, locked=[]
        )
    )


async def true_name_link_unknown(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Guesser", world, world.regions[0].id)
    target = await mortal(session, "Unnamed", world, world.regions[0].id)
    session.add(SympatheticLinkRow(holder_node_id=holder.id, target_node_id=target.id, token=LinkToken.TRUE_NAME, strength=90, obtained_epoch=1, locked=[]))


async def made_thing_set(session: AsyncSession, world: CoreWorld, token: CommandToken) -> InstructionSetRow:
    maker = await mortal(session, "Clay Maker", world, world.regions[0].id)
    body = await entity(session, "Clay Hand", EntityType.BEAST, BeastStats(hp=40), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ConstructRow(entity_id=body.id, maker_entity_id=maker.id, locked=[]))
    rules = InstructionSetRow(owner_entity_id=body.id, command_token=token, holder_node_id=maker.id, locked=[])
    session.add(rules)
    await session.flush()
    return rules


async def timed_order_with_no_times(session: AsyncSession, world: CoreWorld) -> None:
    rules = await made_thing_set(session, world, CommandToken.WORD)
    session.add(InstructionOrderRow(set_id=rules.id, kind=OrderKind.GUARD, condition=OrderCondition.AT_SET_TIMES, locked=[]))


async def nameless_made_thing_held_by_name(session: AsyncSession, world: CoreWorld) -> None:
    await made_thing_set(session, world, CommandToken.TRUE_NAME)


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


async def crew_at_a_station_no_section_calls_for(session: AsyncSession, world: CoreWorld) -> None:
    hull = await entity(session, "Bare Hull", EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(VesselProfileRow(entity_id=hull.id, kind=VehicleKind.SHIP, crew=10, locked=[]))
    session.add(ShipCrewRow(vessel_entity_id=hull.id, station=CrewStation.PILOTS, count=3, skill=40, locked=[]))


async def slayer_wound_with_no_mortal(session: AsyncSession, world: CoreWorld) -> None:
    session.add(DivineWoundRow(god_node_id=world.son.id, kind=DivineWoundKind.BOUND, cause=WoundCause.MORTAL_SLAYER, locked=[]))


async def penance_with_no_deed(session: AsyncSession, world: CoreWorld) -> None:
    session.add(CouncilRulingRow(motion=CouncilMotion.PUNISH_SON, target_node_id=world.son.id, punishment=SonPunishment.PENANCE, epoch=1, locked=[]))


async def defector_with_no_former_god(session: AsyncSession, world: CoreWorld) -> None:
    spirit = await entity(session, "Turncoat", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id)
    session.add(ServitorRow(spirit_entity_id=spirit.id, god_node_id=world.son.id, origin=ServitorOrigin.DEFECTED, locked=[]))


async def regional_being_nowhere(session: AsyncSession, world: CoreWorld) -> None:
    being = await entity(session, "Drifting Mind", EntityType.COSMIC_BEING, CosmicBeingStats(), world_id=world.world.id)
    session.add(
        CosmicBeingProfileRow(
            entity_id=being.id,
            being_kind=BeingKind.ANCIENT_MADE_MIND,
            scale=BeingScale.REGION,
            might=40,
            phase=BeingPhase.DORMANT,
            agenda=BeingAgenda.SLUMBER,
            manifest_epochs=0,
            locked=[],
        )
    )


async def weapon_rift_with_no_source(session: AsyncSession, world: CoreWorld) -> None:
    ctx_rules = Rules()
    await ensure_ladder(session, ctx_rules)
    dimension = await create_dimension(session, ctx_rules, DimensionDraft("The Torn Side", DimensionKind.MIRROR, 0))
    session.add(RiftRow(world_id=world.world.id, dimension_id=dimension.id, state=RiftState.OPEN, cause=RiftCause.MASS_WEAPON, opened_epoch=1, locked=[]))


async def captive(session: AsyncSession, world: CoreWorld, status: CaptiveStatus) -> None:
    captor = await settlement(session, f"Hold of {status.value}", world, world.regions[0])
    held_one = await mortal(session, f"Captive {status.value}", world, world.regions[0].id)
    session.add(CaptiveRow(captive_entity_id=held_one.id, captor_entity_id=captor.id, status=status, taken_epoch=1, locked=[]))


async def parole_with_no_oath(session: AsyncSession, world: CoreWorld) -> None:
    await captive(session, world, CaptiveStatus.PAROLED)


async def ordnance_with_no_remnant(session: AsyncSession, world: CoreWorld) -> None:
    session.add(BattlefieldFeatureRow(place_entity_id=world.regions[0].id, feature=BattlefieldFeature.ORDNANCE, strength=40, epoch=1, locked=[]))


async def expedition_into_a_dimension_with_no_rift(session: AsyncSession, world: CoreWorld) -> None:
    leader = await mortal(session, "Rift Walker", world, world.regions[0].id)
    session.add(
        ExpeditionRow(
            name="Into nothing",
            leader_entity_id=leader.id,
            target_entity_id=world.regions[0].id,
            ground=ExpeditionGround.DIMENSION,
            started_epoch=1,
            locked=[],
        )
    )


async def joining_with_no_spouse(session: AsyncSession, world: CoreWorld) -> None:
    await captive(session, world, CaptiveStatus.MARRIED_IN)


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


async def relocation_with_no_site(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Moving Town", world, world.regions[0])
    session.add(ReconstructionRow(settlement_entity_id=town.id, cause=next(iter(RebuildCause)), plan=RebuildPlan.RELOCATED, locked=[]))


async def regalia_of_no_realm(session: AsyncSession, world: CoreWorld) -> None:
    keeper = await settlement(session, "Treasury Town", world, world.regions[0])
    hoard = MuseumCollectionRow(keeper_entity_id=keeper.id, kind=next(iter(HoardKind)), locked=[])
    session.add(hoard)
    await session.flush()
    session.add(MuseumPieceRow(collection_id=hoard.id, kind=PieceKind.REGALIA, locked=[]))


async def free_city_with_no_charter(session: AsyncSession, world: CoreWorld) -> None:
    host = await settlement(session, "Open Gate", world, world.regions[0])
    runner = await mortal(session, "Runner", world, host.id)
    session.add(SanctuaryRow(fugitive_entity_id=runner.id, host_entity_id=host.id, kind=SanctuaryKind.FREE_CITY, fugitive_kind=FugitiveKind.RUNAWAY, locked=[]))


async def lock_no_one_can_make(session: AsyncSession, world: CoreWorld) -> None:
    vault = await entity(session, "Warded Vault", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SecurityRow(holder_entity_id=vault.id, lock=LockKind.WORKED, lock_quality=60, locked=[]))


async def lift_with_no_power(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Dry Wells", world, world.regions[0])
    session.add(WaterLiftRow(settlement_entity_id=town.id, device=WaterLift.ELECTRIC_PUMP, locked=[]))


async def aid_no_one_can_make(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lensless", world, world.regions[0])
    healer = await mortal(session, "Healer", world, town.id)
    session.add(AssistiveAidRow(holder_node_id=healer.id, kind=AssistiveAid.MICROSCOPE, locked=[]))


async def tongue(session: AsyncSession, world: CoreWorld, name: str) -> EntityRow:
    return await entity(session, name, EntityType.LANGUAGE, LanguageStats(), world_id=world.world.id)


async def revival_with_no_ancestor(session: AsyncSession, world: CoreWorld) -> None:
    revived = await tongue(session, world, "Old Speech")
    session.add(LanguageProfileRow(entity_id=revived.id, phonology=DEFAULT_PHONOLOGY, seed="Old Speech", stage=LanguageStage.REVIVED))


async def tongue_its_speakers_cannot_use(session: AsyncSession, world: CoreWorld) -> None:
    voiced = await tongue(session, world, "Loud Speech")
    session.add(LanguageProfileRow(entity_id=voiced.id, phonology=DEFAULT_PHONOLOGY, seed="Loud Speech", modality=LanguageModality.VOCAL))
    folk = await entity(session, "Mute Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    session.add(
        PeopleBiologyRow(
            people_entity_id=folk.id,
            maturity_years=15,
            adult_years=40,
            elder_years=60,
            fertility_pct=100,
            acclimatised=TemperatureBand.TEMPERATE,
            staple=CommodityKind.GRAIN,
            body_plan=BodyPlan.COLONIAL,
            traits=[],
            locked=[],
        )
    )
    await bond(session, folk.id, voiced.id, BondKind.SPEAKS)


async def electronic_record_unknown(session: AsyncSession, world: CoreWorld) -> None:
    work = await entity(session, "Lost Ledger", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(WrittenWorkRow(work_entity_id=work.id, medium=WritingMedium.ELECTRONIC, locked=[]))


async def route(session: AsyncSession, world: CoreWorld, name: str, **values: object) -> int:
    first = await settlement(session, f"{name} East", world, world.regions[0])
    second = await settlement(session, f"{name} West", world, world.regions[1])
    road = await entity(session, name, EntityType.TRADE_ROUTE, TradeRouteStats(), world_id=world.world.id, location_id=world.regions[0].id)
    base: dict[str, object] = {"mode": TradeMode.ROAD, "status": TradeRouteStatus.OPEN}
    session.add(
        TradeRouteProfileRow(
            route_entity_id=road.id, first_market_id=first.id, second_market_id=second.id, length=2, founded_epoch=1, locked=[], **(base | values)
        )
    )
    return road.id


async def realm_header_behind_its_record(session: AsyncSession, world: CoreWorld) -> None:
    crown = await entity(session, "Stale Crown", EntityType.POLITY, PolityStats(legitimacy=40, stability=16), world_id=world.world.id)
    session.add(
        PolityProfileRow(polity_entity_id=crown.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), legitimacy=30, stability=18)
    )


async def road_across_open_water(session: AsyncSession, world: CoreWorld) -> None:
    await route(session, world, "Road of Swell and Spray")
    for region in world.regions[:2]:
        session.add(
            RegionEnvironmentRow(
                entity_id=region.id,
                world_id=world.world.id,
                dominant_terrain=TerrainKind.SEA,
                elevation_mean=0,
                roughness=0,
                latitude=10,
                moisture=90,
                base_forest=0,
                forest_cover=0,
                base_wetland=0,
                wetland=0,
                river_class=RiverClass.NONE,
                coast_kind=CoastKind.NONE,
                soil=next(iter(SoilKind)),
                soil_fertility=0,
                soil_base=0,
                temperature=50,
                temperature_band=TemperatureBand.TEMPERATE,
                rainfall=50,
                seasonality=10,
                disease_load=0,
                magic_density=0,
                defensibility=10,
                locked=[],
            )
        )


async def seasonal_route_with_no_season(session: AsyncSession, world: CoreWorld) -> None:
    await route(session, world, "Snow Road", status=TradeRouteStatus.SEASONAL, closed_season=None)


async def ships_on_a_road(session: AsyncSession, world: CoreWorld) -> None:
    await route(session, world, "Dry Keel", carrier=CarrierKind.SEA)


async def positioning_with_no_network(session: AsyncSession, world: CoreWorld) -> None:
    hull = await entity(session, "Lone Hull", EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(NavigationKitRow(holder_entity_id=hull.id, aid=NavigationAid.POSITIONING, locked=[]))


async def material_with_no_source(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        WorldMaterialRow(
            world_id=world.world.id,
            origin=MaterialOrigin.DEAD_GOD,
            name="Unclaimed Bone",
            family=next(iter(MaterialFamily)),
            hardness=50,
            toughness=50,
            weight=50,
            edge=50,
            conductivity=50,
            sanctity=50,
            corruption=0,
            rarity=50,
            base_value=50,
            decay=5,
            created_epoch=0,
        )
    )


async def method_under_another_process(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Mixed Works", world, world.regions[0])
    method = next(iter(METHODS))
    other = next(process for process in ProcessKind if process is not METHODS[method].process)
    session.add(CommunityMethodRow(community_node_id=town.id, process=other, method=method, adopted_epoch=1, locked=[]))


async def account_of_nothing(session: AsyncSession, world: CoreWorld) -> None:
    teller = await mortal(session, "Teller", world, world.regions[0].id)
    session.add(AccountRow(holder_entity_id=teller.id, kind=next(iter(AccountKind)), locked=[]))


async def law_sparing_no_named_kind(session: AsyncSession, world: CoreWorld) -> None:
    law = await entity(session, "The Long Dark", EntityType.NATURAL_LAW, NaturalLawStats(), world_id=world.world.id)
    session.add(NaturalLawProfileRow(law_entity_id=law.id, effect=NaturalLaw.BOUNTY, exception=LawException.NAMED_KIND, exempt_kind_entity_id=None, locked=[]))


async def people_breathing_against_its_chemistry(session: AsyncSession, world: CoreWorld) -> None:
    biology, _ = await ensure_profiles(session, Rules(), world.people, None)
    biology.biochemistry, biology.air = Biochemistry.CARBON_WATER, AirNeed.AMMONIA


async def clouds_on_a_solid_world(session: AsyncSession, world: CoreWorld) -> None:
    life = await session.get(WorldLifeRow, world.world.id)
    if life is None:
        life = WorldLifeRow(world_id=world.world.id, locked=[])
        session.add(life)
    life.environments = [LifeEnvironment.CLOUD.value]


async def fragment_with_no_broken_moon(session: AsyncSession, world: CoreWorld) -> None:
    session.add(ImpactEventRow(world_id=world.world.id, body=ImpactBody.MOON_FRAGMENT, size=10, due_epoch=5, outcome=ImpactOutcome.PENDING, text="", locked=[]))


async def end_naming_a_source_its_cause_lacks(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        WorldEndRow(
            world_id=world.world.id,
            state=WorldEnd.FORGOTTEN,
            cause=WorldEndCause.OBLIVION,
            former_type=world.world.world_type,
            source_node_id=world.son.id,
            locked=[],
        )
    )


async def heavy_world_banded_light(session: AsyncSession, world: CoreWorld) -> None:
    physics = await session.get(WorldPhysicsRow, world.world.id)
    if physics is None:
        physics = WorldPhysicsRow(world_id=world.world.id, locked=[])
        session.add(physics)
    physics.gravity_g = 4.0
    world.world.gravity = Gravity.LOW


BREAKERS: dict[str, Breaker] = {
    "relocation_names_site": relocation_with_no_site,
    "regalia_names_polity": regalia_of_no_realm,
    "free_city_has_charter": free_city_with_no_charter,
    "lock_technique_known": lock_no_one_can_make,
    "lift_energy_known": lift_with_no_power,
    "aid_technique_known": aid_no_one_can_make,
    "revived_tongue_ancestor": revival_with_no_ancestor,
    "tongue_modality_heard": tongue_its_speakers_cannot_use,
    "electronic_record_technique": electronic_record_unknown,
    "seasonal_route_season": seasonal_route_with_no_season,
    "route_carrier_medium": ships_on_a_road,
    "positioning_needs_network": positioning_with_no_network,
    "material_origin_source": material_with_no_source,
    "method_in_its_process": method_under_another_process,
    "account_tells_something": account_of_nothing,
    "crisis_mediator_named": crisis_settled_by_no_one,
    "disputed_claim_contender": dispute_with_no_contender,
    "service_names_task": service_with_no_task,
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
    "crew_station_fits": crew_at_a_station_no_section_calls_for,
    "mortal_slayer_named": slayer_wound_with_no_mortal,
    "penance_names_deed": penance_with_no_deed,
    "defector_names_former_god": defector_with_no_former_god,
    "being_scale_reach": regional_being_nowhere,
    "rift_cause_source": weapon_rift_with_no_source,
    "parole_names_oath": parole_with_no_oath,
    "ordnance_names_remnant": ordnance_with_no_remnant,
    "expedition_ground_fits": expedition_into_a_dimension_with_no_rift,
    "married_in_names_union": joining_with_no_spouse,
    "spirit_fits_place": river_spirit_counted_a_mountain,
    "deep_positions_valid": settlement_in_no_cell,
    "passage_state_fits": passage_dug_but_never_open,
    "passage_ends_exist": passage_into_no_cell,
    "vengeance_names_target": vengeance_against_no_one,
    "luck_sign_marked": luck_in_no_creature,
    "rebirth_kind_named": reborn_as_no_kind,
    "contest_stake_named": contest_for_land_staking_a_person,
    "hand_over_names_person": hand_over_of_no_one,
    "law_named_kind": law_sparing_no_named_kind,
    "air_fits_biochemistry": people_breathing_against_its_chemistry,
    "life_place_fits_world": clouds_on_a_solid_world,
    "fall_has_source": fragment_with_no_broken_moon,
    "world_end_source": end_naming_a_source_its_cause_lacks,
    "gravity_fits_mass": heavy_world_banded_light,
    "union_names_spouse": union_with_no_spouse,
    "adoption_names_adopter": adoption_by_no_one,
    "spy_institution_in_target": mole_placed_outside_the_target,
    "siege_flood_has_water": flood_with_no_water,
    "settle_mode_fits": settlement_submerged_on_dry_land,
    "battle_ground_fits": battle_in_open_space_on_a_land_world,
    "unit_honour_names_place": honour_won_nowhere,
    "linked_rite_has_link": linked_rite_with_no_link,
    "rite_condition_named": rite_until_nothing,
    "true_name_link_known": true_name_link_unknown,
    "timed_order_has_times": timed_order_with_no_times,
    "true_name_command_named": nameless_made_thing_held_by_name,
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
    "birth_at_first_sight": birth_after_its_first_record,
    "age_since_birth": child_older_than_its_years,
    "judgment_at_epoch_close": verdict_inside_its_age,
    "rite_after_death": wake_before_the_death,
    "witness_born": witness_before_birth,
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
    "mood_told_of_its_own": household_mood_told_as_a_place,
    "mortal_dwells_in_a_place": mortal_standing_inside_a_guild,
    "grown_out_of_childhood": grown_one_still_called_a_child,
    "route_mode_fits_water": road_across_open_water,
    "polity_stats_follow_record": realm_header_behind_its_record,
    "collection_title_one_standing": funeral_named_after_its_host,
    "collection_title_current_names": plague_named_before_its_naming,
    "title_named_plainly": headship_named_by_its_label,
    "season_names_distinct": two_seasons_one_name,
    "tradition_slot_fits_kind": vigil_kept_at_harvest,
    "strain_named_once": strain_named_twice,
    "injury_dated_in_its_time": wound_dated_outside_its_epoch,
    "tenure_within_presence": seat_held_before_its_holder_came,
    "law_named_once": law_named_twice,
    "birth_sign_by_age": grown_mortal_signed_at_arrival,
    "generations_within_people": generations_outnumber_their_town,
    "son_essence_within_cap": son_overfilled,
    "son_knows_its_audience": son_met_the_creator,
    "son_bond_described_plainly": bond_note_overwritten,
    "god_grudge_names_both": grudge_with_no_names,
    "son_covenant_between_friends": covenant_of_enemies,
    "divine_mind_counts_its_epochs": divine_mind_left_behind,
    "star_lit_by_its_kind": star_left_dim,
    "remembrance_names_its_past": remembrance_of_no_one,
    "star_clock_follows_its_age": star_clock_set_from_birth,
    "adult_born_before_first_sight": grown_mortal_born_at_first_sight,
    "home_on_its_lived_orbit": planet_moved_by_an_old_repair,
    "peopled_world_habitable": planet_far_from_its_star,
    "rebuild_of_a_standing_town": rebuilding_a_ruin,
    "dead_without_health": dead_still_hale,
    "army_led_by_the_living": host_led_by_the_dead,
    "ruin_without_people": ruin_still_peopled,
    "war_named_by_its_parties": war_titled_after_strangers,
    "rite_filed_under_its_dead": mourning_under_another_dead,
    "occasion_holds_one_occasion": two_duels_in_one_history,
    "league_named_with_article": league_named_bare,
    "offshoot_named_after_a_person": offshoot_named_after_a_clique,
    "plague_named_by_its_sickness": plague_named_after_its_carrier,
    "memory_cause_names_its_subject": memory_of_a_stranger_happening,
    "incident_facts_declared": fact_the_kind_no_longer_tells,
    "tradition_kind_fits_subtype": mourning_kept_as_festival,
    "untimely_keeping_told": kept_after_its_time_did_not_come,
    "derived_names_follow": tribute_named_for_an_old_name,
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
