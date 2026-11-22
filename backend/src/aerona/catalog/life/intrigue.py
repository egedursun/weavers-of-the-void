from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.mind import SkillKind

SKILL_SKILL_KINDS = (SkillKind.INTRIGUE, SkillKind.DECEPTION)
FALSE_CAMPFIRES_SKILL_KINDS = (SkillKind.DECEPTION, SkillKind.TACTICS)

SECRETS_KEPT_ELSEWHERE = frozenset({PlotKind.SEDUCE, PlotKind.FABRICATE_HOOK, PlotKind.FRAME, PlotKind.CONVERT_SECRETLY, PlotKind.ECOSABOTAGE})
