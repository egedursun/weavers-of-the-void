from functools import cache

from aerona.rules.registry.battle_tables import BattleTerrainRules, BattleWeatherRules, TacticMatchupRules
from aerona.rules.registry.war_depth import SeafaringRules


@cache
def terrain_family(table: BattleTerrainRules) -> dict[tuple[str, str], int]:
    return {
        ("plain", "mounted"): table.plain_mounted_pct,
        ("steppe", "mounted"): table.steppe_mounted_pct,
        ("forest", "mounted"): table.forest_mounted_pct,
        ("forest", "missile"): table.forest_missile_pct,
        ("forest", "beast"): table.forest_beast_pct,
        ("jungle", "mounted"): table.jungle_mounted_pct,
        ("jungle", "missile"): table.jungle_missile_pct,
        ("jungle", "beast"): table.jungle_beast_pct,
        ("hills", "mounted"): table.hills_mounted_pct,
        ("hills", "missile"): table.hills_missile_pct,
        ("mountains", "mounted"): table.mountains_mounted_pct,
        ("mountains", "engineer"): table.mountains_engineer_pct,
        ("mountains", "beast"): table.mountains_beast_pct,
        ("high_pass", "mounted"): table.high_pass_mounted_pct,
        ("high_pass", "engineer"): table.high_pass_engineer_pct,
        ("marsh", "mounted"): table.marsh_mounted_pct,
        ("marsh", "infantry"): table.marsh_infantry_pct,
        ("marsh", "beast"): table.marsh_beast_pct,
        ("desert", "infantry"): table.desert_infantry_pct,
        ("tundra", "infantry"): table.tundra_infantry_pct,
        ("tundra", "mounted"): table.tundra_mounted_pct,
        ("ice_sheet", "infantry"): table.ice_sheet_infantry_pct,
        ("ice_sheet", "mounted"): table.ice_sheet_mounted_pct,
        ("river_valley", "mounted"): table.river_valley_mounted_pct,
        ("urban", "mounted"): table.urban_mounted_pct,
        ("urban", "engineer"): table.urban_engineer_pct,
        ("underground", "missile"): table.underground_missile_pct,
        ("underground", "mounted"): table.underground_mounted_pct,
        ("crystal_field", "magic"): table.crystal_field_magic_pct,
        ("flesh", "magic"): table.flesh_magic_pct,
        ("flesh", "beast"): table.flesh_beast_pct,
        ("void_shore", "exotic"): table.void_shore_exotic_pct,
        ("void_shore", "magic"): table.void_shore_magic_pct,
        ("canyon", "mounted"): table.canyon_mounted_pct,
        ("canyon", "missile"): table.canyon_missile_pct,
        ("ruin_field", "mounted"): table.ruin_field_mounted_pct,
        ("volcanic", "infantry"): table.volcanic_infantry_pct,
    }


@cache
def terrain_defender(table: BattleTerrainRules) -> dict[str, int]:
    return {
        "hills": table.hills_defender_pct,
        "mountains": table.mountains_defender_pct,
        "high_pass": table.high_pass_defender_pct,
        "urban": table.urban_defender_pct,
        "river_valley": table.river_valley_defender_pct,
        "canyon": table.canyon_defender_pct,
    }


@cache
def kind_terrain(table: BattleTerrainRules) -> dict[tuple[str, str], int]:
    return {
        ("skirmishers", "forest"): table.skirmishers_forest_pct,
        ("skirmishers", "jungle"): table.skirmishers_jungle_pct,
        ("skirmishers", "hills"): table.skirmishers_hills_pct,
        ("horse_archers", "steppe"): table.horse_archers_steppe_pct,
        ("horse_archers", "plain"): table.horse_archers_plain_pct,
        ("light_cavalry", "plain"): table.light_cavalry_plain_pct,
        ("light_cavalry", "steppe"): table.light_cavalry_steppe_pct,
        ("heavy_cavalry", "plain"): table.heavy_cavalry_plain_pct,
        ("beast_riders", "desert"): table.beast_riders_desert_pct,
        ("chariots", "plain"): table.chariots_plain_pct,
        ("chariots", "hills"): table.chariots_hills_pct,
    }


@cache
def weather_family(table: BattleWeatherRules) -> dict[tuple[str, str], int]:
    return {
        ("rain", "missile"): table.rain_missile_pct,
        ("rain", "mounted"): table.rain_mounted_pct,
        ("downpour", "missile"): table.downpour_missile_pct,
        ("downpour", "mounted"): table.downpour_mounted_pct,
        ("storm", "missile"): table.storm_missile_pct,
        ("storm", "mounted"): table.storm_mounted_pct,
        ("storm", "naval"): table.storm_naval_pct,
        ("fog", "missile"): table.fog_missile_pct,
        ("snow", "missile"): table.snow_missile_pct,
        ("snow", "mounted"): table.snow_mounted_pct,
        ("blizzard", "missile"): table.blizzard_missile_pct,
        ("blizzard", "mounted"): table.blizzard_mounted_pct,
        ("blizzard", "infantry"): table.blizzard_infantry_pct,
        ("heat_wave", "infantry"): table.heat_wave_infantry_pct,
        ("heat_wave", "mounted"): table.heat_wave_mounted_pct,
        ("sandstorm", "missile"): table.sandstorm_missile_pct,
        ("hail", "missile"): table.hail_missile_pct,
        ("magic_storm", "magic"): table.magic_storm_magic_pct,
        ("ash_fall", "missile"): table.ash_fall_missile_pct,
        ("void_rain", "exotic"): table.void_rain_exotic_pct,
        ("eclipse_dark", "missile"): table.eclipse_dark_missile_pct,
    }


@cache
def tactic_matchup(table: TacticMatchupRules) -> dict[tuple[str, str], int]:
    return {
        ("hold_line", "frontal_assault"): table.hold_line_vs_frontal_assault_pct,
        ("hold_line", "wedge"): table.hold_line_vs_wedge_pct,
        ("frontal_assault", "missile_attrition"): table.frontal_assault_vs_missile_attrition_pct,
        ("frontal_assault", "skirmish_harass"): table.frontal_assault_vs_skirmish_harass_pct,
        ("double_envelopment", "frontal_assault"): table.double_envelopment_vs_frontal_assault_pct,
        ("double_envelopment", "hold_line"): table.double_envelopment_vs_hold_line_pct,
        ("double_envelopment", "wedge"): table.double_envelopment_vs_wedge_pct,
        ("feigned_retreat", "frontal_assault"): table.feigned_retreat_vs_frontal_assault_pct,
        ("feigned_retreat", "wedge"): table.feigned_retreat_vs_wedge_pct,
        ("flank_cavalry", "hold_line"): table.flank_cavalry_vs_hold_line_pct,
        ("flank_cavalry", "missile_attrition"): table.flank_cavalry_vs_missile_attrition_pct,
        ("flank_cavalry", "shield_wall"): table.flank_cavalry_vs_shield_wall_pct,
        ("missile_attrition", "hold_line"): table.missile_attrition_vs_hold_line_pct,
        ("missile_attrition", "river_defence"): table.missile_attrition_vs_river_defence_pct,
        ("missile_attrition", "shield_wall"): table.missile_attrition_vs_shield_wall_pct,
        ("shield_wall", "flank_cavalry"): table.shield_wall_vs_flank_cavalry_pct,
        ("shield_wall", "frontal_assault"): table.shield_wall_vs_frontal_assault_pct,
        ("wedge", "shield_wall"): table.wedge_vs_shield_wall_pct,
        ("wedge", "skirmish_harass"): table.wedge_vs_skirmish_harass_pct,
        ("night_raid", "hold_line"): table.night_raid_vs_hold_line_pct,
        ("night_raid", "siege_assault"): table.night_raid_vs_siege_assault_pct,
        ("ambush", "flank_cavalry"): table.ambush_vs_flank_cavalry_pct,
        ("ambush", "frontal_assault"): table.ambush_vs_frontal_assault_pct,
        ("ambush", "wedge"): table.ambush_vs_wedge_pct,
        ("skirmish_harass", "hold_line"): table.skirmish_harass_vs_hold_line_pct,
        ("skirmish_harass", "shield_wall"): table.skirmish_harass_vs_shield_wall_pct,
        ("river_defence", "flank_cavalry"): table.river_defence_vs_flank_cavalry_pct,
        ("river_defence", "frontal_assault"): table.river_defence_vs_frontal_assault_pct,
        ("siege_assault", "hold_line"): table.siege_assault_vs_hold_line_pct,
    }


@cache
def hull_values(table: SeafaringRules) -> dict[tuple[str, str], int]:
    return {
        ("raft", "speed"): table.raft_speed,
        ("raft", "cargo"): table.raft_cargo,
        ("raft", "seaworthiness"): table.raft_seaworthiness,
        ("boat", "speed"): table.boat_speed,
        ("boat", "cargo"): table.boat_cargo,
        ("boat", "seaworthiness"): table.boat_seaworthiness,
        ("galley", "speed"): table.galley_speed,
        ("galley", "cargo"): table.galley_cargo,
        ("galley", "seaworthiness"): table.galley_seaworthiness,
        ("longship", "speed"): table.longship_speed,
        ("longship", "cargo"): table.longship_cargo,
        ("longship", "seaworthiness"): table.longship_seaworthiness,
        ("cog", "speed"): table.cog_speed,
        ("cog", "cargo"): table.cog_cargo,
        ("cog", "seaworthiness"): table.cog_seaworthiness,
        ("carrack", "speed"): table.carrack_speed,
        ("carrack", "cargo"): table.carrack_cargo,
        ("carrack", "seaworthiness"): table.carrack_seaworthiness,
        ("warship", "speed"): table.warship_speed,
        ("warship", "cargo"): table.warship_cargo,
        ("warship", "seaworthiness"): table.warship_seaworthiness,
        ("light_sailer", "speed"): table.light_sailer_speed,
        ("light_sailer", "cargo"): table.light_sailer_cargo,
        ("light_sailer", "seaworthiness"): table.light_sailer_seaworthiness,
        ("bone_hull", "speed"): table.bone_hull_speed,
        ("bone_hull", "cargo"): table.bone_hull_cargo,
        ("bone_hull", "seaworthiness"): table.bone_hull_seaworthiness,
        ("generation_ship", "speed"): table.generation_ship_speed,
        ("generation_ship", "cargo"): table.generation_ship_cargo,
        ("generation_ship", "seaworthiness"): table.generation_ship_seaworthiness,
        ("skyship", "speed"): table.skyship_speed,
        ("skyship", "cargo"): table.skyship_cargo,
        ("skyship", "seaworthiness"): table.skyship_seaworthiness,
        ("living_ship", "speed"): table.living_ship_speed,
        ("living_ship", "cargo"): table.living_ship_cargo,
        ("living_ship", "seaworthiness"): table.living_ship_seaworthiness,
    }
