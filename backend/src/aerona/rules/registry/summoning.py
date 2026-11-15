from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class SummoningRules:
    start_existence: int = rule(60, 0, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "A new son's existence (also assumed if unknown)")
    world_unclaimed_weight_pct: int = rule(200, 0, 10000, RuleGroup.SON_SUMMONING_AND_BIRTH, "New son's world: score per community without worshipped god (%)")
    world_living_weight_pct: int = rule(30, 0, 10000, RuleGroup.SON_SUMMONING_AND_BIRTH, "New son's world: score per living community (%)")
    world_son_penalty_pct: int = rule(300, 0, 10000, RuleGroup.SON_SUMMONING_AND_BIRTH, "New son's world: penalty per son already there (%)")
    domain_shift: int = rule(
        7, 1, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "For a son whose two domains came out the same, how many positions away the second domain is taken"
    )
    shared_domain_relation_loss: int = rule(20, 0, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "Relation loss of a new son with a sibling for each shared domain")
    parent_relation: int = rule(40, -100, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "Child's starting relation with its parent")
    other_parent_relation: int = rule(30, -100, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "Child's starting relation with its other parent")
    child_rarity_rolls: int = rule(
        20, 1, 1000, RuleGroup.SON_SUMMONING_AND_BIRTH, "Maximum rolls for a child's rarity (until it comes out lower than the parent)"
    )
    recent_events: int = rule(45, 0, 500, RuleGroup.CONTEXT_BUDGETS, "Recent events in the summoning prompt")
    rebel_ambition: int = rule(60, 0, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "Son prompt: above this ambition (with low loyalty) prone to rebellion")
    opportunities_chars: int = rule(20000, 0, 100000, RuleGroup.CONTEXT_BUDGETS, "Son prompt: opportunities section (characters)")
    power_effect_cap: int = rule(
        2,
        1,
        100,
        RuleGroup.SON_SUMMONING_AND_BIRTH,
        "Maximum sons in the pantheon carrying the same power effect (excess choices revert to the least-used effect)",
    )
    default_passion: int = rule(50, 0, 100, RuleGroup.SON_SUMMONING_AND_BIRTH, "A new son's passion not written by the model")
