from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

R = RuleGroup.REPUTATION
H = RuleGroup.HOUSES
S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class RenownAxisRules:
    mercy_surrender_pct: int = rule(10, 0, 100, R, "How much readier a besieged town is to yield to a commander renowned for mercy, at full renown (%)")
    justice_legitimacy: int = rule(5, 0, 50, R, "Legitimacy a ruler renowned for justice gains each epoch at full renown, with unrest falling as much")
    mercy_gain: int = rule(10, 0, 100, R, "Mercy renown gained for sparing a foe, a captive or one condemned, or for a pardon")
    justice_gain: int = rule(8, 0, 100, R, "Justice renown gained for a judgement given by the law, the more for punishing the powerful")


@dataclass(frozen=True)
class InheritanceRules:
    will_contest_pct: int = rule(20, 0, 100, H, "Chance kin left out of a will contest it when it is read (%)")
    seniority_dispute_pct: int = rule(15, 0, 100, H, "Chance the children of the dead dispute an inheritance passed to the eldest of the line (%)")


@dataclass(frozen=True)
class DwellingRules:
    stilt_flood_cut_pct: int = rule(60, 0, 100, S, "Share of flood harm to households that houses on stilts turn aside (%)")
    burrow_cold_cut_pct: int = rule(50, 0, 100, S, "Share of cold harm and siege hunger to households that burrows turn aside (%)")


@dataclass(frozen=True)
class ShortfallRules:
    thirst_death_pct: int = rule(20, 0, 100, S, "People who die of thirst in an epoch when no water is to be had (%); thirst kills faster than hunger")
    shelter_sickness_pct: int = rule(15, 0, 100, S, "Adults who fall sick in an epoch when no one has a roof, from exposure and crowding (%)")
    shelter_cold_pct: int = rule(50, 0, 100, S, "Share of a want of shelter that counts as a want of warmth (%)")
    drought_thirst_pct: int = rule(50, 0, 100, S, "Want of water a drought brings to a community with no stored water (%)")
    dry_rainfall: int = rule(20, 0, 100, S, "Rainfall below which a community with no wells, cisterns or aqueducts begins to go thirsty")
    dry_thirst_pct: int = rule(40, 0, 100, S, "Want of water at no rainfall for a community with no wells, cisterns or aqueducts (%)")
    siege_thirst_pct: int = rule(90, 0, 100, S, "Want of water in a besieged town whose water has run out (%)")
    thirst_siege_seasons: int = rule(2, 1, 10, S, "Seasons of famine that one season without water counts for in a siege")
    note_pct: int = rule(20, 0, 100, S, "Want at which a shortfall is first told in the chronicle (%)")
    thirst_pressure_pct: int = rule(150, 0, 300, S, "Hunger pressure from the share of the people without water (%)")
    shelter_pressure_pct: int = rule(80, 0, 300, S, "Crowding pressure from the share of the people without a roof (%)")


@dataclass(frozen=True)
class RebuildingRules:
    fire_lesson_pct: int = rule(40, 0, 100, S, "Chance a town rebuilt after a fire raises a firebreak (%)")
    flood_lesson_pct: int = rule(40, 0, 100, S, "Chance a town rebuilt after a flood raises a levee (%)")
    quake_lesson_pct: int = rule(30, 0, 100, S, "Chance a town rebuilt after an earthquake drills its people for the next (%)")
    storm_lesson_pct: int = rule(30, 0, 100, S, "Chance a town rebuilt after a storm raises shelters (%)")
    sack_lesson_pct: int = rule(40, 0, 100, S, "Chance a town rebuilt after a sack raises watchtowers (%)")
    eruption_lesson_pct: int = rule(40, 0, 100, S, "Chance a town rebuilt after an eruption lays out ways of flight (%)")
    sea_wave_lesson_pct: int = rule(50, 0, 100, S, "Chance a town rebuilt after a sea wave raises a seawall (%)")
    landslide_lesson_pct: int = rule(40, 0, 100, S, "Chance a town rebuilt after a landslide watches its slopes and learns to terrace them (%)")
    relocate_pct: int = rule(10, 0, 100, S, "Chance a ruined town is rebuilt on a nearby safer site (%)")
    abandon_pct: int = rule(5, 0, 100, S, "Chance a ruined town is left, its people scattering as the displaced (%)")


@dataclass(frozen=True)
class WaterLiftRules:
    shaduf_lift: int = rule(100, 0, 100, S, "Share of its capacity a shaduf lifts (%)")
    noria_lift: int = rule(100, 0, 100, S, "Share of its capacity a noria lifts (%)")
    screw_lift: int = rule(100, 0, 100, S, "Share of its capacity a water screw lifts (%)")
    chain_pump_lift: int = rule(100, 0, 100, S, "Share of its capacity a chain pump lifts (%)")
    steam_pump_lift: int = rule(100, 0, 100, S, "Share of its capacity a steam pump lifts (%)")
    wind_pump_lift: int = rule(100, 0, 100, S, "Share of its capacity a wind pump lifts at full wind (%)")
    electric_pump_lift: int = rule(100, 0, 100, S, "Share of its capacity a pump driven by electric power lifts (%)")
    still_wind: int = rule(20, 0, 100, S, "Wind strength below which a wind pump stands still")


@dataclass(frozen=True)
class LockRules:
    bar_difficulty: int = rule(20, 0, 100, S, "Most a bar and bolt holds against a thief")
    warded_difficulty: int = rule(40, 0, 100, S, "Most a warded lock holds against a thief")
    tumbler_difficulty: int = rule(60, 0, 100, S, "Most a tumbler lock holds against a thief")
    combination_difficulty: int = rule(80, 0, 100, S, "Most a combination lock holds against a thief")
    warded_seal_difficulty: int = rule(50, 0, 100, S, "Most a warded lock with a seal holds against a thief")
    worked_difficulty: int = rule(90, 0, 100, S, "Most a lock held by a rite or a power holds against one who can work against it")
    electronic_difficulty: int = rule(85, 0, 100, S, "Most an electronic lock holds against an intruder")


@dataclass(frozen=True)
class UnderworldRules(Spanned):
    gang_recruit_pct: int = rule(
        10, 0, 100, S, "Chance in an epoch that the young of the streets, slums and camps of a lawless town band into a street gang (%)"
    )
    trafficking_route_pct: int = rule(15, 0, 100, S, "Chance in an epoch that a trafficking ring takes people along one of the roads of its town (%)")
    trafficked: int = rule(20, 0, 100000, S, "People a trafficking ring takes into bondage along one road in an epoch")
    gang_grow_years: int = span(15, 1, 500, S, "Years a street gang must hold strong turf before it grows into a crime family")
    gang_grow_turf: int = rule(60, 0, 100, S, "Turf strength a street gang must hold to grow into a crime family")
    tolerate_bribe_pct: int = rule(20, 0, 100, S, "Share of the income of a tolerated organisation that its bribes carry to the realm's officials (%)")
    tolerate_corruption: int = rule(3, 0, 100, S, "Corruption a realm gains each epoch for each organisation it tolerates")
    outcry_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a tolerated organisation stirs an outcry that turns its realm to suppression (%)")
    license_tax_pct: int = rule(20, 0, 100, S, "Share of the income of a licensed trade its realm takes in tax (%)")
    license_crime: int = rule(5, 0, 100, S, "Crime a licensed trade takes off its town each epoch by working in the open")
    forbidden_strength: int = rule(100, 0, 100, S, "Strength of the suppression a realm whose law forbids bondage turns on a trafficking ring")


@dataclass(frozen=True)
class FugitiveRules:
    outlaw_hunt_pct: int = rule(20, 0, 100, S, "Chance in an epoch that an outlaw out of sanctuary is caught (%)")
    accused_hunt_pct: int = rule(25, 0, 100, S, "Chance in an epoch that an accused who fled is caught (%)")
    defector_hunt_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a defector out of sanctuary is caught (%)")
    runaway_hunt_pct: int = rule(30, 0, 100, S, "Chance in an epoch that a runaway from bondage is caught by owners and law (%)")
    deserter_hunt_pct: int = rule(25, 0, 100, S, "Chance in an epoch that a deserter is caught by the army it left (%)")
    heretic_hunt_pct: int = rule(20, 0, 100, S, "Chance in an epoch that one who fled a faith's persecution is caught (%)")
    runaway_flee_pct: int = rule(3, 0, 100, S, "Chance in an epoch that a mortal in bondage runs away (%)")
    deserter_flee_pct: int = rule(5, 0, 100, S, "Chance in an epoch that a warrior of a realm at war deserts (%)")
    heretic_flee_pct: int = rule(5, 0, 100, S, "Chance in an epoch that one of another faith flees a realm that persecutes it (%)")
