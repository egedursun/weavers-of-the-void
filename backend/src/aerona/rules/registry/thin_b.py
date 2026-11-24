from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.MIND
D = RuleGroup.DIMENSIONS
F = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class NeedsWiderRules(Spanned):
    captive_autonomy: int = rule(60, 0, 100, M, "Autonomy a captive loses")
    serf_autonomy: int = rule(40, 0, 100, M, "Autonomy a serf or slave loses")
    oppression_autonomy_pct: int = rule(50, 0, 200, M, "How much the oppression of a community takes from its members' autonomy (%)")
    literacy_knowledge_pct: int = rule(70, 0, 200, M, "How much the literacy of a people feeds the need for knowledge (%)")
    network_knowledge: int = rule(25, 0, 100, M, "Knowledge a member of a network gains")
    stimulation_base: int = rule(30, 0, 100, M, "Stimulation everyone has before what they do and attend")
    stimulation_per_gathering: int = rule(15, 0, 100, M, "Stimulation each gathering attended lately gives")
    stimulation_years: int = span(3, 1, 1250, M, "Years over which gatherings attended count toward stimulation")
    upkeep_wealth_pct: int = rule(100, 0, 500, M, "How much the wealth of a made being feeds its upkeep (%)")
    fear_of_ending_at: int = rule(30, 0, 100, M, "How far a mortal's values turn from death before old age makes them fear their ending")
    fear_of_ending: int = rule(40, 0, 100, M, "Continuity an old mortal who fears ending lacks")
    activity_need_pct: int = rule(40, 0, 200, M, "How much each share of the day spent on an activity feeds the needs it serves (%)")
    renown_status_at: int = rule(50, 0, 100, M, "Renown at which achievement feeds the need for status")
    renown_status: int = rule(10, 0, 100, M, "Status renown gives")

    @property
    def stimulation_epochs(self) -> int:
        return self.epochs(self.stimulation_years)


@dataclass(frozen=True)
class PreferenceDepthRules:
    sour_at: int = rule(-40, -100, 0, M, "Magnitude of a bad memory tied to a preferred thing at which the preference turns to aversion")
    fashion_pct: int = rule(10, 0, 100, M, "Chance each epoch that a fashion turns a mortal's preference toward what is new (%)")
    price_pct: int = rule(10, 0, 100, M, "How much a community's preference raises the price of what it prefers (%)")
    migration_pull: int = rule(5, 0, 100, M, "Pull a place of a preferred kind adds to a household's wish to move there")
    partner_pull: int = rule(10, 0, 100, M, "Attraction a shared preference adds between two possible partners")


@dataclass(frozen=True)
class BeliefDepthRules:
    trust_step: int = rule(5, 0, 50, M, "How far trust in a source moves when what it told turns out true or false")
    trust_floor: int = rule(10, 0, 100, M, "Trust below which a source no longer changes what is believed")
    surveillance_confidence: int = rule(60, 0, 100, M, "Confidence of what surveillance reports")
    intrusion_confidence: int = rule(70, 0, 100, M, "Confidence of what is taken by intrusion into a network or a mind")
    made_mind_confidence: int = rule(65, 0, 100, M, "Confidence of what a made mind reports to its keeper")
    shared_at: int = rule(3, 1, 1000, M, "Members holding a belief at which their community holds it too")
    public_opinion_pct: int = rule(5, 0, 100, M, "How much a shared belief moves the opinion of a community (%)")
    dream_confidence: int = rule(35, 0, 100, M, "Confidence a mortal gives what it saw of others in a dream, at full intensity")
    omen_confidence: int = rule(40, 0, 100, M, "Confidence one who heeds an omen gives what it reads of its land")


@dataclass(frozen=True)
class StorytellerDepthRules:
    slow_burn_step: int = rule(2, 0, 50, F, "How far the target tension of a slow burn rises each epoch")
    gentle_pct: int = rule(60, 0, 100, F, "Share of the steady aim a gentle storyteller aims for, leaning toward recoveries whatever the tension (%)")
    seasonal_swing: int = rule(15, 0, 50, F, "How far a seasonal storyteller raises and lowers its aim through the turn of its world's seasons")
    episode_epochs: int = rule(4, 1, 50, F, "Epochs in one episode of an episodic storyteller")
    episode_peak: int = rule(70, 0, 100, F, "Target tension at the height of an episode")
    region_crisis_at: int = rule(70, 0, 100, F, "Tension of a region at which it counts as in crisis")


@dataclass(frozen=True)
class RiftControlRules:
    claim_epochs: int = rule(2, 1, 50, D, "Epochs a rift must stay open in a polity's land before the polity claims it")
    seal_step: int = rule(5, 0, 100, D, "How far a sealing work shrinks a rift each epoch")
    stabilise_step: int = rule(5, 0, 100, D, "How far a stabilising work steadies a rift each epoch")
    gate_toll: int = rule(3, 0, 1000, D, "Coin each party crossing a gated rift pays its keeper, when the keeper sets no toll of its own")
    adapt_step: int = rule(3, 0, 100, D, "How far life near a rift adapts to it each epoch")
    adapted_fertility: int = rule(1, 0, 50, D, "Fertility the land near a rift gains each epoch once its life has adapted")
    adapted_at: int = rule(60, 0, 100, D, "Adaptation at which life near a rift thrives on it")
    claim_tension: int = rule(5, 0, 100, D, "Tension between polities that claim rifts in the same world")


@dataclass(frozen=True)
class NormDepthRules:
    generation_drift: int = rule(2, 0, 50, M, "How far a norm drifts toward the values of the young each generation")
    contact_drift: int = rule(1, 0, 50, M, "How far a norm drifts toward a neighbour's each epoch of contact")
    breach_stance: int = rule(-30, -100, 100, M, "Stance on a behaviour below which a community punishes those who break the norm")
    breach_renown: int = rule(3, 0, 100, M, "Renown a norm breaker loses when the community punishes them")


@dataclass(frozen=True)
class WitchcraftDepthRules:
    distance_weight: int = rule(20, 0, 100, M, "Weight of social distance between accuser and suspect when an accuser picks whom to blame")
    eccentric_weight: int = rule(15, 0, 100, M, "Weight of eccentric traits in the suspect")
    belief_weight: int = rule(25, 0, 100, M, "Weight of what the accuser already believes of the suspect")
