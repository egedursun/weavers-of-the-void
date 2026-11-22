from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class MarketsRules:
    district_merchant_pct: int = rule(3, 0, 100, G, "Merchant share at which a community raises a market district (%)")
    district_chance: int = rule(25, 0, 100, G, "A community ready for a market district raises one (% per epoch)")
    demand_epochs_pct: int = rule(150, 0, 1000, G, "Stock a market wants to hold before a good counts as plentiful (% of an epoch's need)")
    elasticity_pct: int = rule(60, 0, 300, G, "How strongly prices answer the gap between stock and need (%)")
    price_floor_pct: int = rule(25, 1, 100, G, "Lowest price a good can fall to (% of its base price)")
    price_cap_pct: int = rule(2000, 100, 10000, G, "Highest price a good can climb to (% of its base price)")
    transport_cost_pct_per_hop: int = rule(4, 0, 100, G, "Price added to carried goods per region crossed (%)")
    danger_cost_pct: int = rule(30, 0, 200, G, "Price added to carried goods at the most dangerous route (% of the danger)")
    seller_wealth_per_value: int = rule(3, 0, 100, G, "Prosperity or wealth a selling market gains per thousand of value sold")
    rarity_price_pct: int = rule(60, 0, 300, G, "Price added to goods for each point their material's rarity stands above the middle (% of the point)")
    value_price_pct: int = rule(40, 0, 300, G, "Price added to goods for each point their material's base value stands above the middle (% of the point)")


@dataclass(frozen=True)
class MoneyRules:
    mint_ore_units: int = rule(5, 1, 100000, G, "Coin metal each level of an issuer's mint strikes in an epoch (an issuer with no mint strikes as one level)")
    coins_per_unit: int = rule(100, 1, 100000, G, "Coins struck from one unit of coin metal at full purity")
    start_purity: int = rule(90, 0, 100, G, "Purity of a new currency")
    start_trust: int = rule(70, 0, 100, G, "Trust in a new currency")
    trust_drift_pct: int = rule(20, 0, 100, G, "Share of the gap between trust and purity closed each epoch (%)")
    debase_step: int = rule(15, 0, 100, G, "Purity taken out of a coin when it is debased")
    debase_chance: int = rule(40, 0, 100, G, "A poor issuer at war debases its coin (% per epoch)")
    debase_wealth_below: int = rule(30, 0, 100, G, "Wealth or prosperity below which an issuer is tempted to debase")
    debase_treasury_gain: int = rule(10, 0, 100, G, "Wealth an issuer gains at once by debasing")
    debase_trust_loss: int = rule(20, 0, 100, G, "Trust lost by a debased coin")
    debase_merchant_loss: int = rule(10, 0, 100, G, "Merchant satisfaction lost where a debased coin is used")
    inflation_pct: int = rule(60, 0, 300, G, "How strongly a coin's lost purity and trust raise prices where it is used (%)")
    trust_trade_pct: int = rule(50, 0, 100, G, "Trade kept with a coin no one trusts (%)")
    counterfeit_chance: int = rule(6, 0, 100, G, "Chance each epoch a currency least trusted and easiest to copy is counterfeited, before its form's share (%)")
    counterfeit_trust_loss: int = rule(8, 0, 100, G, "Trust a counterfeited currency loses")
    intrusion_chance: int = rule(5, 0, 100, G, "Chance each epoch network or energy money is broken into (%)")
    intrusion_supply_pct: int = rule(10, 0, 100, G, "Share of the supply of network or energy money lost to a break-in (%)")
    reform_chance: int = rule(30, 0, 100, G, "Chance each epoch an issuer that knows the technique of a newer form of money moves its currency to it (%)")
    issue_units: int = rule(
        200, 0, 100000, G, "Money an issuer of a currency not made of metal adds to its supply each epoch, per thousand of its people (at least one thousand)"
    )
    beast_hoard_chance: int = rule(40, 0, 100, G, "A slain beast leaves a hoard that the hero's people carry home to market (%)")
    hoard_supply_pct: int = rule(30, 0, 1000, G, "Coin supply a hoard adds when it floods a market (% of the hoard)")
    hoard_luxury_units: int = rule(40, 0, 100000, G, "Luxuries a looted hoard pours into the market of the one who took it")
    temple_hoard_units: int = rule(30, 0, 100000, G, "Luxuries a sacked temple pours into the market of the army that took it, before its material's worth")
    temple_worth_pct: int = rule(100, 0, 500, G, "How strongly a temple's material rarity and value enlarge its looted hoard (%)")


@dataclass(frozen=True)
class TradeRoutesRules(Spanned):
    formation_years: int = span(10, 1, 2500, G, "Years of steady traffic between two markets before the way becomes a named route")
    decay_years: int = span(10, 1, 2500, G, "Years without traffic after which a route falls out of use")
    contact_hops: int = rule(3, 0, 100, G, "Regions merchants will cross to reach a market they have no road to and no trade bond with")
    found_cap: int = rule(6, 0, 100000, G, "Most new ways merchants open between markets in an epoch, before the number of markets adds more")
    found_markets_per_extra: int = rule(4, 0, 100000, G, "Markets that let merchants open one more new way in an epoch (0 for none)")
    market_route_cap: int = rule(5, 1, 10000, G, "Most routes that meet at one market of few people")
    market_route_people_per_extra: int = rule(10000, 0, 100000000, G, "People of a market that let one more route meet there (0 for none)")
    capacity_base: int = rule(600, 0, 100000, G, "Units of goods a bare path carries in an epoch")
    capacity_per_road: int = rule(400, 0, 100000, G, "Units added per road along the way")
    capacity_per_bridge: int = rule(250, 0, 100000, G, "Units added per bridge along the way")
    capacity_per_harbour: int = rule(600, 0, 100000, G, "Units added per harbour at the ends of a sea or river route")
    capacity_per_ship: int = rule(300, 0, 100000, G, "Units a ship of either end adds to a sea route")
    capacity_per_market: int = rule(200, 0, 100000, G, "Units a working market structure halfway along the way adds as a waystation")
    capacity_per_thousand_people: int = rule(100, 0, 100000, G, "Units each thousand people at the two ends add to what a route carries in an epoch")
    capacity_cap: int = rule(5000000, 1, 1000000000, G, "Most units of goods a route can carry in an epoch")
    sea_length_pct: int = rule(50, 1, 100, G, "Length of a sea crossing compared with walking the same regions (%)")
    river_length_pct: int = rule(70, 1, 100, G, "Length of a river voyage compared with walking the same regions (%)")
    danger_loss_pct: int = rule(40, 0, 100, G, "Share of the cargo lost on the most dangerous route (% at danger 100)")
    sea_season_pct: int = rule(30, 0, 100, G, "Cargo kept back by storms in the worst sailing season of a sea route (%)")
    shipwreck_chance: int = rule(15, 0, 100, G, "Losses at sea come with a shipwreck that drowns sailors (%)")
    shipwreck_crew: int = rule(40, 0, 100000, G, "Sailors drowned in a shipwreck")
    bandit_share_pct: int = rule(50, 0, 100, G, "Share of a route's losses that ends in the hands of bandits (%)")
    renown_per_epoch: int = rule(2, 0, 100, G, "Renown a busy route gains each epoch")
    renown_volume: int = rule(1500, 1, 100000, G, "Units carried in an epoch that count as busy for renown and culture")
    legend_renown: int = rule(70, 0, 100, G, "Renown at which a route passes into legend")
    culture_per_epoch: int = rule(3, 0, 100, G, "Culture a busy route carries more each epoch")
    diffusion_pct: int = rule(
        100, 0, 500, G, "How strongly route traffic carries knowledge, culture, words, faith and disease (% of the old bond weight per busy route)"
    )
    missionary_pct: int = rule(
        4, 0, 100, G, "Chance missionaries travelling with a route's traders win over the community at the other end, before the route's weight (%)"
    )
    blockade_merchant_loss: int = rule(12, 0, 100, G, "Merchant satisfaction lost at either end of a blockaded route")
    blockade_peace_push: int = rule(8, 0, 100, G, "Peace chance a merchant guild adds when a war blockades its routes (%)")
    route_war_chance: int = rule(6, 0, 100, G, "A strong merchant power goes to war over a blockaded or overtaxed route (% per epoch)")

    @property
    def formation_epochs(self) -> int:
        return self.epochs(self.formation_years)

    @property
    def decay_epochs(self) -> int:
        return self.epochs(self.decay_years)


@dataclass(frozen=True)
class BankingRules(Spanned):
    bank_wealth: int = rule(55, 0, 100, G, "Wealth a merchant guild needs to lend")
    lend_chance: int = rule(25, 0, 100, G, "A rich guild lends to a poor community at war (% per epoch)")
    borrower_wealth_below: int = rule(40, 0, 100, G, "Wealth or prosperity below which a community at war borrows")
    principal: int = rule(15, 1, 100, G, "Wealth a war loan brings the borrower")
    interest_pct: int = rule(20, 0, 100, G, "Interest on a war loan")
    risk_interest_pct: int = rule(15, 0, 100, G, "Extra interest charged to a borrower that has defaulted before")
    term_years: int = span(5, 1, 2500, G, "Years before a war loan falls due")
    repay_pct: int = rule(40, 0, 100, G, "Share of what is owed a borrower pays each epoch while it can (%)")
    repay_wealth_floor: int = rule(20, 0, 100, G, "Wealth a borrower keeps before it pays its lender")
    default_relation_loss: int = rule(25, 0, 100, G, "Relation a lender loses with a borrower that defaults")
    default_bank_loss: int = rule(15, 0, 100, G, "Wealth a bank loses when a loan defaults")
    collapse_wealth: int = rule(10, 0, 100, G, "Wealth below which a bank that has lost loans collapses")
    collapse_merchant_loss: int = rule(20, 0, 100, G, "Merchant satisfaction lost in a community whose bank collapses")
    polity_lend_chance: int = rule(30, 0, 100, G, "A rich guild lends to an indebted realm or a realm at war with an empty treasury (% per epoch)")
    polity_treasury_below: int = rule(40, 0, 100000, G, "Treasury below which a realm at war or in debt asks a bank for a loan")
    polity_principal: int = rule(60, 1, 100000, G, "Treasury a bank lends a realm")
    polity_repay_pct: int = rule(35, 0, 100, G, "Share of what a realm owes that it pays its bank each epoch while its treasury allows (%)")
    polity_default_debt_pct: int = rule(100, 0, 500, G, "Share of an unpaid realm loan that becomes the realm's standing debt on default (%)")
    polity_bank_wealth_per_silver: int = rule(4, 0, 100, G, "Wealth a bank gains or loses per hundred of treasury lent to or repaid by a realm")
    credit_shy_years: int = span(10, 0, 2500, G, "Years a bank refuses a borrower after it defaulted, unless the bank is its own")

    @property
    def term_epochs(self) -> int:
        return self.epochs(self.term_years)

    @property
    def credit_shy_epochs(self) -> int:
        return self.epochs(self.credit_shy_years)


@dataclass(frozen=True)
class TollsRules:
    default_rate_pct: int = rule(5, 0, 100, G, "Toll a region's master takes from the value of goods crossing it (%)")
    greed_rate_pct: int = rule(10, 0, 100, G, "Extra toll taken by a greedy master (%)")
    divert_total_pct: int = rule(30, 0, 100, G, "Total toll along a route at which merchants seek another way (%)")
    revenue_wealth_per_value: int = rule(5, 0, 100, G, "Prosperity or wealth a toll-taker gains per thousand of tolls")
    polity_share_pct: int = rule(40, 0, 100, G, "Share of a member's tolls that goes to the treasury of its realm (%)")
    territory_control_pct: int = rule(50, 0, 100, G, "Control a realm needs over a land to take the tolls on it itself")
