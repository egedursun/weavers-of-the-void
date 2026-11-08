from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

K = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class TheoriesRules:
    found_pct: int = rule(5, 0, 100, K, "Chance each epoch that learned scholars found a theory in a field their people has none in (%)")
    found_level: int = rule(2, 0, 10, K, "Level a people must reach in a field's branch before its scholars found a theory of it")
    found_strength: int = rule(40, 0, 100, K, "How firmly a people first holds a theory its scholars founded")
    spread_pct: int = rule(8, 0, 100, K, "Chance each epoch a theory passes to a trade partner or ally of a people that holds it (%)")
    effect_pct: int = rule(20, 0, 100, K, "Most a people's ruling theory helps when true or harms when false (%)")
    anomaly_pct: int = rule(20, 0, 100, K, "Chance each epoch a wholly false ruling theory meets an anomaly; a true one never does (%)")
    explanatory_gain: int = rule(2, 0, 100, K, "Explanatory power a theory gains each epoch it rules without anomaly")
    anomaly_window: int = rule(10, 1, 200, K, "Epochs of anomalies weighed against a theory's explanatory power")
    contest_margin: int = rule(10, 0, 100, K, "Score a rival needs above the ruling theory to win a paradigm contest")
    tradition_weight_pct: int = rule(50, 0, 200, K, "How much a people's tradition favours the ruling theory in a contest (%)")
    institution_bonus: int = rule(15, 0, 100, K, "Contest score an embraced institution or endorsing faith gives a theory")
    endorsed_anomaly_pct: int = rule(50, 0, 100, K, "Share of anomalies a faith's endorsement hides (%)")
    heresy_trial_pct: int = rule(10, 0, 100, K, "Chance each epoch a scholar of a true theory a faith condemns is tried for blasphemy (%)")
    persecution_blow: int = rule(10, 0, 100, K, "Strength a condemned theory loses each epoch among the faithful")
    reveal_cost: int = rule(25, 0, 1000, K, "Essence a son spends to reveal the truth")
    reveal_standing: int = rule(10, 0, 100, K, "Standing a son gains with the scholars of a people it reveals the truth to")
    reveal_anger: int = rule(10, 0, 100, K, "Standing a son loses with a faith that held the theory it overturned")


@dataclass(frozen=True)
class ArtFormsRules:
    invent_pct: int = rule(3, 0, 100, K, "Chance each epoch a creative mortal of great skill invents an art form (%)")
    invent_skill: int = rule(60, 0, 100, K, "Skill a mortal needs to invent an art form")
    stirred_pct: int = rule(100, 0, 400, K, "How much more likely an invention is for an inspired mortal or after a plague or a lost war at home (%)")
    notation_pct: int = rule(50, 0, 400, K, "How much faster a form that is written down spreads (%)")
    fusion_pct: int = rule(4, 0, 100, K, "Chance each epoch two forms of the same discipline meeting in one place fuse into a new one (%)")
    spread_pct: int = rule(8, 0, 100, K, "Chance each epoch a form passes to a trade partner or ally (%)")
    value_fit_pct: int = rule(50, 0, 200, K, "How much a receiving culture's taste for beauty and tradition weighs on taking up a form (%)")
    mastery_gain: int = rule(4, 0, 100, K, "Mastery a practitioner gains each epoch in a form of no difficulty; harder forms are mastered more slowly")
    mastery_quality_pct: int = rule(20, 0, 100, K, "Quality an artwork gains from full mastery of its form (%)")
    prestige_renown_pct: int = rule(20, 0, 100, K, "Renown an artwork gains from full prestige of its form (%)")
    prestige_drift: int = rule(2, 0, 100, K, "Prestige a form gains or loses each epoch as its practitioners grow or fall")
    decline_epochs: int = rule(5, 1, 200, K, "Epochs a form without practitioners or notation survives before it is lost")
    sacred_tradition_pct: int = rule(
        15,
        0,
        200,
        K,
        "Share of the gap to full participation a tradition closes each epoch when a sacred form, or a form made for its occasion, is part of it (%)",
    )
    suppression_resistance: int = rule(10, 0, 100, K, "Resistance a people gains when its own form is banned")
    translation_pct: int = rule(50, 0, 100, K, "Most mastery and prestige a verbal form loses in a tongue unlike its own (%)")


@dataclass(frozen=True)
class NameMeaningsRules:
    exonym_contacts: int = rule(3, 0, 50, K, "Neighbouring tongues that give each name a foreign form")
    epithet_renown: int = rule(40, 0, 100, K, "Renown a mortal needs before the world gives them an epithet")
    misread_pct: int = rule(10, 0, 100, K, "Chance each epoch a clause is misread between court tongues that share nothing (%)")
    misread_relation: int = rule(5, 0, 100, K, "Relation each party loses when a clause is misread")
    named_per_epoch: int = rule(200, 1, 100000, K, "Most names given a meaning each epoch")
