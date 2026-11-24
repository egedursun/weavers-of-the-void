from collections.abc import Callable, Mapping

from aerona.core.total import total
from aerona.domain.enums.crafts import AssistiveAid, ClockKind, LinkToken
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.mind import SkillKind
from aerona.rules.registry import Rules

FROM_SKILL = {
    SkillKind.ASTRONOMY: AssistiveAid.TELESCOPE,
    SkillKind.SMITHING: AssistiveAid.MAGNIFIER,
    SkillKind.CARPENTRY: AssistiveAid.MAGNIFIER,
    SkillKind.MEDICINE: AssistiveAid.MICROSCOPE,
    SkillKind.SCIENCE: AssistiveAid.MICROSCOPE,
}

AID_NEEDS: Mapping[AssistiveAid, tuple[Technique, ...]] = total(
    AssistiveAid,
    {
        AssistiveAid.SPECTACLES: (),
        AssistiveAid.MAGNIFIER: (),
        AssistiveAid.TELESCOPE: (),
        AssistiveAid.HEARING_HORN: (),
        AssistiveAid.CANE: (),
        AssistiveAid.MICROSCOPE: (Technique.EMPIRICISM,),
        AssistiveAid.HEARING_AID: (),
        AssistiveAid.TACTILE_SCRIPT: (Technique.ALPHABET,),
    },
)


PRECISION: Mapping[ClockKind, int] = total(
    ClockKind,
    {
        ClockKind.SUNDIAL: 20,
        ClockKind.CANDLE_CLOCK: 25,
        ClockKind.SAND_GLASS: 30,
        ClockKind.WATER_CLOCK: 35,
        ClockKind.MECHANICAL: 70,
        ClockKind.ASTRONOMICAL: 85,
        ClockKind.CHRONOMETER: 92,
        ClockKind.ELECTRONIC: 99,
        ClockKind.FIRE_CLOCK: 30,
    },
)
LONGITUDE_CLOCKS = frozenset({ClockKind.CHRONOMETER, ClockKind.ELECTRONIC})


LADDER = (
    (ClockKind.ELECTRONIC, (Technique.ELECTRICITY, Technique.COMPUTATION)),
    (ClockKind.CHRONOMETER, (Technique.MACHINE_TOOLS, Technique.CARTOGRAPHY)),
    (ClockKind.MECHANICAL, (Technique.STEEL, Technique.ASTRONOMY_INSTRUMENTS)),
    (ClockKind.ASTRONOMICAL, (Technique.ASTRONOMY_INSTRUMENTS,)),
    (ClockKind.WATER_CLOCK, (Technique.CALENDAR, Technique.AQUEDUCT)),
    (ClockKind.SAND_GLASS, (Technique.CALENDAR, Technique.NAVIGATION_STARS)),
    (ClockKind.CANDLE_CLOCK, (Technique.CALENDAR, Technique.ORGANISED_CLERGY)),
    (ClockKind.SUNDIAL, (Technique.CALENDAR,)),
)


SCHOOLING = (Technique.ALPHABET, Technique.BUREAUCRACY, Technique.UNIVERSITIES, Technique.DOUBLE_ENTRY)


TOKEN_STRENGTH: Mapping[LinkToken, Callable[[Rules], int]] = total(
    LinkToken,
    {
        LinkToken.HAIR: lambda rules: rules.links.hair_strength,
        LinkToken.BLOOD: lambda rules: rules.links.blood_strength,
        LinkToken.NAME: lambda rules: rules.links.name_strength,
        LinkToken.PORTRAIT: lambda rules: rules.links.portrait_strength,
        LinkToken.FRAGMENT: lambda rules: rules.links.fragment_strength,
        LinkToken.TRUE_NAME: lambda rules: rules.links.true_name_strength,
        LinkToken.POSSESSION: lambda rules: rules.links.possession_strength,
        LinkToken.FOOTPRINT: lambda rules: rules.links.footprint_strength,
        LinkToken.VOICE: lambda rules: rules.links.voice_strength,
        LinkToken.BIRTH_RECORD: lambda rules: rules.links.birth_record_strength,
    },
)
KNOWN_NAME_TOKENS = frozenset({LinkToken.TRUE_NAME})
NAME_TOKENS = frozenset({LinkToken.NAME, LinkToken.TRUE_NAME})

TOKENS_WITHIN_REACH_LINK_TOKENS = (LinkToken.HAIR, LinkToken.BLOOD, LinkToken.FOOTPRINT, LinkToken.VOICE)
GUARDED_TOKENS = frozenset({LinkToken.FOOTPRINT, LinkToken.VOICE, LinkToken.BIRTH_RECORD})
BURN_AND_FADE_LINK_TOKENS = frozenset({LinkToken.HAIR, LinkToken.BLOOD})
