from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MIND
S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class RelationRules:
    betrothal_break_grievance: int = rule(30, 0, 100, G, "Friendship the houses of a broken betrothal lose toward each other, and rivalry they gain")
    sworn_kin_duty: int = rule(70, 0, 100, G, "Chance a sworn kin answers a duty of vengeance, aid or hospitality as blood kin would (%)")
    foster_loyalty: int = rule(50, 0, 100, G, "Strength of the loyalty a fostered one holds toward the household that raised them")
    betrothal_break_at: int = rule(-20, -100, 0, G, "Friendship at or below which a betrothed pair breaks the promise")


@dataclass(frozen=True)
class InteractionRules:
    converse_weight: int = rule(50, 0, 100, G, "How readily beings choose to converse; 50 keeps the weight their nature gives")
    converse_effect: int = rule(50, 0, 100, G, "How far one converse moves friendship, romance and rivalry; 50 keeps the usual step")
    befriend_weight: int = rule(50, 0, 100, G, "How readily beings choose to befriend; 50 keeps the weight their nature gives")
    befriend_effect: int = rule(50, 0, 100, G, "How far one befriend moves friendship, romance and rivalry; 50 keeps the usual step")
    gossip_weight: int = rule(50, 0, 100, G, "How readily beings choose to gossip; 50 keeps the weight their nature gives")
    gossip_effect: int = rule(50, 0, 100, G, "How far one gossip moves friendship, romance and rivalry; 50 keeps the usual step")
    joke_weight: int = rule(50, 0, 100, G, "How readily beings choose to joke; 50 keeps the weight their nature gives")
    joke_effect: int = rule(50, 0, 100, G, "How far one joke moves friendship, romance and rivalry; 50 keeps the usual step")
    comfort_weight: int = rule(50, 0, 100, G, "How readily beings choose to comfort; 50 keeps the weight their nature gives")
    comfort_effect: int = rule(50, 0, 100, G, "How far one comfort moves friendship, romance and rivalry; 50 keeps the usual step")
    flatter_weight: int = rule(50, 0, 100, G, "How readily beings choose to flatter; 50 keeps the weight their nature gives")
    flatter_effect: int = rule(50, 0, 100, G, "How far one flatter moves friendship, romance and rivalry; 50 keeps the usual step")
    boast_weight: int = rule(50, 0, 100, G, "How readily beings choose to boast; 50 keeps the weight their nature gives")
    boast_effect: int = rule(50, 0, 100, G, "How far one boast moves friendship, romance and rivalry; 50 keeps the usual step")
    insult_weight: int = rule(50, 0, 100, G, "How readily beings choose to insult; 50 keeps the weight their nature gives")
    insult_effect: int = rule(50, 0, 100, G, "How far one insult moves friendship, romance and rivalry; 50 keeps the usual step")
    argue_weight: int = rule(50, 0, 100, G, "How readily beings choose to argue; 50 keeps the weight their nature gives")
    argue_effect: int = rule(50, 0, 100, G, "How far one argue moves friendship, romance and rivalry; 50 keeps the usual step")
    flirt_weight: int = rule(50, 0, 100, G, "How readily beings choose to flirt; 50 keeps the weight their nature gives")
    flirt_effect: int = rule(50, 0, 100, G, "How far one flirt moves friendship, romance and rivalry; 50 keeps the usual step")
    court_weight: int = rule(50, 0, 100, G, "How readily beings choose to court; 50 keeps the weight their nature gives")
    court_effect: int = rule(50, 0, 100, G, "How far one court moves friendship, romance and rivalry; 50 keeps the usual step")
    propose_weight: int = rule(50, 0, 100, G, "How readily beings choose to propose; 50 keeps the weight their nature gives")
    propose_effect: int = rule(50, 0, 100, G, "How far one propose moves friendship, romance and rivalry; 50 keeps the usual step")
    seduce_weight: int = rule(50, 0, 100, G, "How readily beings choose to seduce; 50 keeps the weight their nature gives")
    seduce_effect: int = rule(50, 0, 100, G, "How far one seduce moves friendship, romance and rivalry; 50 keeps the usual step")
    quarrel_weight: int = rule(50, 0, 100, G, "How readily beings choose to quarrel; 50 keeps the weight their nature gives")
    quarrel_effect: int = rule(50, 0, 100, G, "How far one quarrel moves friendship, romance and rivalry; 50 keeps the usual step")
    reconcile_weight: int = rule(50, 0, 100, G, "How readily beings choose to reconcile; 50 keeps the weight their nature gives")
    reconcile_effect: int = rule(50, 0, 100, G, "How far one reconcile moves friendship, romance and rivalry; 50 keeps the usual step")
    teach_weight: int = rule(50, 0, 100, G, "How readily beings choose to teach; 50 keeps the weight their nature gives")
    teach_effect: int = rule(50, 0, 100, G, "How far one teach moves friendship, romance and rivalry; 50 keeps the usual step")
    gift_weight: int = rule(50, 0, 100, G, "How readily beings choose to gift; 50 keeps the weight their nature gives")
    gift_effect: int = rule(50, 0, 100, G, "How far one gift moves friendship, romance and rivalry; 50 keeps the usual step")
    ask_favour_weight: int = rule(50, 0, 100, G, "How readily beings choose to ask favour; 50 keeps the weight their nature gives")
    ask_favour_effect: int = rule(50, 0, 100, G, "How far one ask favour moves friendship, romance and rivalry; 50 keeps the usual step")
    confide_secret_weight: int = rule(50, 0, 100, G, "How readily beings choose to confide secret; 50 keeps the weight their nature gives")
    confide_secret_effect: int = rule(50, 0, 100, G, "How far one confide secret moves friendship, romance and rivalry; 50 keeps the usual step")
    threaten_weight: int = rule(50, 0, 100, G, "How readily beings choose to threaten; 50 keeps the weight their nature gives")
    threaten_effect: int = rule(50, 0, 100, G, "How far one threaten moves friendship, romance and rivalry; 50 keeps the usual step")
    brawl_weight: int = rule(50, 0, 100, G, "How readily beings choose to brawl; 50 keeps the weight their nature gives")
    brawl_effect: int = rule(50, 0, 100, G, "How far one brawl moves friendship, romance and rivalry; 50 keeps the usual step")
    apologise_weight: int = rule(50, 0, 100, G, "How readily beings choose to apologise; 50 keeps the weight their nature gives")
    apologise_effect: int = rule(50, 0, 100, G, "How far one apologise moves friendship, romance and rivalry; 50 keeps the usual step")
    share_meal_weight: int = rule(50, 0, 100, G, "How readily beings choose to share meal; 50 keeps the weight their nature gives")
    share_meal_effect: int = rule(50, 0, 100, G, "How far one share meal moves friendship, romance and rivalry; 50 keeps the usual step")
    ask_counsel_weight: int = rule(50, 0, 100, G, "How readily beings choose to ask counsel; 50 keeps the weight their nature gives")
    ask_counsel_effect: int = rule(50, 0, 100, G, "How far one ask counsel moves friendship, romance and rivalry; 50 keeps the usual step")
    apology_grievance: int = rule(12, 0, 100, G, "Friendship an accepted apology restores, before standing and temper")
    meal_opinion: int = rule(6, 0, 50, G, "Friendship a shared meal adds where the guest's people keep guest right")
    counsel_standing: int = rule(3, 0, 50, G, "Renown a counsellor gains when asked for counsel")


@dataclass(frozen=True)
class IntoxicantRules:
    synthetic_dependence_pct: int = rule(30, 0, 100, S, "Chance each epoch a people that takes a made substance daily gains a dependence on it (%)")
    animal_yield: int = rule(10, 0, 100, S, "Share of a kept or hunted species' yield that goes to a substance drawn from beasts (%)")
    medicine_ease_pct: int = rule(20, 0, 100, S, "Share of pain and lasting harm a substance taken as medicine eases (%)")
    hospitality_bond: int = rule(10, 0, 50, S, "Friendship a guest gains toward a host who offers the people's drink or smoke")
