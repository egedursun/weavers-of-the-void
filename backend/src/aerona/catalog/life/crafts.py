from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.crafts import AssistiveAid, ClockKind, LinkToken
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.mind import SkillKind

FROM_SKILL = {
    SkillKind.ASTRONOMY: AssistiveAid.TELESCOPE,
    SkillKind.SMITHING: AssistiveAid.MAGNIFIER,
    SkillKind.CARPENTRY: AssistiveAid.MAGNIFIER,
}


PRECISION = {
    ClockKind.SUNDIAL: 20,
    ClockKind.CANDLE_CLOCK: 25,
    ClockKind.SAND_GLASS: 30,
    ClockKind.WATER_CLOCK: 35,
    ClockKind.MECHANICAL: 70,
    ClockKind.ASTRONOMICAL: 85,
}


LADDER = (
    (ClockKind.MECHANICAL, (Technique.STEEL, Technique.ASTRONOMY_INSTRUMENTS)),
    (ClockKind.ASTRONOMICAL, (Technique.ASTRONOMY_INSTRUMENTS,)),
    (ClockKind.WATER_CLOCK, (Technique.CALENDAR, Technique.AQUEDUCT)),
    (ClockKind.SAND_GLASS, (Technique.CALENDAR, Technique.NAVIGATION_STARS)),
    (ClockKind.CANDLE_CLOCK, (Technique.CALENDAR, Technique.ORGANISED_CLERGY)),
    (ClockKind.SUNDIAL, (Technique.CALENDAR,)),
)


SCHOOLING = (Technique.ALPHABET, Technique.BUREAUCRACY, Technique.UNIVERSITIES, Technique.DOUBLE_ENTRY)


TOKEN_STRENGTH: Mapping[LinkToken, int] = total(
    LinkToken,
    {LinkToken.HAIR: 50, LinkToken.BLOOD: 65, LinkToken.NAME: 90, LinkToken.PORTRAIT: 40, LinkToken.FRAGMENT: 55},
)

TOKENS_WITHIN_REACH_LINK_TOKENS = (LinkToken.HAIR, LinkToken.BLOOD)
BURN_AND_FADE_LINK_TOKENS = frozenset({LinkToken.HAIR, LinkToken.BLOOD})
