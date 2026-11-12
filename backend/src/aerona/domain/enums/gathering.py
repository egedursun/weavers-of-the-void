from enum import StrEnum


class GatheringKind(StrEnum):
    FEAST = "feast"
    WEDDING = "wedding"
    FUNERAL = "funeral"
    CORONATION = "coronation"
    TOURNAMENT = "tournament"
    HUNT = "hunt"
    PILGRIMAGE = "pilgrimage"
    COUNCIL = "council"
    SUMMIT = "summit"
    FESTIVAL = "festival"
    FAIR = "fair"
    GAMES = "games"
    PERFORMANCE = "performance"
    TRIAL = "trial"
    EXECUTION = "execution"
    PROCESSION = "procession"
    MILESTONE = "milestone"
    WAKE = "wake"
    EXAMINATION = "examination"


class GatheringStatus(StrEnum):
    PLANNED = "planned"
    HELD = "held"
    DISRUPTED = "disrupted"
    CANCELLED = "cancelled"


class GatheringOutcome(StrEnum):
    CONVIVIAL = "convivial"
    UNEVENTFUL = "uneventful"
    QUARRELSOME = "quarrelsome"
    VIOLENT = "violent"
    MASSACRE = "massacre"


class Milestone(StrEnum):
    BIRTH = "birth"
    COMING_OF_AGE = "coming_of_age"
    ANNIVERSARY = "anniversary"


class AttendanceReason(StrEnum):
    HOST = "host"
    KIN = "kin"
    FRIEND = "friend"
    OBLIGATION = "obligation"
    FAITH = "faith"
    RENOWN = "renown"
    NEIGHBOUR = "neighbour"
    SUMMONED = "summoned"


class GuestRole(StrEnum):
    HOST = "host"
    GUEST = "guest"
    HONOURED = "honoured"
    CONTESTANT = "contestant"
    PERFORMER = "performer"
    ACCUSED = "accused"
    MOURNED = "mourned"
    WEDDED = "wedded"
    CROWNED = "crowned"
    ENVOY = "envoy"


class CollectionKind(StrEnum):
    WAR = "war"
    BATTLE = "battle"
    SIEGE = "siege"
    DUEL = "duel"
    ABDUCTION = "abduction"
    BEAST_ATTACK = "beast_attack"
    RAID = "raid"
    PERSECUTION = "persecution"
    PURGE = "purge"
    INSURRECTION = "insurrection"
    COUP = "coup"
    SUCCESSION_CRISIS = "succession_crisis"
    OCCUPATION = "occupation"
    JOURNEY = "journey"
    PILGRIMAGE = "pilgrimage"
    COMPETITION = "competition"
    PERFORMANCE = "performance"
    PROCESSION = "procession"
    CEREMONY = "ceremony"
    WEDDING = "wedding"
    FUNERAL = "funeral"
    CORONATION = "coronation"
    FEAST = "feast"
    TOURNAMENT = "tournament"
    HUNT = "hunt"
    COUNCIL = "council"
    SUMMIT = "summit"
    PLAGUE = "plague"
    FAMINE = "famine"
    MIGRATION = "migration"
    FOUNDING = "founding"
    THEFT = "theft"
    INVESTIGATION = "investigation"
    TRIAL = "trial"
    CONVERSION_WAVE = "conversion_wave"
    SCHISM = "schism"
    EXCAVATION = "excavation"
    HEROQUEST = "heroquest"
    RIOT = "riot"
    PANIC = "panic"
    MOVEMENT = "movement"
    STORYLET = "storylet"


class CollectionRole(StrEnum):
    LEADER = "leader"
    MEMBER = "member"
    VICTIM = "victim"
    WITNESS = "witness"
    HOST = "host"
    GUEST = "guest"
    WINNER = "winner"
    LOSER = "loser"
    FOUNDER = "founder"
    ACCUSED = "accused"
    FINDER = "finder"
    PLACE = "place"
