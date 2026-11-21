from enum import StrEnum


class LandUseRule(StrEnum):
    ALLOWED_USES = "allowed_uses"
    BANNED_USES = "banned_uses"
    HEIGHT_LIMIT = "height_limit"
    DENSITY_LIMIT = "density_limit"
    BUILD_MATERIAL = "build_material"
    FIRE_SPACING = "fire_spacing"
    FRONTAGE_RULE = "frontage_rule"
    GREEN_SHARE = "green_share"


class RuleMaker(StrEnum):
    COUNCIL = "council"
    RULER = "ruler"
    GUILD = "guild"
    FAITH = "faith"


class MunicipalService(StrEnum):
    REFUSE = "refuse"
    LIGHTING = "lighting"
    WATER_DISTRIBUTION = "water_distribution"
    STREET_CLEANING = "street_cleaning"
    NIGHT_WATCH = "night_watch"
    BURIAL_GROUND = "burial_ground"
    MARKET_INSPECTION = "market_inspection"


class ConurbationGovernance(StrEnum):
    ONE_COUNCIL = "one_council"
    FEDERATED_COUNCILS = "federated_councils"
    RULED_BY_CORE = "ruled_by_core"
