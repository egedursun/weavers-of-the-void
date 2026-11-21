from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.city_rules import ConurbationGovernance, LandUseRule, MunicipalService

CONURBATION_GOVERNANCE = total(
    ConurbationGovernance,
    {
        ConurbationGovernance.ONE_COUNCIL: Defined(
            "one council", checked_by=("engine.city_rules.conurbations.share_unrest",), used_by=("engine.city_rules.conurbations.SPREADING_LAWS",)
        ),
        ConurbationGovernance.FEDERATED_COUNCILS: Defined(
            "councils joined in federation", checked_by=(), used_by=("db.tables.city_rules.ConurbationRow", "engine.city_rules.conurbations.grow_together")
        ),
        ConurbationGovernance.RULED_BY_CORE: Defined("the rule of its core", checked_by=(), used_by=("engine.city_rules.conurbations.SPREADING_LAWS",)),
    },
)

LAND_USE_RULE = total(
    LandUseRule,
    {
        LandUseRule.ALLOWED_USES: Defined("Allowed uses", checked_by=("engine.city_rules.effects.use_barred",), used_by=("engine.city_rules.effects.ZONING",)),
        LandUseRule.BANNED_USES: Defined("Banned uses", checked_by=("engine.city_rules.effects.use_barred",), used_by=("engine.city_rules.effects.ZONING",)),
        LandUseRule.HEIGHT_LIMIT: Defined("Height limit", checked_by=("engine.city_rules.effects.housing_cap",), used_by=()),
        LandUseRule.DENSITY_LIMIT: Defined("Density limit", checked_by=("engine.city_rules.effects.level_cap",), used_by=()),
        LandUseRule.BUILD_MATERIAL: Defined(
            "Build material", checked_by=("engine.city_rules.effects.required_material",), used_by=("engine.city_rules.effects.FIRE_RULES",)
        ),
        LandUseRule.FIRE_SPACING: Defined(
            "Fire spacing",
            checked_by=(),
            used_by=(
                "db.tables.city_rules.LandUseRuleRow",
                "engine.city_rules.effects.FIRE_RULES",
                "engine.city_rules.land.apply_legacy",
                "engine.city_rules.land.crowded_towns",
            ),
        ),
        LandUseRule.FRONTAGE_RULE: Defined(
            "Frontage rule", checked_by=("engine.city_rules.effects.amenity_of",), used_by=("engine.city_rules.land.apply_legacy",)
        ),
        LandUseRule.GREEN_SHARE: Defined("Green share", checked_by=("engine.city_rules.effects.amenity_of",), used_by=()),
    },
)

MUNICIPAL_SERVICE = total(
    MunicipalService,
    {
        MunicipalService.REFUSE: Defined(
            "Refuse",
            checked_by=("engine.city_rules.effects.SERVICE_COVERS", "engine.city_rules.services.act"),
            used_by=("db.tables.city_rules.MunicipalServiceRow",),
        ),
        MunicipalService.LIGHTING: Defined("Lighting", checked_by=("engine.city_rules.services.act",), used_by=()),
        MunicipalService.WATER_DISTRIBUTION: Defined(
            "Water distribution", checked_by=("engine.city_rules.effects.SERVICE_COVERS",), used_by=("engine.city_rules.services.apply_legacy",)
        ),
        MunicipalService.STREET_CLEANING: Defined("Street cleaning", checked_by=("engine.city_rules.effects.SERVICE_COVERS",), used_by=()),
        MunicipalService.NIGHT_WATCH: Defined(
            "Night watch", checked_by=("engine.city_rules.effects.SERVICE_COVERS",), used_by=("engine.city_rules.services.LEGACY_OF",)
        ),
        MunicipalService.BURIAL_GROUND: Defined(
            "Burial ground", checked_by=("engine.city_rules.effects.SERVICE_COVERS",), used_by=("engine.city_rules.services.LEGACY_OF",)
        ),
        MunicipalService.MARKET_INSPECTION: Defined("Market inspection", checked_by=("engine.city_rules.effects.SERVICE_COVERS",), used_by=()),
    },
)
