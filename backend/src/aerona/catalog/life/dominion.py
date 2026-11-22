from aerona.core.total import total
from aerona.domain.enums.dominion import CreatureLesson
from aerona.domain.enums.mind import SkillKind

LESSON_SIGN = total(CreatureLesson, {CreatureLesson.REWARD: 1, CreatureLesson.PUNISH: -1})


SCOUTING = (SkillKind.TRACKING, SkillKind.NAVIGATION, SkillKind.MOUNTAINEERING)
