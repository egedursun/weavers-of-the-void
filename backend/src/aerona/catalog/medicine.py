from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import MEDICINE_ORDER, MedicineTier
from aerona.domain.enums.culture import Technique
from aerona.rules.registry.body import HealingRules

M = MedicineTier


@dataclass(frozen=True)
class MedicineSpec:
    level: int | None
    technique: Technique | None
    epidemic_cut: int
    lifespan_pct: int
    mind_care: bool = False


MEDICINE: Mapping[MedicineTier, MedicineSpec] = total(
    MedicineTier,
    {
        M.NONE: MedicineSpec(0, None, 0, 0),
        M.HERBS: MedicineSpec(None, Technique.HERBALISM, 5, 0),
        M.SURGERY: MedicineSpec(None, Technique.SURGERY, 5, 2),
        M.ANTISEPSIS: MedicineSpec(3, Technique.EMPIRICISM, 15, 4),
        M.ANAESTHESIA: MedicineSpec(3, Technique.INDUSTRIAL_CHEMISTRY, 15, 4),
        M.PROSTHETICS: MedicineSpec(None, Technique.PROSTHETICS, 15, 4),
        M.IMMUNISATION: MedicineSpec(4, Technique.VACCINES, 35, 8),
        M.ANTIMICROBIALS: MedicineSpec(5, Technique.ANTIBIOTICS, 50, 12),
        M.REATTACHMENT: MedicineSpec(None, None, 50, 12),
        M.TRANSPLANTATION: MedicineSpec(6, Technique.HOSPITALS, 55, 15),
        M.MIND_MEDICINE: MedicineSpec(6, Technique.HOSPITALS, 55, 15, mind_care=True),
        M.REGENERATION: MedicineSpec(7, Technique.GENETIC_ENGINEERING, 60, 25, mind_care=True),
        M.GENOME_REPAIR: MedicineSpec(8, Technique.GENETIC_ENGINEERING, 70, 40, mind_care=True),
        M.CELLULAR_MACHINES: MedicineSpec(9, Technique.ARTIFICIAL_MINDS, 80, 60, mind_care=True),
    },
)


def threshold(rules: HealingRules, tier: MedicineTier) -> int:
    level = MEDICINE[tier].level
    if level is not None:
        return level
    return total(
        MedicineTier,
        {
            **dict.fromkeys(MedicineTier, 0),
            MedicineTier.HERBS: rules.herbs_level,
            MedicineTier.SURGERY: rules.surgery_level,
            MedicineTier.PROSTHETICS: rules.prosthetics_level,
            MedicineTier.REATTACHMENT: rules.reattachment_level,
        },
    )[tier]


def tier_of(rules: HealingRules, medicine: int, magic: int, biomancy: bool) -> MedicineTier:
    best = next((tier for tier in reversed(MEDICINE_ORDER) if medicine >= threshold(rules, tier)), MedicineTier.NONE)
    if (biomancy or magic >= rules.magic_reattachment_level) and MEDICINE_ORDER.index(best) < MEDICINE_ORDER.index(MedicineTier.REATTACHMENT):
        return MedicineTier.REATTACHMENT
    return best
