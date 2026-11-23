from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

F = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class EstateRules:
    found_share: int = rule(10, 0, 100, F, "Share of a realm's people a class must make up before it gathers as an estate (%)")
    found_pct: int = rule(30, 0, 100, F, "Chance each epoch a class large enough gathers as an estate (%)")
    privilege_loyalty: int = rule(10, 0, 100, F, "Scale of the loyalty an estate's privileges buy (tenths)")
    tax_exemption_loyalty: int = rule(10, 0, 100, F, "Loyalty freedom from taxes buys an estate")
    monopoly_loyalty: int = rule(10, 0, 100, F, "Loyalty a monopoly buys an estate")
    council_seat_loyalty: int = rule(10, 0, 100, F, "Loyalty a seat in council buys an estate")
    arms_loyalty: int = rule(8, 0, 100, F, "Loyalty the right to bear arms buys an estate")
    judicial_immunity_loyalty: int = rule(10, 0, 100, F, "Loyalty freedom from the common courts buys an estate")
    reserved_offices_loyalty: int = rule(15, 0, 100, F, "Loyalty offices kept for an estate buy it")
    land_holding_loyalty: int = rule(15, 0, 100, F, "Loyalty the sole right to hold land buys an estate")
    tax_exemption_cost: int = rule(10, 0, 100, F, "Treasury a realm forgoes each epoch for an estate's freedom from taxes")
    monopoly_cost: int = rule(4, 0, 100, F, "Treasury a realm forgoes each epoch for an estate's monopoly")
    council_seat_cost: int = rule(2, 0, 100, F, "Treasury a realm spends each epoch keeping an estate's seat in council")
    arms_cost: int = rule(2, 0, 100, F, "Treasury a realm forgoes each epoch for an estate's right to bear arms")
    judicial_immunity_cost: int = rule(3, 0, 100, F, "Treasury a realm forgoes each epoch in fines an immune estate never pays")
    reserved_offices_cost: int = rule(5, 0, 100, F, "Treasury a realm loses each epoch to the lesser hands that fill offices kept for one estate")
    land_holding_cost: int = rule(6, 0, 100, F, "Treasury a realm forgoes each epoch from land only one estate may hold")
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
    abolition_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the abolition cause gather a movement and its support (%)")
    independence_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the independence cause gather a movement and its support (%)")
    revival_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the revival cause gather a movement and its support (%)")
    land_reform_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the land reform cause gather a movement and its support (%)")
    franchise_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the franchise cause gather a movement and its support (%)")
    peace_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the peace cause gather a movement and its support (%)")
    conservation_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the conservation cause gather a movement and its support (%)")
    labour_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the labour cause gather a movement and its support (%)")
    faith_reform_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the faith reform cause gather a movement and its support (%)")
    temperance_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the temperance cause gather a movement and its support (%)")
    mind_rights_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the mind rights cause gather a movement and its support (%)")
    equal_standing_weight: int = rule(100, 0, 100, F, "How strongly the pressures for the equal standing cause gather a movement and its support (%)")
    temperance_cut: int = rule(10, 0, 100, F, "Acceptance of each intoxicant a risen temperance movement takes from its people's customs")


@dataclass(frozen=True)
class CompanyRules(Spanned):
    found_pct: int = rule(10, 0, 100, F, "Chance each epoch a rich merchant guild with routes abroad charters a company (%)")
    found_wealth: int = rule(50, 0, 100, F, "Wealth a merchant guild needs to charter a company")
    route_profit: int = rule(4, 0, 100, F, "Wealth a company draws each epoch from the route it holds a monopoly over")
    dividend_wealth: int = rule(2, 0, 100, F, "Wealth each full share of a company pays its holder each epoch at the company's dividend")
    collapse_wealth: int = rule(5, 0, 100, F, "Wealth below which a company collapses and its shareholders lose their stakes")
    collapse_loss: int = rule(10, 0, 100, F, "Wealth each shareholder loses when a company collapses")
    conquest_strength: int = rule(60, 0, 100, F, "Strength from which an armed company seizes the land at its route's far end")
    guard_wealth: int = rule(30, 0, 100, F, "Wealth from which a company keeps hired guards on its route")
    guard_wage: int = rule(3, 0, 100, F, "Wealth a company pays its hired guards each epoch")
    guard_strength: int = rule(5, 0, 100, F, "Strength a company's hired guards add each epoch")
    dominion_years: int = span(30, 1, 2500, F, "Years a company must hold the land at its route's far end before it rules that land as a realm")

    @property
    def dominion_epochs(self) -> int:
        return self.epochs(self.dominion_years)


@dataclass(frozen=True)
class OrderRules:
    found_pct: int = rule(10, 0, 100, F, "Chance each epoch a faith with warriors among its faithful founds a holy order (%)")
    warrior_share: int = rule(10, 0, 100, F, "Share of warriors a faith's heartland needs before a holy order rises (%)")
    tithe_wealth: int = rule(3, 0, 100, F, "Wealth a holy order draws each epoch from its faith's tithes")
    fortress_defense: int = rule(10, 0, 100, F, "Defence a holy order adds to the border town it holds")
    recruit_pct: int = rule(20, 0, 100, F, "Chance each epoch a warrior or noble of the faith near a holy order takes its vows (%)")
    host_per_strength: int = rule(
        5,
        0,
        10000,
        F,
        "Soldiers a holy order sends to a holy war for each point of its strength, for every thousand followers of its faith (at least a thousand counted)",
    )


@dataclass(frozen=True)
class GuildRules:
    fellow_at: int = rule(30, 0, 100, F, "Craft skill from which a guild member is a fellow of the craft")
    master_at: int = rule(60, 0, 100, F, "Craft skill from which a guild member is a master")
    grandmaster_at: int = rule(85, 0, 100, F, "Craft skill from which a guild member is the grandmaster")
    secret_pct: int = rule(25, 0, 100, F, "Chance each epoch a guild makes one of its craft's techniques a secret of its town (%)")
    quality_bonus: int = rule(10, 0, 100, F, "Quality a guild's standards add to its town's works")
