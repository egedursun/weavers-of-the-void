from dataclasses import dataclass
from enum import StrEnum

from aerona.rules.registry import Rules


class VitalityChange(StrEnum):
    DIED = "died"
    REVIVED = "revived"


@dataclass(frozen=True)
class VitalityAssessment:
    change: VitalityChange
    decipherable: bool = False


def assess_vitality(age_in_epochs: int, living_speakers: int, is_dead: bool, has_script: bool, rules: Rules) -> VitalityAssessment | None:
    if age_in_epochs <= rules.deep_life.language_death_grace:
        return None
    if living_speakers == 0 and not is_dead:
        return VitalityAssessment(change=VitalityChange.DIED, decipherable=has_script)
    if living_speakers > 0 and is_dead:
        return VitalityAssessment(change=VitalityChange.REVIVED)
    return None
