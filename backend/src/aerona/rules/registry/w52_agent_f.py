from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class CrewsRules:
    gunners_effect: int = rule(10, 0, 100, W, "Strength a fully manned and skilled gun crew adds to its vessel in a fight (%)")
    riggers_effect: int = rule(15, 0, 100, W, "Storm harm a fully manned and skilled rigging crew spares its vessel (%)")
    marines_effect: int = rule(10, 0, 100, W, "Strength fully manned and skilled marines add to their vessel in a fight (%)")
    officers_effect: int = rule(5, 0, 100, W, "Strength fully manned and skilled officers add to their vessel in a fight (%)")
    rowers_effect: int = rule(5, 0, 100, W, "Strength a fully manned and skilled bank of rowers adds to its vessel in a fight (%)")
    pilots_effect: int = rule(15, 0, 100, W, "Strength fully manned and skilled pilots add to their vessel in a fight (%)")
    engineers_effect: int = rule(10, 0, 100, W, "Strength fully manned and skilled engineers add to their vessel in a fight (%)")
    sensor_operators_effect: int = rule(10, 0, 100, W, "Strength fully manned and skilled sensor operators add to their vessel in a fight (%)")
    medics_effect: int = rule(40, 0, 100, W, "Share of crew losses in storms and fights fully manned and skilled medics save (%)")
    handlers_effect: int = rule(15, 0, 100, W, "Storm harm fully manned and skilled handlers spare a vessel with a living body or team (%)")
    link_operators_effect: int = rule(10, 0, 100, W, "Strength fully manned and skilled link operators add to their vessel in a fight (%)")
    casters_effect: int = rule(15, 0, 100, W, "Strength fully manned and skilled casters add to their vessel in a fight through its wards (%)")
    navigators_effect: int = rule(30, 0, 100, W, "Storm harm and crew loss fully manned and skilled navigators with sure instruments spare their vessel (%)")


@dataclass(frozen=True)
class CaptivesRules(Spanned):
    parole_pct: int = rule(20, 0, 100, W, "Chance each epoch a captor frees a captive of a war on parole, an oath not to fight again (%)")
    parole_kept_pct: int = rule(80, 0, 100, W, "Chance a paroled captive keeps the oath when its realm goes to war again (%)")
    married_in_pct: int = rule(5, 0, 100, W, "Chance each epoch a captive married into its captors' people stays and joins them for good (%)")
    parole_shame: int = rule(20, 0, 100, W, "Grievance the captors bear a paroled captive who fights again")
    married_in_traitor_pct: int = rule(
        20, 0, 100, W, "Chance each epoch of a war between its two peoples a captive married in passes its first home's secrets to its new one (%)"
    )
    married_in_bridge: int = rule(5, 0, 100, W, "Relation a captive married in wins between its first and new homes each epoch of a war it does not betray")
    recruited_loyalty: int = rule(30, 0, 100, W, "Morale of captives pressed into the victor's army")
    executed_dread: int = rule(10, 0, 100, W, "Relation a captor loses with the captives' people and its neighbours when it kills captives")
    execute_pct: int = rule(20, 0, 100, W, "Chance a captor whose people judge the killing of captives acceptable kills captives it cannot use (%)")
    recruit_pct: int = rule(25, 0, 100, W, "Chance a captor at war presses captives of warrior class into its army (%)")
    recruited_desertion_pct: int = rule(30, 0, 100, W, "Share of pressed captives who desert at the first hardship (%)")
    adopt_pct: int = rule(10, 0, 100, W, "Chance captives are taken into their captors' households instead of held (%)")
    adoption_pct: int = rule(20, 0, 100, W, "Chance a young captive long held is taken into its captors' people in an epoch (%)")
    adoption_years: int = span(5, 0, 500, W, "Years a young captive is held before its captors may take it in as their own")
