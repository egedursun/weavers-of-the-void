from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

D = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class CommunicationRules(Spanned):
    envoy_hops: int = rule(2, 1, 1000, D, "Regions an envoy crosses in a season")
    letter_hops: int = rule(3, 1, 1000, D, "Regions a letter crosses in a season")
    herald_hops: int = rule(2, 1, 1000, D, "Regions a herald crosses in a season")
    bird_hops: int = rule(6, 1, 1000, D, "Regions a messenger bird crosses in a season")
    signal_fire_hops: int = rule(20, 1, 10000, D, "Regions a chain of signal fires carries word in a season")
    winter_delay_pct: int = rule(100, 0, 400, D, "How much longer messages over land take in each cold season of the year, when passes close (%)")
    interworld_epochs: int = rule(12, 0, 100000, D, "Seasons a message takes between worlds by any medium but magic and dreams")
    signal_cut: int = rule(1, 0, 10, D, "Epochs a sender's signal links take off the journey of its messages")
    spy_intercept_pct: int = rule(25, 0, 100, D, "Chance a spy network at full depth intercepts a message to or from its target (%)")
    outlaw_loss_pct: int = rule(8, 0, 100, D, "Chance outlaws at either end waylay a messenger over land (%)")
    forge_replace_pct: int = rule(15, 0, 100, D, "Chance an interceptor forges a replacement for a message it read (%)")
    misread_pct: int = rule(20, 0, 100, D, "Chance a message between tongues is misread, for each clause it carries (%)")
    interpreter_pct: int = rule(100, 0, 200, D, "How much the recipient's skill in languages lowers the chance of a misreading (%)")
    report_confidence: int = rule(70, 0, 100, D, "Confidence a received report gives")
    misread_confidence: int = rule(30, 0, 100, D, "Confidence a misread report gives")
    gift_friendship: int = rule(10, 0, 100, D, "Friendship a well-chosen gift brings, scaled by the recipient's taste for it")
    gift_favour: int = rule(15, 0, 100, D, "Magnitude of the favour a gift between rulers earns")
    insult_harm: int = rule(15, 0, 100, D, "Friendship an insult costs, doubled in a culture of honour")
    threat_harm: int = rule(10, 0, 100, D, "Friendship a threat costs")
    plea_mercy: int = rule(5, 0, 100, D, "Friendship a heartfelt plea earns")
    precedence_pct: int = rule(
        30, 0, 100, D, "How much a hierarchical culture cools to a message whose forms of address and precedence fall short of its envoy's etiquette (%)"
    )
    etiquette_pct: int = rule(50, 0, 200, D, "How much an envoy's negotiation and etiquette raise the welcome a message gets (%)")
    envoy_hostility: int = rule(-50, -100, 0, D, "Friendship below which a hostile court may mistreat an envoy")
    envoy_harm_pct: int = rule(30, 0, 100, D, "Chance a hostile court mistreats an envoy (%)")
    ruler_gift_pct: int = rule(10, 0, 100, D, "Chance each epoch a ruler sends a gift to a realm it is warm to (%)")
    ruler_insult_pct: int = rule(8, 0, 100, D, "Chance each epoch a ruler sends an insult to a realm it is cold to (%)")
    warm_at: int = rule(40, 0, 100, D, "Friendship from which a ruler sends gifts")
    cold_at: int = rule(-40, -100, 0, D, "Friendship below which a ruler sends insults")
    cipher_base: int = rule(30, 0, 100, D, "Strength of a realm's first cipher once it knows cryptography")
    cipher_skill_pct: int = rule(50, 0, 200, D, "How much the best cryptographer of a realm strengthens its cipher (%)")
    codebreak_pct: int = rule(10, 0, 100, D, "Chance each epoch a codebreaker breaks a cipher of equal skill and strength, for each intercepted message (%)")
    break_noticed_pct: int = rule(10, 0, 100, D, "Chance each epoch the owner of a broken cipher learns it is broken (%)")
    signal_build_pct: int = rule(
        15, 0, 100, D, "Chance each epoch a realm that knows the needed technique builds a signal link between its seat and a border land (%)"
    )
    opinion_drift_pct: int = rule(25, 0, 100, D, "Share of the gap to what a community should think that opinion closes each epoch (%)")
    herald_approval: int = rule(10, 0, 100, D, "Approval of the ruler a herald's proclamations add")
    propaganda_approval: int = rule(5, 0, 100, D, "Approval each artwork glorifying a subject adds")
    sermon_approval: int = rule(10, 0, 100, D, "Approval of a god its zealous temples add")
    rumour_weight: int = rule(3, 0, 50, D, "Approval each rumour a community hears about a subject moves, by the rumour's tone")
    broadsheet_pct: int = rule(50, 0, 200, D, "How much printing amplifies rumour in public opinion (%)")
    censorship_pct: int = rule(60, 0, 100, D, "How much a law of censorship at full strictness mutes contrary rumour (%)")
    censorship_found_pct: int = rule(10, 0, 100, D, "Chance each epoch censorship is noticed, souring approval of the ruler (%)")
    censorship_distrust: int = rule(15, 0, 100, D, "Approval of the ruler lost when censorship is noticed")
    legitimacy_pct: int = rule(20, 0, 100, D, "Share of the realm's mean approval of its ruler added to legitimacy (%)")
    disapproval_unrest_pct: int = rule(10, 0, 100, D, "Unrest a town gains each epoch for every hundred points it disapproves of its ruler (%)")
    army_intercept_pct: int = rule(30, 0, 100, D, "Chance an enemy army sitting at either end seizes a message passing over land (%)")
    stability_pct: int = rule(20, 0, 100, D, "Share of the realm's mean disapproval of its ruler taken from stability (%)")
    war_support_pct: int = rule(30, 0, 100, D, "Share of approval of a war that eases or deepens war weariness (%)")
    enforcement_pct: int = rule(20, 0, 100, D, "Share of approval of a law added to its enforcement (%)")
    censor_wish_at: int = rule(-30, -100, 0, D, "Approval of the ruler below which a hierarchical realm wishes for censorship")
    drum_and_whistle_hops: int = rule(5, 1, 1000, D, "Regions drummed or whistled speech carries in a season")
    courier_animal_hops: int = rule(4, 1, 1000, D, "Regions a courier animal carries a message in a season")
