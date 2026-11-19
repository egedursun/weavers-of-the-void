from enum import StrEnum


class HumourForm(StrEnum):
    WORDPLAY = "wordplay"
    TEASING = "teasing"
    SATIRE = "satire"
    ABSURD = "absurd"
    BODILY = "bodily"
    IRONY = "irony"
    STORYTELLING = "storytelling"
    RITUAL_CLOWNING = "ritual_clowning"


class SpeechVenue(StrEnum):
    ASSEMBLY = "assembly"
    COURT = "court"
    TEMPLE = "temple"
    SQUARE = "square"
    SCHOOL = "school"
    CAMP = "camp"
    OUTLET = "outlet"


class SpeechAim(StrEnum):
    PERSUADE = "persuade"
    TEACH = "teach"
    MOCK = "mock"
    MOURN = "mourn"
    RALLY = "rally"
    DEFEND = "defend"
    ACCUSE = "accuse"
