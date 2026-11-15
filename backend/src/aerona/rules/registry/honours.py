from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class UnitHonourRules:
    seed_esprit: int = rule(30, 0, 100, W, "Esprit a unit raised from one land holds when it takes a name after its first battle")
    massacre_share: int = rule(50, 0, 100, W, "Share of a unit lost in one battle from which the battle is a massacre it remembers (%)")
    honour_esprit: int = rule(10, 0, 100, W, "Esprit a unit gains for each honour on its standard")
    survival_esprit: int = rule(3, 0, 100, W, "Esprit a unit gains for each battle it survives")
    massacre_esprit: int = rule(15, 0, 100, W, "Esprit a unit loses for a massacre it suffers")
    morale_pct: int = rule(20, 0, 100, W, "Share more morale a unit of full esprit holds in battle (%)")
    disband_renown: int = rule(5, 0, 100, W, "Renown a realm loses for disbanding a unit with honours")
    reconstitute_pct: int = rule(50, 0, 100, W, "Share of its old esprit a unit raised again from its veterans regains (%)")


@dataclass(frozen=True)
class VeteranRules:
    land_martial_from: int = rule(20, -100, 100, W, "Martial value of a realm's people from which it grants its veterans land")
    colony_veterans: int = rule(50, 0, 100000, W, "Veterans a realm needs to found a colony of them")
    colony_loyalty: int = rule(20, 0, 100, W, "Loyalty a veteran colony holds to the ruler who granted it")
    pension_cost: int = rule(1, 0, 100, W, "Coin each veteran's pension costs the treasury each epoch")
    pension_years: int = rule(5, 1, 100, W, "Epochs a pension is paid")
    unpaid_grievance: int = rule(10, 0, 100, W, "Relation each town of a realm loses with it when its veterans' pensions go unpaid")
    association_from: int = rule(30, 0, 100000, W, "Veterans of a town from which they band into an association")
