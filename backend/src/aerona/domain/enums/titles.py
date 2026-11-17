from enum import StrEnum


class TitleTier(StrEnum):
    LOCAL = "local"
    DISTRICT = "district"
    REGIONAL = "regional"
    REALM = "realm"
    IMPERIAL = "imperial"
    FAITH_LOCAL = "faith_local"
    FAITH_HIGH = "faith_high"
    FAITH_SUPREME = "faith_supreme"
    MILITARY = "military"
    GUILD = "guild"


class TitleTenure(StrEnum):
    FOUNDED = "founded"
    INHERITED = "inherited"
    CREATED = "created"
    USURPED = "usurped"
    GRANTED = "granted"
    RESTORED = "restored"
