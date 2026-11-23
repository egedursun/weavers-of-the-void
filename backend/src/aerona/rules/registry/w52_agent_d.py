from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CIVILIZATION
M = RuleGroup.MIND
S = RuleGroup.SETTLEMENTS


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
