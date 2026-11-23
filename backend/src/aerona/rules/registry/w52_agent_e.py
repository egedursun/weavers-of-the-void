from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND
C = RuleGroup.CIVILIZATION
Y = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class GiftExchangeRules:
    courtesy_debt: int = rule(100, 0, 100, M, "Share of a gift courtesy its receiver owes back (%)")
    feast_debt: int = rule(100, 0, 100, M, "Share of a gift a rank-claiming feast its receiver owes back (%)")
    circuit_debt: int = rule(0, 0, 100, M, "Share of a gift a ceremonial circuit its receiver owes back (%)")
    offering_debt: int = rule(0, 0, 100, M, "Share of a gift an offering its receiver owes back (%)")
    marriage_debt: int = rule(0, 0, 100, M, "Share of a gift a marriage gift its receiver owes back (%)")
    return_debt: int = rule(0, 0, 100, M, "Share of a gift a return gift its receiver owes back (%)")
    alliance_debt: int = rule(100, 0, 100, M, "Share of a gift between allies its receiver owes back (%)")
    relief_debt: int = rule(50, 0, 100, M, "Share of a gift aid in a stricken hour its receiver owes back (%)")
    birth_debt: int = rule(50, 0, 100, M, "Share of a gift at a birth its receiver owes back (%)")
    funeral_debt: int = rule(100, 0, 100, M, "Share of a gift to the bereaved its receiver owes back (%)")
    amends_debt: int = rule(0, 0, 100, M, "Share of a gift amends for a wrong its receiver owes back (%)")
    patronage_debt: int = rule(0, 0, 100, M, "Share of a gift from a patron its receiver owes back (%)")
    hospitality_debt: int = rule(100, 0, 100, M, "Share of a gift between host and guest its receiver owes back (%)")
    amends_grievance_cut: int = rule(60, 0, 100, M, "Grievance an accepted gift of amends takes from a feud")
    patronage_loyalty: int = rule(10, 0, 100, M, "Regard a client gains for the patron whose gift it took")
    exceed_ratio_pct: int = rule(
        150, 100, 500, M, "Share of a gift's worth an answer must reach before it exceeds the gift and puts the first giver in debt (%)"
    )
    rivalry_drain_pct: int = rule(10, 0, 100, M, "Share of its coin each side of a rivalry of outgiving spends when the rivalry goes on (%)")
    release_loyalty: int = rule(15, 0, 100, M, "Regard a receiver gains for a giver who releases its debt")
    exceed_pct: int = rule(15, 0, 100, M, "Chance a receiver with the coin answers a gift by exceeding it (%)")
    release_pct: int = rule(20, 0, 100, M, "Chance a giver that regards its receiver well releases a debt the receiver cannot pay (%)")
    release_regard: int = rule(30, -100, 100, M, "Relation from which a giver may release a debt instead of letting it lapse")
    birth_gift_pct: int = rule(30, 0, 100, M, "Chance the kin of a newborn send a gift at its birth (%)")
    funeral_gift_pct: int = rule(30, 0, 100, M, "Chance a friend of the dead sends a gift to the bereaved (%)")
    amends_pct: int = rule(20, 0, 100, M, "Chance each epoch one side of a feud sends a gift of amends (%)")
    patronage_pct: int = rule(20, 0, 100, M, "Chance each epoch a patron sends a gift to an artist whose work it keeps (%)")
    hospitality_pct: int = rule(40, 0, 100, M, "Chance the host of a gathering gives a guest gift to a guest (%)")
    occasion_value: int = rule(10, 0, 100000, M, "Coin a gift at a birth, a funeral, a gathering or from a patron is worth")
    amends_value: int = rule(40, 0, 100000, M, "Coin a gift of amends is worth")
    gifts_per_occasion: int = rule(3, 0, 100, M, "Gifts one birth, death or gathering may draw")
    guest_right_infamy: int = rule(40, 0, 100, M, "Infamy one who kills a guest it exchanged guest gifts with gains, the gravest breach of guest right")


@dataclass(frozen=True)
class ArtMarketRoleRules:
    critic_price_swing_pct: int = rule(20, 0, 100, Y, "Share by which a critic of full renown raises or sinks the price of a work it reviews (%)")
    forger_detect_pct: int = rule(30, 0, 100, Y, "Chance each epoch a connoisseur or curator finds out a forger working in its land (%)")
    curator_prestige: int = rule(5, 0, 50, Y, "Prestige a curator's shown collection gives its town each epoch")
    critic_chance: int = rule(10, 0, 100, Y, "Chance each epoch a renowned mortal of a land with an art market takes up the trade of a critic (%)")
    critic_renown: int = rule(40, 0, 100, Y, "Renown a mortal needs before it may judge works as a critic")
    reviews_per_critic: int = rule(1, 0, 20, Y, "Works a critic reviews each epoch")
    movement_swing: int = rule(1, 0, 20, Y, "Patrons a movement gains or scandals it suffers when a critic praises or pans its work")


@dataclass(frozen=True)
class CulturalRightsRules:
    technique_license_fee: int = rule(10, 0, 500, C, "Wealth a licensee pays each epoch to the holder of a technique right")
    wed_pct: int = rule(30, 0, 100, C, "Chance a line that pays for a union passes one of its rights with it (%)")
    recipe_claim_pct: int = rule(20, 0, 100, C, "Chance each epoch the maker of a dish claims its recipe as a right (%)")
    technique_claim_pct: int = rule(10, 0, 100, C, "Chance each epoch a holder of a technique claims it as a right (%)")


@dataclass(frozen=True)
class ClubRules:
    team_game_fan_draw: int = rule(10, 0, 100, C, "Fans a club of team games draws each epoch from its town (%)")
    racing_fan_draw: int = rule(10, 0, 100, C, "Fans a racing club draws each epoch from its town (%)")
    combat_fan_draw: int = rule(8, 0, 100, C, "Fans a club of combat draws each epoch from its town (%)")
    athletics_fan_draw: int = rule(6, 0, 100, C, "Fans a club of athletics draws each epoch from its town (%)")
    animal_contest_fan_draw: int = rule(8, 0, 100, C, "Fans a club of animal contests draws each epoch from its town (%)")
    mind_games_fan_draw: int = rule(4, 0, 100, C, "Fans a club of games of the mind draws each epoch from its town (%)")
    fixing_detect_pct: int = rule(20, 0, 100, C, "Chance a fixed contest is found out (%)")
    fixing_riot_push: int = rule(30, 0, 100, C, "Unrest the finding out of a fixed contest adds to its town")
    fixing_standing_loss: int = rule(20, 0, 100, C, "Rating and fandom a club loses when a fixing of its contest is found out")
    animal_breed_pct: int = rule(20, 0, 100, C, "Chance each epoch a club of animal contests breeds a new animal for the sport (%)")
    mind_patron_pct: int = rule(20, 0, 100, C, "Chance each epoch a club of games of the mind draws a patron's gift (%)")
