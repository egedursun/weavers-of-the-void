from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

R = RuleGroup.RELIGION_AND_LANGUAGE
L = RuleGroup.POLITY


@dataclass(frozen=True)
class MysticVisionRules:
    vision_weight: int = rule(30, 0, 100, R, "Weight of a seen vision among the kinds of direct experience a mystic has")
    union_weight: int = rule(15, 0, 100, R, "Weight of a felt union with the divine among the kinds of direct experience a mystic has")
    voice_weight: int = rule(20, 0, 100, R, "Weight of a heard voice among the kinds of direct experience a mystic has")
    trance_weight: int = rule(15, 0, 100, R, "Weight of a trance among the kinds of direct experience a mystic has")
    dream_weight: int = rule(25, 0, 100, R, "Weight of a vision in sleep among the kinds of direct experience a mystic has")
    oracle_speech_weight: int = rule(10, 0, 100, R, "Weight of speech in words not one's own among the kinds of direct experience a mystic has")
    dream_awe_pct: int = rule(50, 0, 200, R, "More awe a vision in sleep stirs where the mystic's people keep readings of dreams (%)")
    oracle_followers_pct: int = rule(100, 0, 400, R, "More followers a public oracle draws than another vision (%)")
    oracle_court_legitimacy: int = rule(3, 0, 50, R, "Legitimacy a ruler of the town gains when a public oracle there proves answered by a god")


@dataclass(frozen=True)
class RebirthRules:
    kind_path_pct: int = rule(
        20, 0, 100, R, "Chance a soul under a doctrine of rebirth into other kinds is reborn as a creature of its land rather than a person (%)"
    )
    kind_reverence: int = rule(20, 0, 100, R, "Strength of the regard the faithful of a home hold toward a kind one of their dead was reborn as")


@dataclass(frozen=True)
class PetitionRules:
    healing_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for healing (50 = as its office allows)")
    harvest_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for a harvest (50 = as its office allows)")
    fertility_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for children (50 = as its office allows)")
    safe_passage_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for safe passage (50 = as its office allows)")
    prosperity_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for prosperity (50 = as its office allows)")
    suit_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit upholds a suit against another spirit (50 = as its office allows)")
    rain_grant_pct: int = rule(40, 0, 100, R, "How readily a spirit grants a petition for rain (50 = as its office allows)")
    protection_grant_pct: int = rule(50, 0, 100, R, "How readily a spirit grants a petition for protection (50 = as its office allows)")
    vengeance_grant_pct: int = rule(30, 0, 100, R, "How readily a spirit grants a petition for vengeance on a wrongdoer (50 = as its office allows)")
    drought_rainfall: int = rule(30, 0, 100, R, "Rainfall of a town's land below which its folk petition for rain")
    rain_shift: int = rule(8, 0, 100, R, "Rainfall a granted petition for rain brings the land of the town")
    protection_defence: int = rule(10, 0, 100, R, "Defence a granted petition for protection gives the town")
    protection_unrest_at: int = rule(40, 0, 100, R, "Unrest of a town from which its folk petition for protection")


@dataclass(frozen=True)
class LuckRules:
    day_weight: int = rule(60, 0, 100, R, "Weight of a day read as lucky or unlucky among the signs a people believes")
    number_weight: int = rule(50, 0, 100, R, "Weight of a number read as luck among the signs a people believes")
    sign_weight: int = rule(50, 0, 100, R, "Weight of a sign in the sky or weather read as luck among the signs a people believes")
    gesture_weight: int = rule(40, 0, 100, R, "Weight of a gesture read as luck among the signs a people believes")
    place_weight: int = rule(40, 0, 100, R, "Weight of a place read as luck among the signs a people believes")
    act_weight: int = rule(40, 0, 100, R, "Weight of an act read as luck among the signs a people believes")
    person_weight: int = rule(30, 0, 100, R, "Weight of a person read as luck among the signs a people believes")
    animal_weight: int = rule(50, 0, 100, R, "Weight of a kind of creature read as luck among the signs a people believes")
    colour_weight: int = rule(40, 0, 100, R, "Weight of a colour read as luck among the signs a people believes")
    read_chance: int = rule(30, 0, 100, R, "Chance each epoch that a believing people reads one of its signs at a moment that matters (%)")
    trade_pct: int = rule(10, 0, 100, R, "Prosperity a town gains or loses for a reading of luck in trade, by the boldness of its deals (%)")
    union_stress: int = rule(8, 0, 100, R, "Stress a reading of luck in unions lifts or lays on the newly wed of the town")
    building_pct: int = rule(25, 0, 100, R, "Share of a town's new works that wait for a better day after an ill reading of luck in building (%)")


@dataclass(frozen=True)
class CharmRules:
    protection_effect: int = rule(50, 0, 100, R, "Force of a charm of protection (50 = as the charm's strength gives)")
    fertility_effect: int = rule(50, 0, 100, R, "Force of a charm of fertility (50 = as the charm's strength gives)")
    luck_effect: int = rule(50, 0, 100, R, "Force of a charm of luck (50 = as the charm's strength gives)")
    healing_effect: int = rule(50, 0, 100, R, "Force of a charm of healing (50 = as the charm's strength gives)")
    love_effect: int = rule(50, 0, 100, R, "Force of a charm of love (50 = as the charm's strength gives)")
    travel_effect: int = rule(50, 0, 100, R, "Force of a charm of travel (50 = as the charm's strength gives)")
    travel_loss_cut_pct: int = rule(30, 0, 100, R, "Share of a journey's losses a real charm of travel at full strength turns aside (%)")
    comfort: int = rule(4, 0, 100, R, "Stress a charm without force lifts from its bearer each epoch by the comfort of belief")


@dataclass(frozen=True)
class HuntRules:
    confession_spread_pct: int = rule(30, 0, 100, L, "Fervour a confession adds to its town's hunt, and the chance it names another accused (%)")
    true_confession_pct: int = rule(40, 0, 100, L, "Chance an accused who truly did the harm confesses before judgement (%)")
    flight_pct: int = rule(15, 0, 100, L, "Chance an accused flees before judgement where it is free to go (%)")
    flight_fervour: int = rule(10, 0, 100, L, "Fervour an accused's flight adds to its town's hunt, read as guilt")
