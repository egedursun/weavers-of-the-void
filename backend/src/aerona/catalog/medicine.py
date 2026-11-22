from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.catalog.life.domain import MEDICINE_ORDER
from aerona.core.total import total
from aerona.domain.enums.body import MedicineTier
from aerona.domain.enums.culture import Technique
from aerona.rules.registry.body import HealingRules

M = MedicineTier
LevelRule = Literal["herbs_level", "surgery_level", "prosthetics_level", "reattachment_level"]
InfectionRule = Literal["herbs_infection_cut_pct", "surgery_infection_cut_pct"]


@dataclass(frozen=True)
class MedicineSpec:
    level: int | None
    technique: Technique | None
    epidemic_cut: int
    lifespan_pct: int
    mind_care: bool = False
    level_rule: LevelRule | None = None
    infection_rule: InfectionRule | None = "surgery_infection_cut_pct"


MEDICINE: Mapping[MedicineTier, MedicineSpec] = total(
    MedicineTier,
    {
        M.NONE: MedicineSpec(0, None, 0, 0, infection_rule=None),
        M.HERBS: MedicineSpec(None, Technique.HERBALISM, 5, 0, level_rule="herbs_level", infection_rule="herbs_infection_cut_pct"),
        M.SURGERY: MedicineSpec(None, Technique.SURGERY, 5, 2, level_rule="surgery_level"),
        M.ANTISEPSIS: MedicineSpec(3, Technique.EMPIRICISM, 15, 4),
        M.ANAESTHESIA: MedicineSpec(3, Technique.INDUSTRIAL_CHEMISTRY, 15, 4),
        M.PROSTHETICS: MedicineSpec(None, Technique.PROSTHETICS, 15, 4, level_rule="prosthetics_level"),
        M.IMMUNISATION: MedicineSpec(4, Technique.VACCINES, 35, 8),
        M.ANTIMICROBIALS: MedicineSpec(5, Technique.ANTIBIOTICS, 50, 12),
        M.REATTACHMENT: MedicineSpec(None, None, 50, 12, level_rule="reattachment_level"),
        M.TRANSPLANTATION: MedicineSpec(6, Technique.HOSPITALS, 55, 15),
        M.MIND_MEDICINE: MedicineSpec(6, Technique.HOSPITALS, 55, 15, mind_care=True),
        M.REGENERATION: MedicineSpec(7, Technique.GENETIC_ENGINEERING, 60, 25, mind_care=True),
        M.GENOME_REPAIR: MedicineSpec(8, Technique.GENETIC_ENGINEERING, 70, 40, mind_care=True),
        M.CELLULAR_MACHINES: MedicineSpec(9, Technique.ARTIFICIAL_MINDS, 80, 60, mind_care=True),
    },
)


def threshold(rules: HealingRules, tier: MedicineTier) -> int:
    spec = MEDICINE[tier]
    if spec.level is not None:
        return spec.level
    return int(getattr(rules, spec.level_rule)) if spec.level_rule is not None else 0


def infection_cut(rules: HealingRules, tier: MedicineTier) -> int:
    rule_name = MEDICINE[tier].infection_rule
    return int(getattr(rules, rule_name)) if rule_name is not None else 0


def tier_of(rules: HealingRules, medicine: int, magic: int, biomancy: bool) -> MedicineTier:
    best = next((tier for tier in reversed(MEDICINE_ORDER) if medicine >= threshold(rules, tier)), MedicineTier.NONE)
    if (biomancy or magic >= rules.magic_reattachment_level) and MEDICINE_ORDER.index(best) < MEDICINE_ORDER.index(MedicineTier.REATTACHMENT):
        return MedicineTier.REATTACHMENT
    return best
