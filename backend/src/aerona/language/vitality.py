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


def vitality_note(language_name: str, assessment: VitalityAssessment, last_home: str | None = None) -> str:
    if assessment.change is VitalityChange.REVIVED:
        return f"{language_name} is spoken again."
    script = "; its script survives to be read" if assessment.decipherable else ""
    home = f" It was last spoken {last_home}." if last_home else ""
    return f"{language_name} is now a dead language: no one is left who speaks it{script}.{home}"


def death_notes_allowed(already_written: int, rules: Rules) -> bool:
    return already_written < rules.deep_life.language_death_note_cap
