from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class UnitHonourRules:
    seed_esprit: int = rule(30, 0, 100, W, "Esprit a unit raised from one land holds when it takes a name after its first battle")
    massacre_share: int = rule(50, 0, 100, W, "Share of a unit lost in one battle from which the battle is a massacre it remembers (%)")
    honour_esprit: int = rule(10, 0, 100, W, "Esprit a unit gains for each honour on its standard")
    survival_esprit: int = rule(3, 0, 100, W, "Esprit a unit gains for each battle it survives")
    massacre_esprit: int = rule(15, 0, 100, W, "Esprit a unit loses for a massacre it suffers")
    relief_esprit: int = rule(15, 0, 100, W, "Esprit a unit gains for breaking a siege of its own side")
    crossing_esprit: int = rule(10, 0, 100, W, "Esprit a unit gains for crossing a river, strait or pass under arms")
    morale_pct: int = rule(20, 0, 100, W, "Share more morale a unit of full esprit holds in battle (%)")
    disband_renown: int = rule(5, 0, 100, W, "Renown a realm loses for disbanding a unit with honours")
    reconstitute_pct: int = rule(50, 0, 100, W, "Share of its old esprit a unit raised again from its veterans regains (%)")
    nickname_honours: int = rule(
        3, 1, 100, W, "Honours of victory, stand or siege after which a unit earns a nickname in the tongue of the land it was raised from"
    )
    standard_renown: int = rule(4, 0, 100, W, "Renown the standard its army or realm bears gains for each honour a unit earns")
    mercy_esprit: int = rule(8, 0, 100, W, "Esprit a unit gains for sparing a city or a foe its people read as worth sparing")
    first_in_esprit: int = rule(12, 0, 100, W, "Esprit a unit gains for being first through a breach")


@dataclass(frozen=True)
class VeteranRules(Spanned):
    land_martial_from: int = rule(20, -100, 100, W, "Martial value of a realm's people from which it grants its veterans land")
    colony_veterans: int = rule(50, 0, 100000, W, "Veterans a realm needs to found a colony of them")
    colony_loyalty: int = rule(20, 0, 100, W, "Loyalty a veteran colony holds to the ruler who granted it")
    pension_cost: int = rule(1, 0, 100, W, "Coin each veteran's pension costs the treasury each epoch")
    ungranted_unrest: int = rule(2, 0, 100, W, "Unrest that veterans a realm could grant nothing add to its towns each epoch while their claim stands")
    paid_years: int = span(20, 1, 2500, W, "Years a pension is paid")
    unpaid_grievance: int = rule(10, 0, 100, W, "Relation each town of a realm loses with it when its veterans' pensions go unpaid")
    land_loyalty: int = rule(15, 0, 100, W, "Relation each town of a realm gains with it when it grants its veterans land")
    pension_loyalty: int = rule(10, 0, 100, W, "Relation each town of a realm gains with it when it grants its veterans pensions")
    none_loyalty: int = rule(0, 0, 100, W, "Relation each town of a realm gains with it when it grants its veterans nothing")
    membership_loyalty: int = rule(12, 0, 100, W, "Relation each town of a realm gains with it when it grants veterans of other peoples full membership")
    title_loyalty: int = rule(18, 0, 100, W, "Relation each town of a realm gains with it when it raises a veteran into a lesser title")
    tax_exemption_loyalty: int = rule(14, 0, 100, W, "Relation each town of a realm gains with it when it frees its veterans from taxes")
    land_cost: int = rule(0, 0, 100, W, "Coin each veteran granted land costs the treasury once")
    pension_grant_cost: int = rule(0, 0, 100, W, "Coin each veteran granted a pension costs the treasury once, beside the pension")
    none_cost: int = rule(0, 0, 100, W, "Coin each ungranted veteran costs the treasury once")
    membership_cost: int = rule(0, 0, 100, W, "Coin each veteran granted membership costs the treasury once")
    title_cost: int = rule(20, 0, 100, W, "Coin raising a veteran into a lesser title costs the treasury")
    tax_exemption_cost: int = rule(2, 0, 100, W, "Coin each tax-free veteran costs the treasury in lost revenue once")
    association_from: int = rule(30, 0, 100000, W, "Veterans of a town from which they band into an association")

    @property
    def pension_years(self) -> int:
        return self.epochs(self.paid_years)

    office_loyalty: int = rule(12, 0, 100, W, "Relation each town of a realm gains with it when it raises a veteran into an office")
    office_cost: int = rule(40, 0, 10000, W, "Coin a realm spends to place one veteran in an office")
