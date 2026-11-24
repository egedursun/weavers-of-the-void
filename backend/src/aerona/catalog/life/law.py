from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import LawArea
from aerona.domain.enums.society import SocialClass

CLASSES: Mapping[LawArea, frozenset[SocialClass] | None] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({SocialClass.NOBLE}),
        LawArea.PROPERTY: None,
        LawArea.FISCAL: frozenset({SocialClass.MERCHANT, SocialClass.ARTISAN, SocialClass.PROFESSIONAL, SocialClass.NOBLE}),
        LawArea.PENAL: None,
        LawArea.MILITARY: frozenset({SocialClass.WARRIOR}),
        LawArea.SOCIAL: None,
        LawArea.PUBLIC_HEALTH: frozenset({SocialClass.MERCHANT, SocialClass.ARTISAN, SocialClass.FARMER, SocialClass.WORKER}),
        LawArea.MAGIC: frozenset({SocialClass.PRIEST, SocialClass.MONASTIC, SocialClass.SCRIBE, SocialClass.OUTCAST}),
        LawArea.CONSTITUTIONAL: frozenset({SocialClass.OFFICIAL, SocialClass.NOBLE, SocialClass.SCRIBE, SocialClass.PROFESSIONAL}),
        LawArea.COMMERCE: frozenset({SocialClass.MERCHANT, SocialClass.ARTISAN, SocialClass.PROFESSIONAL}),
        LawArea.FAITH: frozenset({SocialClass.PRIEST, SocialClass.MONASTIC}),
        LawArea.LABOUR: frozenset({SocialClass.WORKER, SocialClass.FARMER, SocialClass.ARTISAN, SocialClass.SERF_OR_SLAVE}),
        LawArea.FAMILY: None,
        LawArea.ENVIRONMENT: frozenset({SocialClass.FARMER, SocialClass.WORKER, SocialClass.ARTISAN}),
    },
)


HUNTING = (SkillKind.TRACKING, SkillKind.HUNTING, SkillKind.BLADE)
