from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.agrarian import CommonsRow, GameReserveRow, ReconstructionRow
from aerona.db.tables.arcana import LawUpkeepRow, VisStockRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.collective import AccountRow, StoryletRunRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionRow, PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow, LegendProfileRow, RiteProfileRow
from aerona.db.tables.cycles import DivineDebtRow, GiftRow, LongPlanRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.divine import DivineWoundRow, NaturalLawProfileRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.dominion import DivineCreatureRow, DominionRow, MagicSiteRow
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesUseRow
from aerona.db.tables.economy import MarketPriceRow, TradeRouteProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow, WorldSeasonRow
from aerona.db.tables.estates import EstateProfileRow
from aerona.db.tables.evolution import CarrierRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.intrigue import HookRow, SecretRow, TrueNameRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import LegalSystemRow, OutlawRow, PrisonerRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.mythic import CosmicOfficeRow, GeasRow, ServitorRow
from aerona.db.tables.operations import EchelonRow, ExpeditionMemberRow, ExpeditionRow, TheatreRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow, TreatyProfileRow
from aerona.db.tables.regime import CoalitionMemberRow, ExaminationRow, SchoolLineageRow, SchoolMemberRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.renown import ReputationRow
from aerona.db.tables.sacred import DivinationSystemRow, GeniusLocusRow, MysticRow, PetitionRow, SpiritOfficeRow, TheodicyCrisisRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRelationRow, SonRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow
from aerona.db.tables.titles import DeJureLinkRow, TitleProfileRow
from aerona.db.tables.urban import ConvoyRow, OrderLawRow, TurfRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.agrarian import CommonsKind, RebuildCause
from aerona.domain.enums.arcana import LawSource, SpellForm
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.collective import AccountKind, StoryletId, StoryletStatus
from aerona.domain.enums.cosmography import BeingKind, BeingScale, DimensionKind, PhenomenonCause, PhenomenonKind, RiftCause, RiftState
from aerona.domain.enums.culture import LegendArchetype, MagicSchool, Technique
from aerona.domain.enums.cycles import GiftState, LongPlanKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.disease import ClimateAffinity, DiseaseVector
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb, DivineWoundKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import MagicSiteKind
from aerona.domain.enums.ecology import AnimalRole, Diet, DomesticationStage, SpeciesClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import CivilizationTier, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.intrigue import HookSource, HookStrength, IntrigueSecret
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.law_depth import LegalSystem
from aerona.domain.enums.mind import ActKind, SkillKind, SkillSource, ValueAxis, ValueHolder
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.mythic import CosmicOffice, GeasMode, OfficeChoice, ServitorRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.operations import EchelonLevel, ExpeditionRole
from aerona.domain.enums.physics import ImpactBody, ImpactOutcome
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.sacred import BureauRank, DivinationKind, GeniusLocusKind, MysticState, PetitionKind, TheodicyCause
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.statecraft import CrisisDemand
from aerona.domain.enums.structure import ConstructionStatus, StructureKind
from aerona.domain.enums.titles import TitleTier
from aerona.domain.enums.tongues import WordRegister
from aerona.domain.enums.urban import ConvoyStatus, OrderLaw
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import (
    ArmyStats,
    BeastStats,
    CosmicBeingStats,
    DiseaseStats,
    FactionStats,
    HouseStats,
    LanguageStats,
    LegendStats,
    MortalStats,
    NaturalLawStats,
    PhenomenonStats,
    PolityStats,
    SpiritStats,
    StructureStats,
    TitleStats,
    TradeRouteStats,
)
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.economy.stocks import goods_of
from aerona.engine.households.formation import found_household
from aerona.engine.mind.book import write_values
from aerona.engine.phases.environment import environment_survey
from aerona.engine.phases.physics import settle_heavens
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.services.war import open_war, take_captive
from aerona.engine.tongues.modality import own_tongue
from aerona.rules.registry import Rules
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, add_world, connect, make_entity

EPOCH = 3


async def surveyed(session: AsyncSession, _realm: Realm) -> Ids:
    await session.flush()
    context = await manual_context(session, "survey")
    await refresh_world_maps(session, context.rules, EPOCH)
    await environment_survey(context)
    return {}


async def death_son(session: AsyncSession, realm: Realm) -> Ids:
    son = await session.get(SonRow, realm.son_id)
    assert son is not None
    son.domain_secondary = Domain.DEATH
    return await spirit(session, realm)


async def second_mortal(session: AsyncSession, realm: Realm) -> Ids:
    stats = MortalStats(hp=40, strength=30, agility=30, intellect=30, charisma=30, age=12, lifespan=70)
    other = await make_entity(session, "Oren Vale", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=stats)
    return {"mortal": other.id}


async def second_settlement(session: AsyncSession, realm: Realm) -> Ids:
    town = await make_entity(session, "Lowmere", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    return {"settlement": town.id}


async def second_region(session: AsyncSession, realm: Realm) -> Ids:
    land = await make_entity(session, "Greyfold", EntityType.REGION, world_id=realm.cosmos.world_id)
    return {"region": land.id}


async def spirit(session: AsyncSession, realm: Realm) -> Ids:
    being = await make_entity(session, "Lantern Wisp", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    return {"spirit": being.id}


async def faithful_spirit(session: AsyncSession, realm: Realm) -> Ids:
    ids = await spirit(session, realm)
    await connect(session, ids["spirit"], realm.son_id, BondKind.WORSHIPS)
    return ids


async def plant(session: AsyncSession, realm: Realm) -> Ids:
    crop = await make_entity(session, "Field Sedge", EntityType.SPECIES, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    session.add(SpeciesProfileRow(species_entity_id=crop.id, species_class=SpeciesClass.PLANT, body_plan=BodyPlan.ARBOREAL, diet=Diet.PHOTOSYNTHETIC))
    session.add(PlantProfileRow(species_entity_id=crop.id))
    return {"plant": crop.id}


async def pet_herd(session: AsyncSession, realm: Realm) -> Ids:
    mortal = await session.get(EntityRow, realm.mortal_id)
    assert mortal is not None and mortal.location_id is not None
    session.add(SpeciesUseRow(species_entity_id=realm.species_id, use=AnimalRole.COMPANION))
    session.add(
        HerdRow(
            community_entity_id=mortal.location_id, species_entity_id=realm.species_id, head=12, stage=DomesticationStage.HERDED, since_epoch=1, fed_epochs=0
        )
    )
    return {}


async def herd_handler(session: AsyncSession, realm: Realm) -> Ids:
    mortal = await session.get(EntityRow, realm.mortal_id)
    assert mortal is not None and mortal.location_id is not None
    session.add(SkillRow(holder_node_id=mortal.id, skill=SkillKind.BEAST_HANDLING, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    session.add(
        HerdRow(
            community_entity_id=mortal.location_id, species_entity_id=realm.species_id, head=20, stage=DomesticationStage.HERDED, since_epoch=1, fed_epochs=0
        )
    )
    return {}


async def item(session: AsyncSession, realm: Realm) -> Ids:
    thing = await make_entity(session, "Ledger Lamp", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    return {"item": thing.id}


async def outsider(session: AsyncSession, realm: Realm) -> Ids:
    being = await make_entity(session, "The Far Listener", EntityType.OUTER_BEING, world_id=realm.cosmos.world_id)
    return {"outsider": being.id}


async def dead_star(session: AsyncSession, realm: Realm) -> Ids:
    world = await session.get(WorldRow, realm.cosmos.world_id)
    assert world is not None and world.star_id is not None
    star = await session.get(StarRow, world.star_id)
    assert star is not None
    star.star_type = StarType.DEAD_STAR
    return {"star": star.id}


async def home_star(session: AsyncSession, realm: Realm) -> Ids:
    world = await session.get(WorldRow, realm.cosmos.world_id)
    assert world is not None and world.star_id is not None
    return {"star": world.star_id}


async def dead_sibling(session: AsyncSession, realm: Realm) -> Ids:
    son = await session.get(SonRow, realm.sibling_id)
    assert son is not None
    son.status = SonStatus.DEAD
    son.death_epoch = EPOCH - 1
    return {}


async def worships_dead_sibling(session: AsyncSession, realm: Realm) -> Ids:
    await dead_sibling(session, realm)
    await connect(session, realm.people_id, realm.sibling_id, BondKind.WORSHIPS)
    return {}


async def sky_son(session: AsyncSession, realm: Realm) -> Ids:
    son = await session.get(SonRow, realm.son_id)
    assert son is not None
    son.domain_primary = Domain.SKY
    son.domain_secondary = Domain.STORM
    return {}


async def friendly_sibling(session: AsyncSession, realm: Realm) -> Ids:
    first, second = sorted((realm.son_id, realm.sibling_id))
    session.add(SonRelationRow(son_a_id=first, son_b_id=second, value=60))
    return {}


async def travel_resource(session: AsyncSession, _realm: Realm) -> Ids:
    cosmos = await session.scalar(select(CosmosRow))
    assert cosmos is not None
    cosmos.travel_resource = TravelResource(name="Lampdust", rule="Carries ships between worlds.")
    return {}


async def leaking_world(session: AsyncSession, realm: Realm) -> Ids:
    world = await session.get(WorldRow, realm.cosmos.world_id)
    assert world is not None
    world.leakage = 40
    return {}


async def ley_line(session: AsyncSession, realm: Realm) -> Ids:
    ids = await second_region(session, realm)
    line = LeyLineRow(world_id=realm.cosmos.world_id, region_a_id=realm.cosmos.region_id, region_b_id=ids["region"], strength=50, formed_epoch=1)
    session.add(line)
    await session.flush()
    return {"line": line.id}


async def house(session: AsyncSession, realm: Realm) -> Ids:
    entity = await make_entity(session, "House Morrow", EntityType.HOUSE, world_id=realm.cosmos.world_id, stats=HouseStats())
    session.add(HouseProfileRow(house_entity_id=entity.id, founder_entity_id=realm.mortal_id, head_entity_id=realm.mortal_id, divine_son_id=realm.son_id))
    await connect(session, realm.mortal_id, entity.id, BondKind.MEMBER_OF)
    return {"house": entity.id}


async def ruler(session: AsyncSession, realm: Realm) -> Ids:
    polity = await make_entity(session, "Vale Crown", EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=realm.mortal_id))
    await connect(session, realm.settlement_id, polity.id, BondKind.MEMBER_OF)
    return {"polity": polity.id}


async def advanced(session: AsyncSession, realm: Realm) -> Ids:
    for entity_id in (realm.people_id, realm.settlement_id):
        row = await session.get(EntityRow, entity_id)
        assert row is not None
        row.civ_tier = int(max(CivilizationTier))
    return {}


async def knows(session: AsyncSession, realm: Realm, branch: KnowledgeBranch, name: str) -> Ids:
    lore = await make_entity(session, name, EntityType.KNOWLEDGE, world_id=realm.cosmos.world_id, knowledge_branch=branch)
    await connect(session, realm.mortal_id, lore.id, BondKind.KNOWS)
    return {"lore": lore.id}


async def knows_magic(session: AsyncSession, realm: Realm) -> Ids:
    return await knows(session, realm, KnowledgeBranch.MAGIC, "Lampcraft")


async def knows_biomancy(session: AsyncSession, realm: Realm) -> Ids:
    return await knows(session, realm, KnowledgeBranch.BIOMANCY, "Grafting")


async def captive_of_outlaws(session: AsyncSession, realm: Realm) -> Ids:
    captor = await session.get(EntityRow, realm.faction_id)
    captive = await session.get(EntityRow, realm.mortal_id)
    assert captor is not None and captive is not None
    await take_captive(await manual_context(session, "capture"), captor, captive, None, description="taken on the road", home_id=realm.settlement_id)
    return {}


async def ruin(session: AsyncSession, realm: Realm) -> Ids:
    site = await make_entity(session, "Old Waystation", EntityType.PLACE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    await EntityRepository(session).add_flag(site.id, EntityFlag.RUIN)
    return {"ruin": site.id}


async def technique(session: AsyncSession, realm: Realm) -> Ids:
    session.add(HolderTechniqueRow(holder_entity_id=realm.mortal_id, technique=next(iter(Technique))))
    return {}


async def knows_written_law(session: AsyncSession, realm: Realm) -> Ids:
    session.add(HolderTechniqueRow(holder_entity_id=realm.mortal_id, technique=Technique.WRITTEN_LAW))
    await session.flush()
    return {}


async def market(session: AsyncSession, realm: Realm) -> Ids:
    session.add(MarketPriceRow(market_entity_id=realm.people_id, commodity=CommodityKind.GRAIN, epoch=EPOCH, price=10, supply=500, demand=100))
    session.add(WorkshopRow(community_entity_id=realm.people_id, kind=WorkshopKind.MARKET, built_epoch=1, owner_node_id=realm.faction_id))
    await goods_of(session, EPOCH).add(realm.people_id, CommodityKind.GRAIN, 500, GoodsFlow.HARVEST)
    return {}


async def owns_resource(session: AsyncSession, realm: Realm) -> Ids:
    await connect(session, realm.people_id, realm.resource_id, BondKind.OWNS)
    return {}


async def second_species(session: AsyncSession, realm: Realm) -> Ids:
    beast = await make_entity(session, "Ridge Hare", EntityType.SPECIES, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    return {"species": beast.id}


async def folk_knows(session: AsyncSession, realm: Realm, branch: KnowledgeBranch, name: str) -> Ids:
    lore = await make_entity(session, name, EntityType.KNOWLEDGE, world_id=realm.cosmos.world_id, knowledge_branch=branch)
    await connect(session, realm.people_id, lore.id, BondKind.KNOWS)
    return {"lore": lore.id}


async def lawgivers(session: AsyncSession, realm: Realm) -> Ids:
    session.add(
        HolderLevelRow(
            holder_entity_id=realm.people_id, branch=KnowledgeBranch.CIVICS, level=1, practitioners=1, progress=0, secret=False, updated_epoch=1, locked=[]
        )
    )
    await session.flush()
    return {}


async def seafarers(session: AsyncSession, realm: Realm) -> Ids:
    await advanced(session, realm)
    await folk_knows(session, realm, KnowledgeBranch.SHIPBUILDING, "Hullcraft")
    return await folk_knows(session, realm, KnowledgeBranch.SKY_NAVIGATION, "Starcharts")


async def last_war(session: AsyncSession, _realm: Realm, ids: Ids) -> Ids:
    war = await session.scalar(select(WarRow.id).order_by(WarRow.id.desc()).limit(1))
    army = await session.scalar(select(ArmyRow.entity_id).order_by(ArmyRow.entity_id.desc()).limit(1))
    return {**ids, **({"war": war} if war is not None else {}), **({"army": army} if army is not None else {})}


async def last_treaty(session: AsyncSession, _realm: Realm, ids: Ids) -> Ids:
    treaty = await session.scalar(select(TreatyProfileRow.treaty_entity_id).order_by(TreatyProfileRow.treaty_entity_id.desc()).limit(1))
    assert treaty is not None
    return {**ids, "treaty": treaty}


async def last_rite(session: AsyncSession, _realm: Realm, ids: Ids) -> Ids:
    rite = await session.scalar(select(RiteProfileRow.rite_entity_id).order_by(RiteProfileRow.rite_entity_id.desc()).limit(1))
    assert rite is not None
    return {**ids, "rite": rite}


async def last_trade_route(session: AsyncSession, _realm: Realm, ids: Ids) -> Ids:
    route = await session.scalar(select(TradeRouteProfileRow.route_entity_id).order_by(TradeRouteProfileRow.route_entity_id.desc()).limit(1))
    assert route is not None
    return {**ids, "trade_route": route}


def created(key: str) -> Any:
    def pick(_realm: Realm, ids: Ids) -> int:
        return ids[key]

    return pick


async def seasons(session: AsyncSession, realm: Realm) -> Ids:
    await surveyed(session, realm)
    await sky_son(session, realm)
    count = len(list(await session.scalars(select(WorldSeasonRow.position).where(WorldSeasonRow.world_id == realm.cosmos.world_id))))
    return {"seasons": count}


async def well_housed(session: AsyncSession, realm: Realm) -> Ids:
    head = await session.get(EntityRow, realm.mortal_id)
    assert head is not None
    home = await found_household(await manual_context(session, "household"), head)
    home.wealth = 200
    return {"household": home.id}


async def named_spirit(session: AsyncSession, realm: Realm) -> Ids:
    found = await spirit(session, realm)
    session.add(TrueNameRow(bearer_node_id=found["spirit"], name="Ashvael", known_by=[found["spirit"]], since_epoch=EPOCH, locked=[]))
    await session.flush()
    return found


async def hooked_mortal(session: AsyncSession, realm: Realm) -> Ids:
    found = await second_mortal(session, realm)
    session.add(
        HookRow(holder_node_id=realm.mortal_id, target_node_id=found["mortal"], strength=HookStrength.STRONG, source=HookSource.SECRET, created_epoch=EPOCH)
    )
    await session.flush()
    return found


async def claimable_title(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(PolityTerritoryRow(polity_entity_id=found["polity"], region_entity_id=realm.cosmos.region_id, control=80, locked=[]))
    title = await make_entity(session, "Old Crown of the Vale", EntityType.TITLE, world_id=realm.cosmos.world_id, stats=TitleStats())
    session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleTier.REGIONAL, regalia=[], drift={}, locked=[]))
    session.add(DeJureLinkRow(title_entity_id=title.id, member_entity_id=realm.cosmos.region_id, since_epoch=EPOCH))
    await session.flush()
    return {**found, "title": title.id}


async def realm_estate(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    estate = await make_entity(session, "Lords of the Vale", EntityType.FACTION, world_id=realm.cosmos.world_id, stats=FactionStats())
    session.add(FactionProfileRow(faction_entity_id=estate.id, kind=FactionKind.ESTATE, home_entity_id=realm.settlement_id, influence_over={}, locked=[]))
    session.add(
        EstateProfileRow(faction_entity_id=estate.id, polity_entity_id=found["polity"], social_class=SocialClass.NOBLE, loyalty=30, influence=30, locked=[])
    )
    await session.flush()
    return {**found, "estate": estate.id}


async def other_realm(session: AsyncSession, realm: Realm, name: str) -> int:
    polity = await make_entity(session, name, EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), treasury=200))
    await session.flush()
    return polity.id


async def rival_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    return {**found, "rival": await other_realm(session, realm, "Marsh Crown")}


async def foreign_crisis(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    first = await other_realm(session, realm, "Reed Throne")
    second = await other_realm(session, realm, "Fen Throne")
    crisis = CrisisRow(demander_entity_id=first, target_entity_id=second, demand=CrisisDemand.PAY, amount=20, opened_epoch=EPOCH, locked=[])
    session.add(crisis)
    await session.flush()
    return {**found, "crisis": crisis.id}


async def council_office(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    other = await second_mortal(session, realm)
    office = OfficeRow(polity_entity_id=found["polity"], kind=OfficeKind.MARSHAL, holder_entity_id=other["mortal"])
    session.add(office)
    await session.flush()
    return {**found, "office": office.id}


async def pact_friend(session: AsyncSession, realm: Realm) -> Ids:
    session.add(RelationshipRow(holder_node_id=realm.god_id, subject_node_id=realm.son_id, friendship=80, kinds=[], since_epoch=1, last_epoch=1, locked=[]))
    return {}


async def wounded(session: AsyncSession, realm: Realm) -> Ids:
    wound = DivineWoundRow(god_node_id=realm.son_id, kind=DivineWoundKind.STOLEN_NAME, severity=40, healed=0, cause=WoundCause.DUEL, epoch=1, locked=[])
    session.add(wound)
    await session.flush()
    return {"wound": wound.id}


async def heavens(session: AsyncSession, realm: Realm) -> Ids:
    rules = Rules()
    await ensure_ladder(session, rules)
    plane = await create_dimension(session, rules, DimensionDraft("Astral Reach", DimensionKind.ASTRAL, EPOCH))
    cosmography = await Cosmography.load(session)
    placement = cosmography.place_world_id(realm.cosmos.world_id)
    assert placement.galaxy is not None and placement.dimension is not None
    return {"dimension": plane.id, "galaxy": placement.galaxy.id, "prime": placement.dimension.id}


async def ruled_law(session: AsyncSession, realm: Realm) -> Ids:
    ids = await heavens(session, realm)
    dimension = await session.get(DimensionRow, ids["prime"])
    assert dimension is not None
    dimension.ruler_node_id = realm.son_id
    law = await make_entity(
        session, "The Long Summer", EntityType.NATURAL_LAW, world_id=realm.cosmos.world_id, stats=NaturalLawStats(), natural_law=NaturalLaw.BOUNTY
    )
    return {**ids, "law": law.id}


async def two_stars(session: AsyncSession, realm: Realm) -> Ids:
    stars = [
        StarRow(name=name, star_type=StarType.YELLOW_DWARF, brightness=50, x=x, y=0.0, created_epoch=1, patron_son_id=realm.son_id)
        for name, x in (("Twin Dawn", 10.0), ("Twin Dusk", 14.0))
    ]
    session.add_all(stars)
    await session.flush()
    return {"first_star": stars[0].id, "second_star": stars[1].id}


async def dead_creation(session: AsyncSession, realm: Realm) -> Ids:
    stats = MortalStats(hp=0, strength=30, agility=30, intellect=30, charisma=30, age=60, lifespan=70)
    mortal = await make_entity(
        session,
        "Ansel Rook",
        EntityType.MORTAL,
        world_id=realm.cosmos.world_id,
        location_id=realm.settlement_id,
        stats=stats,
        origin=EntityOrigin.SON,
        creator_son_id=realm.son_id,
    )
    mortal.status = EntityStatus.DEAD
    mortal.end_epoch = EPOCH - 1
    return {"dead": mortal.id}


async def rifted(session: AsyncSession, realm: Realm) -> Ids:
    ids = await heavens(session, realm)
    rift = RiftRow(
        world_id=realm.cosmos.world_id,
        region_entity_id=realm.cosmos.region_id,
        dimension_id=ids["dimension"],
        size=30,
        stability=50,
        state=RiftState.OPEN,
        cause=RiftCause.GOD,
        opened_epoch=EPOCH,
        locked=[],
    )
    session.add(rift)
    await session.flush()
    return {**ids, "rift": rift.id}


async def cosmic_being(session: AsyncSession, realm: Realm) -> Ids:
    being = await make_entity(
        session,
        "The Long Watcher",
        EntityType.COSMIC_BEING,
        world_id=realm.cosmos.world_id,
        location_id=realm.cosmos.region_id,
        stats=CosmicBeingStats(size=50),
    )
    session.add(CosmicBeingProfileRow(entity_id=being.id, being_kind=BeingKind.VOID_KEEPER, scale=BeingScale.GALAXY, might=50, locked=[]))
    await session.flush()
    return {"being": being.id}


async def phenomenon(session: AsyncSession, realm: Realm) -> Ids:
    found = await make_entity(
        session, "The Standing Fog", EntityType.PHENOMENON, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=PhenomenonStats(danger=20)
    )
    session.add(
        PhenomenonProfileRow(entity_id=found.id, kind=PhenomenonKind.MOVING_FOG, intensity=50, cause=PhenomenonCause.DIVINE, formed_epoch=EPOCH, locked=[])
    )
    session.add(PhenomenonFootprintRow(phenomenon_entity_id=found.id, region_entity_id=realm.cosmos.region_id, intensity=50))
    await session.flush()
    return {"phenomenon": found.id}


async def falling_body(session: AsyncSession, realm: Realm) -> Ids:
    impact = ImpactEventRow(
        world_id=realm.cosmos.world_id,
        region_entity_id=realm.cosmos.region_id,
        body=ImpactBody.ASTEROID,
        size=40,
        due_epoch=EPOCH + 2,
        outcome=ImpactOutcome.PENDING,
        winter_epochs=0,
        text="",
        locked=[],
    )
    session.add(impact)
    await session.flush()
    return {"impact": impact.id}


async def near_moon(session: AsyncSession, realm: Realm) -> Ids:
    moon = await add_world(session, "Pebble")
    moon.parent_world_id, moon.star_id, moon.orbit = realm.cosmos.world_id, None, 0.2
    await session.flush()
    return {"moon": moon.id}


async def world_body(session: AsyncSession, _realm: Realm) -> Ids:
    await settle_heavens(session, Rules())
    return {}


async def lair_site(session: AsyncSession, realm: Realm) -> Ids:
    site = await make_entity(session, "Hollow Den", EntityType.PLACE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    session.add(PlaceProfileRow(entity_id=site.id, kind=PlaceKind.LAIR, locked=[]))
    await session.flush()
    return {"site": site.id}


async def dig_ready(session: AsyncSession, realm: Realm) -> Ids:
    site = await make_entity(session, "Old Mound", EntityType.PLACE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    session.add(PlaceProfileRow(entity_id=site.id, kind=PlaceKind.RUIN, locked=[]))
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.LORE, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {"site": site.id}


async def rich_son(session: AsyncSession, realm: Realm) -> Ids:
    son = await session.get(SonRow, realm.son_id)
    assert son is not None
    son.essence = max(son.essence, 1000)
    await session.flush()
    return {}


async def son_creature(session: AsyncSession, realm: Realm) -> Ids:
    await rich_son(session, realm)
    beast = await make_entity(session, "Grey Warden", EntityType.BEAST, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=BeastStats())
    session.add(DivineCreatureRow(creature_entity_id=beast.id, god_node_id=realm.son_id, weights={}, locked=[]))
    await session.flush()
    return {"creature": beast.id}


async def hidden_magic(session: AsyncSession, realm: Realm) -> Ids:
    rite = await session.scalar(select(RiteProfileRow).order_by(RiteProfileRow.rite_entity_id).limit(1))
    school = rite.school if rite is not None else MagicSchool.LIFE
    session.add(MagicSiteRow(place_entity_id=realm.cosmos.place_id, kind=MagicSiteKind.SOURCE, school=school, strength=50, locked=[]))
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.SPELLCRAFT, level=90, peak=90, last_used_epoch=1, source=SkillSource.PRACTICE))
    if rite is not None:
        session.add(
            SkillRow(
                holder_node_id=realm.mortal_id,
                skill=SkillKind.SPELLCRAFT,
                subject_node_id=rite.rite_entity_id,
                level=90,
                peak=90,
                last_used_epoch=1,
                source=SkillSource.PRACTICE,
            )
        )
    await session.flush()
    return {}


async def son_servitor(session: AsyncSession, realm: Realm) -> Ids:
    await rich_son(session, realm)
    spirit = await make_entity(session, "Watcher", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.place_id, stats=SpiritStats())
    session.add(ServitorRow(spirit_entity_id=spirit.id, god_node_id=realm.son_id, role=ServitorRole.MESSENGER, loyalty=80, locked=[]))
    await session.flush()
    return {"servitor": spirit.id}


async def son_geas(session: AsyncSession, realm: Realm) -> Ids:
    row = GeasRow(bearer_entity_id=realm.mortal_id, layer_node_id=realm.son_id, mode=GeasMode.TABOO, act=ActKind.THEFT, locked=[])
    session.add(row)
    await session.flush()
    return {"geas": row.id}


async def son_legend(session: AsyncSession, realm: Realm) -> Ids:
    legend = await make_entity(session, "The First Walk", EntityType.LEGEND, world_id=realm.cosmos.world_id, stats=LegendStats())
    session.add(
        LegendProfileRow(
            legend_entity_id=legend.id,
            archetype=LegendArchetype.HERO_QUEST,
            credence=70,
            subject_node_id=realm.son_id,
            tellers=[realm.people_id, realm.settlement_id],
            locked=[],
        )
    )
    await session.flush()
    return {"legend": legend.id}


async def son_office(session: AsyncSession, realm: Realm) -> Ids:
    session.add(CosmicOfficeRow(office=CosmicOffice.DEAD, holder_node_id=realm.son_id, chosen_by=OfficeChoice.CREATOR, neglect=0, duty=0, locked=[]))
    await session.flush()
    return {}


async def son_enchantment(session: AsyncSession, realm: Realm) -> Ids:
    law = await make_entity(session, "The Long Calm", EntityType.NATURAL_LAW, world_id=realm.cosmos.world_id, stats=NaturalLawStats())
    session.add(NaturalLawProfileRow(law_entity_id=law.id, effect=NaturalLaw.BOUNTY, world_id=realm.cosmos.world_id, author_node_id=realm.son_id, locked=[]))
    session.add(LawUpkeepRow(law_entity_id=law.id, caster_node_id=realm.son_id, source=LawSource.ENCHANTMENT, essence_upkeep=1, locked=[]))
    await session.flush()
    return {"law": law.id}


async def quester(session: AsyncSession, realm: Realm) -> Ids:
    found = await son_legend(session, realm)
    for community_id in (realm.people_id, realm.settlement_id):
        community = await session.get(EntityRow, community_id)
        if community is not None:
            set_stats(community, piety=90)
    session.add(
        ReputationRow(subject_node_id=realm.mortal_id, community_node_id=realm.settlement_id, axis=ReputationAxis.HEROISM, value=90, heard_epoch=1, locked=[])
    )
    await session.flush()
    return found


async def mortal_vis(session: AsyncSession, realm: Realm) -> Ids:
    session.add(VisStockRow(holder_node_id=realm.mortal_id, form=SpellForm.BODY, amount=20, locked=[]))
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.SPELLCRAFT, level=90, peak=90, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {}


async def tongue_words(session: AsyncSession, realm: Realm) -> Ids:
    for word, meaning in (("Alvo", "river"), ("Brena", "stone"), ("Corim", "field")):
        session.add(
            LexemeRow(language_entity_id=realm.language_id, word=word, meaning=meaning, added_by_kind=ActorKind.ENGINE, epoch=1, register=WordRegister.COMMON)
        )
    await session.flush()
    return {}


async def dead_script(session: AsyncSession, realm: Realm) -> Ids:
    dead = await make_entity(session, "Old Speech", EntityType.LANGUAGE, world_id=realm.cosmos.world_id, stats=LanguageStats())
    await EntityRepository(session).add_flag(dead.id, EntityFlag.DEAD_LANGUAGE)
    await EntityRepository(session).add_flag(dead.id, EntityFlag.DECIPHERABLE)
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.LANGUAGES, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {"dead_tongue": dead.id}


async def scribe(session: AsyncSession, realm: Realm) -> Ids:
    mortal = await session.get(EntityRow, realm.mortal_id)
    assert mortal is not None
    await connect(session, realm.settlement_id, realm.language_id, BondKind.SPEAKS)
    tongue = await own_tongue(session, mortal)
    language = await session.get(EntityRow, tongue.id if tongue is not None else realm.language_id)
    assert language is not None
    profile = await language_profile(session, language)
    profile.writing_system = WritingSystem.PICTOGRAPHIC
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.LANGUAGES, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {}


async def sickness(session: AsyncSession, realm: Realm) -> Ids:
    disease = await make_entity(
        session,
        "Grey Cough",
        EntityType.DISEASE,
        world_id=realm.cosmos.world_id,
        stats=DiseaseStats(virulence=40, lethality=20),
    )
    session.add(
        DiseaseProfileRow(
            disease_entity_id=disease.id,
            vector=next(iter(DiseaseVector)),
            virulence=40,
            lethality=20,
            chronic_rate=0,
            incubation=1,
            target_functions=[],
            climate_affinity=ClimateAffinity.ANY,
            immunity_epochs=4,
            mutation_rate=5,
            stigma=10,
            cure_level=5,
            locked=[],
        )
    )
    await session.flush()
    return {"disease": disease.id}


async def healer(session: AsyncSession, realm: Realm) -> Ids:
    found = await sickness(session, realm)
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.MEDICINE, level=80, peak=80, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return found


async def carrying(session: AsyncSession, realm: Realm) -> Ids:
    found = await healer(session, realm)
    session.add(CarrierRow(mortal_entity_id=realm.mortal_id, disease_entity_id=found["disease"], identified=False, seeded=0, since_epoch=1, locked=[]))
    await session.flush()
    return found


async def hospital(session: AsyncSession, realm: Realm) -> Ids:
    found = await healer(session, realm)
    seat = await make_entity(
        session, "House of Healing", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(StructureProfileRow(structure_entity_id=seat.id, kind=StructureKind.HOSPITAL))
    await session.flush()
    return {**found, "hospital": seat.id}


async def ruled_sickness(session: AsyncSession, realm: Realm) -> Ids:
    return {**await ruler(session, realm), **await sickness(session, realm)}


async def road(session: AsyncSession, realm: Realm) -> Ids:
    town = (await second_settlement(session, realm))["settlement"]
    route = await make_entity(session, "Long Road", EntityType.TRADE_ROUTE, world_id=realm.cosmos.world_id, stats=TradeRouteStats(capacity=40))
    session.add(
        TradeRouteProfileRow(
            route_entity_id=route.id,
            first_market_id=realm.settlement_id,
            second_market_id=town,
            mode=TradeMode.ROAD,
            status=TradeRouteStatus.OPEN,
            length=2,
            founded_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    return {"trade_route": route.id, "settlement": town}


async def led_faction(session: AsyncSession, realm: Realm, kind: FactionKind, name: str) -> int:
    faction = await make_entity(session, name, EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(
        FactionProfileRow(
            faction_entity_id=faction.id, kind=kind, home_entity_id=realm.settlement_id, leader_entity_id=realm.mortal_id, influence_over={}, locked=[]
        )
    )
    session.add(FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=realm.mortal_id, rank=FactionRank.LEADER, locked=[]))
    await session.flush()
    return faction.id


async def first_district(session: AsyncSession, realm: Realm) -> int:
    found = await session.scalar(select(DistrictRow.id).where(DistrictRow.settlement_entity_id == realm.settlement_id).limit(1))
    if found is not None:
        return int(found)
    district = DistrictRow(settlement_entity_id=realm.settlement_id, kind=DistrictKind.MARKET, level=1, condition=100, built_epoch=1, locked=[])
    session.add(district)
    await session.flush()
    return district.id


async def crime_boss(session: AsyncSession, realm: Realm) -> Ids:
    faction = await led_faction(session, realm, FactionKind.CRIME_FAMILY, "The Lantern Family")
    district = await first_district(session, realm)
    other = await second_mortal(session, realm)
    return {"faction": faction, "district": district, "official": other["mortal"]}


async def turf_held(session: AsyncSession, realm: Realm) -> Ids:
    found = await crime_boss(session, realm)
    session.add(TurfRow(district_id=found["district"], faction_entity_id=found["faction"], strength=50, since_epoch=1, locked=[]))
    await session.flush()
    return found


async def merchant_house(session: AsyncSession, realm: Realm) -> Ids:
    faction = await led_faction(session, realm, FactionKind.MERCHANT_GUILD, "House Varro")
    return {"faction": faction, **await road(session, realm)}


async def on_the_road(session: AsyncSession, realm: Realm) -> Ids:
    found = await road(session, realm)
    convoy = ConvoyRow(
        owner_entity_id=realm.settlement_id,
        route_entity_id=found["trade_route"],
        cargo={},
        capacity=20,
        status=ConvoyStatus.TRAVELLING,
        departed_epoch=1,
        locked=[],
    )
    session.add(convoy)
    await session.flush()
    return {**found, "convoy": convoy.id}


async def order_master(session: AsyncSession, realm: Realm) -> Ids:
    faction = await led_faction(session, realm, FactionKind.MAGE_ORDER, "The Quiet Order")
    session.add(OrderLawRow(faction_entity_id=faction, law=OrderLaw.SHARE_DISCOVERIES, strength=40, locked=[]))
    other = await second_mortal(session, realm)
    session.add(FactionMembershipRow(faction_entity_id=faction, mortal_entity_id=other["mortal"], rank=FactionRank.MEMBER, locked=[]))
    await session.flush()
    return {"faction": faction, "mortal": other["mortal"]}


async def ruled_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(PolityMemberRow(polity_entity_id=found["polity"], member_entity_id=realm.settlement_id))
    await session.flush()
    return found


async def oracle_case(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    session.add(LegalSystemRow(holder_entity_id=found["polity"], system=LegalSystem.ORACLE, since_epoch=0, locked=[]))
    case = CrimeCaseRow(
        settlement_entity_id=realm.settlement_id,
        polity_entity_id=found["polity"],
        crime=CrimeKind.THEFT,
        accused_entity_id=realm.mortal_id,
        stage=CaseStage.TRIAL,
        locked=[],
    )
    session.add(case)
    await session.flush()
    return {**found, "case": case.id}


async def dreamer(session: AsyncSession, realm: Realm) -> Ids:
    other = await second_mortal(session, realm)
    session.add(SecretRow(holder_node_id=other["mortal"], kind=next(iter(IntrigueSecret)), severity=40, known_by=[], locked=[]))
    session.add(DominionRow(god_node_id=realm.son_id, region_entity_id=realm.cosmos.region_id, strength=100, locked=[]))
    await session.flush()
    return other


async def convicted(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await second_mortal(session, realm)
    session.add(OfficeRow(polity_entity_id=found["polity"], kind=OfficeKind.GOVERNOR, holder_entity_id=other["mortal"]))
    session.add(
        CrimeCaseRow(
            settlement_entity_id=realm.settlement_id,
            polity_entity_id=found["polity"],
            crime=CrimeKind.THEFT,
            accused_entity_id=realm.mortal_id,
            stage=CaseStage.CLOSED,
            verdict=Verdict.GUILTY,
            closed_epoch=0,
            locked=[],
        )
    )
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=realm.mortal_id, wealth=PERCENT, locked=[]))
    else:
        profile.wealth = PERCENT
    await session.flush()
    return found


async def outlaw_hunted(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await second_mortal(session, realm)
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.TRACKING, level=80, xp=0, peak=80, last_used_epoch=0, source=SkillSource.PLAYER))
    session.add(OutlawRow(mortal_entity_id=other["mortal"], polity_entity_id=found["polity"], bounty=10, renown=0, declared_epoch=0, locked=[]))
    await session.flush()
    return {**found, "outlaw": other["mortal"]}


async def prisoner_held(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await second_mortal(session, realm)
    jail = await make_entity(session, "The Keep", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(StructureProfileRow(structure_entity_id=jail.id, kind=StructureKind.PRISON, host_entity_id=realm.settlement_id))
    session.add(PrisonerRow(mortal_entity_id=other["mortal"], prison_entity_id=jail.id, term=3, gang_rank=0, since_epoch=0, locked=[]))
    await session.flush()
    return {**found, "prisoner": other["mortal"], "prison": jail.id}


async def spymaster(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    session.add(OfficeRow(polity_entity_id=found["polity"], kind=OfficeKind.SPYMASTER, holder_entity_id=realm.mortal_id))
    await session.flush()
    return found


async def bounty_poster(session: AsyncSession, realm: Realm) -> Ids:
    found = await outlaw_hunted(session, realm)
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=realm.mortal_id, wealth=PERCENT, locked=[]))
    else:
        profile.wealth = PERCENT
    await session.flush()
    return found


async def town_profile(session: AsyncSession, realm: Realm) -> Ids:
    if await session.get(SettlementProfileRow, realm.settlement_id) is None:
        session.add(SettlementProfileRow(settlement_entity_id=realm.settlement_id, size_tier=SizeTier.TOWN, locked=[], foreigners={}))
        await session.flush()
    return {"town": realm.settlement_id}


async def storylet_waiting(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    run = StoryletRunRow(
        storylet=StoryletId.HOARDED_STORE,
        world_id=realm.cosmos.world_id,
        cast={"town": realm.settlement_id, "ruler": realm.mortal_id, "realm": found["polity"]},
        status=StoryletStatus.OPEN,
        chooser_node_id=realm.mortal_id,
        due_epoch=EPOCH + 5,
        opened_epoch=0,
        locked=[],
    )
    session.add(run)
    await session.flush()
    return {**found, **await town_profile(session, realm), "storylet_run": run.id}


async def chronicled_event(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    event = CollectionRow(kind=CollectionKind.CORONATION, name="The crowning at Brinewatch", world_id=realm.cosmos.world_id, start_epoch=0, locked=[])
    session.add(event)
    await session.flush()
    return {**found, "collection": event.id}


async def figure_to_strike(session: AsyncSession, realm: Realm) -> Ids:
    return {**await ruled_realm(session, realm), **await second_mortal(session, realm)}


async def rewritten_account(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    original = AccountRow(holder_entity_id=found["polity"], kind=AccountKind.OFFICIAL_CHRONICLE, subject_node_id=realm.mortal_id, epoch=0, locked=[])
    session.add(original)
    await session.flush()
    revision = AccountRow(
        holder_entity_id=found["polity"], kind=AccountKind.OFFICIAL_CHRONICLE, subject_node_id=realm.mortal_id, revised_from_id=original.id, epoch=1, locked=[]
    )
    session.add(revision)
    await session.flush()
    return {**found, "revision": revision.id}


async def hungry_town(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    await town_profile(session, realm)
    shares = {f"share_{item.value}": 0.1 for item in SocialClass}
    satisfaction = {f"satisfaction_{item.value}": 50 for item in SocialClass}
    if await session.get(CommunitySocietyRow, realm.settlement_id) is None:
        session.add(
            CommunitySocietyRow(
                entity_id=realm.settlement_id,
                **shares,
                **satisfaction,
                stock_food=0,
                stock_ore=0,
                stock_goods=0,
                price_food=100,
                price_ore=100,
                price_goods=100,
            )
        )
    await session.flush()
    return found


async def offered_town(session: AsyncSession, realm: Realm) -> Ids:
    session.add(DivineDebtRow(god_node_id=realm.son_id, community_entity_id=realm.settlement_id, offered=60, answered=0, locked=[]))
    await session.flush()
    return {}


async def son_plan(session: AsyncSession, realm: Realm) -> Ids:
    plan = LongPlanRow(holder_node_id=realm.son_id, kind=LongPlanKind.WONDER, name="The Long Work", steps=10, progress=0, step_cost=0, secrecy=50, locked=[])
    session.add(plan)
    await session.flush()
    return {"plan": plan.id}


async def son_divine_power(session: AsyncSession, realm: Realm) -> Ids:
    row = DivinePowerRow(holder_node_id=realm.son_id, name="A Kind Hand", verb=DivineVerb.BLESS, object=DivineObject.STAT, scope=DivineScope.PERSON)
    row.object_key, row.mode, row.cost, row.cost_amount, row.cooldown, row.strength, row.domains, row.locked = (
        "prosperity",
        DivineMode.ACTIVE,
        DivineCost.ATTENTION,
        1,
        0,
        20,
        [],
        [],
    )
    session.add(row)
    await session.flush()
    return {"divine_power": row.id}


async def son_natural_law(session: AsyncSession, realm: Realm) -> Ids:
    world = realm.cosmos.world_id
    law = await make_entity(session, "The Even Hand", EntityType.NATURAL_LAW, world_id=world, stats=NaturalLawStats(), natural_law=NaturalLaw.BOUNTY)
    session.add(NaturalLawProfileRow(law_entity_id=law.id, effect=NaturalLaw.BOUNTY, world_id=realm.cosmos.world_id, author_node_id=realm.son_id, locked=[]))
    await session.flush()
    return {"natural_law": law.id}


async def wealthy(session: AsyncSession, realm: Realm) -> Ids:
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        profile = MortalProfileRow(entity_id=realm.mortal_id, locked=[])
        session.add(profile)
    profile.wealth = PERCENT
    await session.flush()
    return {}


async def owed_gift(session: AsyncSession, realm: Realm) -> Ids:
    await wealthy(session, realm)
    gift = GiftRow(giver_node_id=realm.son_id, receiver_node_id=realm.mortal_id, value=10, state=GiftState.OPEN, due_epoch=5, epoch=1, locked=[])
    session.add(gift)
    await session.flush()
    return {"gift": gift.id}


async def devout(session: AsyncSession, realm: Realm) -> Ids:
    await wealthy(session, realm)
    await connect(session, realm.mortal_id, realm.son_id, BondKind.WORSHIPS)
    return {}


async def bound_town(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    session.add(
        CohortRow(
            community_entity_id=realm.settlement_id,
            age_band=AgeBand.ADULT,
            sex=Sex.FEMALE,
            social_class=SocialClass.SERF_OR_SLAVE,
            condition=CohortCondition.ENSLAVED,
            count=20,
        )
    )
    await session.flush()
    return found


async def raising_work(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    work = await make_entity(
        session, "Long Wall", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(
        ConstructionRow(
            structure_entity_id=work.id,
            site_entity_id=realm.settlement_id,
            kind=StructureKind.WALL,
            status=ConstructionStatus.ACTIVE,
            cost=100,
            started_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    return {**found, "work": work.id}


async def learning_house(session: AsyncSession, realm: Realm) -> Ids:
    house = await make_entity(session, "Hall of Records", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(StructureProfileRow(structure_entity_id=house.id, kind=StructureKind.ACADEMY, host_entity_id=realm.settlement_id))
    await session.flush()
    return {"structure": house.id}


async def seat_for_sale(session: AsyncSession, realm: Realm) -> Ids:
    await wealthy(session, realm)
    polity = await make_entity(session, "Vale Council", EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=realm.settlement_id))
    office = OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.CHANCELLOR, holder_entity_id=None)
    session.add(office)
    await session.flush()
    return {"office": office.id, "polity": polity.id}


async def examined_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    session.add(ExaminationRow(polity_entity_id=found["polity"], locked=[]))
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.LAW, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return found


async def open_school(session: AsyncSession, realm: Realm) -> Ids:
    master = await second_mortal(session, realm)
    school = SchoolLineageRow(name="The First School", founder_entity_id=master["mortal"], locked=[])
    session.add(school)
    await session.flush()
    session.add(SchoolMemberRow(school_id=school.id, mortal_entity_id=master["mortal"], generation=0, locked=[]))
    await session.flush()
    return {"school": school.id}


async def ruling_circle(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    member = await second_mortal(session, realm)
    session.add(CoalitionMemberRow(polity_entity_id=found["polity"], mortal_entity_id=member["mortal"], locked=[]))
    await session.flush()
    return {**found, **member}


async def house_head(session: AsyncSession, realm: Realm) -> Ids:
    house = await make_entity(session, "House Vale", EntityType.HOUSE, world_id=realm.cosmos.world_id, stats=HouseStats())
    session.add(HouseProfileRow(house_entity_id=house.id, founder_entity_id=realm.mortal_id, head_entity_id=realm.mortal_id))
    await session.flush()
    return {"house": house.id}


async def land_common(session: AsyncSession, realm: Realm) -> Ids:
    row = CommonsRow(region_entity_id=realm.cosmos.region_id, kind=CommonsKind.PASTURE, steward_entity_id=realm.settlement_id, locked=[])
    session.add(row)
    await session.flush()
    return {"commons": row.id}


async def game_reserve(session: AsyncSession, realm: Realm) -> Ids:
    holder = await second_mortal(session, realm)
    row = GameReserveRow(region_entity_id=realm.cosmos.region_id, holder_node_id=holder["mortal"], strictness=60, locked=[])
    session.add(row)
    await session.flush()
    return {"reserve": row.id}


async def ruined_town(session: AsyncSession, realm: Realm) -> Ids:
    row = ReconstructionRow(settlement_entity_id=realm.settlement_id, cause=RebuildCause.FIRE, cost=300, locked=[])
    session.add(row)
    await session.flush()
    return {"rebuild": row.id}


async def aiding_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await second_settlement(session, realm)
    profile = await session.get(PolityProfileRow, found["polity"])
    assert profile is not None
    profile.treasury = 5000
    await session.flush()
    return {**found, **other}


async def war_trained(session: AsyncSession, realm: Realm) -> Ids:
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.TACTICS, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {}


async def builder_trained(session: AsyncSession, realm: Realm) -> Ids:
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.ENGINEERING, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return {}


async def war_theatre(session: AsyncSession, realm: Realm) -> Ids:
    found = await rival_realm(session, realm)
    polity, rival = await session.get(EntityRow, found["polity"]), await session.get(EntityRow, found["rival"])
    assert polity is not None and rival is not None
    war = await open_war(await manual_context(session, "theatre"), polity, rival)
    row = TheatreRow(owner_entity_id=polity.id, war_id=war.id, locked=[])
    session.add(row)
    await session.flush()
    return {**found, "theatre": row.id}


async def camping_party(session: AsyncSession, realm: Realm) -> Ids:
    region = await second_region(session, realm)
    row = ExpeditionRow(name="The First Venture", leader_entity_id=realm.mortal_id, target_entity_id=region["region"], provisions=10, locked=[])
    session.add(row)
    await session.flush()
    session.add(ExpeditionMemberRow(expedition_id=row.id, mortal_entity_id=realm.mortal_id, role=ExpeditionRole.SCOUT, fatigue=60, locked=[]))
    await session.flush()
    return {"expedition": row.id}


async def commanded_brigade(session: AsyncSession, realm: Realm) -> Ids:
    army = await make_entity(
        session, "Vale Host", EntityType.ARMY, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=ArmyStats(size=100)
    )
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=realm.settlement_id, commander_entity_id=realm.mortal_id, raised_epoch=0))
    await session.flush()
    row = EchelonRow(owner_entity_id=realm.settlement_id, army_entity_id=army.id, level=EchelonLevel.BRIGADE, name="Brigade 1 of Vale Host", locked=[])
    session.add(row)
    await session.flush()
    return {"echelon": row.id, "army": army.id}


async def spirit_office(session: AsyncSession, realm: Realm) -> Ids:
    spirit = await make_entity(session, "Spirit of Brinewatch", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(
        GeniusLocusRow(
            spirit_entity_id=spirit.id, place_entity_id=realm.settlement_id, community_entity_id=realm.settlement_id, kind=GeniusLocusKind.CITY, locked=[]
        )
    )
    session.add(
        SpiritOfficeRow(spirit_entity_id=spirit.id, rank=BureauRank.CITY, overseer_node_id=realm.son_id, jurisdiction_entity_id=realm.settlement_id, locked=[])
    )
    await session.flush()
    petition = PetitionRow(
        petitioner_node_id=realm.mortal_id, office_spirit_id=spirit.id, kind=PetitionKind.HEALING, filed_epoch=EPOCH, due_epoch=EPOCH, locked=[]
    )
    session.add(petition)
    await session.flush()
    return {"spirit": spirit.id, "petition": petition.id}


async def faith_crisis(session: AsyncSession, realm: Realm) -> Ids:
    row = TheodicyCrisisRow(
        cult_entity_id=realm.cult_id, community_entity_id=realm.settlement_id, god_node_id=realm.son_id, cause=TheodicyCause.PLAGUE, suffering=60, locked=[]
    )
    session.add(row)
    await session.flush()
    return {"crisis": row.id}


async def court_diviners(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(PolityMemberRow(polity_entity_id=found["polity"], member_entity_id=realm.settlement_id))
    town = await session.get(EntityRow, realm.settlement_id)
    assert town is not None
    await connect(session, town.id, realm.people_id, BondKind.DESCENDS_FROM)
    session.add(DivinationSystemRow(people_entity_id=realm.people_id, kind=DivinationKind.AUGURY, locked=[]))
    await session.flush()
    return found


async def open_mind(session: AsyncSession, realm: Realm) -> Ids:
    mortal = await session.get(EntityRow, realm.mortal_id)
    assert mortal is not None
    set_stats(mortal, wisdom=90)
    await write_values(session, ValueHolder.PERSONAL, realm.mortal_id, {ValueAxis.PIETY: 95})
    await session.flush()
    return {}


async def visionary(session: AsyncSession, realm: Realm) -> Ids:
    session.add(MysticRow(mortal_entity_id=realm.mortal_id, state=MysticState.VISIONARY, visions=3, followers=20, locked=[]))
    await session.flush()
    return {}
