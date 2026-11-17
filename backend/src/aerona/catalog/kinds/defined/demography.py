from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.demography import CohortCondition, MartialStyle

COHORT_CONDITION = total(
    CohortCondition,
    {
        CohortCondition.NONE: Defined(
            "None",
            checked_by=(
                "engine.demography.basket.sicken",
                "engine.demography.cohorts.rebalance_classes",
                "engine.demography.cohorts.reconcile",
                "engine.demography.labour.CONDITION_WORK",
                "engine.demography.mobility.bitter_emigration",
                "engine.military.aftermath.send_home_wounded",
            ),
            used_by=(
                "engine.demography.bound.move_people",
                "engine.demography.cohorts.apply_flow",
                "engine.demography.cohorts.rebalance_classes",
                "engine.demography.cohorts.seed",
                "engine.demography.control.move_cohort",
                "engine.demography.mobility.settle_captives",
                "engine.demography.promotion.sync_maimed",
                "engine.demography.promotion.sync_veterans",
                "engine.demography.vital.give_births",
                "engine.disease.sickness.shift",
                "engine.happenings.profile.even_split",
                "engine.structures.profiles.LIVING_ADULTS",
                "services.player.peoples.SetCohort",
            ),
        ),
        CohortCondition.VETERAN: Defined(
            "Veteran",
            checked_by=(
                "engine.demography.labour.CONDITION_WORK",
                "engine.demography.promotion.sync_veterans",
                "engine.honours.veterans.band_veterans",
                "engine.honours.veterans.veterans_in",
            ),
            used_by=("engine.demography.promotion.sync_veterans", "engine.military.aftermath.recover_wounded", "engine.structures.profiles.LIVING_ADULTS"),
        ),
        CohortCondition.SICK: Defined(
            "Sick",
            checked_by=(
                "agents.context.society.sickness_lines",
                "api.views.disease.disease_sick",
                "engine.demography.cohorts.weights_for",
                "engine.demography.labour.condition_work",
                "engine.demography.labour.fighting_age",
                "engine.demography.vital.one_year",
                "engine.disease.sickness.sicken_cohorts",
            ),
            used_by=("engine.demography.basket.sicken", "engine.disease.sickness.shift", "engine.military.aftermath.RECOVERING"),
        ),
        CohortCondition.ENSLAVED: Defined(
            "Enslaved",
            checked_by=(
                "engine.demography.bound.move_people",
                "engine.demography.control.move_cohort",
                "engine.demography.labour.CONDITION_WORK",
                "engine.demography.labour.allocate",
            ),
            used_by=("engine.demography.control.move_cohort", "engine.demography.mobility.settle_captives", "engine.structures.profiles.LIVING_ADULTS"),
        ),
        CohortCondition.CAPTIVE: Defined(
            "Captive",
            checked_by=(
                "engine.demography.bound.move_people",
                "engine.demography.labour.CONDITION_WORK",
                "engine.demography.labour.allocate",
                "engine.demography.mobility.settle_captives",
            ),
            used_by=("db.tables.military.CaptiveCohortRow", "engine.demography.cohorts.FLOW_CONDITION"),
        ),
        CohortCondition.MAIMED: Defined(
            "Maimed",
            checked_by=("engine.demography.labour.condition_work", "engine.demography.labour.fighting_age", "engine.demography.promotion.sync_maimed"),
            used_by=("engine.demography.promotion.sync_maimed",),
        ),
    },
)

MARTIAL_STYLE = total(
    MartialStyle,
    {
        MartialStyle.SHIELDWALL: Defined(
            "Shieldwall",
            checked_by=(),
            used_by=(
                "catalog.units.ROLE_STYLES",
                "db.tables.military.ArmyTemplateRow",
                "engine.demography.peoples.martial_of",
                "engine.military.marshal.draw_template",
            ),
        ),
        MartialStyle.HORSE_ARCHER: Defined("Horse archer", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.SKIRMISHER: Defined("Skirmisher", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.CHARIOT: Defined("Chariot", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.PHALANX: Defined("Phalanx", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.SHOCK: Defined("Shock", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.NAVAL_RAIDER: Defined("Naval raider", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.SIEGE_ENGINEER: Defined("Siege engineer", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.WAR_MAGIC: Defined("War magic", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.BEAST_WAR: Defined("Beast war", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.MECHANISED: Defined("Mechanised", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.AIR_MOBILE: Defined("Air mobile", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.GUERRILLA: Defined("Guerrilla", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.DRONE_WAR: Defined("Drone war", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.ORBITAL: Defined("Orbital", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
        MartialStyle.COMBINED_ARMS: Defined("Combined arms", checked_by=(), used_by=("catalog.units.ROLE_STYLES", "engine.demography.peoples.martial_of")),
    },
)
