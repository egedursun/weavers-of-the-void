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


class SpellDuration(StrEnum):
    INSTANT = "instant"
    SEASON = "season"
    EPOCH = "epoch"
    PERMANENT = "permanent"


class SpellTarget(StrEnum):
    ONE = "one"
    GROUP = "group"
    STRUCTURE = "structure"
    REGION = "region"


class RechargeRule(StrEnum):
    SITE = "site"
    VIS = "vis"
    MOON = "moon"
    NONE = "none"


class LawSource(StrEnum):
    AUTHORED = "authored"
    ENCHANTMENT = "enchantment"
