from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

R = RuleGroup.CREATURES


@dataclass(frozen=True)
class CreatureGroupsRules(Spanned):
    raid_hunger_threshold: int = rule(60, 0, 100, R, "Hunger at which a group of hunting creatures raids a settlement in its territory")
    contest_chance_pct: int = rule(10, 0, 100, R, "Chance in an epoch that a group's leader is challenged and falls (%)")
    territory_war_pct: int = rule(5, 0, 100, R, "Chance in an epoch that two rival groups of hunting creatures fight over their ground (%)")
    form_floor: int = rule(20, 0, 100, R, "Abundance of a species in a region at which it forms a group there")
    size_per_abundance: int = rule(5, 0, 1000, R, "Creatures in a group for each point of its species' abundance in the region")
    raid_loss: int = rule(5, 0, 100, R, "Prosperity a settlement loses to a group's raid")
    war_loss_pct: int = rule(30, 0, 100, R, "Share of its numbers the loser of a territory war loses (%)")
    push_population: int = rule(5000, 0, 10000000, R, "People settled in a region at which its groups begin to move away")
    move_pct: int = rule(20, 0, 100, R, "Chance in an epoch that a group pushed by settlement or season moves to a neighbouring region (%)")
    travel_danger_pct: int = rule(10, 0, 100, R, "Danger to travellers a group of hunting creatures adds to a road for each thousand of its numbers (%)")
    hunt_bonus_pct: int = rule(10, 0, 100, R, "Further yield hunters take from a herd or flock for each thousand of its numbers (%)")
    aim_years: int = span(10, 0, 1000, R, "Years a god's leading of a group holds")

    @property
    def aim_epochs(self) -> int:
        return self.epochs(self.aim_years)
