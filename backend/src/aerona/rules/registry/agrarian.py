from dataclasses import dataclass
from math import ceil

from aerona.rules.groups import RuleGroup
from aerona.rules.model import FULL_PROGRESS, Spanned, rule, span

E = RuleGroup.ENVIRONMENT
C = RuleGroup.CIVILIZATION
M = RuleGroup.MARKETS_AND_MONEY
W = RuleGroup.CREATURES
P = RuleGroup.POLITY


@dataclass(frozen=True)
class ThunenRules:
    hop_cost: int = rule(100, 1, 10000, M, "Cost of carrying goods one region overland to a market")
    river_cost_pct: int = rule(50, 1, 100, M, "Share of the overland cost a hop costs where both lands lie on a river (%)")
    road_cost_pct: int = rule(70, 1, 100, M, "Share of the overland cost a hop costs into a land with roads (%)")
    canal_cost_pct: int = rule(40, 1, 100, M, "Share of the overland cost a hop costs into a land with a canal (%)")
    forestry_reach: int = rule(60, 0, 100000, M, "Carrying cost up to which a land beside the market grows fuel wood")
    grain_reach: int = rule(220, 0, 100000, M, "Carrying cost up to which a land grows grain for the market")
    ranching_reach: int = rule(400, 0, 100000, M, "Carrying cost up to which a land raises herds for the market")
    gardens_farm_pct: int = rule(120, 0, 300, M, "Fields a market's own land ploughs against the common share (%)")
    gardens_graze_pct: int = rule(60, 0, 300, M, "Pasture a market's own land keeps against the common share (%)")
    forestry_farm_pct: int = rule(90, 0, 300, M, "Fields a land of fuel wood ploughs against the common share (%)")
    forestry_graze_pct: int = rule(60, 0, 300, M, "Pasture a land of fuel wood keeps against the common share (%)")
    grain_farm_pct: int = rule(115, 0, 300, M, "Fields a land of grain ploughs against the common share (%)")
    grain_graze_pct: int = rule(80, 0, 300, M, "Pasture a land of grain keeps against the common share (%)")
    ranching_farm_pct: int = rule(60, 0, 300, M, "Fields a land of herds ploughs against the common share (%)")
    ranching_graze_pct: int = rule(150, 0, 300, M, "Pasture a land of herds keeps against the common share (%)")
    industry_farm_pct: int = rule(40, 0, 300, M, "Fields a land given over to works ploughs against the common share (%)")
    industry_graze_pct: int = rule(30, 0, 300, M, "Pasture a land given over to works keeps against the common share (%)")
    industry_pollution: int = rule(3, 0, 100, M, "Foul air a land given over to works sends into the lands beside it each epoch")
    fallow_farm_pct: int = rule(20, 0, 300, M, "Fields a land left fallow still ploughs against the common share (%)")
    fallow_graze_pct: int = rule(110, 0, 300, M, "Pasture a land left fallow keeps against the common share (%)")
    fallow_below: int = rule(35, 0, 100, M, "Soil fertility below which a land of grain is left fallow to rest")


@dataclass(frozen=True)
class CentralPlaceRules:
    weekly_range: int = rule(1, 0, 20, C, "Regions people travel to a market for the goods of every week")
    rare_range: int = rule(3, 0, 20, C, "Regions people travel to a city for rare goods")
    weekly_threshold: int = rule(3000, 1, 100000000, C, "People within reach a market needs to sell the goods of every week")
    rare_threshold: int = rule(15000, 1, 100000000, C, "People within reach a city needs to sell rare goods")
    weekly_centrality: int = rule(40, 0, 100, C, "Centrality a market of weekly goods starts from")
    rare_centrality: int = rule(70, 0, 100, C, "Centrality a city of rare goods starts from")
    seasonal_threshold: int = rule(8000, 1, 100000000, C, "People within reach a fair town needs to draw traders in its season")
    seasonal_range: int = rule(2, 0, 50, C, "Regions people travel to a fair town outside its season")
    seasonal_centrality: int = rule(55, 0, 100, C, "Centrality a fair town starts from")
    fair_reach_pct: int = rule(150, 0, 500, C, "How much farther traders travel to a fair town in its season (%)")
    metropolitan_threshold: int = rule(60000, 1, 100000000, C, "People within reach the top market of a world needs")
    metropolitan_range: int = rule(6, 0, 100, C, "Regions people travel to the top market of a world")
    metropolitan_centrality: int = rule(90, 0, 100, C, "Centrality the top market of a world starts from")
    regional_threshold: int = rule(5000, 1, 100000000, C, "People within reach a regional market needs to set the prices of its region")
    regional_range: int = rule(2, 0, 50, C, "Regions people travel to a regional market")
    regional_centrality: int = rule(45, 0, 100, C, "Centrality a regional market starts from")
    catchment_centrality: int = rule(30, 0, 100, C, "Most centrality a place gains from the buyers within its reach")
    tier_pct: int = rule(30, 0, 200, C, "How much full centrality counts as more people when a settlement grows into a larger tier (%)")
    gap_from: int = rule(200, 0, 100000, C, "Carrying cost to the nearest market beyond which a land counts as a gap between markets")
    gap_span: int = rule(300, 1, 100000, C, "Carrying cost over the gap mark at which the gap is full")
    gap_pull_pct: int = rule(60, 0, 300, C, "How much a full gap between markets draws migrants to found a settlement there (%)")
    settle_gap: int = rule(50, 0, 100, C, "Gap between markets a neighbouring land needs before a people founds its next village there")


@dataclass(frozen=True)
class BoserupRules:
    onset: int = rule(70, 0, 300, E, "Population against the land's capacity at which farmers begin to work the land harder (%)")
    intensity_pct: int = rule(60, 0, 300, E, "Labour per land gained for each point of pressure over the onset (%)")
    boost_pct: int = rule(50, 0, 300, E, "Research boost to farming gained for each point of pressure over the onset (%)")
    boost_cap: int = rule(60, 0, 100, E, "Most research boost population pressure gives to farming (%)")
    drift_pct: int = rule(30, 0, 100, E, "Share of the gap to its target the labour on the land closes each epoch (%)")
    harvest_pct: int = rule(25, 0, 100, E, "Harvest gained when the land is worked at full intensity (%)")
    method_pct: int = rule(100, 0, 300, E, "How much the research boost raises the worth of intensive farming methods (%)")


@dataclass(frozen=True)
class NutrientRules:
    fixed_draw: int = rule(5, 0, 100, E, "Fixed element the crops draw from fully farmed land each epoch")
    mineral_draw: int = rule(2, 0, 100, E, "Mineral the crops draw from fully farmed land each epoch")
    organic_draw: int = rule(3, 0, 100, E, "Organic matter the crops draw from fully farmed land each epoch")
    rotation_fix: int = rule(5, 0, 100, E, "Fixed element rotations with legumes return to the land each epoch")
    seed_build: int = rule(6, 0, 100, E, "Seeds a fully wooded or wild land lays into its soil each epoch")
    seed_draw: int = rule(4, 0, 100, E, "Seeds lying in the soil that clearing and ploughing spend each epoch on fully cleared land")
    seed_regrowth_pct: int = rule(100, 0, 400, E, "How much faster scars heal on land whose soil holds a full store of seeds (%)")
    soil_life_follow_pct: int = rule(50, 0, 100, E, "Share of the gap to the life of its soil the soil life stock closes each epoch (%)")
    fallow_pct: int = rule(6, 0, 100, E, "Fixed element fully fallow land regains each epoch")
    manure_pct: int = rule(6, 0, 100, E, "Organic matter and fixed element fully grazed land regains from manure each epoch")
    litter_pct: int = rule(3, 0, 100, E, "Organic matter full forest cover returns to the soil each epoch")
    fodder_fix: int = rule(6, 0, 100, E, "Fixed element a land sown wholly with fodder crops regains each epoch")
    root_mineral: int = rule(3, 0, 100, E, "Extra mineral a land sown wholly with root crops loses each epoch")
    erosion_pct: int = rule(10, 0, 100, E, "Organic matter full erosion washes away each epoch")
    river_silt: int = rule(2, 0, 100, E, "Mineral a river leaves on its lands each epoch")
    flood_mineral: int = rule(10, 0, 100, E, "Mineral a flood leaves on the land it covers")
    ash_mineral: int = rule(20, 0, 100, E, "Mineral the ash of an eruption leaves on the land")
    recovery_divisor: int = rule(6, 1, 1000, E, "Epochs over which an unworked soil returns toward its natural stock")
    irrigation_salt: int = rule(3, 0, 100, E, "Salt each level of irrigation without drainage leaves in the land each epoch")
    leach: int = rule(1, 0, 100, E, "Salt the rains wash from land that is not irrigated each epoch")
    salinity_weight: int = rule(100, 0, 300, E, "How much salt in the soil lowers its fertility (%)")
    noted_salinity: int = rule(40, 0, 100, E, "Salt in a land at which its salting is recorded")


@dataclass(frozen=True)
class PerennialRules(Spanned):
    orchard_years: int = span(5, 1, 2500, E, "Years an orchard takes to bear fully")
    plantation_years: int = span(7, 1, 2500, E, "Years a plantation takes to bear")
    forest_garden_years: int = span(15, 1, 2500, E, "Years a forest garden takes to bear")
    vineyard_years: int = span(4, 1, 2500, E, "Years a vineyard takes to bear fully")
    grove_years: int = span(20, 1, 2500, E, "Years a grove takes to bear fully")
    timber_years: int = span(30, 1, 2500, E, "Years a timber plantation takes to be felled")
    coppice_years: int = span(8, 1, 2500, E, "Years a coppice of trees cut to regrow takes before its first cutting")
    hedgerow_years: int = span(10, 1, 2500, E, "Years a hedgerow at the edge of fields takes to grow thick")
    palm_stand_years: int = span(8, 1, 2500, E, "Years a stand of palms takes to bear")
    coppice_fuel: int = rule(2, 0, 100, E, "Fuel a grown coppice yields its owner each epoch for each point of area")
    plant_pct: int = rule(25, 0, 100, E, "Chance each epoch a settled land with a long-lived crop plants it (%)")
    area: int = rule(5, 1, 100, E, "Share of a land a new planting covers")
    coin_per_area: int = rule(20, 0, 100000, E, "Coin a fully grown planting yields its owner each epoch for each point of area")
    prosperity_cap: int = rule(2, 0, 100, E, "Most prosperity the plantings of a land add to its settlements in an epoch")
    recover: int = rule(10, 0, 100, E, "Condition a damaged planting regains each epoch")
    felling_pct: int = rule(50, 0, 100, E, "Share of the growth of a land's plantings an army cuts down when it lays the land waste (%)")
    raid_felling_pct: int = rule(15, 0, 100, E, "Share of the growth of a land's plantings raiders and invaders cut down as they plunder (%)")
    life_pct: int = rule(600, 100, 10000, E, "Epochs a grown planting bears before it ages, against the epochs it took to grow (%)")
    ageing: int = rule(10, 0, 100, E, "Condition an old planting loses each epoch until it is replanted")

    @property
    def orchard_epochs(self) -> int:
        return self.epochs(self.orchard_years)

    @property
    def plantation_epochs(self) -> int:
        return self.epochs(self.plantation_years)

    @property
    def forest_garden_epochs(self) -> int:
        return self.epochs(self.forest_garden_years)

    @property
    def vineyard_epochs(self) -> int:
        return self.epochs(self.vineyard_years)

    @property
    def grove_epochs(self) -> int:
        return self.epochs(self.grove_years)

    @property
    def timber_epochs(self) -> int:
        return self.epochs(self.timber_years)


@dataclass(frozen=True)
class CommonsRules:
    pasture_grazed: int = rule(15, 0, 100, E, "Grazed share at which a land's pasture is held in common")
    woods_forest: int = rule(25, 0, 100, E, "Forest cover at which a land's woods are held in common")
    water_rain: int = rule(60, 0, 100, E, "Rainfall at which a land's waters are held in common")
    wild_built: int = rule(20, 0, 100, E, "Built share below which wooded land is a common hunting ground")
    source_density: int = rule(50, 0, 100, E, "Magic density at which a land's source ground is held in common")
    sustainable: int = rule(60, 0, 200, E, "Use of a common it bears without wearing down")
    degrade_pct: int = rule(20, 0, 100, E, "Condition lost each epoch for each point of use over what a common bears (%)")
    council_pct: int = rule(20, 0, 100, E, "Share of the wear a council that rules a common still lets happen (%)")
    enclosed_pct: int = rule(50, 0, 100, E, "Share of the wear an enclosed common still suffers (%)")
    state_pct: int = rule(40, 0, 100, E, "Share of the wear a common held by a realm's officials still suffers (%)")
    licensed_pct: int = rule(60, 0, 100, E, "Share of the wear a common used by permit still suffers (%)")
    rotational_pct: int = rule(30, 0, 100, E, "Share of the wear a common its households take in turns by year still suffers (%)")
    rotational_calm: int = rule(2, 0, 100, E, "Public order the folk of a common held in turns regain each epoch as quarrels over it ease")
    rotational_at: int = rule(25, 0, 100, E, "Condition under which the folk forming a council over a worn common take it in turns by year")
    turbary_peat: int = rule(30, 0, 100, E, "Wetland at which a land's peat cutting is held in common, and below which its coast is a shore for gathering")
    state_enforcement: int = rule(50, 0, 100, E, "Strength of the officials a realm sets over a common it takes")
    state_grievance: int = rule(10, 0, 100, E, "Public order the folk of a common lose each epoch while a realm's officials hold it")
    state_coin: int = rule(20, 0, 100000, E, "Coin a common held by a realm in full condition yields its treasury each epoch")
    licence_price: int = rule(10, 0, 1000, E, "Coin a permit for each point of a common's quota costs each epoch")
    licence_concentration_pct: int = rule(
        20, 0, 100, E, "Share of a licensed common's yield the poorer towns of its land lose as permits gather in few hands (%)"
    )
    poaching_pct: int = rule(30, 0, 100, E, "Chance use beyond a common's quota slips past weak officials as poaching in an epoch (%)")
    state_take_pct: int = rule(30, 0, 100, E, "Share of a ruler's moves on a common that set officials over it instead of enclosing it (%)")
    licensed_take_pct: int = rule(20, 0, 100, E, "Share of a ruler's moves on a common that sell its use by permit instead of enclosing it (%)")
    regrow: int = rule(4, 0, 100, E, "Condition a common regains each epoch while it is used within its bearing")
    prosperity_weight: int = rule(4, 0, 100, E, "Most prosperity a common in good condition adds to the settlements of its land, or a worn one takes")
    council_at: int = rule(45, 0, 100, E, "Condition under which the folk of a common may form a council to rule it")
    council_chance: int = rule(30, 0, 100, E, "Chance each epoch a worn common gets a council where the town keeps order (%)")
    council_order: int = rule(50, 0, 100, E, "Public order a steward town needs to form a council")
    enclose_pct: int = rule(1, 0, 100, P, "Chance each epoch a ruler orders the commons of a town of its realm enclosed, for each common it holds (%)")
    horizon_mark: int = rule(40, 0, 100, P, "Time horizon under which a ruler is twice as eager to enclose")
    labour_span: int = rule(
        50, 1, 1000000, P, "Dispossessed folk already in a realm, per 1000 of its subjects, that double the profit a ruler sees in enclosure"
    )
    dispossess_pct: int = rule(8, 0, 100, P, "Share of the people of a land driven off when its common is enclosed (%)")
    sol_loss: int = rule(6, 0, 100, P, "Prosperity the settlements of a land lose when its common is enclosed")
    unrest_gain: int = rule(10, 0, 100, P, "Unrest the settlements of a land gain when its common is enclosed")
    enclosed_coin: int = rule(30, 0, 100000, P, "Coin an enclosed common in full condition yields its owner each epoch")
    freehold_pct: int = rule(300, 0, 1000, P, "How much a law of freehold tenure multiplies the chance of enclosure (%)")
    communal_pct: int = rule(25, 0, 1000, P, "How much a law of communal tenure multiplies the chance of enclosure (%)")
    household_loss: int = rule(20, 0, 100, P, "Share of their wealth the households of farmers and the bound lose when their common is enclosed (%)")


@dataclass(frozen=True)
class GameLawRules:
    forest_at: int = rule(35, 0, 100, W, "Forest cover a land needs before its lord reserves its game")
    wealth_at: int = rule(40, 0, 100, W, "Wealth of a house or lord at which it reserves the game of its land")
    reserve_pct: int = rule(10, 0, 100, W, "Chance each epoch a rich house reserves the game of its seat's land (%)")
    protect_pct: int = rule(80, 0, 100, W, "Share of the hunting a fully strict reserve stops (%)")
    hunger_poach: int = rule(60, 0, 300, W, "Poaching a land gains for each point of failed harvest (%)")
    poverty_poach: int = rule(40, 0, 300, W, "Poaching a land gains for each point of poverty in its settlements (%)")
    deter_pct: int = rule(50, 0, 100, W, "Share of the poaching a fully strict reserve deters (%)")
    drift_pct: int = rule(30, 0, 100, W, "Share of the gap to its target poaching and resentment close each epoch (%)")
    crime_pct: int = rule(10, 0, 100, W, "Crime the settlements of a land gain for full poaching")
    punish_at: int = rule(50, 0, 100, W, "Poaching at which a strict holder punishes poachers")
    resentment_pct: int = rule(60, 0, 300, W, "Resentment gained for each point of strictness that meets poaching (%)")
    regard_loss: int = rule(8, 0, 100, W, "Regard the folk of a land lose for the holder of its reserve when resentment is full")
    unrest_gain: int = rule(4, 0, 100, W, "Unrest the settlements of a land gain when poachers are punished")


@dataclass(frozen=True)
class FamineFoodRules(Spanned):
    per_famine: int = rule(25, 0, 100, E, "Famine memory each remembered hungry year adds to a people")
    memory_years: int = span(60, 1, 25000, E, "Years a people counts its hungry years")
    per_generation: int = rule(20, 0, 100, E, "Famine memory each living generation formed by a famine adds to its people")
    fade_pct: int = rule(10, 0, 100, E, "Share of its famine memory a people forgets each epoch as generations pass (%)")
    foods_at: int = rule(40, 0, 100, E, "Famine memory at which a people learns its famine foods")
    storage_pct: int = rule(80, 0, 200, E, "Share of its famine memory a people's tradition of storing food grows toward (%)")
    drift_pct: int = rule(25, 0, 100, E, "Share of the gap to its target the storage tradition closes each epoch (%)")
    floor: int = rule(60, 0, 100, E, "Harvest below which famine foods and stores are drawn on")
    foods_fill: int = rule(40, 0, 100, E, "Share of a failed harvest famine foods make good (%)")
    storage_fill: int = rule(40, 0, 100, E, "Share of a failed harvest a full storage tradition makes good (%)")
    health_cost: int = rule(6, 0, 100, E, "Sickness a land gains in an epoch its people live on famine foods")

    @property
    def memory_epochs(self) -> int:
        return self.epochs(self.memory_years)


@dataclass(frozen=True)
class ResilienceRules(Spanned):
    cost: int = rule(150, 0, 1000000, C, "Investment a town pays for each level of a disaster work")
    per_level_pct: int = rule(12, 0, 100, C, "Disaster losses each level of a fitting work prevents (%)")
    watch_pct: int = rule(4, 0, 100, C, "Disaster losses each level of watchtowers prevents of any kind (%)")
    cap_pct: int = rule(70, 0, 100, C, "Most disaster losses works can prevent (%)")
    noted_pct: int = rule(20, 0, 100, C, "Losses prevented at which the works that held are recorded")
    decay: int = rule(3, 0, 100, C, "Condition a disaster work loses each epoch")
    memory_years: int = span(50, 1, 25000, C, "Years a town remembers the disasters that struck it when it chooses what to build")
    fire_risk_at: int = rule(40, 0, 100, C, "Fire risk at which a town wants firebreaks")

    @property
    def memory_epochs(self) -> int:
        return self.epochs(self.memory_years)


@dataclass(frozen=True)
class ReliefRules:
    givers: int = rule(10, 0, 1000, P, "Most realms and cults that send aid to one stricken town")
    regard_at: int = rule(-10, -100, 100, P, "Regard a realm needs for a stricken town before it sends aid")
    chance_pct: int = rule(50, 0, 100, P, "Chance a realm or cult that can sends aid (%)")
    share_pct: int = rule(5, 0, 100, P, "Share of its treasury a realm sends as aid (%)")
    cap: int = rule(200, 0, 10000000, P, "Most coin one gift of aid carries, per 1000 people of the stricken town")
    coin_per_prosperity: int = rule(100, 1, 1000000, P, "Coin of goods that restores one point of a town's prosperity")
    grain: int = rule(40, 0, 1000000, P, "Grain a gift of goods carries from the giver's capital, per 1000 people of the stricken town")
    prosperity_cap: int = rule(8, 0, 100, P, "Most prosperity aid restores to a town in an epoch")
    healer_disease: int = rule(10, 0, 100, P, "Sickness healers sent as aid take from a stricken land")
    labour_progress: int = rule(15, 0, 100, P, "Progress labour sent as aid adds to a town's rebuilding")
    shelter_relief: int = rule(10, 0, 100, P, "Unrest shelter sent as aid takes from a stricken town")
    soldiers_sent: int = rule(10, 0, 100000, P, "Militia soldiers sent as aid add to a threatened town, per 1000 of its people")
    favour: int = rule(20, 0, 100, P, "Size of the favour a town's ruler owes for aid")
    love: int = rule(8, 0, 100, P, "Love a town gains for the god of those who sent it aid")
    refuse_below: int = rule(-30, -100, 100, P, "Regard under which a stricken realm refuses the aid of a rival")
    face_loss: int = rule(6, 0, 100, P, "Honour a ruler loses for refusing aid in a stricken hour, doubled in a culture of face")
    granary_cost: int = rule(60, 0, 500, P, "Coin for every thousand people of the realm that grain kept against hunger costs each epoch")
    granary_effect: int = rule(100, 0, 100, P, "Strength of grain kept against hunger at full reach (%)")
    alms_cost: int = rule(40, 0, 500, P, "Coin for every thousand people of the realm that alms handed to the poor costs each epoch")
    alms_effect: int = rule(100, 0, 100, P, "Strength of alms handed to the poor at full reach (%)")
    workhouse_cost: int = rule(
        50, 0, 500, P, "Coin for every thousand people of the realm that a workhouse that feeds the poor for their work costs each epoch"
    )
    workhouse_effect: int = rule(100, 0, 100, P, "Strength of a workhouse that feeds the poor for their work at full reach (%)")
    parish_cost: int = rule(40, 0, 500, P, "Coin for every thousand people of the realm that relief given through the parishes of a faith costs each epoch")
    parish_effect: int = rule(100, 0, 100, P, "Strength of relief given through the parishes of a faith at full reach (%)")
    foster_care_cost: int = rule(50, 0, 500, P, "Coin for every thousand people of the realm that foster care of orphans costs each epoch")
    foster_care_effect: int = rule(30, 0, 100, P, "Strength of foster care of orphans at full reach (%)")
    sick_house_cost: int = rule(
        70, 0, 500, P, "Coin for every thousand people of the realm that houses for the sick and those shunned for their illness costs each epoch"
    )
    sick_house_effect: int = rule(30, 0, 100, P, "Strength of houses for the sick and those shunned for their illness at full reach (%)")
    pension_cost: int = rule(80, 0, 500, P, "Coin for every thousand people of the realm that pensions for veterans, the maimed and the old costs each epoch")
    pension_effect: int = rule(10, 0, 100, P, "Strength of pensions for veterans, the maimed and the old at full reach (%)")
    public_kitchen_cost: int = rule(8, 0, 100, P, "Coin a public kitchen costs each epoch for each level of the town")
    public_kitchen_effect: int = rule(30, 0, 100, P, "Share of a city's hunger a public kitchen eases at full reach (%)")
    shelter_cost: int = rule(5, 0, 100, P, "Coin a night shelter costs each epoch for each level of the town")
    shelter_effect: int = rule(35, 0, 100, P, "Share of deaths from exposure a night shelter spares at full reach (%)")
    transport_progress: int = rule(15, 0, 100, P, "Progress carts and ships of aid add to a town's rebuilding")


@dataclass(frozen=True)
class ReconstructionRules(Spanned):
    cost: int = rule(300, 0, 10000000, C, "Coin a rebuilding costs for each tier of the town")
    planned_pct: int = rule(180, 100, 1000, C, "Cost of a planned rebuilding against a hasty one (%)")
    architecture_level: int = rule(2, 0, 10, C, "Architecture a town needs to plan its rebuilding")
    pay_pct: int = rule(25, 0, 100, C, "Share of its treasury a town pays toward its rebuilding each epoch (%)")
    planned_years: int = span(10, 1, 2000, C, "Years a planned rebuilding takes while it is paid")
    hasty_years: int = span(3, 1, 2000, C, "Years a hasty rebuilding takes")
    restore: int = rule(30, 0, 100, C, "Condition a finished rebuilding restores to every district")
    fire_cut: int = rule(15, 0, 100, C, "Fire risk a planned rebuilding takes away")
    seize_pct: int = rule(25, 0, 100, C, "Chance an elite seizes the burned land of a town it holds (%)")
    seize_share: int = rule(5, 0, 100, C, "Share of a town's people put out of their homes when an elite seizes the burned land (%)")
    seize_coin: int = rule(100, 0, 10000000, C, "Coin the land an elite seizes is worth to it, per 100 people put out of their homes")
    seize_unrest: int = rule(8, 0, 100, C, "Unrest a town gains when an elite seizes its burned land")

    @property
    def planned_step(self) -> int:
        return ceil(FULL_PROGRESS / max(1, self.epochs(self.planned_years)))

    @property
    def hasty_step(self) -> int:
        return ceil(FULL_PROGRESS / max(1, self.epochs(self.hasty_years)))


@dataclass(frozen=True)
class KeystoneResourceRules:
    designate_pct: int = rule(5, 0, 100, M, "Chance each epoch a world without one comes to depend on a rare yield held sacred (%)")
    unique_ranges: int = rule(2, 1, 100, M, "Most lands a producer may live in for its yield to be a world's keystone")
    harm_pct: int = rule(20, 0, 300, M, "Producers lost each epoch for each point of harvest (%)")
    full_abundance: int = rule(60, 1, 100000, M, "Producers in the source land at which the supply is full")
    genesis_epochs: int = rule(2, 0, 1000, M, "Epochs after a world is made in which it comes to depend on a rare sacred yield whenever one exists")
    renewal: int = rule(10, 0, 100, M, "Supply a keystone with a producer that is not a living species regains each epoch")
    designate_abundance: int = rule(30, 0, 100000, M, "Producers a rare yield needs in its land before a world comes to depend on it")
    price_swing: int = rule(150, 0, 1000, M, "How much the price rises for each point the supply falls under half (%)")
    coin_per_point: int = rule(8, 0, 100000, M, "Coin the controller of the source earns each epoch for each point of harvest at full supply")
    scarce_at: int = rule(30, 0, 100, M, "Supply under which the keystone counts as scarce")
    dependent_loss: int = rule(3, 0, 100, M, "Prosperity, piety, health or legitimacy those who depend on it lose in a scarce epoch")
    cult_regard: int = rule(10, 0, 100, M, "Regard the holding cult loses for a controller who lets the keystone run scarce")
    envy: int = rule(5, 0, 100, M, "Regard each realm that depends on it loses for the controller each epoch")
    war_pct: int = rule(10, 0, 100, M, "Chance each scarce epoch the realm that most envies the controller goes to war for the source (%)")
    envy_at: int = rule(-40, -100, 100, M, "Regard at which a realm is envious enough to fight for the source")


@dataclass(frozen=True)
class BrandRules:
    level: int = rule(2, 1, 10, M, "Workshop level at which its makers earn a brand")
    quality: int = rule(60, 0, 100, M, "Mean quality of a workshop's work at which it earns a brand")
    drift_pct: int = rule(25, 0, 100, M, "Share of the gap to its target a brand's reputation closes each epoch (%)")
    renown_pct: int = rule(5, 0, 100, M, "Reputation each renowned work of the town adds")
    counterfeit_pct: int = rule(20, 0, 100, M, "Counterfeits a famous brand draws in a town of full crime (%)")
    erosion_pct: int = rule(30, 0, 100, M, "Reputation lost for full counterfeiting (%)")
    premium_pct: int = rule(30, 0, 300, M, "Price premium a fully famous brand earns on its goods (%)")
    coin_cap: int = rule(100, 0, 10000000, M, "Most coin a brand earns its owner in an epoch, per 1000 people of its town")
    prosperity_cap: int = rule(2, 0, 100, M, "Most prosperity a famous brand adds to its town in an epoch")
