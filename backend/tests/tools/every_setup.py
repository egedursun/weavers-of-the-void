from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow, RiteProfileRow
from aerona.db.tables.divine import DivineWoundRow
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesUseRow
from aerona.db.tables.economy import MarketPriceRow, TradeRouteProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow, WorldSeasonRow
from aerona.db.tables.estates import EstateProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.intrigue import HookRow, TrueNameRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow, PolityProfileRow, PolityTerritoryRow, TreatyProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.sons import SonRelationRow, SonRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.db.tables.titles import DeJureLinkRow, TitleProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import BeingKind, BeingScale, DimensionKind, PhenomenonCause, PhenomenonKind, RiftCause, RiftState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.divine import DivineWoundKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import Diet, DomesticationStage, SpeciesClass, SpeciesUse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import CivilizationTier, EntityFlag, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.intrigue import HookSource, HookStrength
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.physics import ImpactBody, ImpactOutcome
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.statecraft import CrisisDemand
from aerona.domain.enums.titles import TitleRank
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import CosmicBeingStats, FactionStats, HouseStats, MortalStats, PhenomenonStats, PolityStats, TitleStats
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.economy.stocks import goods_of
from aerona.engine.households.formation import found_household
from aerona.engine.phases.environment import environment_survey
from aerona.engine.phases.physics import settle_heavens
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import take_captive
from aerona.rules.registry import Rules
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, connect, make_entity

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
    session.add(SpeciesUseRow(species_entity_id=realm.species_id, use=SpeciesUse.COMPANION))
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
    session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleRank.DUCHY, regalia=[], drift={}, locked=[]))
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
    session.add(CosmicBeingProfileRow(entity_id=being.id, being_kind=BeingKind.VOID_SHEPHERD, scale=BeingScale.GALAXY, might=50, locked=[]))
    await session.flush()
    return {"being": being.id}


async def phenomenon(session: AsyncSession, realm: Realm) -> Ids:
    found = await make_entity(
        session, "The Standing Fog", EntityType.PHENOMENON, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=PhenomenonStats(danger=20)
    )
    session.add(
        PhenomenonProfileRow(entity_id=found.id, kind=PhenomenonKind.LIVING_FOG, intensity=50, cause=PhenomenonCause.DIVINE, formed_epoch=EPOCH, locked=[])
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


async def world_body(session: AsyncSession, _realm: Realm) -> Ids:
    await settle_heavens(session, Rules())
    return {}
