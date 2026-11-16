from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

D = RuleGroup.THE_DIVINE
P = RuleGroup.THE_GODS_POWER


@dataclass(frozen=True)
class DominionRules:
    temple_weight: int = rule(30, 0, 200, D, "Dominion a fully splendid, fully staffed temple of a god radiates over its region")
    holy_site_weight: int = rule(20, 0, 200, D, "Dominion a fully sacred place kept by a god's faithful radiates over its region")
    throne_weight: int = rule(25, 0, 200, D, "Dominion a throne of power radiates for the god who holds it")
    prophet_weight: int = rule(10, 0, 200, D, "Dominion each prophet or saint of a god radiates over the region they live in")
    miracle_weight_pct: int = rule(40, 0, 400, D, "Share of a miracle's belief that becomes dominion in its region this epoch (%)")
    worship_weight: int = rule(30, 0, 200, D, "Dominion a region gives the god of all its believers")
    strength_weight_pct: int = rule(50, 0, 200, D, "Share of a god's dominion strength added to each region where it has a source (%)")
    spread_pct: int = rule(20, 0, 100, D, "Share of a region's dominion that spreads to each neighbouring region per epoch (%)")
    decay_pct: int = rule(15, 0, 100, D, "Share of dominion that fades each epoch in a region where the god has no source (%)")
    contest_pct: int = rule(10, 0, 100, D, "Share of a rival's dominion the strongest god converts in a contested region each epoch (%)")
    dominate_share: int = rule(40, 0, 100, D, "Share of a region's dominion a god needs before its scales rule the land there (%)")
    regions_max: int = rule(4000, 1, 1000000, D, "Regions the dominion step weighs at most each epoch")
    cheap_pct: int = rule(25, 0, 100, D, "Discount on a god's miracles and rites at full dominion in the target's region (%)")
    dear_pct: int = rule(25, 0, 300, D, "Surcharge on a god's miracles and rites in a region another god fully dominates (%)")
    conversion_pct: int = rule(20, 0, 200, D, "Better chance a missionary converts in a region its god fully dominates (%)")
    near_stress: int = rule(6, 0, 100, D, "Stress a worshipper sheds in a region its god dominates")
    alien_stress: int = rule(8, 0, 100, D, "Stress a priest of another god takes in a dominated region")
    thoughts_max: int = rule(200, 0, 100000, D, "Mortals the dominion step gives a thought to each epoch at most")
    existence_per_region: int = rule(1, 0, 100, D, "Existence a son draws from each region its dominion rules")
    existence_cap: int = rule(12, 0, 100, D, "Most existence a son draws from the land its dominion rules")
    danger_per_step: int = rule(4, 0, 100, D, "Danger each step of turmoil adds to a dominated region, and each step of order removes")
    prosperity_per_step: int = rule(3, 0, 100, D, "Prosperity each step of order or productivity adds to the settlements of a dominated region")
    tension_per_step: int = rule(8, 0, 1000, D, "Drama each step of turmoil in a dominated region adds to its world's tension each epoch")
    heat_per_step: int = rule(4, 0, 100, D, "Temperature each step of heat or cold shifts a dominated region")
    harvest_per_step_pct: int = rule(5, 0, 100, D, "Harvest each step of productivity or sloth adds or removes in a dominated region (%)")
    fertility_per_step: int = rule(4, 0, 100, D, "Fertility each step of growth adds to a dominated region, and each step of death removes")
    growth_per_step_pct: int = rule(4, 0, 100, D, "Population growth each step of growth or death adds or removes in a dominated region (%)")
    necromancy_per_step_pct: int = rule(10, 0, 100, D, "Discount on rites that raise the dead for each step of death in the region (%)")
    fortune_per_step_pct: int = rule(
        12, 0, 100, D, "Chance of disasters each step of misfortune adds, and each step of fortune removes, in a dominated region (%)"
    )
    magic_per_step: int = rule(5, 0, 100, D, "Magic density each step of magic adds to a dominated region, and each step of drain removes")
    deed_shift_count: int = rule(3, 1, 100, D, "Like deeds of a god in recent epochs that move one of its scales a step toward them")
    ward_per_step_pct: int = rule(8, 0, 100, D, "Better warding each step of drain gives rites in a dominated region (%)")
    order_per_step: int = rule(4, 0, 100, D, "Public order each step of order adds to the settlements of a dominated region, and each step of turmoil removes")
    crime_per_step: int = rule(3, 0, 100, D, "Crime each step of order removes from the settlements of a dominated region, and each step of turmoil adds")
    unrest_per_step: int = rule(3, 0, 100, D, "Unrest each step of turmoil adds to the settlements of a dominated region each epoch")
    output_per_step_pct: int = rule(
        5, 0, 100, D, "Output of mines, quarries, forests and other works each step of productivity adds, and each step of sloth removes (%)"
    )
    healing_per_step_pct: int = rule(
        8, 0, 100, D, "Better healing of wounds each step of growth gives in a dominated region, and worse healing each step of death (%)"
    )
    spirit_unrest_per_step: int = rule(3, 0, 100, D, "Unrest each step of death adds to the spirits of a dominated region each epoch")
    rite_power_pct: int = rule(25, 0, 200, D, "Extra power of a god's rites cast where its dominion holds the whole region (%)")
    miracle_power_pct: int = rule(25, 0, 200, D, "Extra belief a god's miracle wins where its dominion holds the whole region (%)")
    worship_population: int = rule(1000, 1, 1000000, D, "Folk whose worship gives their god the full worship weight in their region")
    blame_fear: int = rule(6, 0, 100, D, "Fear a disaster in a dominated region wins its ruling god among the communities it strikes")
    blame_love: int = rule(4, 0, 100, D, "Love a disaster in a dominated region costs its ruling god among the communities it strikes")


@dataclass(frozen=True)
class MiracleImpressionRules:
    creator_magnitude: int = rule(100, 0, 100, D, "Magnitude of a miracle the Creator works, against a son's might")
    base_belief: int = rule(10, 0, 1000, D, "Belief a miracle of full magnitude wins with one witness, before need, novelty and legibility")
    witness_cap: int = rule(400, 1, 100000, D, "Witnesses past which a miracle's belief stops growing")
    witness_log_pct: int = rule(100, 0, 1000, D, "Weight of the witnesses on a miracle's belief, by the doubling of their number (%)")
    need_pct: int = rule(100, 0, 400, D, "Extra belief a miracle wins at full need: hunger, sickness, war or disaster (%)")
    repeat_drop_pct: int = rule(25, 0, 100, D, "Novelty a miracle loses for each like miracle the same god worked there lately (%)")
    repeat_window: int = rule(5, 1, 100, D, "Epochs back a god's like miracles count against a new one's novelty")
    misread_pct: int = rule(60, 0, 100, D, "Chance a miracle in a land another god dominates is credited to that god when it fits that god better (%)")
    awe_per_belief_pct: int = rule(50, 0, 400, D, "Awe the witnesses' community gains for each point of belief (%)")
    faith_per_belief_pct: int = rule(100, 0, 400, D, "Faith the credited god gains for each point of belief (%)")


@dataclass(frozen=True)
class WorshipViewRules:
    benevolent_margin: int = rule(15, 0, 100, D, "Love above fear at which a people perceives a god as benevolent")
    malevolent_margin: int = rule(15, 0, 100, D, "Fear above love at which a people perceives a god as malevolent")
    appease_fear: int = rule(40, 0, 100, D, "Fear at which a people worships a god to appease it rather than out of devotion")
    appeasement_offering_pct: int = rule(20, 0, 200, D, "Extra faith a feared god gains from offerings meant to keep it away (%)")
    devotion_morale: int = rule(5, 0, 100, D, "Piety a devoted people's settlements gain toward their god each epoch")
    temple_shift: int = rule(4, 0, 100, D, "Splendour a temple of a god its people love gains each epoch, and one of a god they fear loses")


@dataclass(frozen=True)
class GodImageRules:
    base_pull: int = rule(10, 0, 100, D, "Pull of the believed image on a god's temperament at full belief, share, crisis and malleability")
    stern_gap: int = rule(15, 0, 100, D, "Lead of believed wrath over believed mercy at which a god neither loved nor hated is seen as stern")
    yield_pull_pct: int = rule(100, 0, 400, D, "Share of the pull of its believed image a son that yields to it takes on (%)")
    manifest_order: int = rule(
        2, 0, 100, D, "Unrest the way a god is seen moves in its faithful towns each epoch: a stern god quiets them, a dreadful one unsettles them"
    )
    domain_pressure_at: int = rule(100, 1, 10000, D, "Pressure of a believed domain at which a god's second domain turns to it")
    domain_pressure_gain: int = rule(10, 0, 1000, D, "Pressure a believed domain the god lacks gains each epoch at full pull")
    resist_cost: int = rule(15, 0, 10000, P, "Essence a son spends each epoch to resist the image its peoples hold of it")
    embrace_fame: int = rule(3, 0, 100, P, "Fame a son gains each epoch it embraces the image its peoples hold of it")
    embrace_pull_pct: int = rule(200, 100, 1000, D, "Pull on a son that embraces its believed image (%)")
    crisis_war_pct: int = rule(40, 0, 100, D, "Crisis a war among the god's peoples adds (%)")
    crisis_hunger_pct: int = rule(40, 0, 100, D, "Crisis at full hunger among the god's peoples (%)")
    crisis_disaster_pct: int = rule(30, 0, 100, D, "Crisis a disaster among the god's peoples this epoch adds (%)")
    fading_malleability: int = rule(80, 0, 100, D, "Malleability of a fading god, before its will and pride")
    radiant_malleability: int = rule(10, 0, 100, D, "Malleability of a radiant god, before its will and pride")
    will_resist_pct: int = rule(50, 0, 100, D, "Share of a god's will and ambition that resists its believed image (%)")
    facet_pull_pct: int = rule(50, 0, 200, D, "Share of the pull that moves a god's anger and altruism toward its believed wrath and mercy (%)")
    folk_credence_pct: int = rule(50, 0, 100, D, "Share of belief intensity that comes from the peoples who tell their own stories of the god (%)")


@dataclass(frozen=True)
class ThroneRules:
    per_world: int = rule(3, 0, 50, D, "Thrones of power on each world")
    power: int = rule(60, 0, 100, D, "Power of a new throne")
    dominion_share: int = rule(60, 0, 100, D, "Share of a throne's region a god's dominion needs to hold the throne (%)")
    essence: int = rule(6, 0, 10000, P, "Essence a held throne gives its god each epoch at full power")
    standing: int = rule(2, 0, 100, D, "Awe the communities of a throne's world feel for the god who holds it each epoch")
    spread_pct: int = rule(25, 0, 200, D, "Extra spread a god's dominion gains from each throne it holds (%)")
    ascension_share: int = rule(51, 1, 100, D, "Share of a world's thrones a god must hold for its ascension goal to count that world (%)")
    ascension_worlds: int = rule(1, 1, 100, D, "Worlds whose thrones a god must hold to ascend")
    rank_essence_pct: int = rule(20, 0, 400, P, "Extra essence income for each divine rank a god has reached (%)")


@dataclass(frozen=True)
class MagicSiteRules:
    per_world: int = rule(4, 0, 100, D, "Magic sites hidden on each world")
    strength: int = rule(50, 0, 100, D, "Strength of a new magic site")
    search_pct: int = rule(20, 0, 100, D, "Chance a mage with the site's school searches its land and finds it each epoch (%)")
    search_skill: int = rule(
        40, 0, 100, D, "Spellcraft in a site's school a mage needs, or tracking an explorer needs, before searching for hidden magic sites"
    )
    explorer_search_pct: int = rule(10, 0, 100, D, "Chance an explorer without the site's school searches its land and finds it each epoch (%)")
    output_pct: int = rule(20, 0, 200, D, "Reagents a source site yields its holder each epoch for each point of strength (%)")
    school_pct: int = rule(25, 0, 200, D, "Extra power rites of the site's school gain in its region at full strength (%)")
    ward_pct: int = rule(25, 0, 200, D, "Extra warding rites gain in a warded site's region at full strength (%)")
    sacredness: int = rule(10, 0, 100, D, "Sacredness a found magic site adds to its place")
    war_aim_pct: int = rule(30, 0, 100, D, "Chance each epoch a realm covets a found magic site its rival holds (%)")


@dataclass(frozen=True)
class DivineCreatureRules:
    lesson_shift: int = rule(15, 0, 100, D, "Weight a reward adds to a deed, or a punishment removes, in a divine creature's mind")
    weight_min: int = rule(1, 0, 100, D, "Lowest weight a divine creature keeps for any deed")
    weight_max: int = rule(100, 1, 1000, D, "Highest weight a divine creature gives any deed")
    hunger_gain: int = rule(12, 0, 100, D, "Hunger a divine creature gains each epoch it does not hunt or tend")
    hunger_pull: int = rule(60, 0, 100, D, "Hunger past which a neglected creature hunts on its own need")
    neglect_epochs: int = rule(3, 0, 100, D, "Epochs without a lesson after which a creature drifts on its own needs")
    harm: int = rule(25, 0, 200, D, "Harm a divine creature deals the mortal it hunts or the foe it strikes")
    tend_food: int = rule(30, 0, 10000, D, "Food a divine creature's tending adds to a community")
    heal: int = rule(20, 0, 200, D, "Health a divine creature restores to the sick it tends")
    wreck: int = rule(20, 0, 100, D, "Condition a divine creature's rampage takes from a structure")
    love_per_deed: int = rule(4, 0, 100, D, "Love a helpful deed of the creature wins its god among those it helped")
    fear_per_deed: int = rule(4, 0, 100, D, "Fear a harmful deed of the creature wins its god among those it harmed")
    dominion_per_deed: int = rule(5, 0, 100, D, "Dominion a deed of the creature wins its god in the region where it acted")
    raise_cost: int = rule(120, 0, 100000, P, "Essence a son spends to raise a divine creature")
    teach_cost: int = rule(10, 0, 10000, P, "Essence a son spends to reward or punish its creature")


@dataclass(frozen=True)
class GodDesignRules:
    budget_per_rank: int = rule(20, 0, 1000, P, "Design budget a son gets for each step of its rarity's rank")
    budget_per_star: int = rule(10, 0, 1000, P, "Design budget a son gets for each star")
    dominion_cost_pct: int = rule(20, 0, 200, P, "Design cost of each point of dominion strength (%)")
    magic_cost_pct: int = rule(20, 0, 200, P, "Design cost of each point of magic aptitude (%)")
    manifestation_cost_pct: int = rule(15, 0, 200, P, "Design cost of each point of manifestation strength (%)")
    scale_cost: int = rule(4, 0, 100, P, "Design cost of each step of a scale toward its favoured pole, and refund of each step toward its other pole")
    power_cost: int = rule(10, 0, 100, P, "Design cost of each power")
    stats_floor_pct: int = rule(50, 0, 100, P, "Least share of its rolled stats a son keeps however much it spends on the rest of its design (%)")
    aptitude_rite_pct: int = rule(
        40, 0, 200, P, "Extra power a god of full magic aptitude gives the rites of its faithful, and the power a god of none takes away (%)"
    )
    manifestation_floor_pct: int = rule(50, 0, 100, P, "Share of its full health and power a god's mortal form keeps at no manifestation strength (%)")
    rank_levels: int = rule(5, 0, 100, P, "Levels each divine rank counts as toward unlocking power slots")
