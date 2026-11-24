from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span


@dataclass(frozen=True)
class EspionageRules(Spanned):
    spy_net_enemy_bonus_pct: int = rule(
        20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Bonus to setting up a spy network against an enemy or a tribute counterpart (%)"
    )
    spy_net_chance: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "An influential faction sets up a spy network (%)")
    wider_sabotage_pct: int = rule(
        50,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Chance a sabotage strikes networks, crossings, fields, stores, guards, rites, sources or machines where the target has them (%)",
    )
    sabotage_outage_years: int = span(1, 1, 500, RuleGroup.WAR_AND_DIPLOMACY, "Years a network attack keeps a network dark")
    sabotage_outage_severity: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Severity of the outage a network attack causes")
    haul_damage: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of a town's hauling capacity a destroyed bridge takes (%)")
    blight_pct: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of a town's food a loosed blight destroys (%)")
    theft_pct: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of a town's food a supply theft carries off (%)")
    mutiny_militia: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of a town's militia an incited mutiny takes (%)")
    mutiny_unrest: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Unrest an incited mutiny adds to a town")
    rite_piety: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Piety a disrupted rite takes from a town")
    source_damage: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Stability a poisoning takes from each source of power a town draws on")
    spy_war_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Captured spies lead to war (%)")
    spy_action_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "The spy network acts this epoch (%)")
    spy_steal_knowledge_pct: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of spy actions that steal knowledge (otherwise sabotage) (%)")
    spy_min_sway: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Minimum sway of a faction able to set up a spy network")
    spy_net_cap: int = rule(1, 0, 10000, RuleGroup.WAR_AND_DIPLOMACY, "Maximum new spy networks per epoch (base)")
    spy_net_cap_owner_divisor: int = rule(
        5, 0, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Spy network cap grows by 1 for every this many factions, realms and cults (0: fixed)"
    )
    spy_target_relation: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Coldness counted as a spy target (relation below minus this)")
    spy_capture_base_pct: int = rule(12, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Base chance of spies being captured (%)")
    spy_capture_default: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Capture: value assumed if the target has no sway/defense")
    spy_capture_divisor: int = rule(400, 1, 100000, RuleGroup.WAR_AND_DIPLOMACY, "Capture: target's sway / this number is added")
    spy_caught_relation_loss: int = rule(20, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation damage from captured spies")
    spy_sabotage_damage: int = rule(6, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Damage of sabotage to defense, strength and wealth")
    depth_gain: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Depth a spy network gains in an epoch, more under a skilled spymaster")
    intel_gain: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Intelligence a network at full depth gathers in an epoch")
    exposure_per_operation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure an operation leaves behind")
    exposure_decay: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure that fades in a quiet epoch")
    agent_service_years: int = span(20, 1, 25000, RuleGroup.WAR_AND_DIPLOMACY, "Years a spy serves before retiring from the network")
    counter_intel_pct: int = rule(100, 0, 300, RuleGroup.WAR_AND_DIPLOMACY, "Weight of the target's spymaster in catching spies (%)")
    assassinate_depth: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Depth a network needs to reach a ruler")
    incite_unrest: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Unrest agents stir up in a city")
    incite_uprising_unrest: int = rule(70, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Unrest at which incited townsfolk rise against their rulers")
    blackmail_wealth: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wealth a blackmailed ruler pays")
    counterfeit_trust: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Trust a coin loses to false coins")
    granary_fire_pct: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Food a granary fire destroys (%)")
    wall_damage: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Wall condition lost to sappers in the night")
    arson_damage: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Condition a district loses to arson")
    assassin_hp: int = rule(30, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Harm an assassin deals when the network is too shallow to kill")
    planted_claim: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength of a claim spies plant for a pretender")
    reveal_intel: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Intelligence at which a network reveals the target's war aims")
    blackmail_relation: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Goodwill a blackmailed envoy or chancellor buys")
    polity_spy_chance: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A realm with a spymaster sets up a spy network (%)")
    cult_spy_zeal: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Zeal at which a cult sends spies among its rivals")
    roll_up_exposure: int = rule(80, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure at which a network with no agents left is rolled up")
    poison_severity: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Severity of the sickness from poisoned wells")
    privacy_pct: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of the intel spies gather that a privacy law at full strictness denies them (%)")
    spy_role_skill: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Skill a trained spy brings to a network that recruits them")

    steal_knowledge_difficulty: int = rule(
        30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at stealing knowledge that fail for a network of no depth and a spymaster of no skill (%)"
    )
    sabotage_difficulty: int = rule(
        35, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at sabotage that fail for a network of no depth and a spymaster of no skill (%)"
    )
    assassinate_difficulty: int = rule(
        60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at an assassination that fail for a network of no depth and a spymaster of no skill (%)"
    )
    incite_difficulty: int = rule(
        30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at inciting unrest that fail for a network of no depth and a spymaster of no skill (%)"
    )
    intel_difficulty: int = rule(
        10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at gathering intelligence that fail for a network of no depth and a spymaster of no skill (%)"
    )
    blackmail_difficulty: int = rule(
        40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at blackmail that fail for a network of no depth and a spymaster of no skill (%)"
    )
    counterfeit_difficulty: int = rule(
        35, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of tries at counterfeiting coin that fail for a network of no depth and a spymaster of no skill (%)"
    )
    infiltrate_difficulty: int = rule(
        45,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Share of tries at placing an agent inside an institution that fail for a network of no depth and a spymaster of no skill (%)",
    )
    exfiltrate_difficulty: int = rule(
        50,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Share of tries at bringing an agent or defector out that fail for a network of no depth and a spymaster of no skill (%)",
    )
    disinform_difficulty: int = rule(
        40,
        0,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Share of tries at feeding false beliefs to a rival that fail for a network of no depth and a spymaster of no skill (%)",
    )
    infiltrate_access_pct: int = rule(
        30, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Extra access later operations of a network gain from an agent placed inside an institution (%)"
    )
    exfiltrate_capture_pct: int = rule(
        25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance an agent or defector brought out across a border is caught on the way (%)"
    )
    disinform_confidence: int = rule(
        60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Confidence a false belief fed by a network of full depth carries in its rival's mind"
    )
    exposed_feed_pct: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of an exposed agent's reports the enemy turns into false reports (%)")
    missing_pct: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance each epoch an agent at high exposure drops out of contact and goes missing (%)")
    found_pct: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance each epoch a missing agent is found again by its network (%)")
    exposed_at: int = rule(70, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Exposure from which an agent the enemy has not caught is known to it and watched")

    @property
    def sabotage_outage_epochs(self) -> int:
        return self.epochs(self.sabotage_outage_years)

    @property
    def agent_service_epochs(self) -> int:
        return self.epochs(self.agent_service_years)

    recruit_agent_difficulty: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Difficulty of an operation to win a new agent inside the target")
    surveil_difficulty: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Difficulty of an operation that only watches the target")
    route_block_danger: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Danger of banditry a blocking saboteur adds to each route of the target")
    sleeper_pct: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance an agent won in peace waits embedded as a sleeper until war (%)")
    surveil_gain: int = rule(8, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Intelligence a watch on the target gathers each operation, at little risk")
