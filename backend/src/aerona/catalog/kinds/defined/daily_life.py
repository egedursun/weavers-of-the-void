from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.daily_life import DistanceNorm, NormKind, PostureForm, TouchNorm

DISTANCE_NORM = total(
    DistanceNorm,
    {
        DistanceNorm.CLOSE: Defined("Close", checked_by=(), used_by=("engine.daily.seed.distance_for",)),
        DistanceNorm.ARM: Defined("Arm", checked_by=(), used_by=("db.tables.daily_life.SpaceNormRow", "engine.daily.seed.distance_for")),
        DistanceNorm.WIDE: Defined("Wide", checked_by=(), used_by=("engine.daily.seed.distance_for",)),
    },
)

NORM_KIND = total(
    NormKind,
    {
        NormKind.DISTANCE: Defined("Distance", checked_by=(), used_by=("engine.daily.life.differences",)),
        NormKind.TOUCH: Defined("Touch", checked_by=(), used_by=("engine.daily.life.differences",)),
        NormKind.POSTURE: Defined("Posture", checked_by=(), used_by=("engine.daily.life.differences",)),
        NormKind.CLEANLINESS: Defined("Cleanliness", checked_by=(), used_by=("engine.daily.life.shame_the_poor",)),
    },
)

POSTURE_FORM = total(
    PostureForm,
    {
        PostureForm.STAND: Defined("Stand", checked_by=(), used_by=("db.tables.daily_life.SpaceNormRow",)),
        PostureForm.SIT_FLOOR: Defined("Sit floor", checked_by=(), used_by=()),
        PostureForm.SIT_RAISED: Defined("Sit raised", checked_by=(), used_by=()),
        PostureForm.KNEEL: Defined("Kneel", checked_by=(), used_by=()),
        PostureForm.RECLINE: Defined("Recline", checked_by=(), used_by=()),
    },
)

TOUCH_NORM = total(
    TouchNorm,
    {
        TouchNorm.OPEN: Defined("Open", checked_by=(), used_by=("engine.daily.seed.touch_for",)),
        TouchNorm.KIN_ONLY: Defined("Kin only", checked_by=(), used_by=("engine.daily.seed.touch_for",)),
        TouchNorm.SPARING: Defined("Sparing", checked_by=(), used_by=("db.tables.daily_life.SpaceNormRow", "engine.daily.seed.touch_for")),
        TouchNorm.FORBIDDEN: Defined("Forbidden", checked_by=(), used_by=("engine.daily.seed.touch_for",)),
    },
)
