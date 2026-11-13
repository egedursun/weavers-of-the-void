from itertools import count

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.operations_lines import mortal_operations_lines
from aerona.agents.context.scope import load_scope
from aerona.core.errors import ValidationFailedError
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.operations import (
    AdmiraltyRow,
    DepotRow,
    EchelonRow,
    ExpeditionLogRow,
    QuirkRow,
    SupplyFlowRow,
    TheatreRow,
    TransportAssetRow,
)
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow, TreatyBreachRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.military import ArmourType, ShieldType, Stance, UnitFamily, UnitKind, VesselStatus
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.operations import (
    CarrierKind,
    CrewStation,
    EchelonLevel,
    EchelonOrder,
    ExpeditionEvent,
    ExpeditionGround,
    ExpeditionStatus,
    PointOfSail,
    QuirkKind,
    ResolveKind,
)
from aerona.domain.enums.polity import ClauseKind, DecisionRule, GovernmentKind, OfficeKind, PartyRole, TreatyKind
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.war import WarEnding, WarStatus
from aerona.domain.models.entity_stats import ArmyStats, PolityStats, SpiritStats, VesselStats
from aerona.engine.military.battle import Field, Side, linear_share, make_stacks, missiles
from aerona.engine.military.logistics import March
from aerona.engine.military.orders import create_vessel
from aerona.engine.military.shipyard import Commission
from aerona.engine.operations.admiralty import AdmiraltyTally, keep_admiralty
from aerona.engine.operations.command import CommandTally, command_edge, issue_orders, organise
from aerona.engine.operations.control import set_crew
from aerona.engine.operations.expeditions import ExpeditionTally, advance, eat, launch, party_of
from aerona.engine.operations.limits import over_limit
from aerona.engine.operations.sail import SailTally, engage, ship_state, take_prize
from aerona.engine.operations.supply import SupplyTally, culminate, network, supply_season
from aerona.engine.operations.theatres import TheatreTally, keep_theatres
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.treaties import keep_clause
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from aerona.services.integrity.operations_links import mend_operations_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

RULES = Rules()
ARCHERS = 1000
VOLLEYS = 10
HOSTS = count(1)


def stream(key: str) -> SeededRandom:
    return SeededRandom(RandomKey(7, 1, key))


def unit(kind: UnitKind, count: int, *, ident: int) -> ArmyUnitRow:
    return ArmyUnitRow(
        id=ident,
        army_entity_id=ident,
        kind=kind,
        count=count,
        quality=50,
        armour=ArmourType.NONE,
        shield=ShieldType.NONE,
        helmet=False,
        weapons=[],
        experience=10,
        morale=60,
        fatigue=0,
        wounded=0,
        condition=100,
        ammunition=VOLLEYS,
        locked=[],
    )


def side(name: str, rows: list[ArmyUnitRow], ident: int) -> Side:
    body = EntityRow(id=ident, name=name, entity_type=EntityType.PEOPLE)
    profile = ArmyProfileRow(army_entity_id=ident, stance=Stance.MARCH, doctrine="shieldwall", entrenchment=0, baggage=100, loot=50, locked=[])
    return Side(entity=body, army=body, profile=profile, stacks=make_stacks(rows), edge=1.0, defending=False, skill=0, traits=set())


GROUND = Field(terrain=None, weather=None, night=False)
FAMILIES = frozenset({UnitFamily.MISSILE})


def test_massed_missiles_follow_the_square_law_so_the_larger_force_wins_cheaply() -> None:
    big = side("Many", [unit(UnitKind.ARCHERS, 2 * ARCHERS, ident=1)], 1)
    small = side("Few", [unit(UnitKind.ARCHERS, ARCHERS, ident=2)], 2)
    lost_small = missiles(RULES, stream, big, small, GROUND, families=FAMILIES)
    lost_big = missiles(RULES, stream, small, big, GROUND, families=FAMILIES)
    assert lost_small > 0 and lost_big > 0
    assert lost_small > 1.6 * lost_big
    for _ in range(4):
        missiles(RULES, stream, big, small, GROUND, families=FAMILIES)
        missiles(RULES, stream, small, big, GROUND, families=FAMILIES)
    left_big = big.standing / (2 * ARCHERS)
    left_small = small.standing / ARCHERS
    assert left_big > left_small


def test_missile_stacks_held_in_reserve_still_loose_their_volleys() -> None:
    shooter = side("Many", [unit(UnitKind.ARCHERS, ARCHERS, ident=3)], 3)
    shooter.stacks[0].reserve = True
    target = side("Few", [unit(UnitKind.LINE_INFANTRY, ARCHERS, ident=4)], 4)
    assert missiles(RULES, stream, shooter, target, GROUND, families=FAMILIES) > 0
    assert shooter.square_reserve == ARCHERS
    quiet = side("Held", [unit(UnitKind.ARCHERS, ARCHERS, ident=5)], 5)
    quiet.stacks[0].reserve = True
    assert missiles(tuned_rules(lanchester={"square_reserve_pct": 0}), stream, quiet, target, GROUND, families=FAMILIES) == 0


def test_melee_strength_beyond_the_enemy_front_adds_nothing() -> None:
    horde = side("Horde", [unit(UnitKind.LINE_INFANTRY, 5 * ARCHERS, ident=6)], 6)
    band = side("Band", [unit(UnitKind.LINE_INFANTRY, ARCHERS, ident=7)], 7)
    share = linear_share(RULES, horde, band)
    assert abs(share - RULES.lanchester.linear_overlap_pct / 100 / 5) < 0.01
    assert horde.linear_cap >= 0.69
    assert linear_share(RULES, band, horde) == 1.0


async def realm_with_town(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, "Hollin", world, world.regions[0])
    realm = await entity(session, "Crown of Hollin", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[], emblem={}))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    await session.flush()
    return realm, town


async def host(session: AsyncSession, world: CoreWorld, owner: EntityRow, region: int, *, stacks: int = 1, size: int = 1000) -> EntityRow:
    army = await entity(
        session, f"Host {next(HOSTS)} of {owner.name}", EntityType.ARMY, ArmyStats(size=size), world_id=world.world.id, location_id=world.regions[region].id
    )
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner.id, raised_epoch=0))
    session.add(ArmyProfileRow(army_entity_id=army.id, region_entity_id=world.regions[region].id, stance=Stance.MARCH, supply_days=10, locked=[]))
    for _ in range(stacks):
        session.add(ArmyUnitRow(army_entity_id=army.id, kind=UnitKind.LINE_INFANTRY, count=size // stacks, organisation=40, locked=[]))
    await session.flush()
    return army


async def test_supply_flows_from_stocks_through_a_depot_and_what_arrives_is_what_was_drawn_less_what_was_lost(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "supply")
    realm, town = await realm_with_town(session, world)
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=400))
    depot = DepotRow(owner_entity_id=realm.id, region_entity_id=world.regions[0].id, capacity=500, locked=[])
    session.add(depot)
    session.add(TransportAssetRow(owner_entity_id=realm.id, kind=CarrierKind.WAGONS, count=10, capacity=10, locked=[]))
    army = await host(session, world, realm, 2)
    profile = await session.get(ArmyProfileRow, army.id)
    assert profile is not None
    profile.supply_line = [world.regions[0].id, world.regions[1].id, world.regions[2].id]
    march = March(army, realm, profile, world.regions[3].id, True)
    flows: list[SupplyFlowRow] = []
    for season in range(3):
        flow = await supply_season(ctx, march, season, raided=season == 1, order=EchelonOrder.ATTACK, web=await network(ctx), tally=SupplyTally())
        assert flow is not None
        flows.append(flow)
    produced = sum(flow.produced for flow in flows)
    assert produced > 0
    assert sum(flow.delivered for flow in flows) == produced - sum(flow.lost for flow in flows) - depot.supplies
    assert all(flow.delivered == flow.shipped - flow.lost for flow in flows)
    assert flows[1].lost > flows[0].lost


async def test_an_offensive_that_outruns_its_supply_culminates_and_a_logistician_pauses_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "culmination", rules=tuned_rules(culmination={"collapse_chance": 100}))
    realm, _ = await realm_with_town(session, world)
    general = await mortal(session, "Ilsa", world, world.regions[2].id)
    army = await host(session, world, realm, 2)
    army_row = await session.get(ArmyRow, army.id)
    assert army_row is not None
    army_row.commander_entity_id = general.id
    profile = await session.get(ArmyProfileRow, army.id)
    assert profile is not None
    starving = SupplyFlowRow(owner_entity_id=realm.id, army_entity_id=army.id, need=100, delivered=10, locked=[])
    march = March(army, realm, profile, None, True)
    cohesion = profile.cohesion
    row = await culminate(ctx, march, starving, SupplyTally())
    assert row.culminated and profile.cohesion < cohesion
    session.add(SkillRow(holder_node_id=general.id, skill=SkillKind.LOGISTICS, level=90, peak=90, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    profile.stance = Stance.MARCH
    row = await culminate(ctx, march, starving, SupplyTally())
    assert row.culminated and row.pause_seasons > 0 and profile.stance is Stance.ENTRENCH


async def test_an_army_forms_its_order_of_battle_and_formations_without_orders_lose_organisation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "order_of_battle")
    realm, _ = await realm_with_town(session, world)
    army = await host(session, world, realm, 1, stacks=7)
    await organise(ctx, CommandTally())
    echelons = list(await session.scalars(select(EchelonRow).where(EchelonRow.army_entity_id == army.id)))
    levels = [row.level for row in echelons]
    assert levels.count(EchelonLevel.ARMY) == 1 and levels.count(EchelonLevel.BRIGADE) == 3 and EchelonLevel.DIVISION in levels
    stacks = list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army.id)))
    assert all(stack.echelon_id is not None for stack in stacks)
    profile = await session.get(ArmyProfileRow, army.id)
    assert profile is not None
    top = next(row for row in echelons if row.level is EchelonLevel.ARMY)
    for row in echelons:
        row.command_points = 0
    before = sum(stack.organisation for stack in stacks)
    report = await issue_orders(ctx, army.id, profile, attacking=True, short=False, tally=CommandTally())
    assert report.standing == 3 and sum(stack.organisation for stack in stacks) < before
    assert await command_edge(ctx, army.id) < 1
    for row in echelons:
        row.command_points = 20
    report = await issue_orders(ctx, army.id, profile, attacking=True, short=False, tally=CommandTally())
    assert report.ordered == 3 and top.order is EchelonOrder.ATTACK
    assert await command_edge(ctx, army.id) > 1


async def test_the_marshal_shares_reserves_between_fronts_and_reinforces_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "theatres")
    realm, _ = await realm_with_town(session, world)
    rivals = [await entity(session, f"Rival {index}", EntityType.POLITY, PolityStats(), world_id=world.world.id) for index in range(2)]
    for rival in rivals:
        war = await open_war(ctx, realm, rival)
        army = await host(session, world, realm, 1)
        army_row = await session.get(ArmyRow, army.id)
        assert army_row is not None
        army_row.war_id = war.id
    await keep_theatres(ctx, TheatreTally())
    rows = list(await session.scalars(select(TheatreRow).where(TheatreRow.owner_entity_id == realm.id)))
    assert len(rows) == 2
    assert 95 <= sum(row.priority for row in rows) <= 100
    assert all(row.reserves > 0 for row in rows)


async def ship(session: AsyncSession, world: CoreWorld, owner: EntityRow, name: str, crew: int) -> tuple[EntityRow, VesselProfileRow]:
    vessel = await entity(session, name, EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    row = VesselProfileRow(
        entity_id=vessel.id, kind=VehicleKind.SHIP, crew=crew, cargo_capacity=50, condition=100, status=VesselStatus.AFLOAT, armament=[], locked=[]
    )
    session.add(row)
    await bond(session, owner.id, vessel.id, BondKind.OWNS)
    await session.flush()
    return vessel, row


async def test_a_ship_in_irons_is_raked_and_a_broken_ship_strikes_and_is_taken_as_a_prize(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "sail", rules=tuned_rules(age_of_sail={"strike_crew_pct": 95}))
    _, town = await realm_with_town(session, world)
    rival = await settlement(session, "Marsh", world, world.regions[3])
    hunter = await ship(session, world, town, "Gull", 60)
    prey = await ship(session, world, rival, "Heron", 60)
    stuck = await ship_state(ctx, prey[0].id)
    stuck.point_of_sail = PointOfSail.IN_IRONS
    stuck.locked = ["point_of_sail"]
    tally = SailTally()
    fight = await engage(ctx, hunter, prey, (2.0, 1.0), tally)
    assert stuck.raked > 0 and tally.raked > 0
    assert fight.struck and fight.loser.id == prey[0].id
    money = await take_prize(ctx, hunter[1], prey[0], prey[1], town)
    assert money > 0 and stuck.prize_of_entity_id == town.id and prey[1].crew == stuck.prize_crew > 0


async def test_a_fleet_past_its_treaty_limit_breaks_it_and_a_lawless_admiral_hides_ships_in_a_scheme(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "admiralty", rules=tuned_rules(admiralty={"cheat_share": 0, "max_commissions": 0}))
    realm, town = await realm_with_town(session, world)
    rival = await entity(session, "Marsh Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    admiral = await mortal(session, "Orla", world, world.regions[0].id)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.ADMIRAL, holder_entity_id=admiral.id, since_epoch=0, powers=[], locked=[]))
    for name in ("Gull", "Tern", "Skua"):
        await ship(session, world, town, name, 40)
    treaty = await sign(
        ctx,
        TreatyKind.NAVAL_LIMIT,
        [(realm.id, PartyRole.SIGNATORY), (rival.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.FLEET_LIMIT, realm.id, rival.id, {"tonnage": 100})],
    )
    tally = AdmiraltyTally()
    await keep_admiralty(ctx, realm, [realm.id, rival.id], tally)
    row = await session.get(AdmiraltyRow, realm.id)
    assert row is not None and row.limit_tonnage == 100 and row.tonnage > 100
    assert tally.schemes == 1
    assert await session.scalar(select(SchemeRow.id).where(SchemeRow.kind == PlotKind.HIDE_FLEET)) is not None
    clause = await session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty.id, TreatyClauseRow.kind == ClauseKind.FLEET_LIMIT))
    assert clause is not None and await over_limit(ctx, clause)
    profile = await session.get(TreatyProfileRow, treaty.id)
    assert profile is not None
    assert not await keep_clause(ctx, profile, clause, await MilitaryStrength.load(session, ctx.rules))
    assert await session.scalar(select(TreatyBreachRow.id).where(TreatyBreachRow.treaty_entity_id == treaty.id)) is not None
    row.concealed = row.tonnage
    assert not await over_limit(ctx, clause)


async def test_an_expedition_spends_provisions_and_light_and_the_dark_breaks_or_hardens_its_members(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "expeditions", rules=tuned_rules(expeditions={"resolve_at": 10, "quirk_chance": 100, "light_stock": 1}))
    leader = await mortal(session, "Ilse", world, world.regions[0].id)
    friend = await mortal(session, "Bram", world, world.regions[0].id)
    realm = await entity(session, "The Far Hall", EntityType.SPIRIT, SpiritStats(strength=40), world_id=world.world.id, location_id=world.regions[3].id)
    tally = ExpeditionTally()
    row = await launch(ctx, leader, realm, [friend], sponsor_id=None, tally=tally)
    assert row.ground is ExpeditionGround.REALM and row.light == 1
    provisions = row.provisions
    await advance(ctx, row, tally, row.legs_total)
    assert row.provisions < provisions and row.light == 0
    events = set(await session.scalars(select(ExpeditionLogRow.event).where(ExpeditionLogRow.expedition_id == row.id)))
    assert ExpeditionEvent.SETOUT in events and ExpeditionEvent.LEG in events
    assert events & {ExpeditionEvent.AFFLICTION, ExpeditionEvent.VIRTUE}
    assert await session.scalar(select(QuirkRow.id).where(QuirkRow.mortal_entity_id.in_([leader.id, friend.id]))) is not None
    assert row.status in {ExpeditionStatus.RETURNED, ExpeditionStatus.LOST}


async def test_quirks_change_how_a_member_fares_on_the_way(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "quirks")
    leader = await mortal(session, "Ilse", world, world.regions[0].id)
    land = world.regions[1]
    row = await launch(ctx, leader, land, [], sponsor_id=None, tally=ExpeditionTally())
    session.add(QuirkRow(mortal_entity_id=leader.id, kind=QuirkKind.EATS_ANYTHING, locked=[]))
    await session.flush()
    party = await party_of(ctx, row)
    before = row.provisions
    eat(ctx, party)
    assert row.provisions == before
    member = party.members[0]
    member.resolve = ResolveKind.SELFISH
    party.quirks[leader.id] = set()
    eat(ctx, party)
    assert row.provisions == before - 2
    lines = await mortal_operations_lines(await load_scope(session, ctx.rules), leader)
    assert any("eats anything" in line for line in lines) and any("expedition" in line for line in lines)


async def test_the_mend_drops_fronts_of_ended_wars_and_frees_stacks_from_another_armys_formation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "mend")
    realm, _ = await realm_with_town(session, world)
    rival = await entity(session, "Marsh Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    war = await open_war(ctx, realm, rival)
    session.add(TheatreRow(owner_entity_id=realm.id, war_id=war.id, locked=[]))
    first, second = await host(session, world, realm, 0), await host(session, world, realm, 1)
    brigade = EchelonRow(owner_entity_id=realm.id, army_entity_id=first.id, level=EchelonLevel.BRIGADE, name="Brigade 1", locked=[])
    session.add(brigade)
    await session.flush()
    stray = await session.scalar(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == second.id))
    assert stray is not None
    stray.echelon_id = brigade.id
    war.status = WarStatus.ENDED
    war.ended_epoch = war.started_epoch
    war.ending = WarEnding.EXHAUSTION
    await session.flush()
    assert await mend_operations_links(session) >= 2
    assert await session.scalar(select(TheatreRow.id)) is None
    await session.refresh(stray)
    assert stray.echelon_id is None


async def test_a_ship_is_laid_down_only_for_an_owner_that_can_hold_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "yards")
    realm, town = await realm_with_town(session, world)
    with pytest.raises(ValidationFailedError):
        await create_vessel(ctx, realm.id, "Crown Galley", Commission())
    vessel = await create_vessel(ctx, town.id, "Town Galley", Commission())
    owners = list(await session.scalars(select(BondRow.source_node_id).where(BondRow.target_node_id == vessel.id, BondRow.kind == BondKind.OWNS)))
    assert owners == [town.id]


async def test_each_event_of_an_expedition_is_logged_on_the_leg_it_happened_and_crew_stations_add_up_to_the_crew(
    session: AsyncSession, world: CoreWorld
) -> None:
    ctx = await manual_context(session, "legs")
    leader = await mortal(session, "Ilse", world, world.regions[0].id)
    row = await launch(ctx, leader, world.regions[1], [], sponsor_id=None, tally=ExpeditionTally())
    await advance(ctx, row, ExpeditionTally(), 1)
    legs = list(
        await session.scalars(select(ExpeditionLogRow.leg).where(ExpeditionLogRow.expedition_id == row.id, ExpeditionLogRow.event == ExpeditionEvent.LEG))
    )
    assert legs == [1]
    _, town = await realm_with_town(session, world)
    vessel, profile = await ship(session, world, town, "Gull", 0)
    await set_crew(ctx, vessel.id, CrewStation.GUNNERS, {"count": 24})
    await set_crew(ctx, vessel.id, CrewStation.TOPMEN, {"count": 6})
    assert profile.crew == 30
