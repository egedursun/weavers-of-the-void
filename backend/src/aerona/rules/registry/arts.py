from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.MARKETS_AND_MONEY
C = RuleGroup.CIVILIZATION
H = RuleGroup.HEROES_AND_MORTALS
P = RuleGroup.POLITY
K = RuleGroup.CREATURES
S = RuleGroup.SKY


@dataclass(frozen=True)
class ArtMarketRules:
    collector_chance: int = rule(20, 0, 100, M, "Chance each epoch that a realm, noble house, church or merchant guild without a collection begins one (%)")
    collectors_per_epoch: int = rule(6, 0, 1000, M, "New collectors that may arise on one world in one epoch")
    connoisseur_at: int = rule(65, 0, 100, M, "Discernment at which a private collector is a connoisseur whose taste weighs more on the market")
    base_price: int = rule(20, 0, 100000, M, "Price in coin of a work of middling quality by an unknown hand")
    renown_pct: int = rule(100, 0, 1000, M, "Price a work gains at its maker's full renown (%)")
    canon_pct: int = rule(150, 0, 1000, M, "Price a work of the canon gains (%)")
    provenance_pct: int = rule(10, 0, 100, M, "Price a work gains for every owner it has passed through (%)")
    interest_pct: int = rule(50, 0, 1000, M, "Price a work gains at full collectors' interest (%)")
    sale_chance: int = rule(25, 0, 100, M, "Chance each epoch that an owned work comes up for sale (%)")
    gathering_pct: int = rule(200, 0, 1000, M, "Chance of a sale against the usual when a gathering is held in the work's land (%)")
    sales_per_epoch: int = rule(30, 0, 10000, M, "Works that may change hands on one world in one epoch")
    auction_pct: int = rule(15, 0, 200, M, "Price a work gains at an auction for every rival bidder beyond the first (%)")
    grandeur_per_work: int = rule(2, 0, 100, M, "Grandeur a court gains each epoch for every work its realm holds, capped by its grandeur")
    lure_renown: int = rule(60, 0, 100, M, "Renown from which an artist is drawn to the grandest court of its world")
    lure_chance: int = rule(10, 0, 100, M, "Chance each epoch that a renowned artist moves to the grandest court (%)")


@dataclass(frozen=True)
class ForgeryRules:
    forge_chance: int = rule(5, 0, 100, C, "Chance each epoch that a skilled maker forges a work worth the trouble (%)")
    forgeries_per_epoch: int = rule(4, 0, 1000, C, "Forgeries that may be made on one world in one epoch")
    price_floor: int = rule(40, 0, 100000, C, "Price from which a work is worth forging")
    skill_floor: int = rule(55, 0, 100, C, "Creativity a maker needs before it forges")
    expose_chance: int = rule(10, 0, 100, C, "Chance each epoch that an expert examines a forgery in its land (%)")
    infamy: int = rule(15, 0, 100, C, "Infamy an exposed forger gains")
    sanctity: int = rule(30, 0, 100, C, "Sanctity an exposed forged relic loses")
    artwork_detect_pct: int = rule(100, 0, 100, C, "How readily a forged work of art is found out, against the base chance (%)")
    relic_detect_pct: int = rule(80, 0, 100, C, "How readily a forged relic is found out, against the base chance (%)")
    document_detect_pct: int = rule(100, 0, 100, C, "How readily a forged document is found out, against the base chance (%)")
    brand_detect_pct: int = rule(100, 0, 100, C, "How readily goods under a false mark are found out, against the base chance (%)")
    coin_detect_pct: int = rule(100, 0, 100, C, "How readily false coin is found out, against the base chance (%)")
    lineage_detect_pct: int = rule(70, 0, 100, C, "How readily a forged lineage is found out, against the base chance (%)")
    seal_detect_pct: int = rule(90, 0, 100, C, "How readily a forged seal is found out, against the base chance (%)")
    coin_trust_cut: int = rule(5, 0, 100, C, "Trust a currency loses each time false coin of it is made")
    seal_order_take: int = rule(20, 0, 100000, C, "Coin a forged seal draws from its realm by a false order")
    identity_detect_pct: int = rule(25, 0, 100, M, "Chance each epoch false papers and a false person are seen through (%)")


@dataclass(frozen=True)
class CanonRules(Spanned):
    renown_quality: int = rule(80, 0, 100, C, "Quality from which a work enters its people's canon by renown")
    age_years: int = span(50, 0, 2500, C, "Years a work must last before it enters the canon by renown")
    copies: int = rule(5, 0, 10000, C, "Copies from which a work enters the canon by copying")
    canon_size: int = rule(12, 1, 100000, C, "Works a small people's canon holds (base)")
    canon_people_per_work: int = rule(10000, 0, 100000000, C, "A people's canon holds one more work for every this many of its people (0: fixed)")
    contest_chance: int = rule(20, 0, 100, C, "Chance each epoch that a rival movement contests a work of the canon (%)")
    contest_loss: int = rule(15, 0, 100, C, "Weight a contested work loses each epoch")
    value_pull: int = rule(5, 0, 100, C, "Share of the gap a people's values close each epoch toward the values its canon carries (%)")
    form_prestige: int = rule(10, 0, 100, C, "Prestige an art form holds at least for every work of it in a canon")

    @property
    def age_epochs(self) -> int:
        return self.epochs(self.age_years)


@dataclass(frozen=True)
class ArtMovementRules:
    found_artists: int = rule(3, 1, 100, C, "Makers of works in a town from which they band into a movement")
    found_chance: int = rule(10, 0, 100, C, "Chance each epoch that such makers found a movement (%)")
    movements_per_epoch: int = rule(3, 0, 1000, C, "Movements that may be founded on one world in one epoch")
    scandal_chance: int = rule(8, 0, 100, C, "Chance each epoch that a movement breaches the norms of its town (%)")
    scandal_agitation: int = rule(10, 0, 100, C, "Agitation a scandal stirs in the town's crowd")
    orthodoxy_patrons: int = rule(3, 1, 100, C, "Patrons from which a movement becomes the orthodoxy of its people")


@dataclass(frozen=True)
class SportRules(Spanned):
    club_population: int = rule(1500, 0, 1000000, C, "People a town with an arena or stadium needs before a club forms in it")
    club_chance: int = rule(15, 0, 100, C, "Chance each epoch that such a town gains a club (%)")
    clubs_per_epoch: int = rule(4, 0, 1000, C, "Clubs that may form on one world in one epoch")
    league_clubs: int = rule(2, 2, 100, C, "Clubs a realm needs before they form a league")
    rating_step: int = rule(5, 0, 100, C, "Rating a club gains for a win or loses for a defeat")
    fandom_step: int = rule(3, 0, 100, C, "Fandom a club gains for a win or loses for a defeat")
    stake_pct: int = rule(2, 0, 100, C, "Share of a town's coin its fans wager on a match, at full fandom (%)")
    season_years: int = span(1, 1, 2500, C, "Years a league season runs before a champion is named")
    athletes: int = rule(11, 0, 1000, C, "Athletes a new club signs from the strongest and swiftest mortals of its town")
    field_following: int = rule(
        40,
        0,
        100,
        C,
        "Strength a field game (ball, team, racing, combat sport or athletics) needs among a town's people before a club forms there without an arena",
    )
    friendly_chance: int = rule(50, 0, 100, C, "Chance each epoch that the clubs of a world outside any league meet in friendly matches (%)")

    @property
    def season_epochs(self) -> int:
        return self.epochs(self.season_years)


@dataclass(frozen=True)
class CircusFactionRules:
    line_share: int = rule(40, 0, 100, P, "Share a class must hold in a town before a club's fandom follows its line")
    leverage_pct: int = rule(60, 0, 100, P, "Leverage a club holds at full fandom along a line (%)")
    riot_leverage: int = rule(40, 0, 100, P, "Leverage from which a lost match can spark a riot")
    riot_chance: int = rule(25, 0, 100, P, "Chance a lost match sparks a riot where fans have the leverage (%)")
    buy_legitimacy: int = rule(40, 0, 100, P, "Legitimacy below which a ruler buys the favour of a club")
    buy_cost: int = rule(50, 0, 100000, P, "Coin a ruler pays to buy a club's favour")
    buy_gain: int = rule(4, 0, 100, P, "Legitimacy a ruler gains each epoch from a club it bought")


@dataclass(frozen=True)
class ConstructRules:
    make_chance: int = rule(5, 0, 100, H, "Chance each epoch that a maker with the skill makes a construct (%)")
    constructs_per_epoch: int = rule(3, 0, 1000, H, "Constructs that may be made on one world in one epoch")
    maker_magic: int = rule(4, 0, 10, H, "Magic knowledge a maker's people needs before it makes constructs")
    upkeep: int = rule(5, 0, 100, H, "Power a construct burns each epoch")
    renew: int = rule(20, 0, 100, H, "Power a living maker, or a skilled maker of its town once it is dead, renews in its construct each epoch")
    wear: int = rule(3, 0, 100, H, "Decay a construct gathers each epoch before its material")
    will_chance: int = rule(10, 0, 100, H, "Chance each epoch that a construct with a bound soul grows in will (%)")
    guard_defense: int = rule(5, 0, 100, H, "Defence a guarding construct lends its charge")
    serve_goods: int = rule(20, 0, 100000, H, "Goods a serving construct makes for its charge each epoch")
    gather_ore: int = rule(20, 0, 100000, H, "Ore a gathering construct brings each epoch")
    build_progress: int = rule(10, 0, 100, H, "Progress a building construct adds to a work under way each epoch")
    maintain_repair: int = rule(5, 0, 100, H, "Durability a maintaining construct restores each epoch")
    protect_health: int = rule(5, 0, 100, H, "Health a protecting construct keeps for its charge each epoch")
    destroy_harm: int = rule(5, 0, 100, H, "Defence or durability a destroying construct breaks each epoch")
    destroy_per_mille: int = rule(3, 0, 1000, H, "People in a thousand a destroying construct kills each epoch")
    forbid_organisation: int = rule(10, 0, 100, H, "Organisation a forbidding construct costs a hostile army in its land")
    report_chance: int = rule(30, 0, 100, H, "Chance a reporting construct exposes a scheme against its charge (%)")
    replicate_ore: int = rule(80, 0, 100000, H, "Ore a replicating construct spends to make another")


@dataclass(frozen=True)
class MonsterContractRules:
    post_raids: int = rule(1, 0, 1000, K, "Raids from which a town near a beast's lair posts a contract on it")
    bounty: int = rule(30, 0, 100000, K, "Coin a town offers for a beast")
    take_chance: int = rule(40, 0, 100, K, "Chance each epoch that a hunter takes a posted contract in its world (%)")
    study_step: int = rule(15, 0, 100, K, "Study a hunter gains of its quarry each epoch, before its intellect")
    hunt_base: int = rule(20, 0, 100, K, "Chance a hunt succeeds before study, strength and the beast's might (%)")
    renown: int = rule(10, 0, 100, K, "Renown a hunter gains for a slain beast")
    wound: int = rule(25, 0, 100, K, "Health a hunter loses to a failed hunt")


@dataclass(frozen=True)
class AstrologyRules:
    real_influence: int = rule(70, 0, 100, S, "Influence from which the ruling celestial truly shapes those born under it")
    fortune_scale: int = rule(5, 1, 100, S, "Influence above the middle for each point of fortune a real sign grants")
    dread_chance: int = rule(30, 0, 100, S, "Chance a birth in an epoch of a sign in the sky falls under a dreaded sign (%)")
    foster_chance: int = rule(40, 0, 100, S, "Chance a people reading the stars fosters away a child of a dreaded sign (%)")
    dread_infamy: int = rule(10, 0, 100, S, "Infamy a mortal of a dreaded sign bears among a people reading the stars")


@dataclass(frozen=True)
class PunitiveRemakingRules:
    magic_floor: int = rule(5, 0, 10, P, "Knowledge of magic or of biomancy a people needs before its courts can remake the condemned")
    cruel_mercy: int = rule(
        -20, -100, 100, P, "Weight of mercy among a people's values at or below which its penal ethic is cruel enough to remake the condemned"
    )
    remake_chance: int = rule(30, 0, 100, P, "Chance a court able and willing to remake chooses it over another punishment (%)")
    labour_goods: int = rule(10, 0, 100000, P, "Goods a remade labourer makes for its realm's town each epoch")
    grievance_step: int = rule(5, 0, 100, P, "Grievance a remade mortal gathers each epoch")
    revolt_count: int = rule(3, 1, 1000, P, "Remade in a town from which their grievance can rise in revolt")
    revolt_grievance: int = rule(70, 0, 100, P, "Grievance from which the remade of a town rise")
