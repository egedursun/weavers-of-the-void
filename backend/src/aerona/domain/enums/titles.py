from enum import StrEnum


class TitleRank(StrEnum):
    LORDSHIP = "lordship"
    COUNTY = "county"
    DUCHY = "duchy"
    KINGDOM = "kingdom"
    EMPIRE = "empire"
    SEE = "see"
    ARCHSEE = "archsee"
    HIGH_SEAT = "high_seat"
    CAPTAINCY = "captaincy"
    GUILDMASTERSHIP = "guildmastership"


class TitleTenure(StrEnum):
    FOUNDED = "founded"
    INHERITED = "inherited"
    CREATED = "created"
    USURPED = "usurped"
    GRANTED = "granted"
    RESTORED = "restored"
