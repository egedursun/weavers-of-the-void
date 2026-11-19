from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

H = RuleGroup.HOUSES


@dataclass(frozen=True)
class TitleRules(Spanned):
    creation_share_pct: int = rule(51, 1, 100, H, "Share of a title's de jure lands a realm must hold to create or usurp it (%)")
    drift_years: int = span(100, 1, 2500, H, "Years a land held under another title takes to drift into that title's de jure lands")
    creation_prestige: int = rule(20, 0, 100, H, "Prestige a title's creation costs its holder")
    rank_prestige: int = rule(15, 0, 100, H, "Prestige each tier above a local title lends a title at its creation")
    usurp_legitimacy: int = rule(10, 0, 100, H, "Legitimacy a realm loses when its ruler usurps a title")
    restore_pct: int = rule(20, 0, 100, H, "Chance each epoch a claimant holding enough of a dormant title's lands restores it (%)")
    union_pct: int = rule(100, 0, 100, H, "Chance a mortal who comes to hold the top titles of two realms rules both in a personal union (%)")
    claim_strength: int = rule(40, 0, 100, H, "Strength of a claim on a title a realm holds lands of but not the title")
    faith_local_followers: int = rule(200, 0, 1_000_000, H, "Followers a faith needs before its heartland holds a local seat for its foremost cleric")
    faith_high_followers: int = rule(
        2000, 0, 1_000_000, H, "Followers a faith needs before its local seat becomes a high seat; the largest such faith of a world holds the foremost seat"
    )
    seat_prestige: int = rule(
        2, 0, 50, H, "Prestige the holder of a seat of a faith, a military command or the head of a guild gains each epoch for each step of its tier"
    )

    @property
    def drift_epochs(self) -> int:
        return self.epochs(self.drift_years)
