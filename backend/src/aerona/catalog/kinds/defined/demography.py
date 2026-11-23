from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.demography import MartialStyle

MARTIAL_STYLE = total(
    MartialStyle,
    {
        MartialStyle.SHIELDWALL: Defined(
            "Shieldwall",
            checked_by=(),
            used_by=(
                "catalog.units.ROLE_STYLES",
                "db.tables.military.ArmyProfileRow",
                "db.tables.military.ArmyTemplateRow",
                "engine.demography.peoples.martial_of",
                "engine.military.marshal.draw_template",
                "engine.military.units.doctrine_of",
                "engine.military.units.profile_of",
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
