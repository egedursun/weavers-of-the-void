from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class RemembranceRules:
    great_war_battles: int = rule(3, 1, 100, G, "A war of this many clashes is a great war worth remembering")
    great_war_epochs: int = rule(3, 1, 100, G, "A war lasting this many epochs is a great war worth remembering")
    war_chance: int = rule(65, 0, 100, G, "Chance that a great war is remembered when it ends (%)")
    small_war_chance: int = rule(20, 0, 100, G, "Chance that a small war is remembered when it ends (%)")
    monument_chance: int = rule(50, 0, 100, G, "Chance that a rich victor raises a victory monument (%)")
    disaster_monument_chance: int = rule(30, 0, 100, G, "Chance that a rich community remembering a disaster raises a monument (%)")
    disaster_tradition_chance: int = rule(50, 0, 100, G, "Chance that a community remembering a disaster founds a day of remembrance instead of a tale (%)")
    hero_monument_chance: int = rule(30, 0, 100, G, "Chance that a rich community builds a tomb for its fallen hero (%)")
    rich_threshold: int = rule(40, 0, 100, G, "Least prosperity or wealth of a community that can raise a monument")
    disaster_severity: int = rule(60, 0, 100, G, "A disaster of this severity can be remembered")
    disaster_losses: int = rule(500, 0, 100000000, G, "A disaster that took this many lives in all can be remembered")
    disaster_chance: int = rule(45, 0, 100, G, "Chance that a great disaster is remembered (%)")
    hero_chance: int = rule(55, 0, 100, G, "Chance that a fallen hero without a memorial is remembered an epoch later (%)")
    epoch_cap: int = rule(0, 0, 100000, G, "Most memorial records per epoch, wars, disasters and heroes together (0 for no limit beyond each one's own roll)")
    fallen_named: int = rule(3, 0, 50, G, "Most fallen heroes named in one war epic or lament")
    monument_power: int = rule(3, 1, 12, G, "Power level of a memorial monument")
    monument_splendor: int = rule(35, 0, 100, G, "Base splendor of a memorial monument")
    monument_splendor_die: int = rule(30, 1, 100, G, "Splendor die of a memorial monument")
    monument_durability: int = rule(55, 0, 100, G, "Base durability of a memorial monument")
    monument_durability_die: int = rule(30, 1, 100, G, "Durability die of a memorial monument")
    monument_function: int = rule(15, 0, 100, G, "Base function of a memorial monument")
    monument_function_die: int = rule(20, 1, 100, G, "Function die of a memorial monument")
    work_power: int = rule(2, 1, 12, G, "Power level of an epic or lament")
    work_renown: int = rule(30, 0, 100, G, "Base renown of an epic or lament")
    work_renown_die: int = rule(30, 1, 100, G, "Renown die of an epic or lament")
    work_influence: int = rule(20, 0, 100, G, "Base influence of an epic or lament")
    work_influence_die: int = rule(25, 1, 100, G, "Influence die of an epic or lament")
    tradition_power: int = rule(2, 1, 12, G, "Power level of a remembrance tradition")
    tradition_spread: int = rule(35, 0, 100, G, "Spread of a remembrance tradition")
    tradition_rigidity: int = rule(40, 0, 100, G, "Rigidity of a remembrance tradition")
    legend_power: int = rule(2, 1, 12, G, "Power level of a remembrance tale")
    legend_spread: int = rule(40, 0, 100, G, "Spread of a remembrance tale")
    lament_grudge: int = rule(8, 0, 100, G, "Relation lost to the victor when the loser sings its lament")
    peace_oath_warmth: int = rule(8, 0, 100, G, "Relation gained by both sides of a peace oath")
    plague_severity: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A plague of this severity shakes the faith of those it strikes")
    plague_turn_chance: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance that a plague-struck community turns to a god of death or healing (%)")
    plague_estrange_chance: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance that a plague-struck community turns away from its god (%)")
    plague_piety_gain: int = rule(8, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Piety gained by a plague-struck community clinging to its god")
    plague_piety_loss: int = rule(12, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Piety lost by a plague-struck community turning from its god")
    plague_followers_pct: int = rule(12, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Follower growth of cults where a plague struck (%)")
    plague_cap: int = rule(
        0,
        0,
        100000,
        RuleGroup.RELIGION_AND_LANGUAGE,
        "Most plague-struck communities whose faith is shaken per epoch (0 for no limit beyond each one's own roll)",
    )
    commemorate_cost: int = rule(12, 0, 1000, RuleGroup.INTERVENTION, "Essence cost of the god ordering a war, disaster or death remembered")
