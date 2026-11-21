from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class SecuritiesRules(Spanned):
    herding_pct: int = rule(20, 0, 100, S, "Share of last epoch's move in a price that herding carries into this epoch's (%)")
    bubble_threshold_pct: int = rule(50, 0, 500, S, "How far a price must stand above what its issuer's results are worth before it counts as a bubble (%)")
    crash_drop_pct: int = rule(40, 0, 100, S, "Share of its price a security loses in a crash (%)")
    margin_call_pct: int = rule(30, 0, 100, S, "Share of a holding's worth its borrowed part must stay under before the holding is sold off (%)")
    default_rate_rise: int = rule(5, 0, 50, S, "Points the interest of an issuer rises when its bonds default")
    anchor_pct: int = rule(25, 0, 100, S, "Share of the gap between a price and what its issuer's results are worth closed in an epoch (%)")
    mood_pct: int = rule(10, 0, 100, S, "How far a fully elated or fully gloomy exchange moves its prices in an epoch (%)")
    mood_decay: int = rule(10, 0, 100, S, "Points an exchange's mood returns toward calm in an epoch")
    burst_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a bubble bursts on its own (%)")
    crash_mood: int = rule(40, 0, 100, S, "Gloom a crash spreads over its exchange")
    stir_mood: int = rule(30, 0, 100, S, "Points a son moves the mood of an exchange")
    exchange_min_population: int = rule(3000, 0, 100000000, S, "People a town with a bank needs before an exchange opens there")
    exchange_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a town fit for one opens an exchange (%)")
    bond_treasury_below: int = rule(50, 0, 100000000, S, "Treasury under which a realm at war or building issues bonds")
    bond_amount: int = rule(20, 1, 100000, S, "Units of a bond a realm issues at once")
    bond_face: int = rule(10, 1, 100000, S, "Face value of one unit of a realm's bond")
    bond_term_years: int = span(30, 1, 2500, S, "Years until a realm's bond falls due")
    insider_fine_pct: int = rule(30, 0, 100, S, "Share of the loss it escaped a holder pays when its trading on a secret is exposed (%)")
    insider_exposure_pct: int = rule(25, 0, 100, S, "Chance that a holder who sold on a secret before a crash is exposed where the law bans it (%)")

    @property
    def bond_term_epochs(self) -> int:
        return self.epochs(self.bond_term_years)
