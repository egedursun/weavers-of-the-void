from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND
C = RuleGroup.CIVILIZATION
Y = RuleGroup.MARKETS_AND_MONEY
W = RuleGroup.WAR_AND_DIPLOMACY


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
    occasion_value: int = rule(40, 0, 100000, M, "Most coin a gift at a birth, a funeral, a gathering or from a patron is worth")
    means_share_pct: int = rule(2, 0, 100, M, "Share of what a giver holds that a gift at an occasion or between allies is worth, up to its most (%)")
    amends_value: int = rule(40, 0, 100000, M, "Coin a gift of amends is worth")
    gifts_per_occasion: int = rule(3, 0, 100, M, "Gifts one birth, death or gathering may draw")
    guest_right_infamy: int = rule(40, 0, 100, M, "Infamy one who kills a guest it exchanged guest gifts with gains, the gravest breach of guest right")
    farewell_debt: int = rule(60, 0, 100, M, "Share of a gift at a parting its receiver owes back (%)")
    homecoming_debt: int = rule(60, 0, 100, M, "Share of a gift at a homecoming its receiver owes back (%)")
    initiation_debt: int = rule(30, 0, 100, M, "Share of a gift at an initiation its receiver owes back (%)")
    hoard_shame: int = rule(10, 0, 100, M, "Standing a holder loses each epoch it keeps a gift its circuit expects passed on")
    hoard_chance_pct: int = rule(5, 0, 100, M, "Chance each epoch the holder of a circuit's gift keeps it instead of passing it on (%)")


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
    water_sport_fan_draw: int = rule(30, 0, 100, C, "Share of a town near water drawn to follow a club of water sports (%)")
    hunt_fan_draw: int = rule(20, 0, 100, C, "Share of a town drawn to follow a hunting club (%)")


@dataclass(frozen=True)
class CampaignRules:
    winter_quarters_attrition_cut_pct: int = rule(60, 0, 100, W, "Share of an army's attrition winter quarters spare it in a closed season (%)")
    pursuit_kill_pct: int = rule(20, 0, 100, W, "Share of a routed enemy's scattered soldiers a pursuing army cuts down or takes (%)")
    escort_raid_cut_pct: int = rule(50, 0, 100, W, "Share of raids on its convoys and siege trains an escorting army turns away (%)")
    pursuit_ambush_pct: int = rule(15, 0, 100, W, "Chance a pursuing army runs into an ambush (%)")
    pursuit_ambush_loss_pct: int = rule(5, 0, 100, W, "Share of its soldiers a pursuing army loses when ambushed (%)")


@dataclass(frozen=True)
class ArmyStaffRules:
    chaplain_effect: int = rule(10, 0, 100, W, "Morale a chaplain's rites lend an army each season, half of it as camp sickness eased by burying the dead")
    paymaster_effect: int = rule(20, 0, 100, W, "Mutiny pressure an honest paymaster takes from an army each season, or chest share a corrupt one loses (%)")
    scout_master_effect: int = rule(30, 0, 100, W, "Share of the losses to ambush and danger a master of scouts spares an army (%)")
    engineer_master_effect: int = rule(25, 0, 100, W, "Share a master of engineers adds to the progress of an army's siege works (%)")
    interpreter_effect: int = rule(20, 0, 100, W, "Share an interpreter adds to an army's foraging and parley among a people of another tongue (%)")


@dataclass(frozen=True)
class SiegeRules:
    suborn_base_pct: int = rule(10, 0, 100, W, "Chance a besieger's work on those inside opens a gate or postern (%)")
    suborn_grudge_bonus_pct: int = rule(
        20, 0, 100, W, "Extra chance of suborning those inside where a faction holds a grudge against its rulers or the besieger holds a hook (%)"
    )
    suborn_cost: int = rule(20, 0, 1000, W, "Coin a besieger spends on bribes each season it suborns")
    suborn_harden: int = rule(10, 0, 100, W, "Wall repair and morale a defence gains when a plot to open a gate is found out")
    flood_halt_pct: int = rule(60, 0, 100, W, "Share of the progress of the besiegers' works that flooding the approaches undoes (%)")
    flood_field_harm: int = rule(40, 0, 100, W, "Share of one year's harvest a land loses when its approaches are flooded (%)")
    scorch_forage_cut_pct: int = rule(
        50, 0, 100, W, "Share of the forage around a besieged place, and of that year's harvest of its land, that burning the land destroys (%)"
    )
    expel_food_gain_pct: int = rule(20, 0, 100, W, "Share of its stores a besieged place saves by driving out those who cannot fight (%)")
    expel_share_pct: int = rule(15, 0, 100, W, "Share of a besieged place's people driven out as mouths that cannot fight (%)")
    expel_let_through_pct: int = rule(50, 0, 100, W, "Chance the besiegers let the expelled through rather than leaving them between the lines (%)")
    expel_lost_pct: int = rule(40, 0, 100, W, "Share of the expelled left between the lines who die there (%)")
    circumvallation_labour: int = rule(
        100, 0, 300, W, "Pace at which a siege work that rings the besieged place so no food or help comes in is built, against an ordinary siege work (%)"
    )
    circumvallation_effect: int = rule(
        10, 0, 100, W, "Strength of a siege work that rings the besieged place so no food or help comes in: extra stores the ringed place eats each season (%)"
    )
    towers_labour: int = rule(
        100, 0, 300, W, "Pace at which a siege work that brings attackers level with the wall top is built, against an ordinary siege work (%)"
    )
    towers_effect: int = rule(0, 0, 100, W, "Strength of a siege work that brings attackers level with the wall top: extra breach chance once it stands (%)")
    rams_labour: int = rule(100, 0, 300, W, "Pace at which a siege work that batters a gate or wall is built, against an ordinary siege work (%)")
    rams_effect: int = rule(0, 0, 100, W, "Strength of a siege work that batters a gate or wall: extra breach chance once it stands (%)")
    mines_labour: int = rule(100, 0, 300, W, "Pace at which a siege work that undermines a wall is built, against an ordinary siege work (%)")
    mines_effect: int = rule(0, 0, 100, W, "Strength of a siege work that undermines a wall: extra breach chance once it is dug (%)")
    countermines_labour: int = rule(
        100, 0, 300, W, "Pace at which a siege work that meets the besiegers' mines underground is built, against an ordinary siege work (%)"
    )
    countermines_effect: int = rule(
        30,
        0,
        100,
        W,
        "Strength of a siege work that meets the besiegers' mines underground: share of the besiegers' mining it undoes each season it is dug (%)",
    )
    ladders_labour: int = rule(100, 0, 300, W, "Pace at which a siege work that puts attackers on the wall is built, against an ordinary siege work (%)")
    ladders_effect: int = rule(0, 0, 100, W, "Strength of a siege work that puts attackers on the wall: extra breach chance once they stand (%)")
    bombardment_labour: int = rule(
        100, 0, 300, W, "Pace at which a siege work that groups engines or guns against one section of wall is built, against an ordinary siege work (%)"
    )
    bombardment_effect: int = rule(
        15, 0, 100, W, "Strength of a siege work that groups engines or guns against one section of wall: extra breach chance once it is massed (%)"
    )
    sapping_labour: int = rule(
        75, 0, 300, W, "Pace at which a siege work that lets attackers approach under cover is built, against an ordinary siege work (%)"
    )
    sapping_effect: int = rule(
        30, 0, 100, W, "Strength of a siege work that lets attackers approach under cover: share of the besiegers' losses to sallies it spares (%)"
    )
    blockade_lines_labour: int = rule(
        100, 0, 300, W, "Pace at which a siege work that closes the land and water around the besieged place is built, against an ordinary siege work (%)"
    )
    blockade_lines_effect: int = rule(
        10, 0, 100, W, "Strength of a siege work that closes the land and water around the besieged place: extra stores the closed place eats each season (%)"
    )
    air_assault_labour: int = rule(
        75, 0, 300, W, "Pace at which a siege work that lands attackers on the walls from the air is built, against an ordinary siege work (%)"
    )
    air_assault_effect: int = rule(
        15, 0, 100, W, "Strength of a siege work that lands attackers on the walls from the air: extra breach chance once it is ready (%)"
    )
    network_attack_labour: int = rule(
        75, 0, 300, W, "Pace at which a siege work that breaks into the besieged place's networks is built, against an ordinary siege work (%)"
    )
    network_attack_effect: int = rule(
        15, 0, 100, W, "Strength of a siege work that breaks into the besieged place's networks: extra breach chance once it is through (%)"
    )
    rite_breach_labour: int = rule(
        75, 0, 300, W, "Pace at which a siege work that works a rite against the walls and wards is built, against an ordinary siege work (%)"
    )
    rite_breach_effect: int = rule(
        15, 0, 100, W, "Strength of a siege work that works a rite against the walls and wards: extra breach chance once it is worked (%)"
    )
    ramp_labour: int = rule(
        30, 0, 300, W, "Pace at which a siege work that brings attackers to the wall top by labour over weeks is built, against an ordinary siege work (%)"
    )
    ramp_effect: int = rule(
        20, 0, 100, W, "Strength of a siege work that brings attackers to the wall top by labour over weeks: extra breach chance once it reaches the wall (%)"
    )
    dam_labour: int = rule(60, 0, 100, W, "Labour a dam across a river takes each season from the besiegers (%)")
    dam_effect: int = rule(25, 0, 100, W, "Share of the water of a besieged town a finished dam cuts, or of the approaches it floods (%)")
    burn_works_pct: int = rule(40, 0, 100, W, "Share of the besiegers' works a garrison's fire sets back (%)")
    burn_works_sallies: int = rule(3, 0, 50, W, "Sallies a garrison makes to burn the works before it can no longer spare the soldiers")
    evacuate_share_pct: int = rule(60, 0, 100, W, "Share of a besieged coastal town's people carried away by sea when it is given up (%)")


@dataclass(frozen=True)
class SackRules:
    ransom_share_pct: int = rule(30, 0, 100, W, "Share of a fallen city's treasury and wealth the victor takes as its ransom (%)")
    deport_share_pct: int = rule(70, 0, 100, W, "Share of a fallen city's people the victor moves to its own lands (%)")
    ransom_pick_pct: int = rule(30, 0, 100, W, "Chance a victor who would sack a rich city takes a ransom instead (%)")
    deport_pick_pct: int = rule(20, 0, 100, W, "Chance a victor who would sack a city and holds bondage lawful takes its people instead (%)")
    ransom_from: int = rule(40, 0, 1000, W, "Treasury from which a fallen city can pay a ransom")
    resettle_pick_pct: int = rule(15, 0, 100, W, "Chance a victor settles its own people in a fallen town (%)")
    resettle_share_pct: int = rule(40, 0, 100, W, "Share of a fallen town's people driven out for the victor's settlers (%)")


@dataclass(frozen=True)
class SettleModeRules:
    ground_defence: int = rule(100, 0, 300, C, "How hard a settlement on open ground is to take, against one on open ground (%)")
    ground_exposure: int = rule(100, 0, 300, C, "How much of the weather a settlement on open ground takes, against one on open ground (%)")
    floating_defence: int = rule(120, 0, 300, C, "How hard a settlement that floats is to take, against one on open ground (%)")
    floating_exposure: int = rule(140, 0, 300, C, "How much of the weather a settlement that floats takes, against one on open ground (%)")
    stilt_defence: int = rule(110, 0, 300, C, "How hard a settlement on stilts is to take, against one on open ground (%)")
    stilt_exposure: int = rule(120, 0, 300, C, "How much of the weather a settlement on stilts takes, against one on open ground (%)")
    oasis_defence: int = rule(100, 0, 300, C, "How hard a settlement at an oasis is to take, against one on open ground (%)")
    oasis_exposure: int = rule(110, 0, 300, C, "How much of the weather a settlement at an oasis takes, against one on open ground (%)")
    vent_defence: int = rule(100, 0, 300, C, "How hard a settlement around warm vents is to take, against one on open ground (%)")
    vent_exposure: int = rule(90, 0, 300, C, "How much of the weather a settlement around warm vents takes, against one on open ground (%)")
    habitat_defence: int = rule(130, 0, 300, C, "How hard a settlement in sealed habitats is to take, against one on open ground (%)")
    habitat_exposure: int = rule(60, 0, 300, C, "How much of the weather a settlement in sealed habitats takes, against one on open ground (%)")
    band_defence: int = rule(100, 0, 300, C, "How hard a settlement in a habitable band is to take, against one on open ground (%)")
    band_exposure: int = rule(100, 0, 300, C, "How much of the weather a settlement in a habitable band takes, against one on open ground (%)")
    deck_defence: int = rule(120, 0, 300, C, "How hard a settlement on decks is to take, against one on open ground (%)")
    deck_exposure: int = rule(80, 0, 300, C, "How much of the weather a settlement on decks takes, against one on open ground (%)")
    burrow_defence: int = rule(140, 0, 300, C, "How hard a settlement in burrows is to take, against one on open ground (%)")
    burrow_exposure: int = rule(50, 0, 300, C, "How much of the weather a settlement in burrows takes, against one on open ground (%)")
    submerged_defence: int = rule(150, 0, 300, C, "How hard a settlement beneath the water is to take, against one on open ground (%)")
    submerged_exposure: int = rule(40, 0, 300, C, "How much of the weather a settlement beneath the water takes, against one on open ground (%)")
    canopy_defence: int = rule(120, 0, 300, C, "How hard a settlement in the canopy is to take, against one on open ground (%)")
    canopy_exposure: int = rule(130, 0, 300, C, "How much of the weather a settlement in the canopy takes, against one on open ground (%)")
    exposure_prosperity: int = rule(5, 0, 100, C, "Prosperity a settlement fully exposed loses each epoch to the full force of wind and flood")
    canopy_cover: int = rule(40, 0, 100, C, "Forest cover below which a settlement in the canopy loses its trees and comes down")
    canopy_fall_pct: int = rule(20, 0, 100, C, "Share of the folk of a canopy settlement lost when its forest falls (%)")
    unfit_unrest: int = rule(10, 0, 100, C, "Unrest a settlement gains each epoch while it lives in a way its people cannot (%)")
    cliff_defence: int = rule(170, 0, 300, C, "How hard a settlement on cliffs is to take, against one on open ground (%)")
    cliff_exposure: int = rule(120, 0, 300, C, "How much of the weather a settlement on cliffs takes, against one on open ground (%)")
    drift_defence: int = rule(90, 0, 300, C, "How hard a settlement on drifting ice, rafts or floating masses is to take, against one on open ground (%)")
    drift_exposure: int = rule(150, 0, 300, C, "How much of the weather a settlement on drift takes, against one on open ground (%)")
    cliff_trade_pct: int = rule(70, 0, 200, C, "Trade a settlement on cliffs carries by lifts and paths, against one on open ground (%)")


@dataclass(frozen=True)
class WarGroundRules:
    land_frontage: int = rule(100, 0, 100, W, "Width of the front a battle on land can hold, against one on open land (%)")
    naval_frontage: int = rule(80, 0, 100, W, "Width of the front a battle at sea can hold, against one on open land (%)")
    sky_frontage: int = rule(
        100, 0, 100, W, "Width of the front a battle in the sky can hold, against one on open land (%); the ground itself never narrows it"
    )
    boarding_frontage: int = rule(30, 0, 100, W, "Width of the front a battle by boarding can hold, against one on open land (%)")
    strata_frontage: int = rule(60, 0, 100, W, "Width of the front a battle between strata can hold, against one on open land (%)")
    under_water_frontage: int = rule(
        90, 0, 100, W, "Width of the front a battle beneath the water can hold, against one on open land (%); the ground itself never narrows it"
    )
    space_frontage: int = rule(
        100, 0, 100, W, "Width of the front a battle in open space can hold, against one on open land (%); the ground itself never narrows it"
    )
    underground_frontage: int = rule(25, 0, 100, W, "Width of the front a battle in tunnels and caverns can hold, against one on open land (%)")
    dimension_frontage: int = rule(30, 0, 100, W, "Width of the front when a war is fought across dimensions, through rifts and gates, against open land (%)")
