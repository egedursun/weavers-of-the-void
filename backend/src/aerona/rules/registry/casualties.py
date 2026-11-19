from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY
H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class CasualtiesRules(Spanned):
    commander_loser_death: int = rule(35, 0, 100, W, "Chance that the commander of the losing army falls in a clash (%)")
    commander_victor_death: int = rule(10, 0, 100, W, "Chance that the commander of the winning army falls in a clash (%)")
    warrior_loser_death: int = rule(25, 0, 100, W, "Chance that each named warrior of the losing side falls in a clash (%)")
    warrior_victor_death: int = rule(8, 0, 100, W, "Chance that each named warrior of the winning side falls in a clash (%)")
    indecisive_pct: int = rule(70, 0, 1000, W, "In an unrecorded clash both sides roll this share of the victor's death chances (%)")
    civilian_siege_death: int = rule(12, 0, 100, W, "Chance that each named civilian of a settlement that lost a siege dies (%)")
    civilian_battle_death: int = rule(6, 0, 100, W, "Chance that each named civilian of a community that lost a battle dies (%)")
    captive_chaos_death: int = rule(12, 0, 100, W, "Chance that a captive held by the losing side is killed in the chaos of defeat (%)")
    wound_chance: int = rule(30, 0, 100, W, "Chance that a warrior who did not fall in a clash is wounded (%)")
    wound_hp: int = rule(30, 0, 1000, W, "Hit points taken by a battle wound")
    clash_cap: int = rule(60, 0, 100, W, "Most named dead of one side in a single clash (% of that side's named, at least one)")
    epoch_cap: int = rule(0, 0, 100000, W, "Most named war dead per epoch (0 for no limit beyond each mortal's own roll)")
    disaster_death: int = rule(25, 0, 100, H, "Chance that each named mortal of a community struck by a disaster dies (% at severity 100)")
    plague_death: int = rule(35, 0, 100, H, "Chance that each named mortal of a community struck by a plague dies (% at severity 100)")
    medicine_kept_pct: int = rule(50, 0, 100, H, "Share of the plague death chance kept by a community that knows medicine (%)")
    disaster_epoch_cap: int = rule(0, 0, 100000, H, "Most named disaster and plague dead per epoch (0 for no limit beyond each mortal's own roll)")
    disaster_event_cap: int = rule(80, 0, 100, H, "Most named dead of one disaster (% of the named of the struck communities, at least one)")
    fate_cost: int = rule(10, 0, 1000, RuleGroup.INTERVENTION, "Essence cost of the god writing a mortal's fate")
    veteran_share_pct: int = rule(50, 0, 100, W, "Share of the best experience of a community's disbanded armies a new army inherits (%)")
    veteran_years: int = span(30, 0, 25000, W, "Years the veterans of a disbanded army carry its experience")
    commander_min_intellect: int = rule(60, 0, 100, W, "Least intellect of a commander who adds experience to the army")
    commander_experience: int = rule(4, 0, 100, W, "Experience a clever commander adds to the army in every clash")
    rust: int = rule(2, 0, 100, W, "Experience lost by an army at war that did not fight this epoch")
    rust_floor: int = rule(10, 0, 100, W, "Experience below which a rusting army loses nothing")
    commander_rise_chance: int = rule(50, 0, 100, W, "Per-epoch chance that a named commander rises from the community of an army without one (%)")
    commander_stat_base: int = rule(40, 0, 100, W, "Base stat of a commander risen from the ranks")
    commander_stat_die: int = rule(40, 1, 100, W, "Stat die of a commander risen from the ranks")
    commander_hp: int = rule(80, 1, 1000, W, "Hit points of a commander risen from the ranks")
    officer_warfare_level: int = rule(5, 0, 20, W, "Warfare level at which a commander risen from the ranks is a trained officer")
    commander_lifespan: int = rule(60, 1, 1000, W, "Base lifespan of a commander risen from the ranks")
    commander_lifespan_die: int = rule(25, 1, 1000, W, "Lifespan die of a commander risen from the ranks")
    commander_age_pct: int = rule(35, 0, 100, W, "Age of a commander risen from the ranks (% of lifespan)")
    ruler_class_chance: int = rule(40, 0, 100, H, "Chance that a ruler takes the role of the ruled community's dominant class (%)")
    ruler_class_min_share: int = rule(30, 0, 100, H, "Least share of the dominant class for the ruler's role to come from it (%)")

    @property
    def veteran_epochs(self) -> int:
        return self.epochs(self.veteran_years)
