from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.daily_life import DistanceNorm, HouseDuty, LeisureKind, NormKind, PostureForm, TouchNorm

DISTANCE_NORM = total(
    DistanceNorm,
    {
        DistanceNorm.CLOSE: Defined("Close", checked_by=(), used_by=("engine.daily.seed.distance_for",)),
        DistanceNorm.ARM: Defined("Arm", checked_by=(), used_by=("db.tables.daily_life.SpaceNormRow", "engine.daily.seed.distance_for")),
        DistanceNorm.WIDE: Defined("Wide", checked_by=(), used_by=("engine.daily.seed.distance_for",)),
    },
)

HOUSE_DUTY = total(
    HouseDuty,
    {
        HouseDuty.FOOD: Defined("Food", checked_by=(), used_by=()),
        HouseDuty.WATER: Defined("Water", checked_by=(), used_by=("engine.daily.seed.SERVED_DUTIES",)),
        HouseDuty.FUEL: Defined("Fuel", checked_by=(), used_by=("engine.daily.seed.SERVED_DUTIES",)),
        HouseDuty.CLEANING: Defined("Cleaning", checked_by=(), used_by=("engine.daily.seed.SERVED_DUTIES",)),
        HouseDuty.TEXTILES: Defined("Textiles", checked_by=(), used_by=()),
        HouseDuty.CHILDCARE: Defined("Childcare", checked_by=(), used_by=("engine.daily.seed.CARE_DUTIES",)),
        HouseDuty.ELDERCARE: Defined("Eldercare", checked_by=(), used_by=("engine.daily.seed.CARE_DUTIES",)),
        HouseDuty.ANIMALS: Defined("Animals", checked_by=(), used_by=()),
        HouseDuty.REPAIRS: Defined("Repairs", checked_by=(), used_by=()),
    },
)

LEISURE_KIND = total(
    LeisureKind,
    {
        LeisureKind.CONVERSATION: Defined("Conversation", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.GAMES: Defined("Games", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.SPORT: Defined("Sport", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.MUSIC: Defined("Music", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.CRAFTS: Defined("Crafts", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.COLLECTING: Defined("Collecting", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.READING: Defined("Reading", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.EXCURSION: Defined("Excursion", checked_by=(), used_by=("engine.daily.life.TRAVEL_PURSUITS", "engine.daily.seed.LEISURE_AXES")),
        LeisureKind.TOURISM: Defined("Tourism", checked_by=(), used_by=("engine.daily.life.TRAVEL_PURSUITS",)),
        LeisureKind.DRINKING: Defined("Drinking", checked_by=(), used_by=()),
        LeisureKind.WORSHIP_EXTRA: Defined("Worship extra", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.REST: Defined("Rest", checked_by=(), used_by=("engine.daily.seed.LEISURE_AXES",)),
        LeisureKind.MEDIA: Defined("Media", checked_by=(), used_by=()),
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
