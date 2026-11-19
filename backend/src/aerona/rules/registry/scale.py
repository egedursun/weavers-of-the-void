from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.SETTLEMENTS
D = RuleGroup.DEATH_AND_RESURRECTION
P = RuleGroup.POLITY
H = RuleGroup.HOUSES
L = RuleGroup.LANGUAGE_AND_NAMES
M = RuleGroup.MATERIALS
W = RuleGroup.WAR_AND_DIPLOMACY
F = RuleGroup.MORTALS
BIG = 1000000000


@dataclass(frozen=True)
class ScaleRules(Spanned):
    death_workers_per_mille: int = rule(1, 0, 1000, D, "Workers each death role of a people needs per 1000 of its people")
    death_recruit_gap_pct: int = rule(
        10, 0, 100, D, "Share of the gap to its needed workers an honoured death role closes, and the share of its workers an avoided one loses (% per year)"
    )
    trainees_per_training_level: int = rule(5, 0, 100000, S, "Townsfolk a training structure trains each epoch for each of its levels")
    tower_root: int = rule(2, 1, 1000, S, "Square root of a walled settlement's people that one tower of its wall circuit covers")
    circuit_tower_weight: int = rule(
        20, 0, 10000, W, "Towers' worth of siege defence a wall circuit gives when it has a tower at every spacing its length calls for"
    )
    towers_per_gate: int = rule(8, 1, 1000, S, "Towers of a wall circuit for each gate it opens")
    quarter_people: int = rule(10000, 1, BIG, S, "People for each level of a market, craft, temple, burial, industrial or business quarter a settlement wants")
    preparedness_level_people: int = rule(5000, 1, BIG, S, "People for each level a work against disaster may rise beyond its fifth")
    preparedness_works_people: int = rule(5000, 1, BIG, S, "People for each extra work against disaster a settlement raises in one epoch")
    council_seat_people: int = rule(500000, 1, BIG, P, "Subjects for each extra seat of ministers, generals and admirals a realm keeps")
    realm_subjects_tier: int = rule(100000, 1, BIG, P, "Subjects at which a realm gains a tier from its people, gaining one more with each tenfold")
    council_offices_per_voice: int = rule(4, 1, 1000, P, "Offices of a realm for each councillor heard beyond the first three when a vote is argued")
    breeding_match_pct: int = rule(3, 0, 100, H, "Share of a house's unwed adults a long breeding design matches (% per year)")
    replicator_mass_per_reach: int = rule(200, 1, BIG, M, "Mass of a replicator presence for each extra neighbouring region it seeds in one epoch")
    book_quality_per_subject: int = rule(20, 1, 100, RuleGroup.CIVILIZATION, "Quality of a book for each subject it holds beyond its first")
    hire_seek_people: int = rule(500, 1, BIG, RuleGroup.MORTAL_AGENTS, "People of a place for each extra local a schemer weighs when hiring, beyond twelve")
    ambush_people_per_victim: int = rule(10, 1, 100000, W, "Folk of a feuding side for each one an ambush catches beyond the first")
    missile_rounds_carried: int = rule(3, 1, 100, W, "Battle phases of shooting a missile unit carries ammunition for")
    pidgin_lexicon_pct: int = rule(15, 0, 100, L, "Share of a parent tongue's words a newborn pidgin takes (%)")
    sparse_town_people: int = rule(500, 0, BIG, RuleGroup.POPULATION_AND_GROWTH, "Average people per town below which a realm counts its land as underpeopled")
    skill_per_carried_technique: int = rule(25, 1, 1000, F, "Skill of a migrating scholar for each technique carried beyond the first")
