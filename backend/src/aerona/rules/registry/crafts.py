from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

E = RuleGroup.ECONOMY
M = RuleGroup.MARKETS_AND_MONEY
B = RuleGroup.BODY
V = RuleGroup.CIVILIZATION
D = RuleGroup.THE_BEYOND
P = RuleGroup.PHENOMENA


@dataclass(frozen=True)
class GroundRules:
    marine_hunt_chance: int = rule(15, 0, 100, E, "Chance a fishing ground is first read as a hunt of great sea beasts (%)")
    war_at: int = rule(-40, -100, 0, E, "Opinion of those who work its waters at or below which the owner of a ground may go to war over them")
    war_pct: int = rule(10, 0, 100, E, "Chance each epoch that the owner of a ground goes to war on those it holds in such contempt for working it (%)")
    fowling_chance: int = rule(40, 0, 100, E, "Chance a gathering ground is first read as fowling rather than trapping (%)")
    owned_chance: int = rule(20, 0, 100, E, "Chance a ground is first held as owned water or land by the realm or community that works it (%)")
    lines_pct: int = rule(80, 0, 400, E, "Catch with lines (% of the plain catch)")
    nets_pct: int = rule(120, 0, 400, E, "Catch with nets (% of the plain catch)")
    weirs_pct: int = rule(110, 0, 400, E, "Catch with weirs (% of the plain catch)")
    traps_pct: int = rule(100, 0, 400, E, "Catch with traps (% of the plain catch)")
    snares_pct: int = rule(90, 0, 400, E, "Catch with snares (% of the plain catch)")
    harpoons_pct: int = rule(150, 0, 400, E, "Catch with harpoons (% of the plain catch)")
    lines_depletion: int = rule(10, 0, 100, E, "How hard lines press the stock they take from, slowing its regrowth (%)")
    nets_depletion: int = rule(30, 0, 100, E, "How hard nets press the stock they take from, slowing its regrowth (%)")
    weirs_depletion: int = rule(25, 0, 100, E, "How hard weirs press the stock they take from, slowing its regrowth (%)")
    traps_depletion: int = rule(20, 0, 100, E, "How hard traps press the stock they take from, slowing its regrowth (%)")
    snares_depletion: int = rule(20, 0, 100, E, "How hard snares press the stock they take from, slowing its regrowth (%)")
    harpoons_depletion: int = rule(15, 0, 100, E, "How hard harpoons press the stock they take from, slowing its regrowth (%)")
    missiles_pct: int = rule(110, 0, 400, E, "Catch with missiles (% of the plain catch)")
    missiles_depletion: int = rule(20, 0, 100, E, "How hard missiles press the stock they take from, slowing its regrowth (%)")
    trawls_pct: int = rule(180, 0, 400, E, "Catch with trawls (% of the plain catch)")
    trawls_depletion: int = rule(70, 0, 100, E, "How hard trawls press the stock they take from, slowing its regrowth (%)")
    poison_pct: int = rule(160, 0, 400, E, "Catch with poison (% of the plain catch)")
    poison_depletion: int = rule(60, 0, 100, E, "How hard poison press the stock they take from, slowing its regrowth (%)")
    hunting_animals_pct: int = rule(130, 0, 400, E, "Catch with hunting animals (% of the plain catch)")
    hunting_animals_depletion: int = rule(15, 0, 100, E, "How hard hunting animals press the stock they take from, slowing its regrowth (%)")
    game_hunt_rate: int = rule(
        10,
        0,
        100,
        E,
        "Meat a hunt of large game yields the towns of its land each epoch at full stock, shared among them; a game reserve leaves them only what is poached",
    )
    shore_rate: int = rule(8, 0, 100, E, "Food gathering on a shore yields each epoch at full stock")
    shore_depletion: int = rule(3, 0, 100, E, "Stock gathering wears from a shore each epoch at full effort")
    diving_rate: int = rule(5, 0, 100, E, "Luxuries divers bring up each epoch at full stock")
    diving_depletion: int = rule(4, 0, 100, E, "Stock diving wears from the beds below each epoch at full effort")
    diving_death_pct: int = rule(3, 0, 100, E, "Chance a diver of a people that cannot live under water is lost in an epoch (%)")
    pond_yield: int = rule(15, 0, 100, E, "Fish a kept fish pond yields each epoch")
    pond_feed: int = rule(5, 0, 100, E, "Grain a fish pond eats each epoch")
    pond_build_pct: int = rule(5, 0, 100, E, "Chance a river town with grain to spare builds fish ponds in an epoch (%)")
    pond_flood_scar: int = rule(30, 0, 100, E, "Depth of flooding that ruins the fish ponds of a land")
    ground_regrow: int = rule(5, 0, 100, E, "Stock a worked shore, bed or pond regains each epoch")
    trawl_bed_harm: int = rule(10, 0, 100, E, "Erosion trawls leave on the bed of the waters they drag")
    poison_sickness_pct: int = rule(5, 0, 100, E, "Disease load a land gains each epoch from catch taken with poison")
    effort_pct: int = rule(100, 0, 400, E, "Scale of the effort on a ground: at full effort the catch grows by this share (%)")
    recover_at: int = rule(40, 0, 100, E, "Share of its first stock a collapsed ground must regrow to before it can be worked again (%)")
    collapsed_regrowth_pct: int = rule(30, 0, 100, E, "Regrowth of a collapsed ground (% of its usual regrowth)")
    marine_risk: int = rule(15, 0, 100, E, "Chance a hunt of great sea beasts hurts one of its hunters each epoch (%)")
    marine_harm: int = rule(30, 0, 100, E, "Harm the great sea beast deals the hunter it hurts")
    poach_opinion: int = rule(10, 0, 100, E, "Opinion an owner loses of a community that works its owned ground")


@dataclass(frozen=True)
class ChemistryRules:
    found_chance: int = rule(25, 0, 100, E, "Chance each epoch a town with the craft and the workshop founds a chemical works it lacks (%)")
    output_gain: int = rule(5, 0, 100, E, "Output a working chemical works gains each epoch toward its full output")
    input_per_output: int = rule(10, 1, 100, E, "Output points a works turns from one unit of its raw goods")
    yield_per_output: int = rule(10, 1, 100, E, "Output points that yield one unit of its product")
    soap_disease: int = rule(5, 0, 100, E, "Disease load soap takes off its region at full output")
    fertiliser_yield_pct: int = rule(15, 0, 100, E, "Farm yield fertiliser adds to its town at full output (%)")
    explosive_mining_pct: int = rule(20, 0, 100, E, "Mining output explosives add to their town at full output (%)")
    accident_harm: int = rule(25, 0, 100, E, "Harm an accident at a chemical works deals a worker")
    pollution_pct: int = rule(5, 0, 100, E, "Pollution a chemical works adds to its region each epoch at full output (% of its own pollution)")


@dataclass(frozen=True)
class InsuranceRules(Spanned):
    found_chance: int = rule(20, 0, 100, M, "Chance each epoch a guild or company of a people that knows insurance begins to insure (%)")
    seed_pool: int = rule(30, 0, 100000, M, "Means an insurer first holds, before its members are counted")
    seed_pool_per_member: int = rule(3, 0, 10000, M, "More means an insurer first holds for each of its members")
    policies_per_epoch: int = rule(3, 0, 1000, M, "Policies an insurer writes each year")
    sum_insured: int = rule(20, 0, 1000, M, "Means a policy pays at most on a loss")
    cargo_payout_pct: int = rule(60, 0, 100, M, "Share of the value lost on a road an insured cargo is paid back (%)")
    life_payout: int = rule(5, 0, 100, M, "Wealth an insured life pays to its household when it ends")
    house_payout: int = rule(10, 0, 100, M, "Wealth an insured house pays its town when a disaster strikes it")
    belief_step: int = rule(5, 0, 100, M, "Change in an insurer's belief about risk after an epoch of claims or none")
    moral_hazard_pct: int = rule(40, 0, 100, M, "Share of the cost of danger an insured merchant stops counting when choosing a road (%)")
    ruin_opinion: int = rule(10, 0, 100, M, "Opinion holders lose of an insurer that is ruined")


@dataclass(frozen=True)
class RightsRules:
    seed_per_epoch: int = rule(
        0, 0, 100000, V, "Most works and rites each epoch that become the held right of their maker's house or maker (0 no limit, each work once)"
    )
    infringe_chance: int = rule(10, 0, 100, V, "Chance each epoch someone of another clan performs or copies a held right (%)")
    insult_opinion: int = rule(15, 0, 100, V, "Opinion a holder loses of one who performs or copies its right")
    licence_fee: int = rule(2, 0, 100, V, "Wealth a licensee pays the holder each epoch")
    steal_chance: int = rule(20, 0, 100, V, "Chance one who copies a design, mark or privilege without leave claims it as their own (%)")
    buy_price: int = rule(10, 0, 100, V, "Wealth a licensee pays a holder in want to buy a right outright")


@dataclass(frozen=True)
class AidRules:
    spectacles_age_pct: int = rule(60, 0, 100, B, "Share of its lifespan from which a mortal of a people with lenses takes spectacles (%)")
    fit_chance: int = rule(20, 0, 100, B, "Chance each epoch a mortal who needs an aid that its people can make receives it (%)")
    hearing_restore_pct: int = rule(70, 0, 100, B, "Hearing a hearing horn restores at full quality (%)")
    cane_aid_pct: int = rule(40, 0, 100, B, "Walking a cane restores at full quality (%)")
    magnifier_craft_pct: int = rule(15, 0, 100, B, "Fine craft a magnifier adds at full quality (%)")
    telescope_xp: int = rule(3, 0, 100, B, "Astronomy practice a telescope gives its holder each epoch")
    telescope_forecast_pct: int = rule(
        40, 0, 100, B, "Error a scholar with a telescope of full quality no longer makes forecasting the turn of a long season (%)"
    )


@dataclass(frozen=True)
class ClockRules:
    build_chance: int = rule(10, 0, 100, V, "Chance each epoch a town whose people can keep time sets up a public clock (%)")
    output_pct: int = rule(10, 0, 100, V, "Output a public clock adds to its town at full precision (%)")
    discipline_unrest: int = rule(3, 0, 100, V, "Unrest the labour discipline of a public clock brings its town at full precision")
    command_pct: int = rule(15, 0, 100, V, "Levy a precise public clock adds to the town that raises an army, at full precision (%)")
    navigation_pct: int = rule(15, 0, 100, V, "Sea danger a precise clock in a port takes off its sea roads at full precision (%)")


@dataclass(frozen=True)
class GameRules:
    invent_chance: int = rule(15, 0, 100, V, "Chance each epoch a people without a game invents one (%)")
    strategy_xp: int = rule(2, 0, 100, V, "Practice of its skill a game gives each noble and officer of its players each epoch, less the part left to chance")
    gamble_loss: int = rule(2, 0, 100, V, "Prosperity a game of full chance and full betting takes from each town of its players each epoch at full strength")
    gamble_crime: int = rule(2, 0, 100, V, "Crime a game of full chance and full betting adds to each town of its players each epoch at full strength")
    ball_contentment: int = rule(2, 0, 100, V, "Unrest a game watched by full crowds eases in each town of its players each epoch at full strength")
    violence_pct: int = rule(50, 0, 300, V, "Extra chance of an everyday mishap for the players of a game of full violence, at full strength (%)")


@dataclass(frozen=True)
class NumeracyRules:
    milestone_chance: int = rule(5, 0, 100, V, "Chance each epoch a people that knows logic finds the zero or positional notation (%)")
    numeracy_gain: int = rule(2, 0, 100, V, "Numeracy a people with schools or scribes gains each epoch")
    tax_pct: int = rule(15, 0, 100, V, "Taxes full numeracy adds to a realm of the people (%)")
    build_pct: int = rule(10, 0, 100, V, "Building quality full numeracy adds (%)")
    trade_pct: int = rule(10, 0, 100, V, "Price gap a merchant of a fully numerate people still trades on (% less than the usual)")
    milestone_pct: int = rule(10, 0, 100, V, "Numeracy the zero and positional notation each add at once")
    research_pct: int = rule(10, 0, 100, V, "Research the zero and positional notation each add to astronomy, architecture, trade and seafaring (%)")
    forecast_pct: int = rule(40, 0, 100, V, "Error a fully numerate people's scholars no longer make when they forecast the turn of a long season (%)")


@dataclass(frozen=True)
class AffinityRules:
    seed_chance: int = rule(30, 0, 100, D, "Chance a precious or exotic material of a world carries a magical affinity when first read (%)")
    rite_pct: int = rule(30, 0, 100, D, "Strength an affinity at full power adds to a rite of its school worked near the material (%)")
    mining_pct: int = rule(20, 0, 100, D, "Value an affinity at full power adds to mining its material (%)")
    consumed_gift_pct: int = rule(100, 0, 400, D, "Share of a caster's gift added to the boost of a material that is consumed (%)")


@dataclass(frozen=True)
class SympathyRules:
    take_chance: int = rule(10, 0, 100, D, "Chance each epoch a caster near the one it means to curse takes something of it (%)")
    rite_pct: int = rule(50, 0, 100, D, "Strength a link at full strength adds to a rite through it (%)")
    decay: int = rule(5, 0, 100, D, "Strength a link loses each epoch")
    burn_chance: int = rule(20, 0, 100, D, "Chance each epoch a cursed mortal burns what could link to it (%)")


@dataclass(frozen=True)
class EmotionSpiritRules(Spanned):
    spawn_density: int = rule(60, 0, 100, P, "Magic of a region from which strong shared feeling takes the shape of spirits")
    spawn_from: int = rule(300, 0, 100000, P, "Shared feeling of one kind a region must hold in an epoch before a spirit takes shape")
    lifetime_years: int = span(30, 1, 1250, P, "Years an emotion spirit lasts unless bound")
    amplify: int = rule(10, 0, 100, P, "Intensity a spirit adds to the matching feeling of the mortals of its region each epoch")
    feed_pct: int = rule(50, 0, 400, P, "Share of a spirit's strength fed to the gods whose faithful live in its region (%)")
    reagent_yield: int = rule(2, 0, 100, P, "Magical reagents a bound spirit yields its binder each epoch")

    @property
    def lifetime(self) -> int:
        return self.epochs(self.lifetime_years)
