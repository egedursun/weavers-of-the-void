from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

P = RuleGroup.POLITY
S = RuleGroup.SETTLEMENTS
G = RuleGroup.POPULATION_AND_GROWTH
H = RuleGroup.HOUSES
M = RuleGroup.MIND
R = RuleGroup.RELIGION_AND_LANGUAGE
E = RuleGroup.ECONOMY
W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class StructuralDemographyRules:
    pressure_floor_pct: int = rule(50, 0, 200, P, "Share of its carrying capacity a realm's people fill before population pressure starts (%)")
    pressure_full_pct: int = rule(110, 1, 400, P, "Share of its carrying capacity at which population pressure is full (%)")
    content_at: int = rule(60, 1, 100, P, "Satisfaction of the poor at and above which they count as free of misery")
    youth_norm_pct: int = rule(30, 0, 100, P, "Share of children in the cohorts above which the young swell the mass mobilisation potential (%)")
    youth_weight: int = rule(100, 0, 400, P, "How much each point of youth share above the norm raises popular immiseration (%)")
    urban_norm_pct: int = rule(30, 0, 100, P, "Share of town dwellers above which towns swell the mass mobilisation potential (%)")
    urban_weight: int = rule(50, 0, 400, P, "How much each point of town dwellers above the norm raises popular immiseration (%)")
    merchant_elite_pct: int = rule(50, 0, 100, P, "Share of the merchants that count as aspirants to elite positions (%)")
    scribe_elite_pct: int = rule(50, 0, 100, P, "Share of the scribes and the credentialed that count as aspirants to elite positions (%)")
    positions_per_office: int = rule(40, 0, 10000, P, "Elite positions each office of a realm offers")
    positions_per_title: int = rule(60, 0, 10000, P, "Elite positions each title of a realm offers")
    positions_per_town: int = rule(20, 0, 10000, P, "Elite positions each town of a realm offers in land and benefices")
    overproduction_scale: int = rule(50, 0, 1000, P, "Elite overproduction for each aspirant beyond one per position")
    debt_weight: int = rule(60, 0, 200, P, "How much a realm's debt against its means weighs in fiscal distress (%)")
    corruption_weight: int = rule(40, 0, 200, P, "How much corruption weighs in fiscal distress (%)")
    weariness_weight: int = rule(30, 0, 200, P, "How much war weariness weighs in fiscal distress (%)")
    empty_treasury: int = rule(20, 0, 100, P, "Fiscal distress an empty treasury adds")
    crisis_at: int = rule(55, 0, 100, P, "Political stress index from which a realm is in crisis")
    recovery_pressure: int = rule(40, 0, 100, P, "Population pressure below which a realm after crisis stays in depression")
    stagflation_pressure: int = rule(60, 0, 100, P, "Population pressure from which a realm's growth turns to stagflation")
    counter_elite_at: int = rule(40, 0, 100, P, "Elite overproduction from which aspirants without a post gather as counter-elites")
    counter_elite_pct: int = rule(20, 0, 100, P, "Chance each epoch counter-elites gather into a faction where overproduction allows it (%)")
    elite_fall_pct: int = rule(5, 0, 100, P, "Share of the nobles of a realm in crisis that fall from their station each epoch (%)")
    coup_lift: int = rule(100, 0, 400, P, "How much a full political stress index raises the chance of coups (%)")
    revolt_lift: int = rule(100, 0, 400, P, "How much a full political stress index raises the chance of revolts (%)")
    faction_lift: int = rule(80, 0, 400, P, "How much a full political stress index raises the chance of factions forming (%)")
    threshold_cut: int = rule(20, 0, 100, P, "Threshold points a full political stress index takes from collective action")
    crisis_weight: int = rule(50, 0, 400, P, "How much a realm's stress beyond crisis weighs in the storyteller's turmoil (%)")
    misery_growth_cut: int = rule(30, 0, 100, G, "How much full immiseration on a full land slows population growth (%)")
    misery_death_pct: int = rule(20, 0, 200, G, "How much full immiseration on a full land raises deaths (%)")


@dataclass(frozen=True)
class AsabiyyaRules:
    frontier_ratio_pct: int = rule(
        150, 100, 1000, M, "Value distance against the mean between neighbouring peoples from which a neighbour forms a meta-ethnic frontier (%)"
    )
    frontier_floor: int = rule(3, 0, 200, M, "Least value distance that can form a meta-ethnic frontier")
    frontier_gain: int = rule(2, 0, 50, M, "Solidarity each frontier region adds each epoch")
    frontier_cap: int = rule(8, 0, 100, M, "Most solidarity frontiers can add in one epoch")
    conflict_rise: int = rule(40, 0, 100, M, "Conflict an epoch of war adds to a holder's shared struggle")
    conflict_fade: int = rule(30, 0, 100, M, "Share of the shared struggle that fades each epoch (%)")
    conflict_gain: int = rule(5, 0, 50, M, "Solidarity a full shared struggle adds each epoch")
    luxury_at: int = rule(65, 0, 100, M, "Mean satisfaction from which a generation counts as one of luxury")
    luxury_generations: int = rule(3, 1, 20, M, "Generations of luxury after which solidarity starts to decay")
    luxury_decay: int = rule(3, 0, 50, M, "Solidarity lost each epoch for each generation of luxury past the limit")
    inland_decay: int = rule(1, 0, 50, M, "Solidarity lost each epoch far from any frontier")
    psi_decay: int = rule(4, 0, 50, M, "Solidarity a full political stress index takes each epoch through elite intrigue")
    surge_at: int = rule(75, 0, 100, M, "Solidarity at which a holder is noted as forged into one")
    soft_at: int = rule(30, 0, 100, M, "Solidarity below which a holder is noted as gone soft")
    cohesion_pull: int = rule(10, 0, 100, M, "Share of its solidarity above or below the middle a people's cohesion gains or loses each epoch (%)")
    assimilation_weight: int = rule(80, 0, 400, M, "How much solidarity resists assimilation (%)")
    levy_weight: int = rule(40, 0, 400, W, "How much solidarity raises the levies a community can raise (%)")
    morale_weight: int = rule(40, 0, 400, W, "How much solidarity raises the morale of new armies (%)")
    conquest_weight: int = rule(60, 0, 400, W, "How much solidarity raises the chance of going raiding for conquest (%)")


@dataclass(frozen=True)
class ChallengeResponseRules:
    severity_scale: int = rule(300, 0, 2000, P, "How much a loss against carrying capacity counts as a challenge (%)")
    collapse_below: int = rule(30, 0, 100, P, "Stability below which a realm meets the trial of collapse")
    depleted_below: int = rule(25, 0, 100, P, "Stability of a source of power below which a realm meets the trial of its depletion")
    signal_step: int = rule(15, 0, 100, P, "Severity each arrival, loosed line or new technique adds to its trial")
    notice_at: int = rule(3, 0, 100, P, "Severity from which a loss is recorded as a challenge")
    fade_pct: int = rule(25, 0, 100, P, "Share of the challenge index that fades each epoch (%)")
    band_low: int = rule(15, 0, 100, P, "Challenge index from which a realm answers with innovation instead of stagnation")
    band_high: int = rule(60, 0, 100, P, "Challenge index above which a realm collapses instead of answering")
    research_progress: int = rule(20, 0, 100, P, "Research progress a full challenge in the band gives the realm's capital")
    civic_pct: int = rule(30, 0, 100, P, "Chance a challenge in the band brings a new way of ordering the realm (%)")
    civic_progress: int = rule(25, 0, 100, P, "Research progress such a new way gives a civic technique")
    response_asabiyya: int = rule(4, 0, 50, M, "Solidarity a realm gains when it answers a challenge")
    stagnation_asabiyya: int = rule(1, 0, 50, M, "Solidarity a realm loses when its challenges are too slight to answer")
    calm_decay: int = rule(1, 0, 50, M, "Solidarity a realm with no challenge at all loses each epoch")
    collapse_asabiyya: int = rule(6, 0, 50, M, "Solidarity a realm loses when it collapses under its challenges")
    collapse_stability: int = rule(10, 0, 100, P, "Stability a realm loses when it collapses under its challenges")
    collapse_legitimacy: int = rule(8, 0, 100, P, "Legitimacy a realm loses when it collapses under its challenges")


@dataclass(frozen=True)
class LongPlanRules:
    steps_per_epoch: int = rule(1, 1, 100, P, "Steps a long plan advances each epoch it is paid for")
    default_cost: int = rule(10, 0, 100000, P, "Coin each step of a new long plan costs when none is given")
    expose_pct: int = rule(10, 0, 100, P, "Chance each epoch a long plan without any secrecy comes to light (%)")
    exposed_relation: int = rule(15, 0, 100, P, "Relation the target of an exposed plan loses with its holder")
    disrupt_pct: int = rule(20, 0, 100, P, "Chance each epoch rivals set back an exposed plan (%)")
    disrupt_steps: int = rule(2, 0, 100, P, "Steps rivals take from an exposed plan they set back")
    eco_moisture: int = rule(25, -100, 100, P, "Moisture a fulfilled ecological transformation gives each land it remakes")
    eco_fertility: int = rule(20, -100, 100, P, "Soil fertility a fulfilled ecological transformation gives each land it remakes")
    bloodline_gift_pct: int = rule(20, 0, 100, P, "How far a fulfilled bloodline plan aimed at a people moves its pool toward the gifted allele (%)")
    wonder_funds_pct: int = rule(50, 0, 100, P, "Share of a wonder plan's savings that fund the wonder it raises (%)")
    programme_head_start: int = rule(30, 0, 100, P, "Progress a long plan gives the programme it opens")
    realm_gain: int = rule(10, 0, 100, P, "Administration and legitimacy a long plan to bind a realm gives")
    reform_cut: int = rule(15, 0, 100, P, "Corruption a long plan of reform takes away")
    routes_found: int = rule(2, 0, 50, P, "Hidden ways a long plan of exploration charts")


@dataclass(frozen=True)
class ReciprocityRules(Spanned):
    return_years: int = span(5, 1, 1250, M, "Years a receiver has to return a gift where the norm of gifts is neutral")
    norm_weight: int = rule(60, 0, 200, M, "How much the norm of gifts in hospitality strengthens or loosens the obligations of a gift (%)")
    preference_weight: int = rule(50, 0, 200, M, "How much the receiver's liking for a gift's material raises its value (%)")
    give_prestige: int = rule(10, 0, 100, M, "Standing a giver gains for each hundred of a gift's value (%)")
    gift_regard: int = rule(5, 0, 100, M, "Regard a receiver feels for a giver")
    refuse_below: int = rule(-50, -100, 100, M, "Relation below which a receiver refuses a gift")
    refusal_insult: int = rule(20, 0, 100, M, "Relation a giver loses when its gift is refused")
    outgive_pct: int = rule(20, 0, 200, M, "How much more a rival must give to answer a competitive gift (%)")
    return_regard: int = rule(5, 0, 100, M, "Regard a giver feels when its gift is returned in kind")
    lapse_prestige: int = rule(20, 0, 200, M, "Standing a receiver loses and a giver gains for each hundred of an unreturned gift's value (%)")
    courtesy_pct: int = rule(10, 0, 100, M, "Chance each epoch an ally sends a gift to its ally (%)")
    courtesy_value: int = rule(10, 0, 100000, M, "Coin a gift between allies is worth")

    @property
    def return_epochs(self) -> int:
        return self.epochs(self.return_years)


@dataclass(frozen=True)
class PotlatchRules:
    claim_pct: int = rule(30, 0, 100, M, "Chance a feast's host claims rank over its greatest guest with a great gift (%)")
    stake_pct: int = rule(10, 0, 100, M, "Share of the host's coin a rank-claiming gift is worth (%)")
    minimum: int = rule(10, 0, 100000, M, "Least coin a rank-claiming gift is worth")
    destroy_pct: int = rule(20, 0, 100, M, "Chance the host destroys the wealth instead of giving it (%)")


@dataclass(frozen=True)
class CircuitRules:
    pass_value: int = rule(20, 0, 100000, M, "Worth of the treasure each pass of a ceremonial circuit hands on")
    holder_prestige: int = rule(3, 0, 100, M, "Standing a stop gains while it holds the circuit's treasure")
    bond_regard: int = rule(4, 0, 100, M, "Regard each pass of a circuit builds between the two stops")
    hospitality_danger: int = rule(2, 0, 100, M, "Danger from outlaws each stop of a ceremonial circuit takes from its land, by its duty of hospitality")


@dataclass(frozen=True)
class SacrificeRules:
    base_piety: int = rule(50, 0, 100, R, "Piety of a worshipping community that has none recorded")
    offering_per_piety: int = rule(10, 0, 1000, R, "Offering a community of full piety makes to its god each epoch")
    answer_value: int = rule(10, 0, 1000, R, "Debt each answered prayer or kind act of a god repays")
    debt_at: int = rule(30, 0, 100000, R, "Unanswered offerings from which a god's standing with the givers falls")
    debt_neglect: int = rule(10, 0, 200, R, "Neglect a community feels for each hundred of unanswered offerings beyond the limit (%)")
    debt_love: int = rule(10, 0, 200, R, "Love a community loses for each hundred of unanswered offerings beyond the limit (%)")
    generous_love: int = rule(10, 0, 200, R, "Love a community gains for each hundred a god gives beyond the offerings (%)")
    forgive_at: int = rule(500, 0, 100000, R, "Offerings from which the settled part of the ledger is cleared")


@dataclass(frozen=True)
class KinshipSystemRules:
    unilineal_at: int = rule(
        30,
        -300,
        300,
        H,
        "Standing of a people's kinship value among the world's peoples, in hundredths of their spread, from which it reckons descent through one line",
    )
    double_at: int = rule(
        150, -300, 300, H, "Standing of a people's kinship value from which it reckons descent through both lines at once, in hundredths of the spread"
    )
    ambilineal_at: int = rule(
        -80, -300, 300, H, "Standing of a people's family value below which each child picks the line it belongs to, in hundredths of the spread"
    )
    clan_at: int = rule(60, -300, 300, H, "Standing of a people's kinship value from which it groups its lines into clans, in hundredths of the spread")
    moiety_at: int = rule(120, -300, 300, H, "Standing of a people's kinship and tradition from which it splits into two halves, in hundredths of the spread")
    house_at: int = rule(60, -300, 300, H, "Standing of a people's hierarchy from which it groups its lines into houses, in hundredths of the spread")
    parallel_siblings_at: int = rule(
        50,
        -300,
        300,
        H,
        "Standing of a people's kinship value from which parallel cousins are called siblings (merging or cross and parallel terms), in hundredths of the spread",
    )
    all_siblings_at: int = rule(
        130, -300, 300, H, "Standing of a people's kinship value from which every cousin is called a sibling (generational terms), in hundredths of the spread"
    )
    descriptive_at: int = rule(
        -100, -300, 300, H, "Standing of a people's kinship value at or below which each kinsperson has a term of its own, in hundredths of the spread"
    )
    heir_adoption_at: int = rule(100, -300, 300, H, "Standing of a people's hierarchy value from which its adoptions make heirs, in hundredths of the spread")
    chosen_kin_at: int = rule(80, -300, 300, H, "Standing of a people's kinship value from which its adoptions make chosen kin, in hundredths of the spread")
    sponsor_at: int = rule(80, -300, 300, H, "Standing of a people's wealth value from which its adoptions are sponsorships, in hundredths of the spread")
    cross_cousin_at: int = rule(
        30, -300, 300, H, "Standing of a people's kinship value from which it prefers cross-cousin marriage, in hundredths of the spread"
    )
    payment_at: int = rule(50, -300, 300, H, "Standing of a people's wealth or perseverance from which marriages carry a payment, in hundredths of the spread")
    payment_value: int = rule(10, 0, 100000, H, "Coin a marriage payment is worth when a people's kinship system is first read")
    first_line_kin_at: int = rule(
        100,
        -300,
        300,
        H,
        "Standing of the kinship value of a people that counts descent through the second line from which a couple lives with kin of the first line, in hundredths of the spread",
    )
    first_side_sibling_union_at: int = rule(
        80,
        -300,
        300,
        H,
        "Standing of a people's kinship value from which a widowed spouse of the second side weds a sibling of the dead, in hundredths of the spread",
    )
    second_side_sibling_union_at: int = rule(
        80,
        -300,
        300,
        H,
        "Standing of a people's family value from which a widowed spouse of the first side weds a sibling of the dead spouse, in hundredths of the spread",
    )


@dataclass(frozen=True)
class MarriageAllianceRules(Spanned):
    cross_cousin_bonus: int = rule(20, 0, 200, H, "Weight a cross-cousin gets in a match where that marriage is preferred")
    exogamy_bonus: int = rule(10, 0, 200, H, "Weight a spouse of another line gets in a match where exogamy is the rule")
    alliance_regard: int = rule(6, 0, 100, H, "Regard each marriage between two lines builds")
    giver_rank: int = rule(2, -20, 20, H, "Standing the line that gives more spouses than it takes gains for each marriage of the gap")
    pact_at: int = rule(3, 1, 100, H, "Marriages between two lines of different realms from which the realms sign a marriage pact")
    pact_years: int = span(30, 1, 25000, H, "Years a marriage pact between the realms holds")

    @property
    def pact_epochs(self) -> int:
        return self.epochs(self.pact_years)


@dataclass(frozen=True)
class ReproductionSystemRules:
    change_age: int = rule(30, 0, 100000, G, "Age at which a sequential people changes sex when its biology gives none")
    breeder_norm_pct: int = rule(10, 0, 100, G, "Share of breeders of a caste people that gives its usual growth (%)")
    soldier_norm_pct: int = rule(20, 0, 100, G, "Share of soldiers of a caste people that gives its usual levies (%)")
    soldier_levy_weight: int = rule(100, 0, 400, W, "How much a soldier share above the norm raises a caste people's levies (%)")
    asexual_growth_pct: int = rule(120, 0, 400, G, "Growth of a people that buds or divides, against two-sex growth (%)")
    ambisexual_growth_pct: int = rule(110, 0, 400, G, "Growth of a people that takes either sex, against two-sex growth (%)")
    budding_pct: int = rule(5, 0, 100, G, "Chance each epoch a fertile mortal of a budding people buds (%)")


@dataclass(frozen=True)
class NomadismRules:
    pastoral_pct: int = rule(40, 0, 100, E, "Share of its workers in herding from which a small settlement takes to the move (%)")
    nomadic_pct: int = rule(60, 0, 100, E, "Share of its workers in herding from which a camp roams rather than moving between two pastures (%)")
    settle_pct: int = rule(25, 0, 100, E, "Share of its workers in herding below which a camp settles (%)")
    circuit_stops: int = rule(4, 2, 20, E, "Pastures a roaming camp's circuit holds before its herd grows")
    reroute_at: int = rule(25, 0, 100, E, "Grazing below which a camp lays a new circuit through fresher pastures")
    trade_pct: int = rule(40, 0, 100, E, "Chance each epoch riders who neither raid nor take tribute trade with a settled neighbour (%)")
    trade_per_herd: int = rule(2, 0, 1000, E, "Coin each hundred herd beasts bring in trade")
    trade_regard: int = rule(4, 0, 100, E, "Regard a trade builds between a camp and its settled neighbour")
    herd_per_dweller: int = rule(200, 0, 10000, E, "Herd beasts per hundred dwellers when a camp first takes to the move")
    herd_growth_pct: int = rule(10, 0, 100, E, "Growth of a herd on full grazing and water each epoch (%)")
    herd_loss_pct: int = rule(4, 0, 100, E, "Herd lost each epoch to age and loss (%)")
    graze_pressure: int = rule(5, 0, 100, E, "Grazing pressure a full herd puts on the land it stands on")
    herd_scale: int = rule(1000, 1, 1000000, E, "Herd size counted as a full herd for grazing pressure")
    rider_pct: int = rule(20, 0, 100, W, "Share of a camp's dwellers who ride out (%)")
    rider_per_herd: int = rule(2, 0, 100, W, "Riders each hundred herd beasts mount")
    tribute_ratio: int = rule(3, 1, 20, W, "Times the guard of a settled neighbour the riders must be to take tribute")
    raid_pct: int = rule(25, 0, 100, W, "Chance each epoch riders strong enough raid a settled neighbour (%)")
    raid_take: int = rule(10, 0, 1000, W, "Coin each hundred riders carry off in a raid")
    raid_relation: int = rule(10, 0, 100, W, "Relation a raided settlement loses with the raiders")
    leader_charisma: int = rule(70, 0, 100, P, "Charisma from which a leader can gather camps into a confederation")
    confederation_min: int = rule(3, 2, 100, P, "Roaming camps near a leader needed to form a confederation")
    steppe_asabiyya: int = rule(2, 0, 50, M, "Solidarity a roaming people gains each epoch on the move")


@dataclass(frozen=True)
class LegacyTraitRules:
    keep_pct: int = rule(60, 0, 100, M, "Chance a successor people keeps each kind of legacy from its predecessor (%)")
    absorbed_keep_pct: int = rule(25, 0, 100, M, "Chance a people keeps each kind of legacy from a people that joined it (%)")
    art_mastery: int = rule(30, 0, 100, M, "Mastery of an art form a people keeps from the one it came from")
    value_pull: int = rule(50, 0, 100, M, "How far a kept value moves toward the predecessor's (%)")


@dataclass(frozen=True)
class LabourRegimeRules:
    misery: int = rule(30, 0, 100, S, "Satisfaction the poor lose where all are bound under full exploitation")
    crowd_cut: int = rule(25, 0, 100, S, "Threshold points a town's bound labourers take from collective action, at a full share")


@dataclass(frozen=True)
class CorveeRules:
    lay_pct: int = rule(15, 0, 100, P, "Chance each epoch a realm raising a great work summons its towns to forced labour (%)")
    share_pct: int = rule(15, 0, 100, P, "Share of farmhands a realm summons to forced labour (%)")
    work_output: int = rule(100, 0, 1000, P, "Work each hundred forced labourers add to the great work each epoch (%)")
    unthinkable_at: int = rule(-70, -100, 0, P, "Ethics reading of forced labour below which a realm will not summon its towns to it")


@dataclass(frozen=True)
class IndentureRules(Spanned):
    misery_at: int = rule(35, 0, 100, S, "Mean satisfaction of farmers and outcasts below which the poor fall into bondage")
    form_pct: int = rule(10, 0, 100, S, "Chance each epoch the poor of a miserable town are bound (%)")
    bound_pct: int = rule(3, 0, 100, S, "Share of a town bound in one contract (%)")
    term_years: int = span(7, 1, 2500, S, "Years an indenture lasts")
    debt_per_head: int = rule(5, 0, 10000, S, "Debt each bound labourer starts with")
    repay_per_head: int = rule(2, 0, 10000, S, "Debt each bound labourer works off each epoch without exploitation")
    exploitation_base: int = rule(30, 0, 100, S, "Exploitation of a new contract before the employer's greed")
    exploitation_spread: int = rule(15, 0, 100, S, "Spread of exploitation around its base")
    greed_weight: int = rule(30, 0, 200, S, "How much the value of wealth raises an employer's exploitation (%)")
    inflate_share: int = rule(50, 0, 200, S, "How much exploitation turns into the chance an employer inflates a debt (%)")
    inflate_pct: int = rule(20, 0, 200, S, "How much an inflated debt grows (%)")
    migrant_pct: int = rule(15, 0, 100, S, "Chance each epoch newcomers living among a town's hosts sign contracts of labour (%)")
    migrant_share_pct: int = rule(20, 0, 100, S, "Share of the newcomers who sign a contract of labour (%)")
    foreign_weight: int = rule(30, 0, 200, S, "How much the distance between the values of hosts and newcomers raises the exploitation of their contract (%)")

    @property
    def term_epochs(self) -> int:
        return self.epochs(self.term_years)


@dataclass(frozen=True)
class SlaveMarketRules:
    base_price: int = rule(20, 0, 100000, E, "Price of a bound adult before skill, age, origin and appearance")
    skill_weight: int = rule(60, 0, 400, E, "How much the craft share of the market town raises the price (%)")
    age_weight: int = rule(40, 0, 400, E, "How much the share of adults among the bound raises the price (%)")
    origin_weight: int = rule(30, 0, 400, E, "How much the value distance of the captives' people lowers the price (%)")
    appearance_weight: int = rule(30, 0, 400, E, "How much the looks of the captives' people raise the price (%)")
    appearance_sample: int = rule(20, 1, 1000, E, "Mortals of a people read to judge its looks")
    sale_pct: int = rule(10, 0, 100, E, "Share of a market town's bound adults offered each epoch (%)")
    scarcity_weight: int = rule(50, 0, 400, E, "How much scarcity raises the price (%)")
    demand: int = rule(20, 1, 1000000, E, "Bound folk a market town wants each epoch, per 1000 of its people")
    raid_lift: int = rule(100, 0, 400, W, "How much a price above the base raises the chance of raiding for captives (%)")


@dataclass(frozen=True)
class ManumissionRules(Spanned):
    service_pct: int = rule(40, 0, 100, S, "Chance the bound freed in wartime are freed for service (%)")
    purchase_prosperity: int = rule(60, 0, 100, S, "Prosperity from which the bound buy their freedom")
    revolt_strength: int = rule(10, 1, 1000, S, "Militia each point of a slave rising's strength overcomes")
    revolt_share_pct: int = rule(30, 0, 100, S, "Share of the bound a successful rising frees (%)")
    revolt_memory_years: int = span(30, 0, 2500, S, "Years a slave rising feeds the abolition movement")
    revolt_pressure: int = rule(30, 0, 200, S, "Abolition pressure each hundred freed by risings adds (%)")
    indenture_pressure: int = rule(30, 0, 200, S, "Abolition pressure a full share of bound labourers adds (%)")
    egalitarian_pct: int = rule(25, 0, 100, S, "How much a disregard for hierarchy feeds the abolition movement (%)")
    freed_standing: int = rule(40, 0, 100, S, "Standing among the free that the newly freed start with")
    standing_rise: int = rule(10, 0, 100, S, "Standing the freed gain each epoch before the respect for hierarchy slows it")
    hierarchy_drag: int = rule(50, 0, 100, S, "How much a culture's respect for hierarchy slows the rise of the freed (%)")
    office_at: int = rule(70, 0, 100, S, "Standing from which the freed take office and the priesthood beside the freeborn")
    stigma: int = rule(20, 0, 100, S, "Satisfaction the freed lose where all of a town's people are freed folk of the lowest standing")
    origin_share_pct: int = rule(50, 0, 100, S, "Share of freed captives who stay a community of their own origin in the town (%)")

    @property
    def revolt_memory_epochs(self) -> int:
        return self.epochs(self.revolt_memory_years)
