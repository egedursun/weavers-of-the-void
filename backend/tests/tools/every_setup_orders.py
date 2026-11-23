from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.city_rules import MunicipalServiceRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.culture import HolderLevelRow, ItemProfileRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.divine_conceptions import DivineConceptionRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import CurrencyRow, LoanRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.faith import CultOfficeRow
from aerona.db.tables.fertility_means import FertilityMeansRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.db.tables.governance import OrgCliqueRow, OrgGovernanceRow, OrgSeatRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.kin_dynamics import KinDisowningRow, KinDynamicRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.mass_weapons import MassWeaponRow, WarRemnantRow
from aerona.db.tables.military import ArmyProfileRow, OccupationRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.reckoning import ReckoningRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, StockExchangeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.city_rules import MunicipalService
from aerona.domain.enums.competition import EntryBarrier, MarketForm
from aerona.domain.enums.creature_groups import GroupForm
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.departures import DepartureKind
from aerona.domain.enums.economy import CommodityKind, CurrencyIssuer, LoanStatus, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.faith import ClergyFunction
from aerona.domain.enums.fertility_means import FertilityMeans
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.governance import CliqueAim, GoverningBody, HeadSelection, OrgStrategy, VoteBasis
from aerona.domain.enums.honours import HonourPrivilege
from aerona.domain.enums.labour import LegalStanding, WorkerBodyForm
from aerona.domain.enums.leagues import LeagueStanding
from aerona.domain.enums.mass_weapons import MassHarm, MassReach, ProgrammeStage, RemnantKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.records import IncidentTier
from aerona.domain.enums.referendums import ReferendumSubject
from aerona.domain.enums.restoration import RestorationStage
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.models.entity_stats import ArmyStats, HouseStats, ItemStats, LeagueStats, MortalStats, PolityStats, RegionStats, SettlementStats
from aerona.engine.body.customs import people_of
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.economy.purse import shift_points
from aerona.engine.lore.research import holder_levels, techniques_of
from aerona.engine.lore.research_depth import open_techniques
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from tests.engine.core.factories import region_record
from tests.tools.every_setup import led_faction, ruled_realm, ruler, second_mortal
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, make_entity

BODY_LEVEL = 3
FAR_EPOCH = 1000
RICH = 90
CRAFT_WORKERS = 300
BODY_FUND = 5000


async def governed(session: AsyncSession, realm: Realm, name: str, head_id: int, members: list[int]) -> int:
    org_id = await led_faction(session, realm, FactionKind.MERCHANT_GUILD, name)
    org = await session.get(EntityRow, org_id)
    profile = await session.get(FactionProfileRow, org_id)
    assert org is not None and profile is not None
    set_stats(org, wealth=RICH, strength=40, sway=30)
    profile.treasury, profile.leader_entity_id = 2000, head_id
    for member in members:
        if await session.get(FactionMembershipRow, (org_id, member)) is None:
            session.add(FactionMembershipRow(faction_entity_id=org_id, mortal_entity_id=member, rank=FactionRank.OFFICER, locked=[]))
    session.add(
        OrgGovernanceRow(
            org_node_id=org_id,
            decision_body=GoverningBody.ASSEMBLY_OF_MEMBERS,
            head_selection=HeadSelection.ELECTED_BY_BODY,
            head_node_id=head_id,
            term_epochs=2,
            term_ends_epoch=FAR_EPOCH,
            vote_basis=VoteBasis.ONE_MEMBER_ONE_VOTE,
            quorum_pct=50,
            strategy=OrgStrategy.HOLD,
            trust=60,
            since_epoch=0,
            locked=[],
        )
    )
    seated = sorted({head_id, realm.mortal_id, *members})
    for index, member in enumerate(seated):
        weight = 100 // len(seated) + (1 if index < 100 % len(seated) else 0)
        session.add(OrgSeatRow(org_node_id=org_id, member_node_id=member, since_epoch=0, vote_weight=weight, locked=[]))
    await session.flush()
    return org_id


async def other_member(session: AsyncSession, realm: Realm) -> int:
    return int((await second_mortal(session, realm))["mortal"])


async def seated_member(session: AsyncSession, realm: Realm) -> Ids:
    other = await other_member(session, realm)
    return {"org": await governed(session, realm, "The Weighing Hall", other, [other])}


async def clique_leader(session: AsyncSession, realm: Realm) -> Ids:
    other = await other_member(session, realm)
    org = await governed(session, realm, "The Parting Hall", other, [other])
    clique = OrgCliqueRow(
        org_node_id=org, name="those who would leave", leader_node_id=realm.mortal_id, members=[realm.mortal_id], aim=CliqueAim.SPLIT, strength=60, locked=[]
    )
    session.add(clique)
    await session.flush()
    return {"org": org, "clique": clique.id}


async def org_head_and_target(session: AsyncSession, realm: Realm) -> Ids:
    other = await other_member(session, realm)
    mine = await governed(session, realm, "The Buying House", realm.mortal_id, [])
    target = await governed(session, realm, "The Sold House", other, [other])
    return {"org": mine, "target": target}


async def research_head(session: AsyncSession, realm: Realm) -> Ids:
    org = await governed(session, realm, "The Seeking House", realm.mortal_id, [])
    for branch in KnowledgeBranch:
        if await session.get(HolderLevelRow, (realm.settlement_id, branch)) is None:
            session.add(HolderLevelRow(holder_entity_id=realm.settlement_id, branch=branch, level=BODY_LEVEL, locked=[]))
    await session.flush()
    levels = (await holder_levels(session)).get(realm.settlement_id, {})
    known = await techniques_of(session, org)
    options = [technique for technique in await open_techniques(session, realm.settlement_id, levels) if technique not in known]
    assert options
    return {"org": org, "technique": list(Technique).index(options[0])}


async def indebted_head(session: AsyncSession, realm: Realm) -> Ids:
    org = await governed(session, realm, "The Owing House", realm.mortal_id, [])
    session.add(
        LoanRow(
            lender_entity_id=realm.faction_id,
            borrower_entity_id=org,
            principal=300,
            interest_pct=5,
            issued_epoch=0,
            due_epoch=1,
            status=LoanStatus.OPEN,
            purpose="stock",
        )
    )
    await session.flush()
    return {"org": org}


async def market_seller_head(session: AsyncSession, realm: Realm) -> Ids:
    other = await other_member(session, realm)
    mine = await governed(session, realm, "The Grain House", realm.mortal_id, [])
    rival = await governed(session, realm, "The Rival House", other, [other])
    structure = MarketStructureRow(
        market_entity_id=realm.settlement_id,
        commodity=CommodityKind.GRAIN,
        sellers={str(mine): 60, str(rival): 40},
        small_sellers_pct=0,
        concentration=52,
        form=MarketForm.FEW_SELLERS,
        barriers={EntryBarrier.CAPITAL.value: 30},
        locked=[],
    )
    session.add(structure)
    await session.flush()
    return {"org": mine, "rival": rival, "market": realm.settlement_id}


async def cartel_in_market(session: AsyncSession, realm: Realm) -> Ids:
    found = await market_seller_head(session, realm)
    cartel = CartelRow(
        name="the compact of the two houses",
        leader_node_id=found["org"],
        members=[found["org"], found["rival"]],
        markets=[realm.settlement_id],
        commodity=CommodityKind.GRAIN,
        locked=[],
    )
    session.add(cartel)
    await session.flush()
    return {**found, "cartel": cartel.id}


async def crafting_town(session: AsyncSession, realm: Realm) -> Ids:
    if await session.get(LabourRow, (realm.settlement_id, Job.CRAFTING)) is None:
        session.add(LabourRow(community_entity_id=realm.settlement_id, job=Job.CRAFTING, workers=CRAFT_WORKERS, output_pct=100, epoch=0, held=False))
        await session.flush()
    return {"town": realm.settlement_id}


async def worker_body_of(session: AsyncSession, realm: Realm, name: str, leader: int) -> int:
    body_id = await led_faction(session, realm, FactionKind.WORKER_BODY, name)
    membership = await session.get(FactionMembershipRow, (body_id, realm.mortal_id))
    if membership is not None and leader != realm.mortal_id:
        await session.delete(membership)
    if await session.get(FactionMembershipRow, (body_id, leader)) is None:
        session.add(FactionMembershipRow(faction_entity_id=body_id, mortal_entity_id=leader, rank=FactionRank.LEADER, locked=[]))
    session.add(
        WorkerBodyRow(
            faction_node_id=body_id,
            form=WorkerBodyForm.CRAFT_UNION,
            trades=[Job.CRAFTING.value],
            works=[],
            members=CRAFT_WORKERS // 2,
            dues=2,
            fund=BODY_FUND,
            solidarity=60,
            standing=LegalStanding.TOLERATED,
            founded_epoch=0,
            locked=[],
        )
    )
    await session.flush()
    return body_id


async def forge_of(session: AsyncSession, realm: Realm, owner: int) -> None:
    session.add(WorkshopRow(community_entity_id=realm.settlement_id, kind=WorkshopKind.FORGE, level=BODY_LEVEL, built_epoch=0, owner_node_id=owner))
    await session.flush()


async def led_worker_body(session: AsyncSession, realm: Realm) -> Ids:
    await crafting_town(session, realm)
    other = await other_member(session, realm)
    hirer = await governed(session, realm, "The Forge Masters", other, [other])
    await forge_of(session, realm, hirer)
    return {"body": await worker_body_of(session, realm, "The Forge Hands", realm.mortal_id), "hirer": hirer}


async def hirer_head(session: AsyncSession, realm: Realm) -> Ids:
    await crafting_town(session, realm)
    other = await other_member(session, realm)
    hirer = await governed(session, realm, "The Anvil House", realm.mortal_id, [])
    await forge_of(session, realm, hirer)
    return {"body": await worker_body_of(session, realm, "The Anvil Hands", other), "hirer": hirer}


async def minted_here(session: AsyncSession, realm: Realm, issuer: int, name: str) -> CurrencyRow:
    currency = CurrencyRow(issuer_entity_id=issuer, name=name, purity=100, supply=1000, trust=70, minted_epoch=0, issuer_kind=CurrencyIssuer.BANK)
    session.add(currency)
    await session.flush()
    return currency


async def money_holder(session: AsyncSession, realm: Realm) -> Ids:
    bank = await led_faction(session, realm, FactionKind.MERCHANT_GUILD, "The Mint House")
    currency = await minted_here(session, realm, bank, "Mint Marks")
    anchor = await minted_here(session, realm, realm.settlement_id, "Town Marks")
    authority = MonetaryAuthorityRow(currency_id=currency.id, holder_node_id=bank, issuer_node_id=bank, reserves=500, locked=[])
    session.add(authority)
    await session.flush()
    return {"authority": authority.id, "currency": currency.id, "anchor": anchor.id}


async def unissued_currency(session: AsyncSession, realm: Realm) -> Ids:
    bank = await led_faction(session, realm, FactionKind.MERCHANT_GUILD, "The Coin House")
    currency = await minted_here(session, realm, bank, "Coin Marks")
    return {"currency": currency.id, "holder": bank}


async def town_currency(session: AsyncSession, realm: Realm) -> Ids:
    currency = await minted_here(session, realm, realm.settlement_id, "Shaken Marks")
    return {"currency": currency.id}


async def exchange_here(session: AsyncSession, realm: Realm) -> int:
    exchange = StockExchangeRow(name="the exchange of the town", settlement_entity_id=realm.settlement_id, margin_pct=60, locked=[])
    session.add(exchange)
    await session.flush()
    return exchange.id


async def issuer_head(session: AsyncSession, realm: Realm) -> Ids:
    issuer = await led_faction(session, realm, FactionKind.MERCHANT_GUILD, "The Listing House")
    org = await session.get(EntityRow, issuer)
    assert org is not None
    set_stats(org, wealth=RICH)
    return {"issuer": issuer, "exchange": await exchange_here(session, realm)}


async def listed_claim(session: AsyncSession, realm: Realm) -> Ids:
    exchange = await exchange_here(session, realm)
    other = await other_member(session, realm)
    issuer = await governed(session, realm, "The Traded House", other, [other])
    security = IssuedSecurityRow(
        name="the shares of the traded house", issuer_node_id=issuer, amount=100, face_value=10, price=5, exchange_id=exchange, locked=[]
    )
    buyer = await session.get(EntityRow, realm.mortal_id)
    assert buyer is not None
    await shift_points(session, buyer, RICH)
    session.add(security)
    await session.flush()
    session.add(SecurityHoldingRow(holder_node_id=issuer, security_id=security.id, amount=100, bought_price=10, locked=[]))
    await session.flush()
    return {"security": security.id, "exchange": exchange}


async def other_realm(session: AsyncSession, realm: Realm, name: str) -> int:
    polity = await make_entity(session, name, EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    await session.flush()
    return polity.id


async def realms_to_bind(session: AsyncSession, realm: Realm) -> Ids:
    mine = (await ruled_realm(session, realm))["polity"]
    return {"mine": mine, "second": await other_realm(session, realm, "Second Crown"), "third": await other_realm(session, realm, "Third Crown")}


async def league_to_join(session: AsyncSession, realm: Realm) -> Ids:
    mine = (await ruled_realm(session, realm))["polity"]
    founders = [await other_realm(session, realm, name) for name in ("North Crown", "South Crown", "East Crown")]
    league = await make_entity(session, "the League of the Crowns", EntityType.LEAGUE, world_id=realm.cosmos.world_id, stats=LeagueStats(strength=30))
    session.add(PolityLeagueRow(league_entity_id=league.id, aims=["trade"], organs=["assembly", "court"], locked=[]))
    for polity in founders:
        session.add(LeagueMemberRow(league_entity_id=league.id, polity_entity_id=polity, standing=LeagueStanding.FOUNDER, locked=[]))
    await session.flush()
    return {"league": league.id, "mine": mine, "subject": founders[0]}


async def league_member_ruler(session: AsyncSession, realm: Realm) -> Ids:
    found = await league_to_join(session, realm)
    session.add(LeagueMemberRow(league_entity_id=found["league"], polity_entity_id=found["mine"], standing=LeagueStanding.MEMBER, locked=[]))
    await session.flush()
    return found


async def office_holder(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    office = OfficeRow(polity_entity_id=polity, kind=OfficeKind.TREASURER, holder_entity_id=realm.mortal_id, since_epoch=0, powers=[])
    session.add(office)
    await session.flush()
    return {"office": office.id, "polity": polity}


async def left_office(session: AsyncSession, realm: Realm) -> Ids:
    found = await office_holder(session, realm)
    office = await session.get(OfficeRow, found["office"])
    assert office is not None
    office.holder_entity_id = None
    row = DepartureRow(
        holder_node_id=realm.mortal_id,
        office_id=office.id,
        office_kind=office.kind,
        polity_entity_id=found["polity"],
        kind=DepartureKind.RESIGNATION,
        conditions=[],
        epoch=0,
        standing=40,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return {"departure": row.id, "holder": realm.mortal_id}


async def left_office_holder(session: AsyncSession, realm: Realm) -> Ids:
    found = await office_holder(session, realm)
    return {**found, "holder": realm.mortal_id}


async def open_vote(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    row = ReferendumRow(
        name="the vote of the crown", holder_node_id=polity, subject=ReferendumSubject.WAR, target_node_id=realm.settlement_id, called_epoch=0, locked=[]
    )
    session.add(row)
    buyer = await session.get(EntityRow, realm.mortal_id)
    assert buyer is not None
    await shift_points(session, buyer, RICH)
    await session.flush()
    return {"referendum": row.id, "polity": polity}


async def open_reckoning_here(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    row = ReckoningRow(polity_entity_id=polity, fallen_epoch=0, opened_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    return {"reckoning": row.id, "polity": polity, "accused": await other_member(session, realm)}


async def cult_in_realm(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    leader = await other_member(session, realm)
    cult = LeaderCultRow(leader_node_id=leader, polity_entity_id=polity, promoters=[realm.mortal_id], instruments=["holidays"], begun_epoch=0, locked=[])
    session.add(cult)
    await session.flush()
    return {"cult": cult.id, "leader": leader}


async def own_cult(session: AsyncSession, realm: Realm) -> Ids:
    cult = LeaderCultRow(leader_node_id=realm.mortal_id, promoters=[], instruments=[], begun_epoch=0, locked=[])
    session.add(cult)
    await session.flush()
    return {"cult": cult.id}


async def fallen_over(session: AsyncSession, realm: Realm, core: int) -> int:
    fallen = await make_entity(session, "The Fallen Crown", EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 0
    session.add(
        PolityProfileRow(polity_entity_id=fallen.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), core_entity_id=core)
    )
    await session.flush()
    return fallen.id


async def fallen_here(session: AsyncSession, realm: Realm) -> Ids:
    return {"fallen": await fallen_over(session, realm, realm.settlement_id)}


async def led_restoration(session: AsyncSession, realm: Realm) -> Ids:
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None
    town = await make_entity(session, "Old Seat", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, location_id=home.location_id)
    fallen = await fallen_over(session, realm, town.id)
    row = RestorationRow(
        fallen_polity_id=fallen,
        claimant_node_id=realm.mortal_id,
        territories=[town.id],
        bases=["bloodline"],
        stage=RestorationStage.MOVEMENT,
        memory=80,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return {"restoration": row.id, "fallen": fallen}


async def regime_over_home(session: AsyncSession, realm: Realm, occupier: int) -> int:
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None and home.location_id is not None
    session.add(OccupationRow(region_entity_id=home.location_id, occupier_entity_id=occupier, since_epoch=0, control=50, resistance=30, locked=[]))
    regime = OccupationRegimeRow(region_entity_id=home.location_id, occupier_entity_id=occupier, administrators=[], imposed_laws=[], locked=[])
    session.add(regime)
    await session.flush()
    return regime.id


async def my_occupation(session: AsyncSession, realm: Realm) -> Ids:
    return {"regime": await regime_over_home(session, realm, (await ruled_realm(session, realm))["polity"])}


async def foreign_occupation(session: AsyncSession, realm: Realm) -> Ids:
    return {"regime": await regime_over_home(session, realm, await other_realm(session, realm, "Occupying Crown"))}


async def exposed_service(session: AsyncSession, realm: Realm) -> Ids:
    regime = (await foreign_occupation(session, realm))["regime"]
    service = CollaborationRow(regime_id=regime, collaborator_node_id=await other_member(session, realm), locked=[])
    session.add(service)
    await session.flush()
    return {"regime": regime, "service": service.id}


async def my_arsenal(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None
    target = await make_entity(session, "Struck Town", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, location_id=home.location_id)
    weapon = MassWeaponRow(holder_entity_id=polity, harm=MassHarm.FIRE, reach=MassReach.SETTLEMENT, stage=ProgrammeStage.READY, count=1, seen_by=[], locked=[])
    session.add(weapon)
    await session.flush()
    return {"polity": polity, "weapon": weapon.id, "target": target.id, "rival": await other_realm(session, realm, "Rival Arsenal")}


async def foreign_weapon(session: AsyncSession, realm: Realm) -> Ids:
    holder = await other_realm(session, realm, "Foreign Arsenal")
    weapon = MassWeaponRow(holder_entity_id=holder, harm=MassHarm.RITE, reach=MassReach.REGION, stage=ProgrammeStage.READY, count=1, seen_by=[], locked=[])
    session.add(weapon)
    await session.flush()
    return {"weapon": weapon.id}


async def scarred_home(session: AsyncSession, realm: Realm) -> Ids:
    home = await session.get(EntityRow, realm.settlement_id)
    me = await session.get(EntityRow, realm.mortal_id)
    assert home is not None and home.location_id is not None and me is not None
    session.add(WarRemnantRow(region_entity_id=home.location_id, kind=RemnantKind.BURIED_CHARGES, density=60, locked=[]))
    await shift_points(session, me, BODY_FUND)
    await session.flush()
    return {"region": home.location_id}


async def way_out(session: AsyncSession, realm: Realm) -> int:
    bridge = TravelMethod.DIVINE_BRIDGE
    route = RouteRow(
        world_a_id=realm.cosmos.world_id, world_b_id=realm.other_world_id, method=bridge, duration_epochs=1, danger=0, created_epoch=0, capacity=100
    )
    session.add(route)
    await session.flush()
    return route.id


async def host_abroad(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None
    army = await make_entity(session, "Crossing Host", EntityType.ARMY, world_id=realm.cosmos.world_id, location_id=home.location_id, stats=ArmyStats(size=800))
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=polity, raised_epoch=0))
    session.add(ArmyProfileRow(army_entity_id=army.id, region_entity_id=home.location_id, baggage=0, supply_line=[], locked=[]))
    await session.flush()
    return {"polity": polity, "army": army.id, "route": await way_out(session, realm), "world": realm.cosmos.world_id, "other": realm.other_world_id}


async def movers_home(session: AsyncSession, realm: Realm) -> Ids:
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None
    home.civ_tier = 3
    return {"route": await way_out(session, realm), "other": realm.other_world_id}


async def ruled_towns(session: AsyncSession, realm: Realm) -> Ids:
    polity = (await ruled_realm(session, realm))["polity"]
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None
    neighbour = await make_entity(session, "Neighbour Town", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, location_id=home.location_id)
    for town in (realm.settlement_id, neighbour.id):
        if await session.get(PolityMemberRow, (polity, town)) is None:
            session.add(PolityMemberRow(polity_entity_id=polity, member_entity_id=town))
    await session.flush()
    return {"polity": polity, "neighbour": neighbour.id}


async def kept_service(session: AsyncSession, realm: Realm) -> Ids:
    session.add(MunicipalServiceRow(settlement_entity_id=realm.settlement_id, service=MunicipalService.REFUSE, coverage={}, quality=50, locked=[]))
    await session.flush()
    return {}


async def wild_home(session: AsyncSession, realm: Realm) -> Ids:
    home = await session.get(EntityRow, realm.settlement_id)
    assert home is not None and home.location_id is not None
    if await session.get(SpeciesRangeRow, (realm.species_id, home.location_id)) is None:
        session.add(SpeciesRangeRow(species_entity_id=realm.species_id, region_entity_id=home.location_id, abundance=0, fit=60, locked=[]))
    await session.flush()
    return {"region": home.location_id}


async def my_house(session: AsyncSession, realm: Realm) -> Ids:
    house = await make_entity(session, "House Of The Case", EntityType.HOUSE, world_id=realm.cosmos.world_id, stats=HouseStats())
    session.add(HouseProfileRow(house_entity_id=house.id, founder_entity_id=realm.mortal_id, head_entity_id=realm.mortal_id, locked=[]))
    grown = MortalStats(hp=40, strength=30, agility=30, intellect=30, charisma=30, age=25, lifespan=70)
    world, town = realm.cosmos.world_id, realm.settlement_id
    children = [
        (await make_entity(session, name, EntityType.MORTAL, world_id=world, location_id=town, stats=grown)).id for name in ("First Child", "Second Child")
    ]
    for member in (realm.mortal_id, *children):
        session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member))
    for child in children:
        await BondRepository(session).connect(BondDraft(realm.mortal_id, child, BondKind.PARENT_OF, 0))
    await session.flush()
    return {"house": house.id, "child": children[0], "other": children[1]}


async def cast_out_child(session: AsyncSession, realm: Realm) -> Ids:
    ids = await my_house(session, realm)
    dynamic = KinDynamicRow(house_entity_id=ids["house"], locked=[])
    session.add(dynamic)
    await session.flush()
    session.add(KinDisowningRow(dynamic_id=dynamic.id, disowner_node_id=realm.mortal_id, disowned_node_id=ids["child"], locked=[]))
    await session.flush()
    return ids


async def an_exchange(session: AsyncSession, realm: Realm) -> Ids:
    other = await make_entity(session, "Far Shore Town", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, stats=SettlementStats(population=400))
    skill = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == realm.mortal_id, SkillRow.skill == SkillKind.LANGUAGES).limit(1))
    if skill is None:
        session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.LANGUAGES, level=80, peak=80, last_used_epoch=0, source=SkillSource.PRACTICE))
    else:
        skill.level = skill.peak = 80
    reading = InterpretationRow(first_party_id=realm.settlement_id, second_party_id=other.id, fidelity=60, epoch=0, locked=[])
    session.add(reading)
    await session.flush()
    return {"exchange": reading.id, "other": other.id}


async def a_grave(session: AsyncSession, realm: Realm) -> Ids:
    dead = await make_entity(
        session,
        "Ancestor Of The Case",
        EntityType.MORTAL,
        world_id=realm.cosmos.world_id,
        location_id=realm.settlement_id,
        stats=MortalStats(hp=0, age=70, lifespan=70),
    )
    dead.status, dead.end_epoch = EntityStatus.DEAD, 0
    item = await make_entity(
        session, "Ring Of The Case", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=ItemStats(might=10)
    )
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.RING, locked=[]))
    await BondRepository(session).connect(BondDraft(realm.mortal_id, item.id, BondKind.OWNS, 0))
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    await shift_points(session, me, 40)
    grave = GraveGoodsRow(dead_entity_id=dead.id, grave_entity_id=realm.settlement_id, goods_value=20, items=[], locked=[])
    session.add(grave)
    await session.flush()
    return {"grave": grave.id, "item": item.id, "dead": dead.id}


async def a_condition(session: AsyncSession, realm: Realm) -> Ids:
    row = ConditionRow(
        bearer_node_id=realm.mortal_id, kind=ConditionKind.CHRONIC_ILLNESS, severity=2, source=HarmCause.BODY, since_epoch=0, cause=ConditionCause.DIET
    )
    session.add(row)
    await session.flush()
    return {"condition": row.id, "being": realm.mortal_id}


async def a_known_means(session: AsyncSession, realm: Realm) -> Ids:
    await BondRepository(session).connect(BondDraft(realm.people_id, realm.settlement_id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    me = await session.get(EntityRow, realm.mortal_id)
    people = await people_of(session, me) if me is not None else None
    assert people is not None
    session.add(FertilityMeansRow(people_entity_id=people.id, means=FertilityMeans.PREVENTION, reliability=60, use_pct=20, locked=[]))
    await session.flush()
    return {"people": people.id}


async def an_honour(session: AsyncSession, realm: Realm) -> Ids:
    crown = await ruler(session, realm)
    other = await second_mortal(session, realm)
    deed = IncidentRow(
        kind="player.history", epoch=1, year=12, world_id=realm.cosmos.world_id, place_entity_id=realm.settlement_id, tier=IncidentTier.STEPS, locked=[]
    )
    session.add(deed)
    kind = HonourKindRow(conferrer_node_id=crown["polity"], name="Order of the Case", rank=1, privileges=[HonourPrivilege.TITLE.value], locked=[])
    session.add(kind)
    await session.flush()
    held_one = HonourHeldRow(holder_node_id=realm.mortal_id, kind_id=kind.id, epoch=0, locked=[])
    session.add(held_one)
    await session.flush()
    return {**crown, "holder": other["mortal"], "kind": kind.id, "deed": deed.id, "held": held_one.id}


async def a_coast(session: AsyncSession, realm: Realm) -> Ids:
    water = await make_entity(session, "The Grey Water", EntityType.REGION, world_id=realm.cosmos.world_id, stats=RegionStats())
    land = region_record(realm.cosmos.region_id, [water.id]).model_dump(mode="json")
    sea = region_record(water.id, [realm.cosmos.region_id]).model_dump(mode="json") | {"is_water": True}
    existing = await session.scalar(select(WorldMapRow).where(WorldMapRow.world_id == realm.cosmos.world_id))
    if existing is None:
        session.add(WorldMapRow(world_id=realm.cosmos.world_id, generator_version=1, epoch=1, geometry={"regions": [land, sea]}))
    else:
        existing.geometry = {"regions": [land, sea]}
    await BondRepository(session).connect(BondDraft(realm.people_id, realm.settlement_id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    session.add(ObservationMethodRow(people_entity_id=realm.people_id, domain=FolkDomain.WATERS, method=ObservationMethod.SIGHT, accuracy=50, locked=[]))
    await session.flush()
    return {"region": realm.cosmos.region_id, "sea": water.id}


CANAL_EPOCH = 3


async def a_canal_river(session: AsyncSession, realm: Realm) -> Ids:
    lowland = await make_entity(session, "Lowmere", EntityType.REGION, world_id=realm.cosmos.world_id, stats=RegionStats())
    land = region_record(realm.cosmos.region_id, [lowland.id]).model_dump(mode="json")
    low = region_record(lowland.id, [realm.cosmos.region_id]).model_dump(mode="json")
    existing = await session.scalar(select(WorldMapRow).where(WorldMapRow.world_id == realm.cosmos.world_id))
    if existing is None:
        session.add(WorldMapRow(world_id=realm.cosmos.world_id, generator_version=1, epoch=1, geometry={"regions": [land, low]}))
    else:
        existing.geometry = {"regions": [land, low]}
    await session.flush()
    context = await manual_context(session, "canal")
    await refresh_world_maps(session, context.rules, CANAL_EPOCH)
    await environment_survey(context)
    ground = await session.get(RegionEnvironmentRow, realm.cosmos.region_id)
    assert ground is not None
    ground.river_class = RiverClass.RIVER
    canal = await make_entity(session, "The Long Cut", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(StructureProfileRow(structure_entity_id=canal.id, kind=StructureKind.CANAL, host_entity_id=realm.settlement_id))
    await session.flush()
    return {"region": realm.cosmos.region_id, "lowland": lowland.id}


async def a_creature_group(session: AsyncSession, realm: Realm) -> Ids:
    region = realm.cosmos.region_id
    session.add(SpeciesRangeRow(species_entity_id=realm.species_id, region_entity_id=region, abundance=40, fit=40, locked=[]))
    group = CreatureGroupRow(
        species_entity_id=realm.species_id, region_entity_id=region, form=GroupForm.PACK, size=400, territory=[region], rivals=[], locked=[]
    )
    session.add(group)
    await session.flush()
    return {"group": group.id}


async def a_faith_conceived(session: AsyncSession, realm: Realm) -> Ids:
    session.add(DivineConceptionRow(cult_entity_id=realm.cult_id, locked=[]))
    session.add(CultOfficeRow(cult_entity_id=realm.cult_id, kind=next(iter(ClergyFunction)), holder_entity_id=realm.mortal_id))
    skill = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == realm.mortal_id, SkillRow.skill == SkillKind.THEOLOGY).limit(1))
    if skill is None:
        session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.THEOLOGY, level=100, peak=100, last_used_epoch=0, source=SkillSource.PRACTICE))
    await session.flush()
    return {"faith": realm.cult_id}
