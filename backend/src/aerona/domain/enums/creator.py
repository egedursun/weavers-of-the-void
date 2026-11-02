from enum import StrEnum


class CreatorPassion(StrEnum):
    ORDER = "order"
    CHAOS = "chaos"
    BEAUTY = "beauty"
    KNOWLEDGE = "knowledge"
    WAR = "war"
    MERCY = "mercy"
    CREATION = "creation"
    SILENCE = "silence"


class CreatorMoodAxis(StrEnum):
    CONTENTMENT = "contentment"
    ANGER = "anger"
    INTEREST = "interest"
    LONELINESS = "loneliness"


class CreatorMoodLabel(StrEnum):
    ANGRY = "angry"
    DISTANT = "distant"
    LONELY = "lonely"
    CONTENT = "content"
    UNEASY = "uneasy"
    SERENE = "serene"


class CreatorSignKind(StrEnum):
    WRATH = "wrath"
    GRACE = "grace"
    SILENCE = "silence"
    DREAM = "dream"
