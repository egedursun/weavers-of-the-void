from aerona.domain.enums.eras import ProgrammeStage
from aerona.domain.enums.mind import SkillKind

LIVE = (ProgrammeStage.PLANNING, ProgrammeStage.BUILDING, ProgrammeStage.TESTING)
KEPT = (*LIVE, ProgrammeStage.SUSPENDED)


SPECIALISMS = (SkillKind.SCIENCE, SkillKind.ENGINEERING, SkillKind.COMPUTING)
