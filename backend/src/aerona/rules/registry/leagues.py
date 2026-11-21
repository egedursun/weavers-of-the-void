from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class LeaguesRules(Spanned):
    dues_pct: int = rule(3, 0, 50, S, "Share of its treasury a member realm pays a league in an epoch (%)")
    obedience_base_pct: int = rule(60, 0, 100, S, "Chance a member obeys a league decision before its interest and the league's strength weigh in (%)")
    sanction_trade_cut_pct: int = rule(50, 0, 100, S, "Duty every buyer adds on the goods of a realm its league sanctions (%)")
    federate_depth_threshold: int = rule(80, 0, 100, S, "Depth at which a league bound for defence and trade becomes a federation")
    court_binding_pct: int = rule(50, 0, 100, S, "Chance a member repeals a law its league's court rules against, beside obedience (%)")
    depth_gain: int = rule(3, 0, 50, S, "Depth a league gains in an epoch its members obey and pay")
    depth_loss: int = rule(8, 0, 100, S, "Depth a league loses in an epoch a member defies it or members fight each other")
    strength_per_member: int = rule(10, 0, 100, S, "Strength each bound member adds to a league")
    defiance_to_expel: int = rule(3, 1, 50, S, "Defiances after which a league moves to expel a member")
    admit_chance_pct: int = rule(15, 0, 100, S, "Chance in an epoch that a league takes up a neighbouring realm that shares its aims (%)")
    exit_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a member that cannot pay its dues leaves (%)")
    found_chance_pct: int = rule(3, 0, 100, S, "Chance in an epoch that three or more realms at peace with each other found a league (%)")
    found_min_members: int = rule(3, 2, 50, S, "Realms a league needs at its founding and below which it dissolves")
    common_tariff_pct: int = rule(10, 0, 100, S, "Common tariff a customs union sets on goods from outside")
    interworld_strength_loss: int = rule(10, 0, 100, S, "Strength a league loses for each further world its members stand on when no network joins them")
