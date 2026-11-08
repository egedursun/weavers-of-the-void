from enum import StrEnum


class NodeKind(StrEnum):
    ENTITY = "entity"
    SON = "son"
    CREATOR = "creator"
    FOREIGN_GOD = "foreign_god"
    WORLD = "world"
    STAR = "star"


class ActorKind(StrEnum):
    CREATOR = "creator"
    SON = "son"
    MORTAL = "mortal"
    FOREIGN_GOD = "foreign_god"
    FATE = "fate"
    ENGINE = "engine"
    SYSTEM = "system"
