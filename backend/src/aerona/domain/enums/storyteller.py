from enum import StrEnum


class StorytellerProfile(StrEnum):
    STEADY = "steady"
    RISING = "rising"
    CYCLIC = "cyclic"
    CHAOTIC = "chaotic"


class TensionBand(StrEnum):
    QUIET = "quiet"
    IN_BAND = "in_band"
    HEATED = "heated"


class SpontaneousKind(StrEnum):
    BEAST_AWAKENING = "beast_awakening"
    RAID = "raid"
    COMET = "comet"
    PLAGUE = "plague"
    CLAIMANT = "claimant"


class RecoveryKind(StrEnum):
    HARVEST = "harvest"
    PEACE_ENVOY = "peace_envoy"
    HEALER_BIRTH = "healer_birth"
