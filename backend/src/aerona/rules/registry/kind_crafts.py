from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class DressRules:
    prestige_pct: int = rule(4, 0, 100, G, "Share of a worn garment's prestige times its status signal a town of its wearers gains in prestige (%)")
    cold_warmth: int = rule(50, 0, 100, G, "Warmth a people must wear to be shielded from the cold of a cold season")
    exposure_pct: int = rule(
        60, 0, 300, G, "Extra chance of an everyday mishap in the cold season for each point of warmth a people's dress falls short, per hundred (%)"
    )
    sumptuary_crime: int = rule(
        2, 0, 100, G, "Crime a town gains each epoch when its folk wear a garment of high status signal that a sumptuary law of its realm restrains"
    )
    signal_floor: int = rule(60, 0, 100, G, "Status signal from which a garment counts as fine dress under a sumptuary law")
    work_wear_prosperity: int = rule(
        2, 0, 50, G, "Prosperity a town gains each epoch where its folk wear slings, packs or wear for water at their work, at full strength"
    )
    rest_wear_calm: int = rule(1, 0, 50, G, "Unrest a town loses each epoch where its folk sleep in wear made for it, at full strength")
    fashion_pull_pct: int = rule(
        20,
        0,
        100,
        G,
        "Share of a garment's novelty above or below the middle that moves the strength with which its holders wear it each epoch, at full fashion (%)",
    )


@dataclass(frozen=True)
class ColourRules:
    rarity_prestige_pct: int = rule(90, 0, 200, G, "Share of a colour's rarity that becomes its prestige each epoch (%)")
    restrict_at: int = rule(60, 0, 100, G, "Prestige from which a realm whose folk use a colour restricts it to its highest rank")
    smuggling_crime: int = rule(4, 0, 100, G, "Crime a town gains each epoch, at full strength of use, when its folk keep using a colour their realm restricts")
    restriction_unrest: int = rule(
        5, 0, 100, G, "Unrest a town gains each epoch, at full strength of use, when its folk keep using a colour their realm restricts"
    )
    repeal_unrest: int = rule(70, 0, 100, G, "Unrest of a town of the realm at which its folk rise and tear a colour restriction down")


@dataclass(frozen=True)
class ScentRules:
    prestige_pct: int = rule(3, 0, 100, G, "Share of a scent's prestige a town of its users gains in prestige each epoch (%)")
    rite_calm_pct: int = rule(3, 0, 100, G, "Share of a scent's weight in rites that eases a town's unrest each epoch (%)")
    trade_pct: int = rule(2, 0, 100, G, "Share of a scent's trade value a town of its makers earns into its treasury each epoch (%)")


@dataclass(frozen=True)
class HouseholdGoodsRules:
    comfort_calm_pct: int = rule(3, 0, 100, G, "Share of a furnishing's comfort that eases unrest in the towns of its users each epoch (%)")
    play_skill_pct: int = rule(2, 0, 100, G, "Share of a play furnishing's comfort that adds to the prosperity of its towns as the young learn by it (%)")
    prestige_pct: int = rule(2, 0, 100, G, "Share of a furnishing's, instrument's or tradition's prestige a town of its holders gains each epoch (%)")
    sanitation_pct: int = rule(
        4, 0, 100, G, "Share of the comfort of a sanitation furnishing or the quality of a medical tool that raises a town's sanitation (%)"
    )
    fire_pct: int = rule(
        3,
        0,
        100,
        G,
        "Share of the comfort of a heating or lighting furnishing that raises a town's fire risk, and of a fire-making tool's quality that lowers it (%)",
    )
    craft_pct: int = rule(2, 0, 100, G, "Share of a tool's craft bonus times its quality a town of its users gains in prosperity each epoch (%)")
    wear_pct: int = rule(40, 0, 300, G, "Extra chance of an everyday mishap, per hundred points of wear of the tools a people uses (%)")
    emblem_order_pct: int = rule(2, 0, 100, G, "Share of an emblem system's legibility that raises public order in the towns of its users (%)")


@dataclass(frozen=True)
class MusicRules:
    rite_calm_pct: int = rule(3, 0, 100, G, "Share of a musical tradition's weight in rites that eases a town's unrest each epoch (%)")
    ensemble_calm: int = rule(1, 0, 20, G, "Unrest eased each epoch in a town for each ten players of its largest ensemble, at full strength")
    loud_pct: int = rule(1, 0, 100, G, "Share of an instrument's loudness that eases unrest at gatherings of its players each epoch (%)")


@dataclass(frozen=True)
class SubstanceRules:
    crime_pct: int = rule(3, 0, 100, G, "Share of a substance's dependence times its potency that becomes crime in the towns of its users each epoch (%)")
    harm_pct: int = rule(3, 0, 100, G, "Share of a substance's harm a town of its users loses in sanitation each epoch (%)")
    rite_calm_pct: int = rule(2, 0, 100, G, "Share of a substance's weight in rites that eases a town's unrest each epoch (%)")
    forbidden_crime: int = rule(4, 0, 100, G, "Crime a town gains each epoch, at full strength of use, when its folk use a substance their realm forbids")
    trade_pct: int = rule(2, 0, 100, G, "Share of a substance's trade value a town of its makers earns into its treasury each epoch (%)")
