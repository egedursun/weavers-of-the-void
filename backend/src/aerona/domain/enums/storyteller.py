from enum import StrEnum


class StorytellerProfile(StrEnum):
    STEADY = "steady"
    RISING = "rising"
    CYCLIC = "cyclic"
    CHAOTIC = "chaotic"
    SLOW_BURN = "slow_burn"
    EPISODIC = "episodic"
    GENTLE = "gentle"
    SEASONAL = "seasonal"


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


class PaletteSubsystem(StrEnum):
    WAR = "war"
    FAITH = "faith"
    ECONOMY = "economy"
    ECOLOGY = "ecology"
    DISEASE = "disease"
    CLIMATE = "climate"
    COSMOS = "cosmos"
    MADE_MINDS = "made_minds"
    NETWORKS = "networks"
    REPLICATORS = "replicators"
    POWERS = "powers"
    SOURCES = "sources"
    CONCEALMENT = "concealment"
    LIVING_CRAFT = "living_craft"
    GODS = "gods"
    OUTER_BEINGS = "outer_beings"
    HOUSEHOLDS = "households"
    MIGRATION = "migration"
    IDEOLOGY = "ideology"
    ART = "art"


class PaletteDirection(StrEnum):
    DISRUPTION = "disruption"
    RECOVERY = "recovery"
