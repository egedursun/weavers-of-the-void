from enum import StrEnum


class QuestAim(StrEnum):
    FIND = "find"
    RESTORE = "restore"
    DESTROY = "destroy"
    FREE = "free"
    BIND = "bind"
    REACH = "reach"
    LEARN = "learn"
    RETURN = "return"
    PROTECT = "protect"
    AVENGE = "avenge"
    HUNT = "hunt"
    DELIVER = "deliver"
    RECONCILE = "reconcile"
    PROVE = "prove"
    RESOLVE = "resolve"


class QuestTargetKind(StrEnum):
    STAR = "star"
    ROUTE = "route"
    KNOWLEDGE = "knowledge"
    OUTER_BEING = "outer_being"
    SPECIES = "species"
    ITEM = "item"
    PERSON = "person"
    PLACE = "place"
    INCIDENT_ARC = "incident_arc"


class QuestObstacle(StrEnum):
    DISTANCE = "distance"
    GUARDIAN = "guardian"
    RIDDLE = "riddle"
    RIVAL = "rival"
    LAW = "law"
    CONCEALMENT = "concealment"
    DANGER_OF_PLACE = "danger_of_place"
    COST = "cost"


class QuestReward(StrEnum):
    RENOWN = "renown"
    POWER = "power"
    KNOWLEDGE = "knowledge"
    ITEM = "item"
    STANDING = "standing"
    OFFICE = "office"
    CURE = "cure"
    PEACE = "peace"


class QuestScale(StrEnum):
    PERSONAL = "personal"
    LEGENDARY = "legendary"
