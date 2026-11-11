from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

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
    gentrify_homeless: int = rule(4, 0, 100, S, "Share of a priced-out district's people left without a home each epoch (%)")


@dataclass(frozen=True)
class CoverageRules:
    planned_reach: int = rule(70, 0, 100, S, "Share of a service a planned town carries to its other districts (%)")
    concentric_reach: int = rule(50, 0, 100, S, "Share of a service a ringed town carries to its other districts (%)")
    organic_reach: int = rule(35, 0, 100, S, "Share of a service a town grown at random carries to its other districts (%)")
    serves_per_level: int = rule(600, 1, 1000000, S, "People one level of a fully staffed service structure serves")
    thirst: int = rule(10, 0, 100, S, "Sanitation a town loses with no water coverage")
    impiety: int = rule(5, 0, 100, S, "Piety a town loses each epoch with no faith coverage")
    crime: int = rule(10, 0, 100, S, "Crime a town gains with no watch coverage")
    disease: int = rule(8, 0, 100, S, "Sanitation a town loses with no healing or bath coverage")
    prices: int = rule(5, 0, 100, S, "Prosperity a town loses each epoch with no market coverage")
    illiteracy: int = rule(5, 0, 100, S, "Literacy a town loses with no school coverage")


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


@dataclass(frozen=True)
class TurfRules:
    claim_crime: int = rule(30, 0, 100, S, "Crime past which a criminal organisation claims a district")
    claim_pct: int = rule(30, 0, 100, S, "Chance each epoch such a claim is made (%)")
    growth: int = rule(5, 0, 100, S, "Strength turf gains each epoch")
    watch_loss: int = rule(10, 0, 100, S, "Strength turf loses each epoch under full watch coverage")
    war_pct: int = rule(30, 0, 100, S, "Chance each epoch two organisations on one district fight (%)")
    war_loss: int = rule(10, 0, 100, S, "Strength the loser of a turf war loses")
    war_order: int = rule(5, 0, 100, S, "Public order a turf war costs the town")
    war_deaths: int = rule(2, 0, 100, S, "Mortals a turf war kills at most")
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
    stance_pct: int = rule(25, 0, 100, P, "Chance each epoch a realm troubled by an organisation takes a stance against it (%)")


@dataclass(frozen=True)
class TradingPostRules:
    open_pct: int = rule(10, 0, 100, M, "Chance each epoch a merchant house opens a trading post in a foreign trading partner (%)")
    informant_gain: int = rule(1, 0, 100, M, "Informants a trading post gains each epoch")
    informant_cap: int = rule(5, 0, 100, M, "Informants a trading post holds at most")
    diaspora: int = rule(20, 0, 10000, M, "Folk of the owner's people a trading post settles in its host each epoch")
    goods_cap: int = rule(200, 0, 100000, M, "Goods a trading post's warehouse holds at most")
    stock_gain: int = rule(20, 0, 10000, M, "Goods a trading post stores each epoch")
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


@dataclass(frozen=True)
class ConvoyRules:
    per_vehicle: int = rule(10, 0, 10000, M, "Goods a wagon or boat carries")
    per_animal: int = rule(3, 0, 10000, M, "Goods a pack animal carries")
    per_route: int = rule(2, 0, 100, M, "Convoys each trading route sends each epoch at most")
    raid_pct: int = rule(10, 0, 100, M, "Chance a convoy on a dangerous route is raided (%)")
    guard_relief: int = rule(2, 0, 100, M, "Raid chance each guard takes away")
    storm_pct: int = rule(5, 0, 100, M, "Chance a convoy at sea is lost in a storm (%)")
    delay_pct: int = rule(10, 0, 100, M, "Chance a convoy is delayed by weather (%)")
    pilgrims: int = rule(10, 0, 10000, M, "Pilgrims, migrants and missionaries a convoy carries at most")
    conversion: int = rule(2, 0, 100, M, "Followers its missionaries win in the town it reaches")


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
    salted_pct: int = rule(60, 0, 100, M, "Spoilage salting spares (%)")
    iced_pct: int = rule(80, 0, 100, M, "Spoilage ice spares (%)")
    magic_pct: int = rule(100, 0, 100, M, "Spoilage magical keeping spares (%)")


@dataclass(frozen=True)
class PortRules:
    per_berth: int = rule(10, 0, 100000, M, "Goods each unit of harbour capacity moves each epoch")


@dataclass(frozen=True)
class ManipulationRules:
    corner_stock: int = rule(100, 0, 100000, M, "Stock of a good a merchant house needs to corner its market")
    corner_pct: int = rule(40, 0, 400, M, "Price rise a full corner causes (%)")
    dump_pct: int = rule(30, 0, 100, M, "Price fall a full dumping causes (%)")
    play_pct: int = rule(10, 0, 100, M, "Chance each epoch a rich merchant house plays a market (%)")
    length: int = rule(3, 1, 100, M, "Epochs a corner or dumping lasts")
    law_counter_pct: int = rule(60, 0, 100, M, "Share of a play a fair-market law undoes (%)")
    guild_counter_pct: int = rule(40, 0, 100, M, "Share of a play a guild holding the good's monopoly undoes (%)")
