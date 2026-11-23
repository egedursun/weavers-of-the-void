from enum import StrEnum


class SpellTechnique(StrEnum):
    CREATE = "create"
    PERCEIVE = "perceive"
    TRANSFORM = "transform"
    DESTROY = "destroy"
    CONTROL = "control"
    BIND = "bind"
    SUMMON = "summon"
    WARD = "ward"
    DRAIN = "drain"
    MIMIC = "mimic"


class SpellForm(StrEnum):
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    PLANT = "plant"
    ANIMAL = "animal"
    BODY = "body"
    MIND = "mind"
    IMAGE = "image"
    SPIRIT = "spirit"
    TIME = "time"
    VOID = "void"
    DEATH = "death"
    LIGHT = "light"
    SPACE = "space"
    FORCE = "force"
    SOUND = "sound"
    EMOTION = "emotion"
    FATE = "fate"
    MACHINE = "machine"
    INFORMATION = "information"


class SpellRange(StrEnum):
    TOUCH = "touch"
    SIGHT = "sight"
    REGION = "region"
    WORLD = "world"
    LINKED = "linked"
    COSMOS = "cosmos"


class SpellDuration(StrEnum):
    INSTANT = "instant"
    SEASON = "season"
    EPOCH = "epoch"
    PERMANENT = "permanent"
    SUSTAINED = "sustained"
    UNTIL_CONDITION = "until_condition"


class RiteCondition(StrEnum):
    ACT = "act"
    TIME = "time"
    WORD = "word"
    DEED = "deed"


class RiteEnd(StrEnum):
    CASTER_GONE = "caster_gone"
    CASTER_STRUCK = "caster_struck"
    CONDITION_MET = "condition_met"


class SpellTarget(StrEnum):
    ONE = "one"
    GROUP = "group"
    STRUCTURE = "structure"
    REGION = "region"
    ITEM = "item"
    LINE = "line"
    WORLD = "world"


class RechargeRule(StrEnum):
    SITE = "site"
    VIS = "vis"
    MOON = "moon"
    NONE = "none"
    SKY_EVENT = "sky_event"
    BODILY_OFFERING = "bodily_offering"


class LawSource(StrEnum):
    AUTHORED = "authored"
    ENCHANTMENT = "enchantment"
