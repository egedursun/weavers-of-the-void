from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

C = RuleGroup.CIVILIZATION
M = RuleGroup.MIND
S = RuleGroup.SETTLEMENTS
W = RuleGroup.WAR_AND_DIPLOMACY
R = RuleGroup.REPUTATION
K = RuleGroup.COSMOS_AND_TRAVEL
G = RuleGroup.COSMIC_HORROR


@dataclass(frozen=True)
class RevivalWayRules:
    restore_weight: int = rule(50, 0, 100, C, "How readily a pressed people answers by bringing back its old ways")
    synthesis_weight: int = rule(40, 0, 100, C, "How readily a pressed people gathers round a prophet who joins old and new")
    adopt_weight: int = rule(30, 0, 100, C, "How readily a pressed people takes its rulers' ways wholesale")
    await_weight: int = rule(25, 0, 100, C, "How readily a pressed people waits for a foretold change")
    withdraw_weight: int = rule(25, 0, 100, C, "How readily a pressed people lives apart from its rulers in a community of its own")
    clash_opinion: int = rule(4, 0, 100, C, "Opinion of its rulers a people loses each epoch it restores its old ways against them")
    synthesis_found_pct: int = rule(25, 0, 100, C, "Chance each epoch a revival round a prophet founds a faith of its own once it revives (%)")
    sign_heat: int = rule(60, 0, 100, C, "Fervour and hope each town of a waiting people gains when a sign in the sky comes")
    withdraw_calm: int = rule(3, 0, 100, C, "Opinion of its rulers a withdrawn people regains each epoch they leave it be")
    land_grievance: int = rule(6, 0, 100, C, "Grievance against its realm each town of a people seeking its lost land gains each epoch it revives")
    rule_pressure: int = rule(30, 0, 100, C, "Pressure for independence a revival seeking rule by the people itself adds at full strength")
    language_met_at: int = rule(70, 0, 100, C, "Standing of its tongue from which a revival of the language has met its goal")


@dataclass(frozen=True)
class CrowdRules:
    riot_threshold: int = rule(60, 0, 100, S, "Share of a district already rioting that an average dweller needs before joining (%)")
    panic_threshold: int = rule(60, 0, 100, S, "Share of a district already fleeing that an average dweller needs before joining a panic (%)")
    lynching_threshold: int = rule(60, 0, 100, S, "Share of a district already acting that an average dweller needs before joining a lynching (%)")
    conversion_threshold: int = rule(60, 0, 100, S, "Share of a district already turning that an average dweller needs before joining a mass conversion (%)")
    revolt_threshold: int = rule(60, 0, 100, S, "Share of a district already risen that an average dweller needs before joining a revolt (%)")
    strike_threshold: int = rule(60, 0, 100, S, "Share of a district already striking that an average dweller needs before laying down work (%)")
    procession_threshold: int = rule(60, 0, 100, S, "Share of a district already marching that an average dweller needs before joining a procession (%)")
    revival_threshold: int = rule(60, 0, 100, S, "Share of a district already stirred that an average dweller needs before joining a revival (%)")
    jubilation_threshold: int = rule(50, 0, 100, S, "Share of a district already rejoicing that an average dweller needs before joining (%)")
    demonstration_threshold: int = rule(
        55, 0, 100, S, "Hope from which a crowd presses its demand peacefully instead of rioting, and the share of a district it needs to join (%)"
    )
    boycott_threshold: int = rule(
        60, 0, 100, S, "Deterrence from which an angry crowd refuses to trade instead of rioting, and the share of a district it needs to join (%)"
    )
    exodus_threshold: int = rule(75, 0, 100, S, "Grief or fear from which a crowd leaves together instead of fleeing or marching, and the share it needs (%)")
    boycott_income_cut_pct: int = rule(30, 0, 100, S, "Share of its income a guild or ruler a town boycotts loses (%)")
    jubilation_riot_pct: int = rule(5, 0, 100, S, "Chance a rejoicing crowd turns to riot as the drink flows (%)")
    jubilation_loyalty: int = rule(5, 0, 100, S, "Legitimacy a realm gains when one of its towns rejoices")
    jubilation_spending: int = rule(5, 0, 100, S, "Prosperity a town gains from what is spent while it rejoices")
    exodus_share_pct: int = rule(10, 0, 100, S, "Share of a district that leaves when its crowd leaves together (%)")
    grief_cut: int = rule(35, 0, 100, S, "Threshold points a town's full grief takes away from mourning acts")
    hope_cut: int = rule(35, 0, 100, S, "Threshold points a town's full hope takes away from peaceful and joyful acts")
    anger_decay: int = rule(10, 0, 50, S, "Anger a town's crowd loses each epoch")
    fear_decay: int = rule(10, 0, 50, S, "Fear a town's crowd loses each epoch")
    fervour_decay: int = rule(10, 0, 50, S, "Fervour a town's crowd loses each epoch")
    grief_decay: int = rule(8, 0, 50, S, "Grief a town's crowd loses each epoch")
    hope_decay: int = rule(10, 0, 50, S, "Hope a town's crowd loses each epoch")
    betrayed_hope_pct: int = rule(50, 0, 100, S, "Share of a crowd's hope that turns to anger when a peaceful demand is put down (%)")
    price_spike_push: int = rule(20, 0, 100, S, "Feeling the price of food adds to a town's crowd at full force")
    execution_push: int = rule(20, 0, 100, S, "Feeling an execution adds to a town's crowd at full force")
    sermon_push: int = rule(20, 0, 100, S, "Feeling a preacher's call adds to a town's crowd at full force")
    omen_push: int = rule(20, 0, 100, S, "Feeling an omen adds to a town's crowd at full force")
    rumour_push: int = rule(20, 0, 100, S, "Feeling a rumour adds to a town's crowd at full force")
    fire_push: int = rule(20, 0, 100, S, "Feeling a fire adds to a town's crowd at full force")
    plague_push: int = rule(20, 0, 100, S, "Feeling a plague adds to a town's crowd at full force")
    beast_push: int = rule(20, 0, 100, S, "Feeling a beast at hand adds to a town's crowd at full force")
    eclipse_push: int = rule(20, 0, 100, S, "Feeling an eclipse adds to a town's crowd at full force")
    miracle_push: int = rule(20, 0, 100, S, "Feeling a miracle adds to a town's crowd at full force")
    famine_push: int = rule(20, 0, 100, S, "Feeling hunger adds to a town's crowd at full force")
    unpaid_wages_push: int = rule(20, 0, 100, S, "Feeling unpaid wages add to a town's crowd at full force")
    lost_match_push: int = rule(20, 0, 100, S, "Feeling a lost match adds to a town's crowd at full force")
    victory_push: int = rule(25, 0, 100, S, "Fervour and hope a victory of its realm adds to a town's crowd at full force")
    great_funeral_push: int = rule(25, 0, 100, S, "Grief the funeral of a great figure adds to a town's crowd at full force")
    election_push: int = rule(20, 0, 100, S, "Anger and fervour an election adds to a town's crowd at full force")
    great_funeral_importance: int = rule(70, 0, 100, S, "Importance from which the death of a figure brings its town a great funeral")


@dataclass(frozen=True)
class IdentityLayerRules:
    people_base_weight: int = rule(30, 0, 100, M, "Weight the people layer of identity rests at when nothing stirs it")
    faith_base_weight: int = rule(30, 0, 100, M, "Weight the faith layer of identity rests at when nothing stirs it")
    class_base_weight: int = rule(30, 0, 100, M, "Weight the class layer of identity rests at when nothing stirs it")
    locality_base_weight: int = rule(30, 0, 100, M, "Weight the locality layer of identity rests at when nothing stirs it")
    house_base_weight: int = rule(30, 0, 100, M, "Weight the house layer of identity rests at when nothing stirs it")
    profession_base_weight: int = rule(30, 0, 100, M, "Weight the profession layer of identity rests at when nothing stirs it")
    generation_base_weight: int = rule(30, 0, 100, M, "Weight the generation layer of identity rests at when nothing stirs it")
    polity_base_weight: int = rule(30, 0, 100, M, "Weight the polity layer of identity rests at when nothing stirs it")
    circle_base_weight: int = rule(30, 0, 100, M, "Weight the circle layer of identity rests at when nothing stirs it")
    language_base_weight: int = rule(30, 0, 100, M, "Weight the language layer of identity rests at when nothing stirs it")
    kind_base_weight: int = rule(30, 0, 100, M, "Weight the kind layer of identity rests at when nothing stirs it")
    cause_base_weight: int = rule(30, 0, 100, M, "Weight the cause layer of identity rests at when nothing stirs it")
    language_suppression_rise: int = rule(15, 0, 100, M, "Language weight a community gains while its realm suppresses or revives the tongue it speaks")
    kind_law_rise: int = rule(15, 0, 100, M, "Kind weight a community gains while its realm's laws treat kinds of being differently")
    kind_contact_rise: int = rule(10, 0, 100, M, "Kind weight a community gains while beings of another kind live among it")
    cause_rise: int = rule(15, 0, 100, M, "Cause weight a community gains while a movement holds its support past the line of protest")
    persecution_rise: int = rule(30, 0, 100, M, "Weight a community gains in the layer its realm persecutes it for")
    commemoration_rise: int = rule(15, 0, 100, M, "Weight a community gains in the layer whose past it remembers at a commemoration")
    election_rise: int = rule(15, 0, 100, M, "Weight a community gains in the layers a vote of its realm divides by")
    contest_rise: int = rule(10, 0, 100, M, "Locality and circle weight a community gains when it meets another in a match")


@dataclass(frozen=True)
class CouncilOfWorldsRules:
    route_security_effect: int = rule(100, 0, 100, W, "Strength with which a council's guard on the routes between its worlds is kept (%)")
    embargo_effect: int = rule(100, 0, 100, W, "Strength with which a council's embargo on a realm is kept (%)")
    void_ban_effect: int = rule(100, 0, 100, W, "Strength with which a council's ban on rites of the void is kept (%)")
    sanction_effect: int = rule(100, 0, 100, W, "Strength with which a council's sanction on the world of a god is kept (%)")
    quarantine_effect: int = rule(60, 0, 100, W, "Share of the outbreaks a council's quarantine keeps from crossing to its other worlds (%)")
    arbitration_effect: int = rule(30, 0, 100, W, "Relation two members at odds regain when a council settles their dispute by vote")
    aid_effect: int = rule(15, 0, 100, W, "Prosperity each town of a stricken member world regains from a council's pooled relief")


@dataclass(frozen=True)
class DispatchRules:
    order_obedience_pct: int = rule(80, 0, 100, W, "Chance a commander who receives an order in their ruler's name obeys it (%)")
    warning_prepare_pct: int = rule(30, 0, 100, W, "Defence a town gains from a warning of danger that reaches it in time (%)")
    misread_pct: int = rule(10, 0, 100, W, "Share of the misreadings of a delivered message that the recipient acts on as if meant (%)")


@dataclass(frozen=True)
class EnvoyRules:
    defect_pct: int = rule(3, 0, 100, W, "Chance a received envoy stays to serve the host and carries the sender's secrets (%)")


@dataclass(frozen=True)
class SignalRules:
    disused_decay: int = rule(5, 0, 50, W, "Condition a signal station left unused loses each epoch")


@dataclass(frozen=True)
class OpinionSubjectRules:
    ruler_weight: int = rule(100, 0, 100, M, "How strongly a town's view of its ruler drifts toward what it lives through (%)")
    law_weight: int = rule(100, 0, 100, M, "How strongly a town's view of a law drifts toward its values (%)")
    war_weight: int = rule(100, 0, 100, M, "How strongly a town's view of a war drifts toward its weariness and martial values (%)")
    god_weight: int = rule(100, 0, 100, M, "How strongly a town's view of its god drifts toward its piety (%)")
    ideology_weight: int = rule(100, 0, 100, M, "How strongly a town's view of a creed drifts toward its devotion (%)")
    faction_weight: int = rule(60, 0, 100, M, "How strongly a town's view of a faction among it sets the faction's recruits and the backlash against it (%)")
    foreign_power_weight: int = rule(50, 0, 100, M, "How strongly a town's view of a foreign power moves its trade, alliance support and will for war (%)")


@dataclass(frozen=True)
class SecretKindRules:
    affair_severity: int = rule(45, 0, 100, R, "Weight of a kept affair when it comes to light")
    illegitimate_child_severity: int = rule(40, 0, 100, R, "Weight of a child born outside a marriage when it comes to light")
    murder_severity: int = rule(85, 0, 100, R, "Weight of a hidden murder when it comes to light")
    heresy_severity: int = rule(50, 0, 100, R, "Weight of a hidden heresy when it comes to light")
    secret_cult_membership_severity: int = rule(45, 0, 100, R, "Weight of membership of a hidden cult when it comes to light")
    debt_severity: int = rule(25, 0, 100, R, "Weight of a hidden debt when it comes to light")
    crime_severity: int = rule(55, 0, 100, R, "Weight of a hidden crime when it comes to light")
    cowardice_in_battle_severity: int = rule(50, 0, 100, R, "Weight of cowardice in battle when it comes to light")
    hidden_condition_severity: int = rule(35, 0, 100, R, "Weight of a hidden illness or madness when it comes to light")
    false_identity_severity: int = rule(60, 0, 100, R, "Weight of a false identity when it comes to light")
    deal_with_outer_being_severity: int = rule(75, 0, 100, R, "Weight of a deal with an outer being when it comes to light")
    true_parentage_severity: int = rule(55, 0, 100, R, "Weight of a true parentage when it comes to light")
    broken_oath_severity: int = rule(50, 0, 100, R, "Weight of a broken oath when it comes to light")
    ecosabotage_severity: int = rule(70, 0, 100, R, "Weight of a sabotage of the land when it comes to light")
    broken_cipher_severity: int = rule(65, 0, 100, R, "Weight of a broken cipher when it comes to light")
    true_history_severity: int = rule(55, 0, 100, R, "Weight of the true history behind an official account when it comes to light")
    hidden_power_severity: int = rule(60, 0, 100, R, "Weight of a concealed innate power when it comes to light")
    forgery_severity: int = rule(60, 0, 100, R, "Weight of a forgery its holder made or used when it comes to light")


@dataclass(frozen=True)
class HookDemandRules:
    marriage_cost: int = rule(100, 0, 100, R, "Chance pressing a marriage wears a strong hook down to a weak one (%)")
    step_down_cost: int = rule(100, 0, 100, R, "Chance pressing someone to step down wears a strong hook down to a weak one (%)")
    support_cost: int = rule(40, 0, 100, R, "Chance pressing for support wears a strong hook down to a weak one (%)")
    vote_cost: int = rule(30, 0, 100, R, "Chance pressing a vote wears a strong hook down to a weak one (%)")
    law_cost: int = rule(50, 0, 100, R, "Chance pressing a ruler to back laws wears a strong hook down to a weak one (%)")
    appointment_cost: int = rule(60, 0, 100, R, "Chance pressing an appointment wears a strong hook down to a weak one (%)")
    silence_cost: int = rule(30, 0, 100, R, "Chance pressing a witness to silence wears a strong hook down to a weak one (%)")
    payment_cost: int = rule(50, 0, 100, R, "Chance extorting a payment wears a strong hook down to a weak one (%)")


@dataclass(frozen=True)
class FavourOriginRules:
    gift_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for a gift keeps (%)")
    rescue_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for a rescue keeps (%)")
    war_support_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for support in a war keeps (%)")
    succession_support_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for support in a succession keeps (%)")
    scheme_aid_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for aid in a scheme keeps (%)")
    vote_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for a vote that carried a law keeps (%)")
    relief_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for aid in a stricken hour keeps (%)")
    hospitality_weight: int = rule(80, 0, 100, R, "Share of its size a favour owed for shelter given keeps (%)")
    ransom_weight: int = rule(100, 0, 100, R, "Share of its size a favour owed for a ransom paid keeps (%)")
    hospitality_favour: int = rule(25, 0, 100, R, "Size of the favour a sheltered fugitive owes its host")
    ransom_favour: int = rule(40, 0, 100, R, "Size of the favour a freed captive owes those who paid the ransom")


@dataclass(frozen=True)
class GravityBandRules:
    micro_gravity_g_hundredths: int = rule(10, 1, 100, K, "Gravity below which a world's pull is so slight that things drift, in hundredths of the reference")
    crushing_gravity_g_hundredths: int = rule(300, 100, 10000, K, "Gravity above which a world's pull crushes, in hundredths of the reference")
    micro_body_strain: int = rule(30, 0, 100, K, "How hard a micro gravity world wears the bodies of those not made for it each epoch")
    low_body_strain: int = rule(5, 0, 100, K, "How hard a low gravity world wears the bodies of those not made for it each epoch")
    normal_body_strain: int = rule(0, 0, 100, K, "How hard a normal gravity world wears the bodies of those not made for it each epoch")
    high_body_strain: int = rule(15, 0, 100, K, "How hard a high gravity world wears the bodies of those not made for it each epoch")
    crushing_body_strain: int = rule(60, 0, 100, K, "How hard a crushing gravity world wears the bodies of those not made for it each epoch")
    micro_martiality: int = rule(-8, -100, 100, K, "Martiality effect in micro gravity")
    crushing_martiality: int = rule(10, -100, 100, K, "Martiality effect in crushing gravity")
    micro_speed_pct: int = rule(20, 0, 300, K, "Speed armies gain on a micro gravity world (%)")
    crushing_speed_pct: int = rule(40, 0, 100, K, "Speed armies lose on a crushing gravity world (%)")
    crushing_build_pct: int = rule(80, 0, 500, K, "Extra cost of building on a crushing gravity world (%)")
    micro_flight_pct: int = rule(40, 0, 300, K, "Room flying creatures gain on a micro gravity world (%)")
    crushing_flight_pct: int = rule(60, 0, 100, K, "Room flying creatures lose on a crushing gravity world (%)")
    crushing_height_cap: int = rule(3, 1, 20, K, "Highest level a work can be raised to on a crushing gravity world")
    strain_endurance: int = rule(1, 0, 20, K, "Endurance a body loses each epoch per ten points of strain it bears")
    under_ice_cryosphere: int = rule(60, 0, 100, K, "Ice cover from which a world's seas lie sealed under ice")
    under_ice_heat: int = rule(30, 0, 100, K, "Tectonics or volcanism from which an ice-sealed sea is warmed enough from beneath to hold life")
    cloud_low_kelvin: int = rule(220, 0, 1000, K, "Coldest surface warmth, in kelvin, at which a giant's cloud layers can hold life")
    cloud_high_kelvin: int = rule(350, 0, 2000, K, "Warmest surface warmth, in kelvin, at which a giant's cloud layers can hold life")


@dataclass(frozen=True)
class OuterBargainRules(Spanned):
    essence_size: int = rule(100, 0, 100, G, "Size of an outer bargain that gives essence, against the full measure (%)")
    power_size: int = rule(100, 0, 100, G, "Chance an outer bargain that gives a power finds a free place for it (%)")
    might_size: int = rule(100, 0, 100, G, "Size of an outer bargain that gives might, against the full measure (%)")
    knowledge_size: int = rule(60, 0, 100, G, "Progress an outer bargain that gives knowledge grants in a branch the bargainer's faithful lack")
    longevity_size: int = rule(30, 0, 100, G, "Existence an outer bargain that gives a longer span restores to a god")
    world_sanity_weight: int = rule(30, 0, 100, G, "How often an outer being asks a world's sanity as its price")
    domain_weight: int = rule(20, 0, 100, G, "How often an outer being asks a domain as its price")
    true_name_weight: int = rule(15, 0, 100, G, "How often an outer being asks a true name as its price")
    worshippers_weight: int = rule(20, 0, 100, G, "How often an outer being asks the souls of a god's faithful as its price")
    descendants_weight: int = rule(15, 0, 100, G, "How often an outer being asks a god's line as its price")
    worshippers_taken_pct: int = rule(
        20, 0, 100, G, "Share of the followers of a god's faithful cults whose souls are handed over when that price falls due (%)"
    )
    descendants_years: int = span(150, 1, 5000, G, "Years a line given as a price stays bound before the debt is paid")
