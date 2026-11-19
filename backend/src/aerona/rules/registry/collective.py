from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.SETTLEMENTS
M = RuleGroup.MIND
C = RuleGroup.CHRONICLE
F = RuleGroup.FATE_AND_CHRONICLE
P = RuleGroup.POPULATION_AND_GROWTH
H = RuleGroup.HOUSES
R = RuleGroup.RELIGION_AND_LANGUAGE
W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class CollectiveBehaviourRules:
    trigger_pct: int = rule(25, 0, 100, S, "Chance each epoch that a town's strongest grievance sparks a collective act (%)")
    base_threshold: int = rule(60, 0, 100, S, "Share of a district already acting that an average dweller needs before joining (%)")
    anger_cut: int = rule(40, 0, 100, S, "Threshold points a town's full anger takes away")
    anxiety_cut: int = rule(35, 0, 100, S, "Threshold points a town's full anxiety takes away from panic")
    fervour_cut: int = rule(40, 0, 100, S, "Threshold points a town's full fervour takes away from faith's mass acts")
    conformity_weight: int = rule(30, 0, 100, M, "Threshold points the conformity facet moves, lower for the conformist when many act")
    deterrence_lift: int = rule(40, 0, 100, S, "Threshold points the full deterrence of watch and garrison adds")
    agitation_cut: int = rule(25, 0, 100, S, "Threshold points a charismatic agitator's full sway takes away")
    spark_share: int = rule(3, 0, 100, S, "Share of a district that starts a collective act when a trigger strikes (%)")
    rounds: int = rule(8, 1, 50, S, "Rounds a cascade is followed within a sampled year")
    mob_share: int = rule(15, 0, 100, S, "Share of a district acting past which a riot becomes a mob (%)")
    movement_share: int = rule(30, 0, 100, S, "Share of a district acting past which a cascade becomes a lasting movement (%)")
    mob_damage_pct: int = rule(20, 0, 100, S, "Condition a raging mob takes from the district or work it storms, at full anger (%)")
    lynch_pct: int = rule(40, 0, 100, S, "Chance a mob with a scapegoat kills it (%)")
    fatigue: int = rule(20, 0, 100, S, "Anger a mob loses each epoch")
    force_pct: int = rule(50, 0, 200, S, "Share of the town's militia that a mob must outnumber to resist being broken (%)")
    concession_calm: int = rule(25, 0, 100, S, "Anger a ruler's concession takes from a mob")
    panic_flight_pct: int = rule(4, 0, 100, S, "Share of a panicking district that flees the town (%)")
    trample_per_mille: int = rule(3, 0, 1000, S, "People per thousand trampled in a crowded panicking district")
    hoard_pct: int = rule(10, 0, 100, S, "Share of a town's food a panic hoards away from the market (%)")
    movement_decay: int = rule(5, 0, 100, S, "Strength a movement loses each epoch without a fresh grievance")
    movement_revolt_at: int = rule(70, 0, 100, S, "Strength at which a movement takes up arms as a rebel faction")
    conversion_pct: int = rule(5, 0, 100, R, "Share of a district a mass conversion wins to the cult that sparked it (%)")
    mood_decay: int = rule(10, 0, 100, S, "Anger, anxiety and fervour a town loses each epoch")
    heat: int = rule(20, 0, 100, S, "Mood a trigger at full force adds to a town's anger, anxiety or fervour")
    deterrence_full: int = rule(8, 1, 100, S, "Soldiers and watch per hundred dwellers that give a town full deterrence")
    spread_pct: int = rule(20, 0, 100, S, "Spread of thresholds around a town's mean, as a share of the scale (%)")
    sample: int = rule(200, 10, 5000, S, "Dwellers a cascade samples to find who joins")
    famine_food: int = rule(30, 0, 1000, S, "Food stock per hundred dwellers below which a town feels famine")
    price_spike: int = rule(160, 100, 1000, S, "Food price, against the usual hundred, past which a town feels a price spike")


@dataclass(frozen=True)
class HistoriographyRules(Spanned):
    official_fidelity: int = rule(60, 0, 100, C, "Fidelity of an official chronicle to what happened (%)")
    folk_fidelity: int = rule(45, 0, 100, C, "Fidelity of folk memory to what happened (%)")
    foreign_fidelity: int = rule(50, 0, 100, C, "Fidelity of a foreign account to what happened (%)")
    fidelity_decay: int = rule(2, 0, 100, C, "Fidelity an oral account loses each epoch")
    credence_decay: int = rule(1, 0, 100, C, "Credence an account loses each epoch it is not retold")
    strike_fade: int = rule(5, 0, 100, C, "Fame a struck figure loses each epoch while no folk memory or foreign account keeps it")
    revise_pct: int = rule(30, 0, 100, C, "Chance a new ruler rewrites the official accounts of a reign it ousted (%)")
    scandal_pct: int = rule(20, 0, 100, C, "Chance each epoch a scholar finds an older account that contradicts a revision (%)")
    myth_cohesion: int = rule(10, 0, 100, C, "Cohesion a fully credited founding myth lends its people")
    myth_legitimacy: int = rule(8, 0, 100, C, "Legitimacy a fully credited founding myth lends its realm")
    debunk_cost: int = rule(15, 0, 100, C, "Cohesion and legitimacy a debunked founding myth costs")
    commemorate_every_years: int = span(100, 1, 25000, C, "Years between the anniversaries a people relives")
    commemoration_fade: int = rule(5, 0, 100, C, "Strength a commemoration loses each anniversary nobody keeps")
    grievance_unrest: int = rule(4, 0, 100, C, "Unrest a kept anniversary of a massacre or defeat stirs")
    pride_order: int = rule(3, 0, 100, C, "Order a kept anniversary of a victory or founding lends")
    irredentist_claim_at: int = rule(60, 0, 100, W, "Memory strength of a lost land past which its old holder presses a claim")
    lost_land_fade: int = rule(2, 0, 100, W, "Memory strength a lost land loses each epoch")

    @property
    def commemorate_every(self) -> int:
        return self.epochs(self.commemorate_every_years)


@dataclass(frozen=True)
class StoryletRules:
    chance_pct: int = rule(30, 0, 100, F, "Chance each epoch a world opens a storylet whose condition holds (%)")
    cooldown_epochs: int = rule(6, 0, 1000, F, "Epochs before the same storylet may open again in a world")
    open_epochs: int = rule(2, 0, 100, F, "Epochs a storylet waits for its chooser before the engine chooses")
    follow_epochs: int = rule(3, 0, 100, F, "Epochs before a chosen branch's follow-up opens")
    max_open: int = rule(3, 0, 100, F, "Storylets a world holds open at once")


@dataclass(frozen=True)
class NormRules:
    drift_pct: int = rule(8, 0, 100, M, "Chance each epoch a culture's norm moves a step toward what its values now favour (%)")
    doctrine_pct: int = rule(50, 0, 100, R, "Chance a doctrine against a behaviour sets its norm at once (%)")
    law_pct: int = rule(60, 0, 100, M, "Chance a sumptuary law sets the dress norm at once (%)")


@dataclass(frozen=True)
class VolitionRules:
    norm_cost: int = rule(60, 0, 300, M, "Score a shameful breach of a norm takes away, scaled by conformity (%)")
    norm_draw: int = rule(30, 0, 300, M, "Score a required behaviour adds (%)")
    rebel_appeal: int = rule(40, 0, 300, M, "Score a norm breach gains for those who scorn tradition (%)")
    whim_pct: int = rule(15, 0, 100, M, "Chance a mortal acts on a whim and not on the best-scored choice (%)")
    breach_shame: int = rule(5, 0, 100, M, "Reputation a witnessed breach of a shameful norm costs")


@dataclass(frozen=True)
class SocialLearningRules:
    learners_pct: int = rule(20, 0, 100, M, "Share of a town's grown mortals that copy someone each epoch (%)")
    copy_step: int = rule(4, 0, 100, M, "Value points a copy moves the learner toward the model")
    prestige_floor: int = rule(30, 0, 100, M, "Renown a model needs before others copy them for prestige")
    fear_stickiness: int = rule(150, 100, 500, M, "How much faster fear-borne beliefs spread in an anxious people (%)")
    learners_cap: int = rule(30, 1, 1000, M, "Most mortals in one town that copy someone in an epoch")


@dataclass(frozen=True)
class GenerationRules(Spanned):
    youth_years: int = span(20, 1, 2500, P, "Years of a generation's youth, when the great incidents shape it")
    shift: int = rule(10, 0, 100, M, "Value points a formative incident shifts the generation it shaped")
    inherited_pct: int = rule(50, 0, 100, M, "Share of a generation's shift its children inherit (%)")
    turnover_unrest: int = rule(5, 0, 100, M, "Unrest a generation's passing stirs as suppressed movements rise")
    lifespan_years: int = span(60, 1, 25000, P, "Years a generation lives on after its youth before it has passed")

    @property
    def youth_epochs(self) -> int:
        return self.epochs(self.youth_years)

    @property
    def lifespan_epochs(self) -> int:
        return self.epochs(self.lifespan_years)


@dataclass(frozen=True)
class DiasporaRules:
    pull_pct: int = rule(50, 0, 500, P, "Extra weight a migrant gives a town where their people already live, at a full diaspora (%)")
    chain_ties: int = rule(5, 0, 100, P, "Ties a diaspora gains with each new wave of its people")
    remittance_pct: int = rule(5, 0, 100, P, "Share of a diaspora's wealth sent home each epoch (%)")
    ties_decay: int = rule(3, 0, 100, P, "Ties a diaspora loses each epoch without new arrivals")
    quarter_at: int = rule(500, 0, 1000000, P, "People a diaspora needs before it raises a foreign quarter")
    assimilate_at: int = rule(10, 0, 100, P, "Ties below which a diaspora merges into its host")


@dataclass(frozen=True)
class DemographicTransitionRules:
    urban_cut: int = rule(30, 0, 100, P, "Fertility points full urbanisation takes away")
    literacy_cut: int = rule(25, 0, 100, P, "Fertility points full literacy takes away")
    education_cut: int = rule(15, 0, 100, P, "Fertility points women's education takes away where role norms let them study")
    lag_pct: int = rule(25, 0, 100, P, "Share of the gap to its new fertility a people closes each epoch (%)")
    elder_levy_cut: int = rule(50, 0, 100, P, "Share of the levy an ageing people loses for each elder share point above a third (%)")
    elder_stability: int = rule(5, 0, 100, P, "Order an elder-respecting people gains when it ages")


@dataclass(frozen=True)
class SexRatioRules:
    skew_at: int = rule(85, 0, 1000, P, "Grown men per hundred grown women below which a war has skewed the marriage market")
    polygamy_pct: int = rule(20, 0, 100, P, "Extra marriages a skewed people makes where several spouses are allowed (%)")
    late_marriage_pct: int = rule(20, 0, 100, P, "Marriages a skewed people delays (%)")
    norm_shift_pct: int = rule(30, 0, 100, P, "Chance a skewed people opens a craft or office to women where its norms are flexible (%)")


@dataclass(frozen=True)
class RoleNormRules:
    drift_pct: int = rule(5, 0, 100, M, "Chance each epoch a role norm moves toward what its people now believe (%)")
    breach_stance_cost: int = rule(10, 0, 100, M, "Reputation a mortal loses for holding a role its people frown on")


@dataclass(frozen=True)
class DatingRules:
    reform_pct: int = rule(5, 0, 100, F, "Chance each epoch a realm or cult with a calendar technique reforms its era (%)")
    dispute_pct: int = rule(30, 0, 100, R, "Chance a calendar reform sets the cults that keep the old festivals against it (%)")


@dataclass(frozen=True)
class HeraldryRules:
    cadet_bordure_pct: int = rule(80, 0, 100, H, "Chance a cadet branch differences its arms with a bordure (%)")
    quarter_pct: int = rule(40, 0, 100, H, "Chance a marriage of two armigerous houses quarters the heir's arms (%)")


@dataclass(frozen=True)
class DesignRules:
    mass_budget: int = rule(30, 1, 1000, W, "Size points a design's components may total")
    wear_per_leg: int = rule(6, 0, 100, W, "Wear a component takes on each voyage leg or campaign")
    storm_wear: int = rule(10, 0, 100, W, "Extra wear a storm leg adds")
    failure_at: int = rule(70, 0, 100, W, "Wear past which a component may fail on a leg")
    failure_pct: int = rule(20, 0, 100, W, "Chance a worn-out component fails on a leg (%)")
    refit_pct: int = rule(15, 0, 100, W, "Chance each epoch a holder with a newer technique refits a design (%)")
    shipyard_repair: int = rule(40, 0, 100, W, "Wear a shipyard takes off a vessel's components each epoch it is in port")
