from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.ECONOMY


@dataclass(frozen=True)
class PublicWorksRules:
    labour_per_stage: int = rule(100, 1, 10000, S, "Treasury paid labour costs for each stage of a public work")
    terracing_erosion: int = rule(15, 0, 100, S, "Erosion finished terraces take from the land of their region")
    terracing_harvest: int = rule(10, 0, 100, S, "Harvest finished terraces open on the slopes of their region (%)")
    irrigation_harvest: int = rule(15, 0, 100, S, "Harvest finished irrigation adds to the land of its region (%)")
    irrigation_salt: int = rule(5, 0, 100, S, "Fertility irrigation with no drainage beside it takes from the soil as it lays salt")
    lighthouse_loss_cut_pct: int = rule(30, 0, 100, S, "Share of the losses at sea a lighthouse at either end of a sea route spares (%)")
    quality_floor: int = rule(30, 0, 100, S, "Quality below which a public work may collapse at each stage or flood when finished")
    upkeep_pct: int = rule(5, 0, 50, S, "Share of a finished public work's budget owed as upkeep each epoch")
    decay_per_neglected_epoch: int = rule(10, 0, 100, S, "Condition a finished public work loses each epoch its upkeep goes unpaid")
    labour_grievance: int = rule(3, 0, 100, S, "Unrest corvée or bound labour on a public work raises in the towns of its polity each epoch")
    collapse_pct: int = rule(20, 0, 100, S, "Chance a stage of a public work below the quality floor collapses")
    blessing_quality: int = rule(15, 0, 100, S, "Quality a blessing of a son adds to a public work")
    finished_prosperity: int = rule(3, 0, 100, S, "Prosperity a finished public work without a typed effect adds to its towns")


@dataclass(frozen=True)
class StateEnterpriseRules:
    monopoly_price_pct: int = rule(30, 0, 300, S, "Share a monopoly adds to the revenue of what it sells")
    skim_chance_pct: int = rule(10, 0, 100, S, "Chance each epoch, at a corruption of fifty, that the manager of a state enterprise skims its revenue")
    revenue_per_output: int = rule(2, 0, 100, S, "Treasury a state enterprise earns each epoch for each point of output")
    starve_rivals: int = rule(2, 0, 100, S, "Stock a monopoly takes each epoch from each rival shop of its good in its polity")
    granary_board_units: int = rule(2, 0, 1000, S, "Grain a granary board moves each epoch from its fullest store to its emptiest, for each point of output")
    state_post_hops: int = rule(2, 0, 50, S, "Regions more a letter crosses each season where the realm keeps a state post")
    privatise_debt: int = rule(0, -100000, 100000, S, "Treasury of a polity at or below which it sells its enterprises to companies")
