from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.COSMOS_AND_TRAVEL


@dataclass(frozen=True)
class WorldBalanceRules:
    son_share_exponent_pct: int = rule(50, 0, 100, G, "Exponent of a world's son share over its communities (%; 50 square root, 100 linear, 0 equal)")
    godless_weight_pct: int = rule(100, 0, 1000, G, "Extra weight of a godless community in a world's son share (%)")
    son_moves: int = rule(1, 0, 100, G, "Most sons moved per epoch to balance the worlds (0 off)")
    son_gap: int = rule(1, 1, 100, G, "Least sons a donor world must exceed and a receiving world must miss its share by")
    agent_share_exponent_pct: int = rule(50, 0, 100, G, "Exponent of a world's mortal agent share over its candidates (%; 50 square root, 100 linear)")
    faction_minimum: int = rule(1, 0, 100, G, "Least factions expected in every living world")
    faction_chance: int = rule(35, 0, 100, G, "Per-epoch chance that a faction rises in a world without one (%)")
    faction_population: int = rule(400, 0, 1000000, G, "Least population of a community a balancing faction can rise from")
    faction_stat: int = rule(25, 0, 100, G, "Base strength, wealth and sway of a balancing faction")
    faction_stat_die: int = rule(20, 1, 100, G, "Stat die of a balancing faction")
    cult_minimum: int = rule(1, 0, 100, G, "Least cults expected in every living world")
    cult_chance: int = rule(30, 0, 100, G, "Per-epoch chance that a cult rises in a world without one (%)")
    cult_piety: int = rule(40, 0, 100, G, "Least piety of a community a balancing cult can rise from")
    cult_followers_pct: int = rule(5, 0, 100, G, "Share of its community's people a balancing cult starts with (%)")
    cult_followers_minimum: int = rule(40, 1, 1000000, G, "Least followers of a balancing cult")
    cult_zeal: int = rule(30, 0, 100, G, "Base zeal and influence of a balancing cult")
    record_quota: int = rule(6, 0, 1000, G, "Least engine records expected in a living world per epoch")
    revival_cap: int = rule(3, 0, 100, G, "Most spontaneous births or traditions in a world below its record quota per epoch")
    revival_chance: int = rule(60, 0, 100, G, "Chance of each revival in a world below its record quota (%)")
    activity_window: int = rule(5, 1, 100, G, "Epochs over which a world's activity is measured")
    tradition_spread: int = rule(25, 0, 100, G, "Spread of a tradition begun by a world's revival")
    tradition_rigidity: int = rule(30, 0, 100, G, "Rigidity of a tradition begun by a world's revival")
    revive_cost: int = rule(25, 0, 1000, RuleGroup.INTERVENTION, "Essence cost of the god reviving a world")
    guardian_cost: int = rule(0, 0, 1000, RuleGroup.INTERVENTION, "Essence cost of the god appointing a world's guardian")
