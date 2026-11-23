from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

W = RuleGroup.WAR_AND_DIPLOMACY
X = RuleGroup.EXPLORATION
P = RuleGroup.POLITY


@dataclass(frozen=True)
class OrderOfBattleRules:
    stacks_per_brigade: int = rule(3, 1, 50, W, "Stacks a brigade holds before the army forms another")
    brigades_per_division: int = rule(3, 1, 50, W, "Brigades a division holds before the army forms another")
    divisions_per_corps: int = rule(3, 1, 50, W, "Divisions a corps holds; an army forms corps only past this many")
    armies_for_group: int = rule(2, 2, 50, W, "Armies a realm keeps at war before it groups them under one headquarters")
    base_points: int = rule(2, 0, 50, W, "Command points a headquarters has each campaign season before its staff")
    staff_points_pct: int = rule(6, 0, 100, W, "Command points a headquarters gains per hundred staff skill (%)")
    officer_staff: int = rule(10, 0, 100, W, "Staff skill each sub-commander and quartermaster adds to a headquarters")
    order_cost: int = rule(1, 0, 20, W, "Command points an order to one subordinate formation costs")
    attack_cost: int = rule(2, 0, 20, W, "Command points an order to attack costs")
    base_range: int = rule(2, 0, 20, W, "Regions a headquarters directs its subordinates across")
    signal_range: int = rule(1, 0, 20, W, "Regions signals and couriers add to a headquarters' range")
    standing_organisation: int = rule(6, 0, 100, W, "Organisation a stack loses in a season it acts on standing orders")
    attack_edge_pct: int = rule(8, 0, 100, W, "Edge an army gains in battle when all its formations hold orders to attack (%)")
    standing_edge_pct: int = rule(10, 0, 100, W, "Edge an army loses in battle when all its formations act on standing orders (%)")
    hold_entrench: int = rule(5, 0, 100, W, "Entrenchment an army gains in a season its formations hold orders to hold")
    manoeuvre_organisation: int = rule(4, 0, 100, W, "Organisation a stack regains in a season its formation holds orders to manoeuvre")


@dataclass(frozen=True)
class SupplyNetworkRules:
    depot_capacity: int = rule(600, 0, 1000000, W, "Supplies a depot at home holds for every thousand people of its realm (at least this much)")
    field_capacity: int = rule(200, 0, 1000000, W, "Supplies a field depot holds for every thousand soldiers of the army that founds it (at least this much)")
    field_hops: int = rule(3, 1, 50, W, "Regions an army may march from its nearest depot before it founds a field depot")
    draw_pct: int = rule(25, 0, 100, W, "Share of a realm's food stocks its depots draw in a campaign season (%)")
    need_per_hundred: int = rule(2, 0, 1000, W, "Supply points a hundred soldiers need each campaign season")
    attack_need_pct: int = rule(150, 0, 500, W, "Supply an army attacking needs against its common need (%)")
    rest_need_pct: int = rule(70, 0, 500, W, "Supply an army resting needs against its common need (%)")
    assets_per_thousand: int = rule(3, 0, 1000, W, "Wagons a realm keeps for every thousand soldiers when it first raises its train")
    road_throughput_pct: int = rule(130, 0, 500, W, "Throughput of a line whose lands all have roads (%)")
    river_throughput_pct: int = rule(150, 0, 500, W, "Throughput of barges along a line that follows a river (%)")
    hop_loss_pct: int = rule(4, 0, 100, W, "Share of supplies lost for each region they travel (%)")
    raided_loss_pct: int = rule(25, 0, 100, W, "Share of supplies lost on a line the enemy raided this season (%)")
    interdicted_pct: int = rule(25, 0, 100, W, "Share of its throughput a line keeps while an enemy army stands on it (%)")
    resupply_pct: int = rule(150, 100, 500, W, "Throughput a line carries in a season the army holds orders to resupply (%)")
    asset_wear: int = rule(5, 0, 100, W, "Condition transport loses in a campaign season of hauling")
    asset_repair: int = rule(10, 0, 100, W, "Condition transport regains in a season at peace")


@dataclass(frozen=True)
class CulminationRules:
    supply_pct: int = rule(60, 0, 100, W, "Share of its need below which an attacking army's supply falls short (%)")
    organisation: int = rule(55, 0, 100, W, "Organisation below which a short-supplied offensive reaches its culmination")
    pause_seasons: int = rule(1, 0, 20, W, "Seasons an army pauses once its offensive culminates")
    foresight_area: int = rule(40, 0, 100, W, "Logistics skill at which a commander sees the culmination coming and pauses in time")
    collapse_chance: int = rule(35, 0, 100, W, "Chance an army that attacks past its culmination collapses (%)")
    collapse_cohesion: int = rule(20, 0, 100, W, "Cohesion a collapsing army loses")
    collapse_morale: int = rule(15, 0, 100, W, "Morale every stack of a collapsing army loses")


@dataclass(frozen=True)
class TheatreRules:
    reserve_per_thousand: int = rule(8, 0, 1000, W, "Soldiers a realm holds in reserve for every thousand of its people")
    levy_per_thousand: int = rule(4, 0, 1000, W, "New levies a realm raises each epoch at war for every thousand of its people")
    reinforce_pct: int = rule(30, 0, 100, W, "Share of a theatre's reserves and levies that reach its army in an epoch (%)")
    error_pct: int = rule(40, 0, 100, W, "Largest error in a marshal's reading of a front's threat at no strategy skill (%)")
    misjudge_gap: int = rule(20, 0, 100, W, "Gap between the believed and true threat at which an allocation counts as misjudged")


@dataclass(frozen=True)
class LanchesterRules:
    square_reserve_pct: int = rule(100, 0, 100, W, "Share of their volley that missile and magic stacks held in reserve still loose (%)")
    linear_overlap_pct: int = rule(150, 100, 500, W, "Fighters that can engage the enemy's front in melee against its engaged number (%)")


@dataclass(frozen=True)
class AgeOfSailRules:
    irons_speed_pct: int = rule(0, 0, 100, W, "Speed of a ship caught in irons (%)")
    close_hauled_pct: int = rule(60, 0, 200, W, "Speed of a ship sailing close-hauled (%)")
    reaching_pct: int = rule(100, 0, 200, W, "Speed of a ship on a reach (%)")
    running_pct: int = rule(85, 0, 200, W, "Speed of a ship running before the wind (%)")
    oars_pct: int = rule(70, 0, 200, W, "Speed of a ship under oars, whatever the wind (%)")
    tack_chance: int = rule(55, 0, 100, W, "Chance a ship heading into the wind tacks cleanly before seamanship (%)")
    rower_fatigue: int = rule(15, 0, 100, W, "Fatigue rowers gain for each leg under oars")
    rower_rest: int = rule(20, 0, 100, W, "Fatigue rowers shed in a leg under sail or at anchor")
    rounds: int = rule(3, 1, 20, W, "Broadsides two ships exchange in a fight")
    base_hits: int = rule(2, 0, 50, W, "Hits a broadside lands before the rate of fire")
    rate_hits_per: int = rule(25, 1, 100, W, "Rate of fire that adds one more hit to a broadside")
    raking_pct: int = rule(200, 100, 500, W, "Hits a raking broadside lands along the length of a ship (%)")
    leak_per_hit: int = rule(8, 0, 100, W, "Water a hull hit lets in")
    pumping: int = rule(5, 0, 100, W, "Water the crew pumps out each broadside")
    founder_leak: int = rule(90, 1, 100, W, "Water at which a ship founders")
    fire_per_hit: int = rule(15, 0, 100, W, "Fire a burning shot starts on deck")
    fire_spread_pct: int = rule(130, 0, 500, W, "Spread of fire on a flammable deck (%)")
    fire_fought: int = rule(6, 0, 100, W, "Fire the crew puts out each broadside")
    magazine_fire: int = rule(70, 1, 100, W, "Fire at which the magazine may go up")
    magazine_chance: int = rule(40, 0, 100, W, "Chance the magazine explodes once fire reaches it (%)")
    grape_crew_pct: int = rule(6, 0, 100, W, "Share of the crew a grapeshot hit kills (%)")
    strike_crew_pct: int = rule(40, 0, 100, W, "Share of its crew below which a ship strikes its colours (%)")
    strike_condition: int = rule(30, 0, 100, W, "Condition below which a ship strikes its colours")
    prize_crew_pct: int = rule(15, 0, 100, W, "Share of the victor's crew sent aboard a prize (%)")
    prize_money_per_ton: int = rule(2, 0, 1000, W, "Prize money a taken ship pays its captors for each ton")
    officer_reload_pct: int = rule(30, 0, 100, W, "Share of the rate of fire the officers' command gives under fire (%)")


@dataclass(frozen=True)
class AdmiraltyRules(Spanned):
    base_share: int = rule(25, 0, 100, P, "Share of a realm's war budget its admiralty asks for at first (%)")
    request_step: int = rule(5, 0, 50, P, "Share the admiralty asks for above or below its grant each epoch (%)")
    influence_skill_pct: int = rule(50, 0, 100, P, "Weight of the admiral's skill in the admiralty's sway in council (%)")
    commission_share: int = rule(20, 1, 100, P, "Budget share that pays for one new ship each year (%)")
    max_commissions: int = rule(2, 0, 1000, P, "Most ships an admiralty orders in one year")
    ship_cost: int = rule(400, 0, 1000000, P, "Coin a new ship costs its realm")
    ships_per_ten_thousand: int = rule(3, 0, 1000, P, "Ships an admiralty keeps afloat for every ten thousand of its realm's people")
    treaty_chance: int = rule(10, 0, 100, P, "Chance in an epoch that two great naval powers at peace bind their fleets by treaty (%)")
    fleet_limit: int = rule(
        300, 0, 1000000, P, "Tonnage a fleet limit clause caps a realm at for every ten thousand of its people when it names none (at least this much)"
    )
    cheat_share: int = rule(50, 0, 100, P, "Disregard for law in its admiral at which an admiralty over its limit hides ships")
    discovery_chance: int = rule(15, 0, 100, P, "Chance in an epoch that a hidden fleet is found out by the treaty's other side (%)")


@dataclass(frozen=True)
class ExpeditionRules:
    launch_chance: int = rule(8, 0, 100, X, "Chance a free hero sets out on an expedition in an epoch (%)")
    launches: int = rule(3, 0, 10000, X, "Base of the most expeditions that set out in one epoch, grown by the number of leaders with companions")
    launches_leader_divisor: int = rule(5, 0, 10000, X, "Leaders with companions per extra expedition setting out in one epoch (0: the cap stays at its base)")
    legs_per_epoch: int = rule(3, 1, 50, X, "Legs an expedition travels in one epoch")
    party_size: int = rule(12, 1, 500, X, "Most companions a leader takes on an expedition")
    site_legs: int = rule(3, 1, 50, X, "Legs into a site")
    wilds_legs: int = rule(4, 1, 50, X, "Legs into the wilds")
    underworld_legs: int = rule(5, 1, 50, X, "Legs into an underworld stratum")
    realm_legs: int = rule(6, 1, 50, X, "Legs into a mythic realm")
    under_water_legs: int = rule(4, 1, 50, X, "Legs into the waters below")
    space_legs: int = rule(5, 1, 50, X, "Legs into the void between worlds, to a derelict or a drifting wreck")
    dimension_legs: int = rule(6, 1, 50, X, "Legs through a rift or a gate into another dimension")
    air_stock: int = rule(6, 0, 50, X, "Air a party packs for a ground where some of its members cannot breathe")
    air_per_leg: int = rule(1, 0, 10, X, "Air a leg uses while any member cannot breathe there")
    airless_hp: int = rule(25, 0, 1000, X, "Harm each member who cannot breathe takes on a leg once the air is gone")
    warder_effect: int = rule(
        40, 0, 100, X, "Strength of a warder against spirits, curses and phenomena; a quarter of it comes off the danger of each leg in the dark"
    )
    interpreter_effect: int = rule(40, 0, 100, X, "Chance an interpreter turns a night ambush into a bargain paid in provisions (%)")
    cartographer_effect: int = rule(30, 0, 100, X, "Map knowledge of the crossed land each cartographer gives its realm on a discovery")
    engineer_effect: int = rule(40, 0, 100, X, "Strength of an engineer in close places; a quarter of it comes off the danger of a site or an underworld")
    fearful_effect: int = rule(30, 0, 100, X, "Weight of a fearful member's flight; it is never the one struck in an ambush and will not walk the rooms")
    irrational_effect: int = rule(20, 0, 100, X, "Stress and danger an irrational member stirs up on a leg")
    compassionate_effect: int = rule(8, 0, 100, X, "Stress and exposure a compassionate member lifts from each companion each leg")
    inspired_effect: int = rule(10, 0, 100, X, "Stress an inspired member lifts from each companion each leg, and chance it adds to their finding a virtue (%)")
    lucky_escape: int = rule(50, 0, 100, X, "Chance a lucky member escapes the blow of a leg (%)")
    discovery_chance: int = rule(8, 0, 100, X, "Chance a leg turns up a discovery (%)")
    quarrel_chance: int = rule(20, 0, 100, X, "Chance two quarrelsome and strained members fall out on a leg and one leaves the party (%)")
    hard_way_legs_pct: int = rule(100, 0, 300, X, "More legs an expedition needs where its way of travel finds no passage at all, less as passage grows (%)")
    provisions_per_member: int = rule(3, 0, 50, X, "Provisions a party packs for each member")
    porter_provisions: int = rule(4, 0, 50, X, "Extra provisions each porter carries")
    light_stock: int = rule(6, 0, 50, X, "Light a party packs")
    light_per_leg: int = rule(1, 0, 10, X, "Light a leg burns")
    leg_stress: int = rule(6, 0, 200, X, "Stress each member gains on a leg")
    dark_stress: int = rule(12, 0, 200, X, "Stress each member gains on a leg in the dark")
    dark_danger_pct: int = rule(50, 0, 500, X, "Danger darkness adds against the party (%)")
    harm_stress: int = rule(20, 0, 200, X, "Stress a member gains when harmed")
    ambush_chance: int = rule(12, 0, 100, X, "Chance of a night ambush on a camp (%)")
    camp_stress: int = rule(15, 0, 200, X, "Stress a camp lifts")
    camp_fatigue: int = rule(30, 0, 100, X, "Fatigue a camp lifts")
    leg_fatigue: int = rule(12, 0, 100, X, "Fatigue a leg adds")
    cold_per_leg: int = rule(10, 0, 100, X, "Cold a leg in a cold land adds")
    wet_per_leg: int = rule(10, 0, 100, X, "Wet a leg in rain adds")
    hunger_step: int = rule(25, 0, 100, X, "Hunger a leg without provisions adds")
    exposure_harm: int = rule(80, 1, 100, X, "Exposure at which a member takes harm")
    exposure_hp: int = rule(12, 0, 1000, X, "Harm exposure deals")
    resolve_at: int = rule(100, 1, 200, X, "Stress at which a member's resolve is tested")
    virtue_chance: int = rule(25, 0, 100, X, "Chance a tested member finds a virtue instead of an affliction (%)")
    abusive_stress: int = rule(8, 0, 200, X, "Stress an abusive member lays on each companion each leg")
    courage_relief: int = rule(6, 0, 200, X, "Stress a courageous member lifts from each companion each leg")
    breaking_stress: int = rule(200, 1, 200, X, "Stress at which a member's heart gives out")
    breaking_hp: int = rule(30, 0, 1000, X, "Harm a heart giving out deals")
    quirk_chance: int = rule(10, 0, 100, X, "Chance a leg leaves a member with a quirk (%)")
    scout_danger: int = rule(8, 0, 100, X, "Danger each scout or guide takes off the party")
    healer_relief: int = rule(10, 0, 100, X, "Exposure a healer lifts from each member each leg while medicine lasts")
    fighter_guard_pct: int = rule(20, 0, 100, X, "Share of an ambush's harm each fighter turns aside (%)")
    scholar_find: int = rule(1, 0, 20, X, "Finds each scholar reads out of the inscriptions of a leg")
    tool_danger: int = rule(10, 0, 100, X, "Danger a tool spent on a leg in a site, an underworld or another realm takes off")
    find_coin: int = rule(30, 0, 100000, X, "Coin each find brings its leader home")
