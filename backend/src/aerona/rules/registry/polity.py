from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

P = RuleGroup.POLITY
H = RuleGroup.HOUSES


@dataclass(frozen=True)
class GovernmentRules(Spanned):
    theocracy_piety: int = rule(50, -100, 100, P, "Piety value at which a realm ruled by a priest becomes a theocracy")
    republic_hierarchy: int = rule(-25, -100, 100, P, "Hierarchy value below which a merchant realm becomes a republic")
    oligarchy_merchant_pct: int = rule(20, 0, 100, P, "Merchant share at which a realm is ruled by its merchants (%)")
    empire_members: int = rule(6, 1, 1000, P, "Communities a realm must hold to count as an empire")
    confederation_peoples: int = rule(3, 1, 1000, P, "Peoples a loose realm must hold to count as a confederation")
    chiefdom_tier: int = rule(1, 0, 10, P, "Realm tier at or below which a monarchy is still a chiefdom")
    occupation_loyalty: int = rule(15, 0, 100, P, "Loyalty to its overlord at or below which a subject realm is ruled as occupied land")
    junta_warrior_pct: int = rule(20, 0, 100, P, "Warrior share at which a realm ruled by an officer becomes a military government (%)")
    technocracy_professional_pct: int = rule(20, 0, 100, P, "Professional share at which a learned realm is ruled by its experts (%)")
    republic_citizen_pct: int = rule(8, 0, 100, P, "Citizen share at which a realm whose commoners hold a vote elects its government (%)")
    citizen_hierarchy: int = rule(25, -100, 100, P, "Hierarchy value at or below which a realm of voting citizens elects its government")
    technocracy_civics_level: int = rule(4, 0, 20, P, "Civics level a realm needs to be ruled by its experts")
    machine_professional_pct: int = rule(25, 0, 100, P, "Professional share at which a realm hands its rule to machines (%)")
    machine_civics_level: int = rule(9, 0, 20, P, "Civics level a realm needs to hand its rule to machines")
    commune_worker_pct: int = rule(25, 0, 100, P, "Worker share at which an equal-minded realm becomes a commune (%)")
    corporate_worker_pct: int = rule(20, 0, 100, P, "Worker share at which a merchant realm becomes a corporate state (%)")
    federation_members: int = rule(6, 1, 1000, P, "Members a realm holds before it becomes a federation")
    federation_civics_level: int = rule(5, 0, 20, P, "Civics level a realm needs to become a federation")
    council_offices: int = rule(3, 1, 20, P, "Office holders needed to decide by council vote")
    decision_cap: int = rule(20, 0, 1000, P, "Most decisions a realm takes in an epoch")
    tax_greed_step: int = rule(5, 0, 50, P, "Tax a greedy ruler adds when the treasury is low")
    temple_piety: int = rule(40, -100, 100, P, "Piety at which a ruler funds temples")
    temple_cost: int = rule(200, 0, 1000000, P, "Treasury a funded temple costs")
    purge_paranoia: int = rule(60, 0, 100, P, "Paranoia at which a ruler purges disloyal officers")
    office_upkeep: int = rule(5, 0, 100000, P, "Treasury each office costs per epoch")
    polity_tax_pct: int = rule(30, 0, 100, P, "Share of members' taxes the realm takes (%)")
    min_founding_population: int = rule(300, 0, 10000000, P, "People a community needs to found a realm of its own")
    ruler_weight_pct: int = rule(60, 0, 100, P, "Weight of an autocrat's own values against the advisers' (%)")
    skill_full: int = rule(150, 1, 10000, P, "Office skill score that counts as full skill")
    chancellor_relation: int = rule(2, 0, 100, P, "Relation a fully skilled chancellor wins with treaty partners each epoch")
    marshal_cohesion: int = rule(3, 0, 100, P, "Cohesion a fully skilled marshal adds to the realm's armies each epoch")
    treasurer_leak_pct: int = rule(50, 0, 100, P, "Share of tax leakage a fully skilled treasurer saves (%)")
    governor_autonomy: int = rule(3, 0, 100, P, "Autonomy a fully skilled governor removes from its province each epoch")
    governor_control: int = rule(3, 0, 100, P, "Control a fully skilled governor adds to its province each epoch")
    ambassador_relation: int = rule(3, 0, 100, P, "Relation a fully skilled ambassador wins with the host each epoch")
    chaplain_piety: int = rule(2, 0, 100, P, "Piety a fully skilled court chaplain kindles in each land of the realm each epoch")
    embassy_count: int = rule(10, 0, 1000, P, "Most embassies a realm keeps")
    emblem_cohesion: int = rule(1, 0, 100, P, "Cohesion the realm's banner adds to its armies each epoch")
    emblem_artwork: int = rule(2, 0, 100, P, "Legitimacy per propaganda artwork bearing the realm's emblem")
    emblem_artwork_cap: int = rule(10, 0, 100, P, "Most legitimacy the realm's displayed emblem gives")
    build_chance: int = rule(30, 0, 100, P, "A realm with a full treasury funds public works in an epoch (%)")
    build_cost: int = rule(150, 0, 1000000, P, "Treasury a public work costs the realm")
    loan_interest_pct: int = rule(10, 0, 100, P, "Interest a lender charges an indebted realm per epoch (%)")
    loan_years: int = span(10, 1, 2500, P, "Years a realm has to repay a loan")
    default_relation: int = rule(25, 0, 100, P, "Relation a lender loses with a realm that defaults")
    default_war_chance: int = rule(30, 0, 100, P, "A defaulted lending realm goes to war over the debt (%)")
    coup_legitimacy: int = rule(30, 0, 100, P, "Legitimacy below which an ambitious marshal may seize the throne")
    coup_chance: int = rule(10, 0, 100, P, "An ambitious marshal of a weak ruler seizes the throne in an epoch (%)")

    @property
    def loan_epochs(self) -> int:
        return self.epochs(self.loan_years)


@dataclass(frozen=True)
class SuccessionRules:
    regency_age: int = rule(16, 0, 200, P, "Age below which an heir rules through a regent")
    designation_contest_pct: int = rule(20, 0, 100, P, "Chance the blood kin of a ruler contest an heir named from outside the blood (%)")
    senile_age_pct: int = rule(90, 0, 200, P, "Share of the lifespan at which a ruler counts as senile (%)")
    claim_press_pct: int = rule(60, 0, 100, P, "Claim strength at which a rival claimant may press it")
    war_chance: int = rule(30, 0, 100, P, "A pressed claim against a weak heir becomes a succession war (%)")
    usurp_chance: int = rule(10, 0, 100, P, "An ambitious regent seizes the throne in an epoch (%)")
    elective_charisma_pct: int = rule(60, 0, 100, P, "Weight of charisma against kinship in an election (%)")
    combat_strength_pct: int = rule(70, 0, 100, P, "Weight of strength in succession by combat (%)")
    patron_favour: int = rule(40, 0, 1000, P, "Weight of the patron god's favour in succession by divine choice")
    house_support_pct: int = rule(50, 0, 200, P, "Weight of house prestige in a succession dispute (%)")
    faction_support_pct: int = rule(50, 0, 200, P, "Weight of backing factions' strength in a succession dispute (%)")
    opinion_support_pct: int = rule(50, 0, 200, P, "Weight of the nobles' discontent in a succession dispute (%)")
    support_press: int = rule(10, -100, 200, P, "Margin of support over the throne at which a claimant goes to war")
    house_join_chance: int = rule(60, 0, 100, P, "A house with a stake in a succession war takes a side (%)")


@dataclass(frozen=True)
class LegitimacyRules(Spanned):
    base: int = rule(50, 0, 100, P, "Legitimacy of a ruler with nothing for or against them")
    rightful: int = rule(15, 0, 100, P, "Legitimacy from taking the throne by the law of succession")
    usurper: int = rule(25, 0, 100, P, "Legitimacy lost by a usurper")
    unwhole: int = rule(15, 0, 100, P, "Legitimacy lost by a maimed ruler where wholeness is required")
    renown_per_10: int = rule(2, 0, 100, P, "Legitimacy per ten points of the ruler's importance")
    title_prestige_pct: int = rule(10, 0, 100, P, "Legitimacy the ruler gains from the prestige of the titles it holds (%)")
    title_cap: int = rule(15, 0, 100, P, "Most legitimacy the titles the ruler holds can give")
    oathbreaker: int = rule(15, 0, 100, P, "Legitimacy lost by an oathbreaker ruler")
    sanction: int = rule(10, 0, 100, P, "Legitimacy from a state religion that favours the ruler")
    excommunication: int = rule(20, 0, 100, P, "Legitimacy lost when the state religion turns against the ruler")
    victory: int = rule(5, 0, 100, P, "Legitimacy per war won in the last epochs")
    defeat: int = rule(8, 0, 100, P, "Legitimacy per war lost in the last epochs")
    prosperity_pct: int = rule(20, 0, 100, P, "Legitimacy at full prosperity of the realm (%)")
    child: int = rule(10, 0, 100, P, "Legitimacy lost by a child ruler")
    senile: int = rule(10, 0, 100, P, "Legitimacy lost by a senile ruler")
    divine_rule: int = rule(20, 0, 100, P, "Legitimacy of a ruler who is a god's chosen or a god")
    weariness_pct: int = rule(40, 0, 100, P, "Stability lost at the worst war weariness (%)")
    faction_pct: int = rule(30, 0, 100, P, "Stability lost when one faction overwhelms the rest (%)")
    unrest_pct: int = rule(50, 0, 100, P, "Stability lost at the worst unrest of the realm's cities (%)")
    weariness_decay: int = rule(10, 0, 100, P, "Least war weariness a realm at peace sheds each epoch, before its maimed and its memories of war slow it")
    body_reading_pct: int = rule(30, 0, 200, P, "Weight of the people's reading of the ruler's body (%)")
    honour_pct: int = rule(20, 0, 100, P, "Legitimacy from the ruler's honour at its fullest")
    infamy_pct: int = rule(30, 0, 100, P, "Legitimacy lost to the ruler's infamy at its worst")
    usurper_fade_years: int = span(30, 1, 2500, P, "Years after which a usurper's mark fades")
    usurper_infamy: int = rule(20, 0, 100, P, "Infamy a usurper gains")
    presence_pct: int = rule(20, 0, 100, P, "Legitimacy a ruler loses at no presence at all (%)")
    martial_melee_pct: int = rule(15, 0, 100, P, "Legitimacy a ruler of a warlike people loses at no strength of arms (%)")
    martial_value: int = rule(30, -100, 100, P, "How warlike a people must be before it judges its ruler by strength of arms")
    acts_pct: int = rule(25, 0, 200, P, "How much the realm's judgement of the ruler's deeds moves legitimacy (%)")
    acts_cap: int = rule(20, 0, 100, P, "Most legitimacy the ruler's deeds can win or lose")
    relic_legitimacy: int = rule(8, 0, 100, P, "Legitimacy from holding an heirloom relic of the line, such as a legendary prosthesis")

    @property
    def usurper_fade_epochs(self) -> int:
        return self.epochs(self.usurper_fade_years)


@dataclass(frozen=True)
class AdministrationRules:
    base: int = rule(3, 0, 1000, P, "Administration of the simplest realm")
    per_literacy: int = rule(6, 0, 1000, P, "Administration per ten points of literacy")
    per_scribe_pct: int = rule(2, 0, 1000, P, "Administration per point of the scribe class share")
    per_official_pct: int = rule(3, 0, 1000, P, "Administration per point of the official class share")
    service_per_point: int = rule(200, 1, 100000, P, "Service workers of the core community that add one point of administration")
    per_writing_level: int = rule(2, 0, 1000, P, "Administration per level of writing")
    per_road: int = rule(1, 0, 1000, P, "Administration per level of roads in the realm's cities")
    land_weight: int = rule(1, 0, 100, P, "Administration a held region needs")
    member_weight: int = rule(1, 0, 100, P, "Administration a member community needs")


@dataclass(frozen=True)
class OverextensionRules:
    autonomy_gain: int = rule(8, 0, 100, P, "Autonomy a distant member gains per epoch of overextension")
    autonomy_decay: int = rule(4, 0, 100, P, "Autonomy lost per epoch when the realm is well run")
    tax_leak_pct: int = rule(60, 0, 100, P, "Share of an autonomous member's taxes that never arrives at full autonomy (%)")
    secession_autonomy: int = rule(80, 0, 100, P, "Autonomy at which a member may break away")
    secession_chance: int = rule(20, 0, 100, P, "A member at the brink breaks away in an epoch (%)")


@dataclass(frozen=True)
class RevoltsRules:
    noble_bitter: int = rule(25, 0, 100, P, "Noble satisfaction below which a revolt is a revolt of the nobles")
    secession_autonomy: int = rule(60, 0, 100, P, "Autonomy above which a revolt is a war of secession")
    rebel_share_pct: int = rule(8, 0, 100, P, "Share of the people who take up arms in a revolt (%)")
    slave_share_pct: int = rule(25, 0, 100, P, "Share of the bound at which a revolt is a slave revolt (%)")
    minority_loyalty: int = rule(40, 0, 100, P, "Loyalty below which a town of a people not the realm's core rises as a minority")
    class_bitter: int = rule(25, 0, 100, P, "Satisfaction below which workers, soldiers or the learned lead a revolt")
    class_share_pct: int = rule(20, 0, 100, P, "Share of workers at which their grievance leads a revolt (%)")
    tax_heavy: int = rule(40, 0, 500, P, "Sum of a realm's tax rates at which a revolt is a tax revolt")
    made_minds_at: int = rule(3, 1, 100000, P, "Made minds per 10,000 people of a town at which a revolt is theirs (at least one)")
    gifted_at: int = rule(
        3, 1, 100000, P, "Gifted held unlicensed or conscripted by a realm, per 10,000 of its subjects, at which a revolt is theirs (at least one)"
    )
    urban_population: int = rule(20000, 0, 10000000, P, "Population at which a revolt in a city is an urban revolt")


@dataclass(frozen=True)
class LegislationRules(Spanned):
    enact_chance: int = rule(1, 0, 100, P, "A realm under pressure enacts a wanted law (% per year)")
    repeal_chance: int = rule(10, 0, 100, P, "A realm repeals a law at odds with its people in an epoch (%)")
    plague_quarantine_chance: int = rule(40, 0, 100, P, "A plague-struck realm enacts a quarantine law (%)")
    defeat_conscription_chance: int = rule(40, 0, 100, P, "A realm that lost a war enacts conscription (%)")
    enforcement_order_pct: int = rule(60, 0, 100, P, "Weight of order in a law's enforcement (%)")
    enforcement_judge_pct: int = rule(40, 0, 100, P, "Weight of the high judge's skill in a law's enforcement (%)")
    discord_distance: int = rule(40, 0, 100, P, "Distance from the people's values at which a law loses its legitimacy")
    discord_unrest: int = rule(6, 0, 100, P, "Unrest a law at odds with the people causes")
    rigidity_resist_pct: int = rule(60, 0, 100, P, "How strongly a customary law's rigidity resists repeal (%)")
    conquest_conflict: int = rule(60, 0, 100, P, "Conflict between conqueror and local law at the conquest")
    conflict_decay: int = rule(15, 0, 100, P, "Conflict that fades per epoch as the laws settle")
    lobby_conflict_pct: int = rule(10, 0, 100, P, "Share of the sway of the factions that press on a law's area it adds to that law's conflict each epoch (%)")
    conflict_unrest_pct: int = rule(20, 0, 100, P, "Unrest from legal conflict (%)")
    levy_share_pct: int = rule(100, 0, 500, P, "Weight of the levy law's share in raising an army (%)")
    pension_outcast_pct: int = rule(50, 0, 100, P, "Share of the maimed a veteran pension keeps out of the outcasts (%)")
    pension_opinion: int = rule(3, 0, 100, P, "Satisfaction warriors gain from a veteran pension")
    sumptuary_pct: int = rule(50, 0, 200, P, "How strongly sumptuary law moves luxury demand by class (%)")
    tolerance_spread_pct: int = rule(140, 0, 500, P, "Spread of foreign faith where worship is free (%)")
    persecution_spread_pct: int = rule(30, 0, 500, P, "Spread of foreign faith under persecution (%)")
    foreigner_pull_pct: int = rule(30, 0, 300, P, "Migration pull of a realm that grants foreigners citizenship (%)")
    sanitation_gain: int = rule(10, 0, 100, P, "Sanitation a sanitation law adds to its cities")
    tenure_shift: int = rule(4, 0, 100, P, "Satisfaction a land tenure law moves between the classes each epoch")
    freehold_prosperity: int = rule(1, 0, 100, P, "Prosperity a freehold tenure adds to a city each epoch")
    feudal_levy_pct: int = rule(15, 0, 200, P, "Extra levy a feudal tenure raises (%)")
    serf_labour_pct: int = rule(20, 0, 500, P, "Share of the serfs' owed labour days that reaches the city treasury (%)")
    serf_resentment: int = rule(3, 0, 100, P, "Satisfaction the bound lose per thirty owed labour days")
    serf_free_pct: int = rule(10, 0, 100, P, "Share of the bound freed each epoch where serfdom and slavery are banned (%)")
    jubilee_relief: int = rule(10, 0, 100, P, "Satisfaction farmers and the bound gain at a debt jubilee")
    levy_return_pct: int = rule(50, 0, 100, P, "Share of levies kept past their term that go home each epoch (%)")
    standing_upkeep_per_100: int = rule(2, 0, 1000, P, "Treasury a hundred standing soldiers cost each epoch")
    fine_amount: int = rule(5, 0, 10000, P, "Treasury a fine or wergild sentence brings the city")
    penal_infamy: int = rule(3, 0, 100, P, "Infamy the ruler gains for a cruel sentence at full cruelty")
    crisis_crime: int = rule(60, 0, 100, P, "Average crime at which a realm hardens its penal code")
    crisis_debt: int = rule(20, 0, 1000000, P, "Realm debt per 1000 subjects at which the realm proclaims a debt jubilee law")
    cult_proposal_chance: int = rule(30, 0, 100, P, "A state church proposes a law from its tenets in an epoch (%)")
    cult_law_chance: int = rule(20, 0, 100, P, "A cult lays down a religious law for its faithful in an epoch (%)")
    proposal_threshold: int = rule(50, 0, 100, P, "Discord with the realm's will below which a proposed law passes")
    sponsor_weight_pct: int = rule(50, 0, 200, P, "How much a sponsor's sway lowers the bar for its proposal (%)")
    endogamy_strict: int = rule(1, 0, 1, P, "An endogamy law forbids marriage outside the people (1 yes)")
    labour_law_worker_pct: int = rule(15, 0, 100, P, "Worker share at which a realm wants a labour law (%)")
    environment_law_pollution: int = rule(40, 0, 100, P, "Worst pollution of the capital's land at which a realm wants an environment law")
    privacy_civics_level: int = rule(6, 0, 20, P, "Civics level at which an equal-minded realm wants a privacy law")
    weapons_law_crime: int = rule(40, 0, 100, P, "Crime in the capital at which a realm with firearms wants a weapons law")
    weapons_law_metallurgy: int = rule(4, 0, 20, P, "Metallurgy level at which weapons are common enough to need a law")
    patent_professional_pct: int = rule(8, 0, 100, P, "Professional share at which a wealth-minded realm wants a patent law (%)")
    machine_law_professional_pct: int = rule(15, 0, 100, P, "Professional share at which a realm wants a law on machines (%)")


@dataclass(frozen=True)
class HousesRules:
    branch_members: int = rule(12, 2, 1000, H, "Living members at which a house splits off a cadet branch")
    prestige_office: int = rule(3, 0, 100, H, "Prestige per office held by a member")
    prestige_victory: int = rule(4, 0, 100, H, "Prestige per war won by a member's realm")
    prestige_renown_per_20: int = rule(1, 0, 100, H, "Prestige per twenty points of a member's importance")
    prestige_defeat: int = rule(4, 0, 100, H, "Prestige lost per war lost")
    prestige_maimed_purity: int = rule(5, 0, 100, H, "Prestige lost per maimed member in a purity-minded culture")
    prestige_decay: int = rule(3, 0, 100, H, "Prestige that fades each epoch")
    marriage_chance: int = rule(25, 0, 100, H, "A house head arranges a marriage for an eligible member in an epoch (%)")
    marriage_cap: int = rule(12, 0, 100000, H, "Most arranged marriages in an epoch (base)")
    marriage_cap_house_divisor: int = rule(2, 0, 100000, H, "Arranged marriage cap grows by 1 for every this many houses (0: fixed)")
    claim_inherit_pct: int = rule(70, 0, 100, H, "Share of a claim a child inherits (%)")
    marriage_claim: int = rule(30, 0, 100, H, "Claim a spouse's children gain on their mother's or father's realm")
    divine_prestige: int = rule(20, 0, 100, H, "Prestige of a house with divine blood")
    prestige_wonder: int = rule(6, 0, 100, H, "Prestige a ruling house gains per wonder raised in its realm")
    prestige_execution: int = rule(2, 0, 100, H, "Prestige a ruling house loses per execution under its law")
    prestige_infamy: int = rule(10, 0, 100, H, "Prestige lost for a member at the worst infamy")
    office_income: int = rule(3, 0, 1000, H, "House wealth earned per member holding an office")
    seat_income_pct: int = rule(5, 0, 100, H, "House wealth from each seat as a share of its prosperity (%)")
    wealth_decay_pct: int = rule(5, 0, 100, H, "Share of house wealth spent on upkeep each epoch (%)")
    union_portion_pct: int = rule(10, 0, 100, H, "Share of a house's wealth given as a portion with a spouse (%)")
    claim_weight_pct: int = rule(30, 0, 200, H, "How much a match's claims weigh when a house chooses a spouse (%)")
    trait_members: int = rule(2, 1, 100, H, "Members showing a sign before the bloodline takes it as a trait")
    trait_chance: int = rule(30, 0, 100, H, "A house showing a bloodline sign takes the trait in an epoch (%)")
    giant_strength: int = rule(85, 0, 100, H, "Strength at which a member counts as giant-blooded")
    fertile_children: int = rule(6, 1, 100, H, "Children alive at once that mark a fertile house")
    fertile_pct: int = rule(150, 0, 500, H, "Birth chance of a fertile house's couples (%)")
    cursed_fertility_pct: int = rule(60, 0, 500, H, "Birth chance of a cursed house's couples (%)")
    feud_memory: int = rule(30, 0, 100, H, "Ill memory a killing leaves between two houses")
    anchor_per_member: int = rule(1, 0, 100, H, "Existence a god's living bloodline lends it per member each epoch")
    anchor_cap: int = rule(5, 0, 100, H, "Most existence a bloodline lends its god each epoch")
    anchor_loss: int = rule(10, 0, 100, H, "Existence a god loses when its bloodline dies out")
    conquest_claim: int = rule(40, 0, 100, H, "Strength of the claim a conqueror's ruler gains on the conquered realm")
    fabricate_chance: int = rule(15, 0, 100, H, "An ambitious ruler with a skilled spymaster forges a claim in an epoch (%)")
    fabricated_claim: int = rule(50, 0, 100, H, "Strength of a forged claim made by a fully skilled spymaster")


@dataclass(frozen=True)
class OathsRules(Spanned):
    fealty_on_office: int = rule(1, 0, 1, H, "Office holders swear fealty to the ruler (1 yes)")
    vengeance_chance: int = rule(30, 0, 100, H, "A mortal whose kin was slain swears vengeance (%)")
    protection_chance: int = rule(20, 0, 100, H, "Chance a sworn warrior swears to protect the one they serve (%)")
    vow_chance: int = rule(15, 0, 100, H, "A mortal whose life calls for a vow of service, poverty, peace, fidelity or secrecy swears it in an epoch (%)")
    poverty_wealth: int = rule(30, 0, 100, H, "Wealth above which a vow of poverty is broken")
    kinship_chance: int = rule(10, 0, 100, H, "Companions in arms swear sworn kinship (%)")
    deadline_years: int = span(3, 1, 2500, H, "Years a vengeance or pilgrimage oath gives the swearer")
    witness_chance: int = rule(40, 0, 100, H, "A god of oaths witnesses a sworn oath (%)")
    essence_per_kept: int = rule(2, 0, 1000, H, "Essence an oath god gains per oath kept in its sight")
    honour_loss: int = rule(20, 0, 100, H, "Importance an oathbreaker loses")
    wrath_relation: int = rule(15, 0, 100, H, "Relation the witnessing god's faithful lose with the oathbreaker")
    breach_relation: int = rule(25, 0, 100, H, "Relation the betrayed party loses with the oathbreaker")
    testimony_weight_pct: int = rule(30, 0, 100, H, "How much more sworn testimony counts in a case (%)")
    wrath_curse_chance: int = rule(40, 0, 100, H, "The witnessing god curses an oathbreaker (%)")
    wrath_essence: int = rule(2, 0, 1000, H, "Essence a god takes in wrath from a broken oath sworn before it")
    celibacy_chance: int = rule(30, 0, 100, H, "A priest of a celibate faith swears celibacy in an epoch (%)")
    pilgrimage_chance: int = rule(10, 0, 100, H, "A devout mortal of a pilgrim faith swears a pilgrimage in an epoch (%)")
    silence_on_office: int = rule(1, 0, 1, H, "A spymaster swears silence on taking office (1 yes)")
    fine: int = rule(10, 0, 10000, H, "Coin an oathbreaker pays when the oath's penalty is a fine")
    shame: int = rule(15, 0, 100, H, "Honour an oathbreaker loses on top of the rest when the oath's penalty is shame")
    curse_fortune: int = rule(15, 0, 100, H, "Fortune an oathbreaker loses when the oath's penalty is a curse")
    witness_relation: int = rule(15, 0, 100, H, "Relation a person or body that witnessed an oath gains when it is kept or loses when it is broken")
    release_friendship: int = rule(60, 0, 100, H, "Friendship toward the swearer at which the one an oath was sworn to may release it")
    release_chance: int = rule(10, 0, 100, H, "A recipient that close releases the oath in an epoch (%)")

    @property
    def deadline_epochs(self) -> int:
        return self.epochs(self.deadline_years)


@dataclass(frozen=True)
class TreatiesRules(Spanned):
    truce_years: int = span(2, 1, 2500, P, "Years a truce holds")
    alliance_years: int = span(20, 1, 2500, P, "Years an alliance holds before it must be renewed")
    trade_years: int = span(10, 1, 2500, P, "Years a trade pact holds")
    renew_relation: int = rule(30, -100, 100, P, "Relation at which parties renew an expiring treaty")
    call_to_arms_chance: int = rule(80, 0, 100, P, "An ally answers a call to arms (%)")
    refuse_relation_loss: int = rule(20, 0, 100, P, "Relation lost by an ally who refuses the call")
    guarantor_chance: int = rule(60, 0, 100, P, "A guarantor joins against the breaker (%)")
    breach_infamy: int = rule(15, 0, 100, P, "Infamy a treaty breaker's ruler gains")
    breach_honour: int = rule(15, 0, 100, P, "Honour a treaty breaker's ruler loses")
    breach_relation: int = rule(15, 0, 100, P, "Relation the betrayed parties lose with a treaty breaker")
    kept_memory: int = rule(5, 0, 100, P, "Good memory per epoch a kept treaty leaves between its parties")
    mediator_standing: int = rule(5, 0, 50, P, "Trust a mediator gains from the parties when a treaty it brokered holds, and loses when it breaks")
    suspension_trust_loss: int = rule(10, 0, 100, P, "Trust the other parties lose in a realm that suspends a treaty, short of a breach")
    unpaid_grace_years: int = span(1, 0, 2500, P, "Years a tribute may go unpaid before the treaty is broken")
    realm_tribute_scale: int = rule(10, 0, 1000, P, "Treasury moved per point of tribute between two realms")
    interworld_relation: int = rule(2, 0, 100, P, "Relation a treaty of the worlds adds between its parties each epoch")
    interworld_prosperity: int = rule(1, 0, 100, P, "Prosperity a treaty of the worlds adds to its parties each epoch")
    weak_overlord_stability: int = rule(35, 0, 100, P, "Stability below which an overlord counts as weak to its vassals")
    vassal_revolt_strength_pct: int = rule(80, 0, 500, P, "Vassal strength against its overlord at which it dares rise (%)")
    revolt_loyalty: int = rule(30, 0, 100, P, "Loyalty below which a vassal may revolt or seek another lord")
    switch_chance: int = rule(30, 0, 100, P, "A disloyal vassal with a better patron changes overlord in an epoch (%)")
    vassal_revolt_chance: int = rule(25, 0, 100, P, "A disloyal vassal rises against a weak overlord in an epoch (%)")
    hegemon_war_pct: int = rule(130, 0, 500, P, "War appetite of a hegemon realm against its neighbours (%)")
    great_war_pct: int = rule(110, 0, 500, P, "War appetite of a great power (%)")
    minor_war_pct: int = rule(90, 0, 500, P, "War appetite of a minor power (%)")
    client_war_pct: int = rule(50, 0, 500, P, "War appetite of a client realm (%)")
    balance_alliance_pct: int = rule(150, 0, 500, P, "Alliance appetite of realms that live beside a hegemon (%)")
    outer_pact_cap: int = rule(5, 0, 100000, P, "Most pacts with cults, beasts or foreign gods of each kind sealed in an epoch (base)")
    outer_pact_cap_realm_divisor: int = rule(2, 0, 100000, P, "Outer pact cap grows by 1 for every this many realms (0: fixed)")
    accept_relation: int = rule(20, -100, 100, P, "Relation toward the proposer at which a party accepts an offered treaty")
    proposal_years: int = span(1, 1, 2500, P, "Years an offered treaty waits before it is turned down")
    hostage_years: int = span(5, 1, 2500, P, "Years a hostage stays with the other party")
    wergild_value: int = rule(30, 0, 100000, P, "Wealth a wergild clause transfers")
    marriage_treaty_years: int = span(30, 1, 25000, P, "Years a marriage pact holds")

    @property
    def truce_epochs(self) -> int:
        return self.epochs(self.truce_years)

    @property
    def alliance_epochs(self) -> int:
        return self.epochs(self.alliance_years)

    @property
    def trade_epochs(self) -> int:
        return self.epochs(self.trade_years)

    @property
    def unpaid_grace(self) -> int:
        return self.epochs(self.unpaid_grace_years)

    @property
    def proposal_epochs(self) -> int:
        return self.epochs(self.proposal_years)

    @property
    def hostage_epochs(self) -> int:
        return self.epochs(self.hostage_years)

    @property
    def marriage_treaty_epochs(self) -> int:
        return self.epochs(self.marriage_treaty_years)

    isolated_war_pct: int = rule(5, 0, 100, P, "Chance a polity that stands apart from all is drawn into a war of its region (%)")
    accord_relation: int = rule(30, -100, 100, P, "Regard two realms of one world need before they fix their borders by accord")
    aid_relation: int = rule(50, -100, 100, P, "Regard two realms need before they pledge each other aid in disaster")
    accord_pct: int = rule(10, 0, 100, P, "Chance each epoch two realms that regard each other well enough sign an accord they lack (%)")
    border_accord_regard: int = rule(3, 0, 100, P, "Regard two realms gain each epoch their borders stay fixed by accord")
    aid_struck_prosperity: int = rule(25, 0, 100, P, "Prosperity below which a realm counts as struck and its pledged partner sends aid")
    aid_prosperity: int = rule(5, 0, 100, P, "Prosperity a partner sends a struck realm each epoch under a pact of mutual aid")
    shared_water_regard: int = rule(2, 0, 100, P, "Regard parties sharing a river by treaty gain each epoch")


@dataclass(frozen=True)
class RealmTierRules:
    territory_per_tier: int = rule(5, 1, 1000, P, "Regions a realm must hold for each tier of territory")
    administration_per_tier: int = rule(15, 1, 10000, P, "Administration a realm needs for each tier")
    knowledge_tier_level: int = rule(3, 1, 100, P, "Writing level that adds a tier")
    worlds_tier: int = rule(1, 0, 10, P, "Tiers a realm gains for each world beyond its first")
    rise_margin: int = rule(1, 0, 10, P, "Points above the next tier a realm needs before it rises (hysteresis)")
    decline_epochs: int = rule(2, 1, 100, P, "Epochs below its tier before a realm declines")
    standing_army: int = rule(2, 0, 20, P, "Tier a realm needs to keep a standing army")
    embassies: int = rule(2, 0, 20, P, "Tier a realm needs to send ambassadors and keep embassies")
    coinage: int = rule(1, 0, 20, P, "Tier a realm needs to strike its own coin")
    interworld: int = rule(4, 0, 20, P, "Tier a realm needs for a presence on other worlds")
    provinces: int = rule(2, 0, 20, P, "Tier a realm needs to group its lands into provinces")
