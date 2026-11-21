from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class ReckoningRules(Spanned):
    office_bar_admin_loss_pct: int = rule(
        20, 0, 100, S, "Share of a realm's administration lost while servants of the fallen regime are barred from office (%)"
    )
    amnesty_grievance_shift: int = rule(15, 0, 100, S, "Grievance an amnesty takes from the old servants and adds to the victims")
    restitution_cost_pct: int = rule(30, 0, 100, S, "Share of its treasury a realm spends returning the holdings the fallen regime took (%)")
    harsh_revolt_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that old servants driven by a harsh reckoning rise in revolt (%)")
    open_chance_pct: int = rule(50, 0, 100, S, "Chance that one who seized rule opens a reckoning with the servants of the fallen regime (%)")
    convict_pct: int = rule(60, 0, 100, S, "Chance a tribunal convicts an old servant whose acts the record names, at full strength (%)")
    measure_years: int = span(60, 1, 2500, S, "Years a measure of a reckoning runs before it is done")
    harsh_from: int = rule(120, 0, 200, S, "Sum of the strength of tribunals and office bars from which a reckoning counts as harsh")
    weak_below: int = rule(30, 0, 200, S, "Sum of the strength of tribunals and office bars under which a reckoning counts as weak")
    weak_unrest: int = rule(5, 0, 100, S, "Unrest a weak reckoning raises at the seat of the realm each epoch")
    flight_chance_pct: int = rule(20, 0, 100, S, "Chance an old servant driven by a harsh reckoning flees the realm (%)")
    reparation_coin: int = rule(20, 0, 100000, S, "Coin a realm pays each living victim of the fallen regime under reparation")
    memorial_legitimacy: int = rule(5, 0, 100, S, "Legitimacy a memorial to the victims of the fallen regime gives the realm")
    inquiry_fidelity: int = rule(80, 0, 100, S, "Fidelity of the account a truth inquiry writes, at full strength")
    servant_resistance: int = rule(5, 0, 100, S, "Resistance each servant of the fallen regime still in office adds")

    @property
    def measure_epochs(self) -> int:
        return self.epochs(self.measure_years)
