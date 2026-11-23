from aerona.catalog.gravity import GRAVITY as GRAVITY_BANDS
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.world import Atmosphere, Gravity

FUNCTION_LEVELS = (
    BodyFunction.VITAL,
    BodyFunction.COGNITION,
    BodyFunction.HEARING,
    BodyFunction.SIGHT,
    BodyFunction.VENOM,
    BodyFunction.HORN,
    BodyFunction.TAIL,
)


AIR: dict[Atmosphere, int] = {Atmosphere.NONE: 0, Atmosphere.THIN: 25, Atmosphere.NORMAL: 50, Atmosphere.DENSE: 75, Atmosphere.TOXIC: 50}


GRAVITY: dict[Gravity, int] = {band: spec.body for band, spec in GRAVITY_BANDS.items()}

POWER_CURE_SPELL_FORMS = (SpellForm.BODY, SpellForm.SPIRIT)
