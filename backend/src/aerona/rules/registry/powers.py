from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

P = RuleGroup.PHENOMENA
H = RuleGroup.HEROES_AND_MORTALS
K = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class PowerSourceRules:
    soul_draw_beings: int = rule(3, 1, 50, P, "Most beings near its user a source drawn from souls takes life from in one working")
    soul_draw_pct: int = rule(100, 0, 500, P, "Share of a soul cost taken from the beings near the user, split between them (%)")
    density_floor: int = rule(15, 0, 100, P, "Density below which a land is overdrawn and suffers the source's depletion")
    locus_pct: int = rule(30, 0, 200, P, "Most a source drawn from feeling, dreams, story, bonds or made things moves a draw by its user's state (%)")
    sky_days: int = rule(28, 1, 1000, P, "Days of the sky cycle a tide of the sky follows")
    draw_per_strength: int = rule(3, 0, 100, P, "Density a draw takes from its land for each point of strength")
    rest_renewal: int = rule(10, 0, 100, P, "Density a source renewed by rest or time regains each epoch")
    season_renewal: int = rule(15, 0, 100, P, "Density a source renewed by the seasons or the sky regains each epoch at the height of its tide")
    worship_renewal: int = rule(1, 0, 100, P, "Density a source renewed by worship regains each epoch for each cult that tends it in the land")
    taking_renewal: int = rule(4, 0, 100, P, "Density a source renewed by taking regains for each user who drew on it this epoch")
    depletion_prosperity: int = rule(3, 0, 100, P, "Prosperity each town of an overdrawn land loses each epoch")
    interaction_pct: int = rule(30, 0, 100, P, "Share of an interaction's strength that lifts or lowers a draw where both sources are drawn (%)")
    tide_pct: int = rule(100, 0, 200, P, "Share of a tide's amplitude that moves draws and renewal (%)")
    discovery_chance: int = rule(5, 0, 100, P, "Chance each epoch a people living in a dense land comes to know a source it did not know")
    teaching_gain: int = rule(5, 0, 100, P, "Knowledge of a source a people gains each epoch from a neighbour who knows it better")
    knowledge_loss: int = rule(2, 0, 100, P, "Knowledge of a source a people loses each epoch it has no living user of it")
    hazard_scale_pct: int = rule(100, 0, 400, P, "Share of a hazard's weight rolled as its chance on each draw (%)")
    start_density: int = rule(50, 0, 100, P, "Density a land starts with for a source that reaches it")
    contention_draw: int = rule(2, 0, 50, P, "Density each further user strips from an overdrawn land as they race to draw before the others")
    contention_rivals: int = rule(6, 0, 100, P, "Most pairs of users of one overdrawn land who come to resent each other in an epoch")
    bought_price: int = rule(10, 0, 10000, P, "Coin in treasury a user pays the keepers of a source open to those who buy their way in, each time it draws")
    offering_renewal: int = rule(3, 0, 100, P, "Density a source renewed by offerings regains each epoch for each holy place in its land")


@dataclass(frozen=True)
class MagicSystemRules:
    spread_pct: int = rule(50, 0, 100, P, "Spread of outcomes in a system of no predictability (%)")
    oppose_pct: int = rule(20, 0, 100, P, "Strength a power loses in a contest against a user of an opposing system (%)")
    complement_pct: int = rule(15, 0, 100, P, "Strength a power gains against a user of a complementing system (%)")
    unheld_structure_pct: int = rule(
        50, 0, 100, P, "Strength a power keeps when what its system rests on is missing: its made thing, its giver or its bond (%)"
    )
    innate_bonus_pct: int = rule(10, 0, 100, P, "Strength a born power gains in a system of innate powers (%)")
    shared_discovery_pct: int = rule(50, 0, 100, P, "Share of a discovery in one system passed to a system of the same root (%)")
    drift: int = rule(2, 0, 100, P, "Largest change in a system's prevalence or predictability each epoch from its sources' density")
    theory_gain: int = rule(2, 0, 100, P, "Predictability a system gains each epoch from the theories of its users")
    overt_cost_unrest: int = rule(
        4, 0, 50, P, "Unrest the towns of a world gain each epoch from an overt system, scaled by how costly and how common its powers are"
    )


@dataclass(frozen=True)
class PowerRules:
    strain_per_use: int = rule(4, 0, 100, H, "Strain a use adds for each point of strength")
    range_strain: int = rule(1, 0, 100, H, "Strain a use adds for each hundred kilometres of reach")
    rest_recovery: int = rule(8, 0, 100, H, "Strain a power sheds each epoch at rest")
    harm_at_pct: int = rule(100, 1, 400, H, "Strain at which a use harms its user, as a share of the cap (%)")
    burnout_at_pct: int = rule(200, 1, 1000, H, "Strain at which a power burns out, as a share of the cap (%)")
    scar_hp: int = rule(6, 0, 100, H, "Harm a power pushed past its cap does to its user")
    hazard_stress: int = rule(15, 0, 100, H, "Stress a madness or dependency a source carries lays on its user")
    burnout_recovery_chance: int = rule(10, 0, 100, H, "Chance each epoch a burned-out power comes back")
    growth_chance: int = rule(10, 0, 100, H, "Chance a use past the cap that succeeds raises strength")
    control_gain: int = rule(2, 0, 100, H, "Control a power gains each epoch it is used or trained")
    misfire_below: int = rule(30, 0, 100, H, "Control below which a use can misfire")
    misfire_chance: int = rule(30, 0, 100, H, "Chance a use under that control misfires")
    emerge_chance: int = rule(8, 0, 100, H, "Chance each epoch a latent power with a trigger present emerges")
    wild_chance: int = rule(20, 0, 100, H, "Chance each epoch an emerging power of low control acts on its own")
    settle_chance: int = rule(20, 0, 100, H, "Chance each epoch an emerging power settles into an active one")
    restriction_cap_pct: int = rule(100, 0, 400, H, "Most strength a power's restrictions can add together (%)")
    secrets_per_strength: int = rule(20, 0, 100, H, "Secrets a reading of a mind finds for each point of strength, in hundredths")
    compulsion_at: int = rule(6, 1, 10, H, "Strength at which a power over the mind compels or edits rather than sways")
    copy_strength_pct: int = rule(60, 0, 100, H, "Share of the source's strength a copied power keeps (%)")
    pace_per_strength: int = rule(20, 0, 100, H, "Speed of mind a quickening or slowing moves for each point of strength")
    years_per_strength: int = rule(100, 0, 1000, H, "Years, in hundredths, an ageing or renewing adds or takes for each point of strength")
    span_epochs: int = rule(1, 1, 20, H, "Epochs an effect that lasts a span holds")
    use_chance: int = rule(30, 0, 100, H, "Chance each epoch an active power is used in its holder's life")
    fade_age_pct: int = rule(85, 0, 100, H, "Share of a lifespan past which powers fade with age (%)")
    gifted_latent_at: int = rule(60, 0, 100, H, "Gift aptitude at which a mortal carries a latent power")
    link_pct: int = rule(60, 0, 100, H, "Share of a linked partner's strength added to a joined use (%)")
    gestalt_members: int = rule(5, 2, 100, H, "Linked users at which a standing link becomes a gestalt")
    break_stress: int = rule(10, 0, 100, H, "Stress a broken link gives each member for each point of strength")
    foresight_blind: int = rule(10, 0, 100, H, "Certainty a foresight loses for each other seer with powers near")
    exposure_chance: int = rule(5, 0, 100, H, "Chance each epoch a mortal living in a land with a phenomenon or a dense source gains a power by exposure")
    grant_cost: int = rule(10, 0, 1000, H, "Essence a god spends to grant a power")
    device_pct: int = rule(30, 0, 100, H, "Share of strength a device of power adds or takes (%)")
    unit_strength_pct: int = rule(5, 0, 100, H, "Battle strength a unit of the gifted adds for each point of its users' strength (%)")
    dampener_pct: int = rule(40, 0, 100, H, "Share of the gifted's battle strength a unit of dampeners takes away (%)")
    siege_breach: int = rule(6, 1, 10, H, "Strength at which a power of force, earth or space can breach or cross walls")
    bloodline_chance: int = rule(50, 0, 100, H, "Chance a child of a line with a bloodline power inherits it by the line's rule")
    discipline_gain: int = rule(1, 0, 100, H, "Strength in tenths a power of discipline gains each epoch of training")
    transfer_loss_pct: int = rule(30, 0, 100, H, "Share of its strength a power loses when it is taken from one being into another (%)")
    memory_source_rate: int = rule(5, 0, 50, H, "Strength a power drawn from memory gains for each ten memories its holder's people keep, until its full sway")
    transfer_device_pct: int = rule(
        10, 0, 100, H, "Chance each epoch the holder of a device that moves powers takes a power from a gifted one in its place (%)"
    )
    store_recovery: int = rule(4, 0, 100, H, "Strain each device that stores power takes from its holder's powers each epoch")
    sleep_stress: int = rule(40, 0, 100, H, "Stress under which a dream of the night can wake a power that wakes in sleep")
    danger_hp_pct: int = rule(30, 0, 100, H, "Share of full health below which a near kin, friend or charge is in danger enough to wake a power (%)")
    hazard_years: int = rule(5, 0, 100, P, "Years a power that ages its user takes from it each time the hazard strikes")


@dataclass(frozen=True)
class PoweredSocietyRules:
    renown_per_use: int = rule(2, 0, 100, H, "Renown an overt use gains its user")
    infamy_per_harm: int = rule(3, 0, 100, H, "Infamy an overt use that harms gains its user")
    registry_detect: int = rule(20, 0, 100, H, "Chance each epoch a registry finds a latent gift in its realm")
    conscription_share: int = rule(20, 0, 100, H, "Share of registered users a conscripting realm sends into its armies (%)")
    attitude_shift: int = rule(10, 0, 100, H, "Weight of a memory of harm or protection by the gifted in a people's attitude")
    testing_finds: int = rule(30, 0, 100, H, "Chance a testing gathering finds each latent gift among its people")
    band_members: int = rule(3, 2, 100, H, "Users of powers in one realm at which they may form a band")
    band_chance: int = rule(10, 0, 100, H, "Chance each epoch such users form a band")
    law_adopt_chance: int = rule(10, 0, 100, H, "Chance each epoch a realm moved by a wild manifestation or fear changes its law of powers")
    hidden_fear: int = rule(5, 0, 100, H, "Weight each gifted one living under a false name adds to a people's fear of the gifted")
    registry_pull: int = rule(60, 0, 100, H, "Share of a realm's gifted on its registry at which a registering realm moves to conscript them")


@dataclass(frozen=True)
class ConcealmentRules(Spanned):
    overt_breach: int = rule(30, 0, 100, K, "Chance an overt use of power before witnesses breaches a truth about it")
    subtle_breach: int = rule(8, 0, 100, K, "Chance a subtle use breaches a truth about it")
    witness_breach: int = rule(5, 0, 100, K, "Chance each epoch a truth of presence is breached by its people living among others")
    accident_breach: int = rule(2, 0, 100, K, "Chance each epoch any kept truth slips out by accident, against its strength")
    hunt_harm: int = rule(10, 0, 100, K, "Harm a seeker who means to destroy the hidden does to them when it finds them")
    hush_money: int = rule(20, 0, 10000, K, "Coin a seeker who means to exploit a hidden truth wrings from its subject")
    seeker_breach_pct: int = rule(50, 0, 100, K, "Share of a seeker's progress added to the chance of a breach (%)")
    seeker_gain: int = rule(10, 0, 100, K, "Progress a seeker makes each epoch")
    spread_pct: int = rule(20, 0, 100, K, "Knowledge a breach adds to its population, before the keepers answer (%)")
    belief_pct: int = rule(50, 0, 100, K, "Share of new knowledge that is believed at full trust (%)")
    cover_cut_pct: int = rule(50, 0, 100, K, "Share of belief a cover story takes back after a breach (%)")
    memory_cut_pct: int = rule(60, 0, 100, K, "Share of the witnesses' knowledge memory removal takes back (%)")
    discredit_cut_pct: int = rule(30, 0, 100, K, "Share of belief discrediting takes back (%)")
    keeper_cost: int = rule(3, 0, 100, K, "Wealth points keepers spend for each answer to a breach")
    reveal_know: int = rule(60, 0, 100, K, "Knowledge at which a truth is revealed in a population")
    reveal_believe: int = rule(50, 0, 100, K, "Belief at which a truth is revealed in a population")
    fade_pct: int = rule(5, 0, 100, K, "Knowledge a truth no one speaks of loses each epoch")
    legend_after_years: int = span(100, 1, 25000, K, "Years without a breach after which a revealed truth turns to legend")
    sanity_harm: int = rule(5, 0, 100, K, "Stress a truth of full sanity cost gives each who learns it")
    strength_decay: int = rule(1, 0, 100, K, "Strength a truth loses each epoch its keepers do not tend it")
    tend_gain: int = rule(2, 0, 100, K, "Strength a truth gains each epoch its keepers tend it")
    hide_chance: int = rule(10, 0, 100, K, "Chance each epoch a persecuted gifted folk hides itself as a hidden truth")
    black_market_gain: int = rule(2, 0, 100, K, "Black market each town where hidden folk pass among the rest gains each epoch")

    @property
    def legend_after(self) -> int:
        return self.epochs(self.legend_after_years)

    children_breach: int = rule(
        4, 0, 100, K, "Chance each epoch a truth whose keepers or subject have young children is let slip by the children, against its strength"
    )
    dream_breach: int = rule(3, 0, 100, K, "Chance each epoch a truth breaks through dreams on a world whose laws make dreams real, against its strength")
    dig_breach: int = rule(15, 0, 100, K, "Chance each epoch an open dig in the land of a truth's subject brings it up, against its strength")
    relocate_at: int = rule(40, 0, 100, K, "Knowledge of a hidden place or presence at which its keepers move the hidden to a new refuge")
    relocate_cost: int = rule(10, 0, 100, K, "Wealth points keepers spend to move the hidden to a new refuge")
    bargain_cut_pct: int = rule(40, 0, 100, K, "Share of knowledge a go-between's bargain takes back by turning finders into keepers (%)")
    archivist_seek_pct: int = rule(50, 0, 200, K, "Added progress a seeker makes on a truth kept by archivists, whose records are its first target (%)")
    protected_seek_cut: int = rule(20, 0, 100, K, "Progress each seeker of a truth a people protects by law loses each epoch")
    bargained_trade: int = rule(3, 0, 100, K, "Prosperity the towns of a hidden people gain each epoch a population trades with them by open treaty")
    lineage_renown: int = rule(15, 0, 100, K, "Renown a mortal of a hidden line gains when its lineage is revealed")
    location_seek_chance: int = rule(5, 0, 100, K, "Chance each epoch a hidden place with no seekers draws one from its world")
    faith_initiates: int = rule(2, 0, 50, K, "Adherents of a faith that keeps a truth initiated into keeping it each epoch")
