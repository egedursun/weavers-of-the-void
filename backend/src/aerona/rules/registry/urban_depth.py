from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.SETTLEMENTS
P = RuleGroup.POLITY
M = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class DesirabilityRules:
    amenity: int = rule(
        6,
        0,
        100,
        S,
        "Desirability each amenity (temple, market, bathhouse, monument, theatre, arena, aqueduct, library, wonder) gives the districts it reaches",
    )
    nuisance: int = rule(
        8, 0, 100, S, "Desirability each nuisance (tannery, prison, forge, mill, mine, quarry, slums, graves) takes from the districts it reaches"
    )
    crime_pct: int = rule(30, 0, 200, S, "Share of the town's crime taken from every district's desirability (%)")
    haunting: int = rule(10, 0, 100, S, "Desirability a restless spirit in the town takes from every district")
    prestige_pct: int = rule(30, 0, 200, S, "Share of the town's prestige added to every district's desirability (%)")
    drift: int = rule(10, 1, 100, S, "Land value a district moves toward its desirability each epoch")
    gentrify_at: int = rule(75, 0, 100, S, "Land value past which a district's poor are priced out")
    rent: int = rule(10, 0, 1000, S, "Coin a household pays each epoch at full land value in its town")
    pollution_pct: int = rule(20, 0, 200, S, "Share of its land's air and water pollution taken from every district's desirability (%)")
    artwork: int = rule(4, 0, 100, S, "Desirability each artwork kept in a town gives its districts")
    gentrify_homeless: int = rule(4, 0, 100, S, "Share of a priced-out district's people left without a home each epoch (%)")


@dataclass(frozen=True)
class CoverageRules:
    planned_reach: int = rule(70, 0, 100, S, "Share of a service a planned town carries to its other districts (%)")
    concentric_reach: int = rule(50, 0, 100, S, "Share of a service a ringed town carries to its other districts (%)")
    organic_reach: int = rule(35, 0, 100, S, "Share of a service a town grown at random carries to its other districts (%)")
    grid_reach: int = rule(75, 0, 100, S, "Share of a service a town laid out on a street grid carries to its other districts (%)")
    vertical_reach: int = rule(85, 0, 100, S, "Share of a service a town built upward carries to its other districts (%)")
    sprawl_reach: int = rule(30, 0, 100, S, "Share of a service a sprawling town carries to its other districts (%)")
    serves_per_level: int = rule(600, 1, 1000000, S, "People one level of a fully staffed service structure serves")
    thirst: int = rule(10, 0, 100, S, "Sanitation a town loses with no water coverage")
    impiety: int = rule(5, 0, 100, S, "Piety a town loses each epoch with no faith coverage")
    crime: int = rule(10, 0, 100, S, "Crime a town gains with no watch coverage")
    disease: int = rule(8, 0, 100, S, "Sanitation a town loses with no healing or bath coverage")
    prices: int = rule(5, 0, 100, S, "Prosperity a town loses each epoch with no market coverage")
    illiteracy: int = rule(5, 0, 100, S, "Literacy a town loses with no school coverage")
    sewerage: int = rule(8, 0, 100, S, "Sanitation a town gains at full sanitation coverage")
    transport_trade: int = rule(3, 0, 100, S, "Prosperity a town gains each epoch at full transport coverage")
    news_calm: int = rule(2, 0, 100, S, "Unrest a town loses each epoch at full communication coverage")
    power_yield: int = rule(3, 0, 100, S, "Prosperity a town gains each epoch at full power coverage")
    courts_order: int = rule(4, 0, 100, S, "Public order a town gains and crime it loses each epoch at full court coverage")
    welfare_calm: int = rule(3, 0, 100, S, "Unrest and crime a town loses each epoch at full welfare coverage")
    granary_store: int = rule(5, 0, 100, S, "Siege stores a town lays by each epoch at full granary coverage")
    parks_health: int = rule(2, 0, 100, S, "Sanitation and prestige a town gains each epoch at full park coverage")
    library_literacy: int = rule(3, 0, 100, S, "Literacy loss a town is spared at full library coverage")
    library_prestige: int = rule(2, 0, 100, S, "Prestige a town gains each epoch at full library coverage")
    burial_health: int = rule(3, 0, 100, S, "Sanitation a town gains each epoch at full burial coverage")
    depot_hauling: int = rule(5, 0, 100, S, "Hauling capacity a town gains each epoch at full depot coverage")
    admin_order: int = rule(3, 0, 100, S, "Public order a town gains each epoch at full administration coverage")
    entertainment_calm: int = rule(3, 0, 100, S, "Unrest a town loses each epoch at full entertainment coverage")
    warded_order: int = rule(
        2, 0, 100, S, "Public order each guardian spirit bound to a building of a town gives it each epoch, or unrest each vengeful one adds"
    )


@dataclass(frozen=True)
class HousingEvolutionRules:
    rise_coverage: int = rule(60, 0, 100, S, "Mean coverage of water, faith and market a district needs for its homes to rise")
    fall_coverage: int = rule(30, 0, 100, S, "Mean coverage below which a district's homes fall")
    goods_needed: int = rule(60, 0, 200, S, "Supply of goods a town needs for its homes to rise")
    step_pct: int = rule(30, 0, 100, S, "Chance each epoch a district's homes rise or fall by a level (%)")
    hut_pct: int = rule(120, 0, 400, S, "People a district of huts houses, against a district of houses (%)")
    cottage_pct: int = rule(110, 0, 400, S, "People a district of cottages houses, against a district of houses (%)")
    townhouse_pct: int = rule(80, 0, 400, S, "People a district of townhouses houses, against a district of houses (%)")
    manor_pct: int = rule(50, 0, 400, S, "People a district of manors houses, against a district of houses (%)")
    tenement_pct: int = rule(160, 0, 400, S, "People a district of tenements houses, against a district of houses (%)")
    apartment_pct: int = rule(180, 0, 400, S, "People a district of apartments houses, against a district of houses (%)")
    tower_block_pct: int = rule(260, 0, 400, S, "People a district of tower blocks houses, against a district of houses (%)")
    arcology_unit_pct: int = rule(320, 0, 400, S, "People a district of arcology units houses, against a district of houses (%)")
    habitat_module_pct: int = rule(140, 0, 400, S, "People a district of habitat modules houses, against a district of houses (%)")
    ship_berth_pct: int = rule(200, 0, 400, S, "People a district of ship berths houses, against a district of houses (%)")
    fine_homes: int = rule(100, 0, 400, S, "Share of homes at townhouse or manor a town needs, against the share of its folk who are nobles or merchants (%)")
    cramped_unrest: int = rule(3, 0, 100, S, "Unrest each epoch when the town's rich lack fine homes")


@dataclass(frozen=True)
class HomelessRules:
    crime: int = rule(15, 0, 100, S, "Crime a town gains when all its people are homeless")
    disease: int = rule(12, 0, 100, S, "Sanitation a town loses when all its people are homeless")
    unrest: int = rule(15, 0, 100, S, "Unrest a town gains each epoch when all its people are homeless")
    slum_share: int = rule(10, 0, 100, S, "Share of homeless past which a town grows slums (%)")
    mob_share: int = rule(25, 0, 100, S, "Share of homeless past which they gather as a mob (%)")
    clearance_unrest: int = rule(15, 0, 100, S, "Unrest clearing a town's slums raises")


@dataclass(frozen=True)
class PreventionRules:
    brigade_pct: int = rule(60, 0, 100, S, "Fire risk a firehouse's full coverage takes away (%)")
    watch_policing: int = rule(15, 0, 100, S, "Policing full watch coverage adds")


@dataclass(frozen=True)
class MorphologyRules:
    organic_fire_pct: int = rule(130, 0, 400, S, "How fast fire spreads through a town grown at random (%)")
    planned_fire_pct: int = rule(70, 0, 400, S, "How fast fire spreads through a planned town (%)")
    concentric_siege: int = rule(15, 0, 100, S, "Defence the inner rings of a ringed town add in a siege")
    planned_hauling_pct: int = rule(20, -100, 200, S, "Hauling a planned town's straight streets add (%)")
    organic_hauling_pct: int = rule(-10, -100, 200, S, "Hauling a town grown at random loses to its crooked lanes (%)")
    rings_at: int = rule(2, 1, 5, S, "Level of walls past which a town grows in rings")
    grid_fire_pct: int = rule(60, 0, 400, S, "How fast fire spreads through a town on a street grid (%)")
    vertical_fire_pct: int = rule(90, 0, 400, S, "How fast fire spreads through a town built upward (%)")
    sprawl_fire_pct: int = rule(80, 0, 400, S, "How fast fire spreads through a sprawling town (%)")
    grid_hauling_pct: int = rule(30, -100, 200, S, "Hauling a town on a street grid adds (%)")
    vertical_hauling_pct: int = rule(10, -100, 200, S, "Hauling a town built upward adds (%)")
    sprawl_hauling_pct: int = rule(-20, -100, 200, S, "Hauling a sprawling town loses to its distances (%)")
    grid_level: int = rule(5, 0, 20, S, "Architecture level at which a town relays its streets on a grid")
    grid_population: int = rule(5000, 0, 10000000, S, "People a town needs before it relays its streets on a grid")
    vertical_share: int = rule(40, 0, 100, S, "Share of districts of tower blocks or arcology units past which a town is built upward (%)")
    sprawl_level: int = rule(5, 0, 20, S, "Metallurgy level at which motor roads let a town sprawl")
    sprawl_population: int = rule(50000, 0, 100000000, S, "People a town needs before it sprawls")


@dataclass(frozen=True)
class TurfRules:
    claim_crime: int = rule(30, 0, 100, S, "Crime past which a criminal organisation claims a district")
    claim_pct: int = rule(30, 0, 100, S, "Chance each epoch such a claim is made (%)")
    growth: int = rule(5, 0, 100, S, "Strength turf gains each epoch")
    watch_loss: int = rule(10, 0, 100, S, "Strength turf loses each epoch under full watch coverage")
    war_pct: int = rule(30, 0, 100, S, "Chance each epoch two organisations on one district fight (%)")
    war_loss: int = rule(10, 0, 100, S, "Strength the loser of a turf war loses")
    war_order: int = rule(5, 0, 100, S, "Public order a turf war costs the town")
    war_deaths: int = rule(10, 0, 100, S, "Share of the losing organisation's members a turf war kills (%, at least one when above 0)")
    crime_per_turf: int = rule(10, 0, 100, S, "Crime full turf adds to its town")


@dataclass(frozen=True)
class CrimeOrgRules:
    income_per_turf: int = rule(3, 0, 1000, P, "Coin each point of turf strength brings its racket each epoch, a hundredth")
    racket_pct: int = rule(20, 0, 100, P, "Chance each epoch an organisation opens a new racket where it holds turf (%)")
    bribe: int = rule(5, 0, 1000, P, "Coin an organisation pays each official on its payroll each epoch")
    payroll_pct: int = rule(15, 0, 100, P, "Chance each epoch an organisation buys an official of its town (%)")
    payroll_shield_pct: int = rule(40, 0, 100, P, "Share of suppression the officials on its payroll turn aside (%)")
    suppress_loss: int = rule(10, 0, 100, P, "Turf a full suppression takes from an organisation each epoch")
    co_opt_crime: int = rule(5, 0, 100, P, "Crime a co-opted organisation takes off its town each epoch")
    traitor_pct: int = rule(5, 0, 100, P, "Chance each epoch a member of an organisation turns informer (%)")
    privateer_pct: int = rule(20, 0, 100, P, "Extra raid chance a co-opted pirate confederacy brings on the convoys of its realm's enemies (%)")
    informant_pct: int = rule(20, 0, 100, P, "Chance each epoch a co-opted organisation gives its realm a secret of its town (%)")
    stance_pct: int = rule(25, 0, 100, P, "Chance each epoch a realm troubled by an organisation takes a stance against it (%)")


@dataclass(frozen=True)
class TradingPostRules:
    open_pct: int = rule(10, 0, 100, M, "Chance each epoch a merchant house opens a trading post in a foreign trading partner (%)")
    informant_gain: int = rule(1, 0, 100, M, "Informants a trading post gains each epoch")
    informant_cap: int = rule(20, 0, 1000, M, "Informants a trading post holds at most")
    diaspora: int = rule(250, 0, 100000, M, "Folk of the owner's people a trading post settles in its host each epoch")
    goods_cap: int = rule(5000, 0, 10000000, M, "Goods a trading post's warehouse holds at most")
    stock_gain: int = rule(500, 0, 1000000, M, "Goods a trading post stores each epoch")
    secret_pct: int = rule(20, 0, 100, M, "Chance each epoch each informant brings its owner a secret of the host (%)")


@dataclass(frozen=True)
class MagicalOrderRules:
    founding_laws: int = rule(2, 0, 4, S, "Laws a magical order keeps from its founding")
    violation_pct: int = rule(10, 0, 100, S, "Chance each epoch a member breaks a law of the order (%)")
    fine: int = rule(20, 0, 10000, S, "Coin a tribunal fines a member for a light breach")
    expel_strength: int = rule(70, 0, 100, S, "Strength of a law past which breaking it means expulsion")
    vis_per_site: int = rule(2, 0, 100, S, "Vis a covenant draws each epoch from each magic site its order holds")
    knowledge_gain: int = rule(2, 0, 100, S, "Magic a covenant's laboratory adds to its town each epoch")
    rivalry: int = rule(5, 0, 100, S, "Reputation an order loses with cults where magic is outlawed")
    defiance_at: int = rule(20, 0, 100, S, "Reputation below which an order under a ban on magic is outlawed by its realm")
    feud_pct: int = rule(10, 0, 100, S, "Chance each epoch two orders of one town turn on each other (%)")
    feud_loss: int = rule(10, 0, 100, S, "Reputation and regard a feud between orders, or an order's defiance, costs")
    share_step: int = rule(2, 0, 50, S, "Craft each member of an order that shares its discoveries gains toward its best, at full strength of the law")
    secrecy_step: int = rule(5, 0, 100, S, "Secrecy an order that keeps its secrets gains each epoch, up to the strength of the law")


@dataclass(frozen=True)
class ConvoyRules(Spanned):
    per_vehicle: int = rule(10, 0, 10000, M, "Goods a wagon or boat carries")
    per_animal: int = rule(3, 0, 10000, M, "Goods a pack animal carries")
    per_route: int = rule(1, 0, 1000, M, "Most convoys a trading route sends each year")
    traffic_per_convoy: int = rule(
        1000, 1, 100000000, M, "Goods a route carried in the last epoch that fill one convoy; busier routes split their goods over more convoys"
    )
    raid_pct: int = rule(10, 0, 100, M, "Chance a convoy on a dangerous route is raided (%)")
    guard_relief: int = rule(2, 0, 100, M, "Raid chance each guard takes away")
    storm_pct: int = rule(5, 0, 100, M, "Chance a convoy at sea is lost in a storm (%)")
    delay_pct: int = rule(10, 0, 100, M, "Chance a convoy is delayed by weather (%)")
    pilgrims: int = rule(100, 0, 100000, M, "Pilgrims, migrants and missionaries a convoy carries at most")
    conversion: int = rule(2, 0, 100, M, "Followers its missionaries win in the town it reaches")
    war_raid_pct: int = rule(20, 0, 100, M, "Extra raid chance on a convoy travelling between realms at war (%)")
    escort_relief: int = rule(10, 0, 100, M, "Raid chance a trade treaty's escort takes away (%)")
    art_pct: int = rule(20, 0, 100, M, "Chance an arriving convoy brings one of its home's art forms (%)")
    news_confidence: int = rule(50, 0, 100, M, "Confidence of the news of its home's wealth and defences a convoy brings")


@dataclass(frozen=True)
class FleetRules:
    wear: int = rule(5, 0, 100, M, "Condition a transport fleet loses each epoch")
    upkeep: int = rule(1, 0, 1000, M, "Coin each wagon, boat or animal costs its owner each epoch")
    replace_at: int = rule(30, 0, 100, M, "Condition below which a fleet is replaced")
    replace_cost: int = rule(5, 0, 10000, M, "Coin replacing each worn wagon, boat or animal costs")
    worn_pct: int = rule(50, 0, 100, M, "Capacity a fleet at no condition keeps (%)")


@dataclass(frozen=True)
class CargoRules:
    water_bulk_pct: int = rule(40, 0, 400, M, "Cost of carrying bulk goods by water against land (%)")
    land_bulk_pct: int = rule(150, 0, 400, M, "Cost of carrying bulk goods over land (%)")
    perishable_loss: int = rule(20, 0, 100, M, "Share of perishable goods spoiled on a slow land route (%)")
    livestock_loss: int = rule(5, 0, 100, M, "Share of livestock lost walking a route (%)")
    spill_loss: int = rule(3, 0, 100, M, "Share of liquids and gases lost to leaks on a route (%)")
    hazard_loss: int = rule(4, 0, 100, M, "Share of dangerous goods lost to accidents on a route (%)")


@dataclass(frozen=True)
class PreservationRules:
    drying_pct: int = rule(30, 0, 100, M, "Spoilage drying spares (%)")
    smoking_pct: int = rule(40, 0, 100, M, "Spoilage smoking spares (%)")
    curing_pct: int = rule(60, 0, 100, M, "Spoilage curing with a mineral spares (%)")
    pickling_pct: int = rule(50, 0, 100, M, "Spoilage pickling spares (%)")
    fermenting_pct: int = rule(45, 0, 100, M, "Spoilage fermenting spares (%)")
    chilling_pct: int = rule(80, 0, 100, M, "Spoilage chilling spares (%)")
    freezing_pct: int = rule(90, 0, 100, M, "Spoilage freezing spares (%)")
    sealing_pct: int = rule(70, 0, 100, M, "Spoilage sealing in closed vessels spares (%)")
    canning_pct: int = rule(90, 0, 100, M, "Spoilage canning spares (%)")
    irradiating_pct: int = rule(95, 0, 100, M, "Spoilage irradiating spares (%)")
    by_working_pct: int = rule(100, 0, 100, M, "Spoilage keeping by a working of power spares (%)")
    living_pct: int = rule(85, 0, 100, M, "Spoilage keeping goods alive or in living vessels spares (%)")


@dataclass(frozen=True)
class PortRules:
    per_berth: int = rule(10, 0, 100000, M, "Goods each unit of harbour capacity moves each epoch")
    warehouse_days: int = rule(30, 0, 1000, M, "Days of food each level of a warehouse adds to a besieged town's stores")


@dataclass(frozen=True)
class ManipulationRules(Spanned):
    corner_stock: int = rule(100, 0, 100000, M, "Stock of a good a merchant house needs to corner its market")
    corner_pct: int = rule(40, 0, 400, M, "Price rise a full corner causes (%)")
    dump_pct: int = rule(30, 0, 100, M, "Price fall a full dumping causes (%)")
    play_pct: int = rule(10, 0, 100, M, "Chance each epoch a rich merchant house plays a market (%)")
    length_years: int = span(2, 1, 2500, M, "Years a corner or dumping lasts")
    law_counter_pct: int = rule(60, 0, 100, M, "Share of a play a fair-market law, or a realm's mandate on the good, undoes (%)")
    guild_counter_pct: int = rule(40, 0, 100, M, "Share of a play a guild holding the good's monopoly undoes (%)")

    @property
    def length(self) -> int:
        return self.epochs(self.length_years)
