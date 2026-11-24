from aerona.domain.enums.culture import Technique
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.regime import LegitimacyType

TYPE_LABELS = {
    LegitimacyType.TRADITIONAL: ("the weight of custom", "custom forsaken"),
    LegitimacyType.CHARISMATIC: ("the ruler's charisma", "a ruler without charisma"),
    LegitimacyType.RATIONAL: ("the rule of law", "laws that bind no one"),
    LegitimacyType.CONQUEST: ("the right of conquest", "a conquest long faded"),
}


EXAMINED = (SkillKind.LAW, SkillKind.WRITING, SkillKind.LORE)


LAW_TECHNIQUES = (Technique.WRITTEN_LAW, Technique.CODIFIED_LAW)
