from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

F = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class EstateRules:
    found_share: int = rule(10, 0, 100, F, "Share of a realm's people a class must make up before it gathers as an estate (%)")
    found_pct: int = rule(30, 0, 100, F, "Chance each epoch a class large enough gathers as an estate (%)")
    privilege_loyalty: int = rule(10, 0, 100, F, "Loyalty each privilege an estate holds adds")
    loyalty_drift_pct: int = rule(25, 0, 100, F, "Share of the gap to its due loyalty an estate closes each epoch (%)")
    share_influence_pct: int = rule(150, 0, 400, F, "How much of its class's share of the realm an estate wields as influence (%)")
    council_seat_influence: int = rule(15, 0, 100, F, "Influence a seat in council adds to an estate")
    grant_below: int = rule(40, 0, 100, F, "Loyalty below which a realm grants an influential estate a privilege")
    grant_influence: int = rule(20, 0, 100, F, "Influence from which an estate is worth buying with a privilege")
    revoke_treasury: int = rule(20, 0, 100000, F, "Treasury below which a realm takes back a loyal estate's tax exemption")
    revoke_above: int = rule(70, 0, 100, F, "Loyalty above which a realm dares take back a privilege")
    revoke_loyalty: int = rule(20, 0, 100, F, "Loyalty an estate loses when a privilege is taken back")
    monopoly_rent: int = rule(3, 0, 100, F, "Wealth a monopoly brings its estate each epoch")
    militia_pct: int = rule(50, 0, 200, F, "How much of an armed class's share swells a town's militia (%)")
    propose_pct: int = rule(15, 0, 100, F, "Chance each epoch an influential estate brings a law its class wants before the realm (%)")


@dataclass(frozen=True)
class MovementRules:
    found_at: int = rule(25, 0, 100, F, "Mean pressure across a realm from which a movement for a cause gathers")
    found_pct: int = rule(25, 0, 100, F, "Chance each epoch a pressed cause gathers a movement (%)")
    drift_pct: int = rule(25, 0, 100, F, "Share of the gap to the pressure it feels that a community's support closes each epoch (%)")
    protest_at: int = rule(40, 0, 100, F, "Support from which a movement protests in a community")
    protest_pct: int = rule(10, 0, 100, F, "Share of its support a protest adds to a town's unrest (%)")
    party_at: int = rule(30, 0, 100, F, "Support from which a movement in a realm with a council or assembly becomes a party")
    revolt_at: int = rule(60, 0, 100, F, "Support from which a movement in a realm with no assembly rises in arms")
    revolt_pct: int = rule(20, 0, 100, F, "Chance each epoch a movement past its threshold rises (%)")


@dataclass(frozen=True)
class CompanyRules:
    found_pct: int = rule(10, 0, 100, F, "Chance each epoch a rich merchant guild with routes abroad charters a company (%)")
    found_wealth: int = rule(50, 0, 100, F, "Wealth a merchant guild needs to charter a company")
    route_profit: int = rule(4, 0, 100, F, "Wealth a company draws each epoch from the route it holds a monopoly over")
    dividend_wealth: int = rule(2, 0, 100, F, "Wealth each full share of a company pays its holder each epoch at the company's dividend")
    collapse_wealth: int = rule(5, 0, 100, F, "Wealth below which a company collapses and its shareholders lose their stakes")
    collapse_loss: int = rule(10, 0, 100, F, "Wealth each shareholder loses when a company collapses")
    conquest_strength: int = rule(60, 0, 100, F, "Strength from which an armed company seizes the land at its route's far end")


@dataclass(frozen=True)
class OrderRules:
    found_pct: int = rule(10, 0, 100, F, "Chance each epoch a faith with warriors among its faithful founds a holy order (%)")
    warrior_share: int = rule(10, 0, 100, F, "Share of warriors a faith's heartland needs before a holy order rises (%)")
    tithe_wealth: int = rule(3, 0, 100, F, "Wealth a holy order draws each epoch from its faith's tithes")
    fortress_defense: int = rule(10, 0, 100, F, "Defence a holy order adds to the border town it holds")


@dataclass(frozen=True)
class GuildRules:
    journeyman_at: int = rule(30, 0, 100, F, "Craft skill from which a guild member is a journeyman")
    master_at: int = rule(60, 0, 100, F, "Craft skill from which a guild member is a master")
    grandmaster_at: int = rule(85, 0, 100, F, "Craft skill from which a guild member is the grandmaster")
    secret_pct: int = rule(25, 0, 100, F, "Chance each epoch a guild makes one of its craft's techniques a secret of its town (%)")
    quality_bonus: int = rule(10, 0, 100, F, "Quality a guild's standards add to its town's works")
