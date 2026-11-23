from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.environment import LandUse, MovementMedium, MovementWork, PlaceCover, SeasonDating, TerrainTrait, WeatherKind, WeatherTrait, WorldLink

LAND_USE = total(
    LandUse,
    {
        LandUse.CLEARED: Defined("Cleared", checked_by=(), used_by=()),
        LandUse.FARMED: Defined("Farmed", checked_by=(), used_by=()),
        LandUse.GRAZED: Defined("Grazed", checked_by=(), used_by=()),
        LandUse.MINED: Defined("Mined", checked_by=(), used_by=()),
        LandUse.BUILT: Defined("Built", checked_by=(), used_by=()),
    },
)

MOVEMENT_MEDIUM = total(
    MovementMedium,
    {
        MovementMedium.GROUND: Defined("Ground", checked_by=(), used_by=("catalog.movement.MOVEMENT",)),
        MovementMedium.WATER_SURFACE: Defined(
            "Water surface", checked_by=("catalog.movement.by_water", "engine.environment.profile.passability_of"), used_by=("catalog.movement.MOVEMENT",)
        ),
        MovementMedium.UNDER_WATER: Defined("Under water", checked_by=("engine.environment.profile.passability_of",), used_by=("catalog.movement.MOVEMENT",)),
        MovementMedium.AIR: Defined("Air", checked_by=(), used_by=("catalog.movement.MOVEMENT",)),
        MovementMedium.THROUGH_MATTER: Defined(
            "Through matter", checked_by=("engine.environment.profile.passability_of",), used_by=("catalog.movement.MOVEMENT",)
        ),
    },
)

MOVEMENT_WORK = total(
    MovementWork,
    {
        MovementWork.ROADS: Defined("Roads", checked_by=(), used_by=("catalog.movement.MOVEMENT", "engine.environment.profile.passability_of")),
        MovementWork.BRIDGES: Defined("Bridges", checked_by=(), used_by=("catalog.movement.MOVEMENT", "engine.environment.profile.passability_of")),
        MovementWork.HARBOURS: Defined("Harbours", checked_by=(), used_by=("catalog.movement.MOVEMENT", "engine.environment.profile.water_passage")),
    },
)

PLACE_COVER = total(
    PlaceCover,
    {
        PlaceCover.OPEN: Defined("Open", checked_by=(), used_by=("catalog.place_terrain.PLACE_KINDS",)),
        PlaceCover.LIGHT: Defined(
            "Light",
            checked_by=("engine.environment.battleground.cover_defence", "engine.environment.battleground.cover_missile_pct"),
            used_by=("catalog.place_terrain.PLACE_KINDS",),
        ),
        PlaceCover.HEAVY: Defined(
            "Heavy",
            checked_by=(
                "engine.environment.battleground.cover_defence",
                "engine.environment.battleground.cover_missile_pct",
                "engine.military.battle.anchored",
                "engine.military.battle.choose_tactic",
                "engine.military.battle.concealment",
                "engine.military.battle.opening",
            ),
            used_by=("catalog.place_terrain.PLACE_KINDS",),
        ),
    },
)

SEASON_DATING = total(
    SeasonDating,
    {
        SeasonDating.POSITION: Defined("Position", checked_by=("services.books.typed.SEASON_COLUMNS",), used_by=("catalog.season_positions.SEASON_POSITIONS",)),
        SeasonDating.DAY: Defined(
            "Day",
            checked_by=("engine.environment.season_remap.Move.of", "engine.environment.season_remap.remap_positions"),
            used_by=("catalog.season_positions.SEASON_POSITIONS",),
        ),
    },
)

TERRAIN_TRAIT = total(
    TerrainTrait,
    {
        TerrainTrait.WOODED: Defined(
            "Wooded",
            checked_by=(),
            used_by=(
                "catalog.settle_modes.SETTLE_MODES",
                "catalog.terrain.TERRAIN",
                "engine.belonging.sanctuary.HIDING",
                "engine.demography.peoples.COVERED",
                "engine.industry.fuels.COAL_TERRAINS_BLOCKED",
                "engine.military.battle.SHELTER",
                "engine.military.clash.WOODS",
            ),
        ),
        TerrainTrait.OPEN: Defined(
            "Open",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.environment.dangers.OPEN_GROUND",
                "engine.environment.dangers.SNOW_TERRAIN",
                "engine.environment.geomorph.DRY_LANDS",
                "engine.industry.fuels.COAL_TERRAINS_BLOCKED",
            ),
        ),
        TerrainTrait.ROUGH: Defined(
            "Rough",
            checked_by=(),
            used_by=(
                "catalog.dangers.HAZARDS",
                "catalog.terrain.TERRAIN",
                "engine.demography.biology.HEIGHTS",
                "engine.economy.extraction.HILLY",
                "engine.environment.dangers.SLOPES",
                "engine.environment.geology.hard_rock",
                "engine.environment.geology.lay_region",
                "engine.military.clash.DRYLANDS",
            ),
        ),
        TerrainTrait.HIGH: Defined(
            "High",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.belonging.sanctuary.HIDING",
                "engine.demography.peoples.COVERED",
                "engine.demography.peoples.HIGHLAND",
                "engine.economy.route_dangers.PASS_TERRAIN",
                "engine.environment.dangers.HIGH_GROUND",
                "engine.environment.dangers.SLOPES",
                "engine.environment.geology.hard_rock",
                "engine.environment.geomorph.DRY_LANDS",
                "engine.industry.fuels.COAL_TERRAINS_BLOCKED",
                "engine.military.battle.ELEVATED",
                "engine.military.battle.HIGHLANDS",
                "engine.military.battle.SHELTER",
                "engine.military.clash.DRYLANDS",
                "engine.military.clash.HILLS",
                "engine.structures.types.CARVED_GROUND",
            ),
        ),
        TerrainTrait.WET: Defined(
            "Wet",
            checked_by=(),
            used_by=(
                "catalog.settle_modes.SETTLE_MODES",
                "catalog.terrain.TERRAIN",
                "engine.belonging.sanctuary.HIDING",
                "engine.demography.peoples.COVERED",
                "engine.ecology.profiles.WATER",
                "engine.economy.extraction.WETLANDS",
                "engine.environment.dangers.WET_GROUND",
                "engine.environment.geology.sediments",
                "engine.military.battle.SHELTER",
                "engine.military.clash.WETLANDS",
            ),
        ),
        TerrainTrait.ARID: Defined(
            "Arid",
            checked_by=(),
            used_by=(
                "catalog.dangers.HAZARDS",
                "catalog.settle_modes.SETTLE_MODES",
                "catalog.terrain.TERRAIN",
                "engine.demography.peoples.STEPPE",
                "engine.economy.extraction.DRYLANDS",
                "engine.economy.route_dangers.CARAVAN_TERRAIN",
                "engine.environment.geology.sediments",
                "engine.military.clash.DRYLANDS",
                "engine.water.ice.DRY_LANDS",
            ),
        ),
        TerrainTrait.COLD: Defined(
            "Cold",
            checked_by=(),
            used_by=(
                "catalog.dangers.HAZARDS",
                "catalog.terrain.TERRAIN",
                "engine.demography.peoples.SKY_LANDS",
                "engine.economy.route_dangers.PASS_TERRAIN",
                "engine.environment.dangers.SNOW_TERRAIN",
                "engine.environment.geomorph.DRY_LANDS",
                "engine.industry.fuels.COAL_TERRAINS_BLOCKED",
                "engine.military.battle.HIGHLANDS",
                "engine.military.battle.SHELTER",
                "engine.structures.types.CARVED_GROUND",
                "engine.vehicles.caravans.SNOW_GROUNDS",
            ),
        ),
        TerrainTrait.HOT: Defined("Hot", checked_by=(), used_by=("catalog.terrain.TERRAIN", "engine.industry.fuels.COAL_TERRAINS_BLOCKED")),
        TerrainTrait.COASTAL: Defined(
            "Coastal",
            checked_by=(),
            used_by=(
                "catalog.dangers.HAZARDS",
                "catalog.settle_modes.SETTLE_MODES",
                "catalog.terrain.TERRAIN",
                "engine.ecology.profiles.WATER",
                "engine.economy.extraction.SEAS",
                "engine.environment.glaze.SURGED",
                "engine.environment.weather.warm_sea_draw",
                "engine.military.clash.SHORES",
            ),
        ),
        TerrainTrait.WATERY: Defined(
            "Watery",
            checked_by=("engine.couplings.carrion.rest_of", "engine.ecology.beast_ways.habitat_ways", "engine.nature.senses.in_water"),
            used_by=(
                "catalog.settle_modes.SETTLE_MODES",
                "catalog.terrain.TERRAIN",
                "engine.demography.biology.WATERS",
                "engine.environment.glaze.SURGED",
                "engine.environment.profile.afloat",
                "engine.environment.weather.warm_sea_draw",
                "engine.operations.expeditions.ground_of",
                "engine.operations.expeditions.wreck_ground",
                "services.integrity.w52_agent_h.ground_fits",
            ),
        ),
        TerrainTrait.UNDERGROUND: Defined(
            "Underground",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.environment.battleground.war_ground",
                "engine.environment.geomorph.DRY_LANDS",
                "engine.phases.geography.nature_of",
                "engine.structures.types.CARVED_GROUND",
            ),
        ),
        TerrainTrait.BUILT: Defined("Built", checked_by=(), used_by=("catalog.terrain.TERRAIN", "engine.military.aftermath.street_toll")),
        TerrainTrait.AMBUSH_COVER: Defined(
            "Ambush cover",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.demography.peoples.COVERED",
                "engine.military.battle.SHELTER",
                "engine.military.battle.choose_tactic",
                "engine.military.battle.opening",
            ),
        ),
        TerrainTrait.CONFINED: Defined(
            "Confined",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.demography.peoples.COVERED",
                "engine.demography.peoples.HIGHLAND",
                "engine.military.battle.NARROW",
                "engine.structures.types.CARVED_GROUND",
            ),
        ),
        TerrainTrait.SLIPPERY: Defined("Slippery", checked_by=(), used_by=("catalog.terrain.TERRAIN", "engine.military.duels.SLIPPERY")),
        TerrainTrait.NON_MINERAL_GROUND: Defined(
            "Non mineral ground",
            checked_by=(),
            used_by=(
                "catalog.terrain.TERRAIN",
                "engine.environment.geomorph.DRY_LANDS",
                "engine.industry.fuels.COAL_TERRAINS_BLOCKED",
                "engine.military.aftermath.EXOTIC",
            ),
        ),
        TerrainTrait.AIRLESS: Defined("Airless", checked_by=(), used_by=("catalog.terrain.TERRAIN",)),
        TerrainTrait.GASEOUS: Defined("Gaseous", checked_by=(), used_by=("catalog.terrain.TERRAIN",)),
        TerrainTrait.FERTILE: Defined("Fertile", checked_by=(), used_by=("catalog.terrain.TERRAIN", "engine.phases.environment.factor_of")),
    },
)

WEATHER_KIND = total(
    WeatherKind,
    {
        WeatherKind.CLEAR: Defined(
            "Clear", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.environment.weather.draw_weather", "engine.forecasting.works.AIM_WEATHER")
        ),
        WeatherKind.OVERCAST: Defined("Overcast", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.RAIN: Defined(
            "Rain",
            checked_by=(),
            used_by=(
                "catalog.life.powers.FORM_WEATHER",
                "catalog.weather.WEATHER",
                "engine.forecasting.works.AIM_WEATHER",
                "engine.lore.rites.SCHOOL_WEATHER",
                "engine.lore.rites.do_weather",
                "engine.powers.effects.weather",
            ),
        ),
        WeatherKind.DOWNPOUR: Defined("Downpour", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.STORM: Defined(
            "Storm",
            checked_by=(),
            used_by=(
                "catalog.cosmography.PHENOMENON_WEATHER",
                "catalog.life.powers.FORM_WEATHER",
                "catalog.weather.WEATHER",
                "engine.lore.rites.SCHOOL_WEATHER",
            ),
        ),
        WeatherKind.FOG: Defined(
            "Fog",
            checked_by=(
                "engine.military.battle.battle_width",
                "engine.military.battle.choose_tactic",
                "engine.military.battle.concealment",
                "engine.military.battle.opening",
            ),
            used_by=(
                "catalog.cosmography.PHENOMENON_WEATHER",
                "catalog.life.powers.FORM_WEATHER",
                "catalog.weather.WEATHER",
                "engine.lore.rites.SCHOOL_WEATHER",
                "engine.military.battle.weather_now",
            ),
        ),
        WeatherKind.SNOW: Defined("Snow", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.forecasting.works.AIM_WEATHER")),
        WeatherKind.BLIZZARD: Defined("Blizzard", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.HEAT_WAVE: Defined(
            "Heat wave",
            checked_by=(),
            used_by=("catalog.life.powers.FORM_WEATHER", "catalog.weather.WEATHER", "engine.forecasting.works.AIM_WEATHER", "engine.lore.rites.SCHOOL_WEATHER"),
        ),
        WeatherKind.DROUGHT_WIND: Defined(
            "Drought wind",
            checked_by=(),
            used_by=(
                "catalog.cosmography.PHENOMENON_WEATHER",
                "catalog.weather.WEATHER",
                "engine.forecasting.works.AIM_WEATHER",
                "engine.phases.environment.region_years",
            ),
        ),
        WeatherKind.SANDSTORM: Defined("Sandstorm", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.HAIL: Defined("Hail", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.MAGIC_STORM: Defined(
            "Magic storm",
            checked_by=("engine.military.aftermath.flaring_items", "engine.military.battle.backlash"),
            used_by=("catalog.cosmography.PHENOMENON_WEATHER", "catalog.weather.WEATHER", "engine.lore.rites.phenomenon"),
        ),
        WeatherKind.ASH_FALL: Defined(
            "Ash fall", checked_by=("engine.phases.environment.weather_year",), used_by=("catalog.weather.WEATHER", "engine.cosmos.impacts.remember_the_fall")
        ),
        WeatherKind.VOID_RAIN: Defined("Void rain", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_WEATHER", "catalog.weather.WEATHER")),
        WeatherKind.ECLIPSE_DARK: Defined("Eclipse dark", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.AURORA: Defined("Aurora", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_WEATHER", "catalog.weather.WEATHER")),
        WeatherKind.FROST: Defined(
            "Frost", checked_by=("engine.phases.environment.region_years",), used_by=("catalog.weather.WEATHER", "engine.forecasting.works.aimed_weather")
        ),
        WeatherKind.ICE_STORM: Defined(
            "Ice storm", checked_by=("engine.environment.glaze.ColdHarm.note",), used_by=("catalog.weather.WEATHER", "engine.forecasting.works.aimed_weather")
        ),
        WeatherKind.DRIZZLE: Defined("Drizzle", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.SLEET: Defined("Sleet", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.FREEZING_FOG: Defined("Freezing fog", checked_by=(), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.THUNDERSTORM: Defined("Thunderstorm", checked_by=("engine.environment.glaze.ColdHarm.note",), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.TORNADO: Defined("Tornado", checked_by=("engine.environment.glaze.ColdHarm.note",), used_by=("catalog.weather.WEATHER",)),
        WeatherKind.CYCLONE: Defined("Cyclone", checked_by=("engine.environment.glaze.ColdHarm.note",), used_by=("catalog.weather.WEATHER",)),
    },
)

WEATHER_TRAIT = total(
    WeatherTrait,
    {
        WeatherTrait.COLD: Defined(
            "Cold", checked_by=("engine.environment.weather.weather_weights",), used_by=("catalog.weather.WEATHER", "engine.demography.biology.trait_edge")
        ),
        WeatherTrait.SNOW_COVER: Defined(
            "Snow cover", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.battle.modifier", "engine.military.clash.wanted_traits")
        ),
        WeatherTrait.WET: Defined("Wet", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.duels.set_footing")),
        WeatherTrait.LIQUID: Defined("Liquid", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.battle.weather_factor")),
        WeatherTrait.HOT: Defined(
            "Hot", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.demography.biology.trait_edge", "engine.environment.weather.SUMMER_TRAITS")
        ),
        WeatherTrait.DRY: Defined(
            "Dry", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.demography.biology.trait_edge", "engine.environment.weather.SUMMER_TRAITS")
        ),
        WeatherTrait.WINDY: Defined(
            "Windy",
            checked_by=(),
            used_by=(
                "catalog.weather.WEATHER",
                "engine.military.battle.weather_factor",
                "engine.military.naval.fleet_power",
                "engine.military.vessels.arms_weight",
            ),
        ),
        WeatherTrait.STORM: Defined(
            "Storm",
            checked_by=(),
            used_by=(
                "catalog.weather.WEATHER",
                "engine.intrigue.schemes.conditions",
                "engine.military.naval.weather_the_storm",
                "engine.military.vessels.seas",
                "engine.military.vessels.weather_leg",
                "engine.plants.bodies.weather_crops",
            ),
        ),
        WeatherTrait.COVERING: Defined("Covering", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.intrigue.schemes.conditions")),
        WeatherTrait.SLOWING: Defined("Slowing", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.campaign.march_budget")),
        WeatherTrait.HEAVY: Defined("Heavy", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.battle.modifier")),
        WeatherTrait.EXTREME: Defined("Extreme", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.phases.environment.region_years")),
        WeatherTrait.ICY: Defined("Icy", checked_by=(), used_by=("catalog.weather.WEATHER", "engine.military.vessels.weather_leg")),
    },
)

WORLD_LINK = total(
    WorldLink,
    {
        WorldLink.WORLD: Defined(
            "World",
            checked_by=("engine.environment.season_remap.of_world", "services.books.typed.TypedIndex.season_name"),
            used_by=("catalog.season_positions.SEASON_POSITIONS",),
        ),
        WorldLink.ENTITY: Defined("Entity", checked_by=("engine.environment.season_remap.of_world",), used_by=("catalog.season_positions.SEASON_POSITIONS",)),
        WorldLink.INCIDENT: Defined("Incident", checked_by=(), used_by=("catalog.season_positions.SEASON_POSITIONS",)),
    },
)
