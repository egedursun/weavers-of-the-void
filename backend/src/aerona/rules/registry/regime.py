from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

P = RuleGroup.POLITY
H = RuleGroup.HOUSES
K = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class SelectorateRules:
    adult_pct: int = rule(60, 0, 100, P, "Share of a tribe's people who are grown and have a say in choosing its leader (%)")
    citizen_pct: int = rule(30, 0, 100, P, "Share of a republic's people who hold the rights of citizens (%)")
    council_pct: int = rule(10, 0, 100, P, "Share of the nobles and merchants who sit in a ruling council (%)")
    autocratic_pct: int = rule(8, 0, 100, P, "Share of the selectorate an autocrat needs in the winning coalition (%)")
    council_rule_pct: int = rule(30, 0, 100, P, "Share of the selectorate a council ruler needs in the winning coalition (%)")
    assembly_pct: int = rule(55, 0, 100, P, "Share of the selectorate an assembly ruler needs in the winning coalition (%)")
    divine_pct: int = rule(15, 0, 100, P, "Share of the selectorate a ruler chosen by the gods needs in the winning coalition (%)")
    public_floor: int = rule(15, 0, 100, P, "Share of spending that goes to public goods under the smallest coalition (%)")
    spend_pct: int = rule(10, 0, 100, P, "Share of the treasury a realm spends each epoch on public and private goods (%)")
    coin_per_prosperity: int = rule(200, 1, 100000, P, "Coin of public goods that raises the prosperity of one town by a point")
    prosperity_cap: int = rule(4, 0, 100, P, "Most prosperity public goods add to one town in an epoch")
    private_corruption: int = rule(20, 0, 100, P, "Corruption a realm leans toward when all its spending is private goods")
    coalition_seats: int = rule(6, 0, 100, P, "Most notable members a winning coalition keeps on its roll")
    reward_per_coin: int = rule(50, 1, 100000, P, "Coin of private goods that raises one member's reward by a point")
    reward_decay: int = rule(10, 0, 100, P, "Reward a coalition member forgets each epoch")
    loyalty_drift_pct: int = rule(30, 0, 100, P, "Share of the gap to its target a member's loyalty closes each epoch (%)")
    rival_offer_pct: int = rule(50, 0, 200, P, "How much the threat of the strongest power base pulls coalition loyalty away (%)")
    purge_at: int = rule(30, 0, 100, P, "Coalition loyalty under which a ruler purges its least loyal member")
    purge_pct: int = rule(40, 0, 100, P, "Chance each epoch a ruler with a disloyal coalition purges (%)")
    coup_weight: int = rule(100, 0, 400, P, "How much a disloyal winning coalition raises the chance of a coup (%)")
    balance_weight: int = rule(40, 0, 100, P, "How much one faction holding the balance of power narrows the winning coalition (%)")
    satisfaction_cap: int = rule(3, 0, 100, P, "Most satisfaction public goods add to the farmers and craftsfolk of one town in an epoch")
    opinion_weight: int = rule(30, 0, 200, P, "How much a member's regard for the ruler moves the member's loyalty (%)")


@dataclass(frozen=True)
class LegitimacyTypeRules:
    drift_pct: int = rule(20, 0, 100, P, "Share of the gap to its target each kind of legitimacy closes each epoch (%)")
    tenure_epochs: int = rule(10, 1, 1000, P, "Epochs of unbroken rule by one house at which traditional legitimacy is full")
    heir_tradition: int = rule(15, 0, 100, P, "Traditional legitimacy a named heir adds")
    usurper_tradition: int = rule(40, 0, 100, P, "Traditional legitimacy a usurper loses")
    chosen_charisma: int = rule(30, 0, 100, P, "Charismatic legitimacy a ruler chosen by the gods gains")
    defeat_charisma: int = rule(25, 0, 100, P, "Charismatic legitimacy a ruler loses for a war lost this epoch")
    victory_charisma: int = rule(15, 0, 100, P, "Charismatic legitimacy a ruler gains for a war won this epoch")
    bureaucracy_rational: int = rule(40, 0, 100, P, "Legal-rational legitimacy a realm with clerks and offices holds")
    law_rational: int = rule(10, 0, 100, P, "Legal-rational legitimacy each written or codified body of law adds")
    corruption_rational: int = rule(50, 0, 200, P, "How much corruption wears legal-rational legitimacy away (%)")
    miracle_charisma: int = rule(10, 0, 100, P, "Charismatic legitimacy each recent miracle credited to the ruler adds")
    miracle_epochs: int = rule(3, 1, 100, P, "Epochs a miracle credited to the ruler lends charisma")
    prophecy_charisma: int = rule(15, 0, 100, P, "Charismatic legitimacy a ruler who fits a believed prophecy of return gains")
    legitimacy_weight: int = rule(10, 0, 100, P, "How much each kind of legitimacy above or below the middle moves a ruler's legitimacy (%)")


@dataclass(frozen=True)
class RoutinisationRules:
    founder_charisma: int = rule(60, 0, 100, P, "Charismatic legitimacy at which a ruler counts as a charismatic founder")
    founder_epochs: int = rule(3, 0, 100, P, "Epochs after a realm's founding in which its ruler counts as its founder")
    convert_pct: int = rule(60, 0, 100, P, "Share of a dead founder's charisma turned into tradition or rules (%)")
    schism_pct: int = rule(30, 0, 100, P, "Chance a charismatic founder's death breaks the realm into schism (%)")
    schism_stability: int = rule(25, 0, 100, P, "Stability a realm loses in a schism")
    fragment_pct: int = rule(50, 0, 100, P, "Share of its member towns a big-man's following loses at the big-man's death (%)")
    schism_claim: int = rule(40, 0, 100, P, "Strength of the claim a schism gives the founder's kin against the heir")


@dataclass(frozen=True)
class TimeHorizonRules:
    heir_horizon: int = rule(20, 0, 100, P, "Time horizon a named heir adds")
    legitimacy_weight: int = rule(40, 0, 200, P, "How much legitimacy lengthens a ruler's time horizon (%)")
    threat_weight: int = rule(40, 0, 200, P, "How much stress and the strongest power base shorten a ruler's time horizon (%)")
    war_horizon: int = rule(15, 0, 100, P, "Time horizon a ruler at war loses")
    plunder_pct: int = rule(60, 0, 200, P, "Extraction above the norm under the shortest time horizon (%)")
    invest_pct: int = rule(25, 0, 100, P, "Extraction below the norm under the longest time horizon (%)")
    invest_public: int = rule(20, 0, 100, P, "Public share of spending a long time horizon adds")


@dataclass(frozen=True)
class ClientelismRules:
    favour_at: int = rule(20, 0, 100, P, "Weight of a favour owed at which the debtor becomes the creditor's client")
    office_strength: int = rule(30, 0, 100, P, "Strength of the tie an appointment makes between the appointer and the appointed")
    decay: int = rule(5, 0, 100, P, "Strength a patronage tie loses each epoch")
    bureaucracy_strength: int = rule(40, 0, 100, P, "Institutional strength clerks and offices give a realm")
    justice_weight: int = rule(30, 0, 100, P, "How much just laws strengthen a realm's institutions (%)")
    literacy_weight: int = rule(30, 0, 100, P, "How much literacy strengthens a realm's institutions (%)")
    patronage_at: int = rule(60, 0, 100, P, "Institutional strength under which appointments follow patronage")
    client_bonus: int = rule(40, 0, 1000, P, "Weight a client of the appointer gains in an appointment for each point institutions fall short")
    client_votes_pct: int = rule(
        40, 0, 400, P, "Votes a town whose lord is a client of a candidate's leader casts for that candidate where institutions are weak (%)"
    )


@dataclass(frozen=True)
class VenalityRules:
    sell_pct: int = rule(10, 0, 100, P, "Chance each epoch an indebted or short-sighted realm sells an office (%)")
    base_price: int = rule(300, 0, 1000000, P, "Price of an office sold by a realm")
    recoup_pct: int = rule(20, 0, 100, P, "Share of its price a bought office yields its buyer each epoch (%)")
    recoup_cap_pct: int = rule(200, 0, 1000, P, "Share of its price a bought office yields before its buyer is content (%)")
    corruption: int = rule(3, 0, 100, P, "Corruption each bought office still recouping adds")
    sinecure_at: int = rule(40, 0, 100, P, "Coalition loyalty under which a ruler hands out sinecures")
    sinecure_reward: int = rule(20, 0, 100, P, "Reward a sinecure gives its holder in the coalition")


@dataclass(frozen=True)
class PowerBaseRules:
    holding_weight: int = rule(10, 0, 1000, P, "Weight of each town a character holds in a power base")
    troop_weight: int = rule(1, 0, 1000, P, "Weight of each hundred soldiers loyal to a character in a power base")
    office_weight: int = rule(15, 0, 1000, P, "Weight of each office a character or its clients hold in a power base")
    wealth_weight: int = rule(30, 0, 1000, P, "Weight of a character's wealth in a power base (%)")
    popularity_weight: int = rule(30, 0, 1000, P, "Weight of a character's renown in a power base (%)")
    defy_at: int = rule(40, 0, 100, P, "Threat at which a character defies the ruler")
    extort_at: int = rule(60, 0, 100, P, "Threat at which a character extorts the ruler")
    plot_at: int = rule(80, 0, 100, P, "Threat at which a character plots to take the throne")
    extortion: int = rule(100, 0, 1000000, P, "Coin an extorting character wrings from the treasury each epoch")
    defiance_stability: int = rule(3, 0, 100, P, "Stability a realm loses for each defiant character")
    counter_pct: int = rule(50, 0, 100, P, "Chance each epoch a ruler answers a plotting subject by marriage, split command or purge (%)")
    marriage_cut: int = rule(30, 0, 100, P, "Threat a marriage between the ruler's kin and a plotting subject's kin takes away")


@dataclass(frozen=True)
class CoupProofingRules:
    insecure_at: int = rule(50, 0, 100, P, "Stress or threat at which a ruler takes up coup-proofing")
    secure_at: int = rule(20, 0, 100, P, "Stress and threat under which a ruler lays coup-proofing down")
    adopt_pct: int = rule(40, 0, 100, P, "Chance each epoch an insecure ruler takes up one more measure (%)")
    coup_cut: int = rule(20, 0, 100, P, "Share of the chance of a coup each measure takes away (%)")
    morale_cut: int = rule(10, 0, 100, P, "Share of its morale an army loses while its commanders are rotated (%)")
    guard_upkeep: int = rule(80, 0, 1000000, P, "Coin a parallel guard costs each epoch")
    hostage_cap: int = rule(60, 0, 100, P, "Threat to which hostages hold a powerful character's ambitions")


@dataclass(frozen=True)
class LeadershipModeRules:
    gift_following: int = rule(5, 0, 100, P, "Legitimacy a big-man's following gains for each gift or feast the big-man gave this epoch")
    chief_pct: int = rule(10, 0, 100, P, "Chance each epoch a long-held following becomes a chiefdom that passes by descent (%)")
    chief_horizon: int = rule(60, 0, 100, P, "Time horizon from which a following can become a chiefdom")


@dataclass(frozen=True)
class SegmentaryRules:
    backing_regard: int = rule(5, 0, 100, H, "Regard a lineage gains for the kin it backs in a feud")
    fusion_weight: int = rule(10, 0, 400, H, "How much each lineage backing a side swells a feud (%)")
    foreign_weight: int = rule(50, 0, 400, H, "How much a feud with foreigners swells when the whole tribe unites (%)")


@dataclass(frozen=True)
class BreedingPlanRules:
    love_pct: int = rule(20, 0, 100, H, "Chance a member chosen for a planned match marries for love instead (%)")
    barren_epochs: int = rule(3, 1, 100, H, "Epochs a planned couple may stay childless before the match counts as barren")
    conceal_pct: int = rule(15, 0, 100, H, "Chance a planned match is hidden behind a concealed parentage (%)")
    conceal_secrecy: int = rule(5, 0, 100, H, "Secrecy a concealed parentage adds to the plan")
    secret_severity: int = rule(40, 0, 100, H, "Severity of the secret of a concealed parentage")


@dataclass(frozen=True)
class ExaminationRules:
    candidate_pct: int = rule(5, 0, 100, K, "Share of a realm's scribes and nobles who sit an examination (%)")
    pass_rate: int = rule(30, 0, 100, K, "Share of the candidates who reach the pass mark (%)")
    notable_passes: int = rule(3, 0, 100, K, "Most notable mortals an examination grants credentials")
    skill_mark: int = rule(30, 0, 100, K, "Skill in law, letters or lore a notable candidate needs to pass")
    quota_growth: int = rule(50, 0, 400, K, "How much elite overproduction raises the quota of an examination (%)")
    credential_bonus: int = rule(60, 0, 1000, K, "Weight a credentialed candidate gains in an appointment")
    credential_epochs: int = rule(5, 1, 100, K, "Epochs graduates of an examination keep pressing for posts")
    graduate_weight: int = rule(100, 0, 1000, K, "Aspirants to elite posts each graduate of an examination counts as (%)")


@dataclass(frozen=True)
class CredentialRules:
    master_at: int = rule(40, 0, 100, K, "Skill at which a scholar at a school or academy is made a master")
    doctor_at: int = rule(70, 0, 100, K, "Skill at which a scholar at an academy is made a doctor")
    ordain_at: int = rule(30, 0, 100, K, "Skill in rites at which a priest is ordained where the clergy are ranked")
    degree_at: int = rule(50, 0, 100, K, "Skill at which a scholar at a university is given a degree")
    licence_at: int = rule(45, 0, 100, K, "Skill in their calling at which a physician, engineer or pilot is licensed where law is written")
    commission_at: int = rule(45, 0, 100, K, "Skill in their calling at which an officer is commissioned where law is written")
    renown: int = rule(3, 0, 100, K, "Importance a credential adds to its holder")


@dataclass(frozen=True)
class AcademicFreedomRules:
    base: int = rule(60, 0, 100, K, "Freedom of a house of learning before laws, orthodoxy and the ruler's will")
    censorship_cut: int = rule(30, 0, 100, K, "Freedom a law of censorship takes away")
    orthodoxy_cut: int = rule(20, 0, 100, K, "Freedom a state faith with an orthodoxy to guard takes away")
    mandate_weight: int = rule(30, 0, 200, K, "How much the ruler's regard for knowledge moves freedom (%)")
    drift_pct: int = rule(30, 0, 100, K, "Share of the gap to its target freedom closes each epoch (%)")
    suppress_at: int = rule(30, 0, 100, K, "Freedom under which learning counts as suppressed")
    research_weight: int = rule(40, 0, 200, K, "How much freedom above or below the middle moves research (%)")
    migrate_pct: int = rule(20, 0, 100, K, "Chance each epoch a scholar under suppressed learning leaves for a freer house (%)")
    carried_progress: int = rule(20, 0, 100, K, "Progress a migrating scholar carries toward each technique the new home lacks")
    theory_weight: int = rule(40, 0, 200, K, "How much freedom above or below the middle moves the weight evidence carries in contests of theories (%)")


@dataclass(frozen=True)
class SchoolLineageRules:
    found_at: int = rule(50, 0, 100, K, "Skill at which a scholar with disciples founds a school")
    disciples: int = rule(2, 1, 100, K, "Lesser scholars beside a master needed to found a school")
    teach_xp: int = rule(20, 0, 1000, K, "Experience a disciple gains from a master each epoch")
    research_pct: int = rule(10, 0, 200, K, "Research a school with members in a community adds (%)")
    rival_regard: int = rule(5, 0, 100, K, "Regard the masters of rival schools lose each epoch")
