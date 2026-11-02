from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CartographyRules:
    grid_spacing: int = rule(22, 8, 200, RuleGroup.CARTOGRAPHY, "Map grid spacing: one cell per square of this size (map units)")
    window_padding: int = rule(900, 100, 10000, RuleGroup.CARTOGRAPHY, "Map margin computed around the outermost positioned record (map units)")
    region_radius: int = rule(320, 50, 5000, RuleGroup.CARTOGRAPHY, "Farthest a top-level region grows from its seed (map units)")
    fog_rings: int = rule(4, 0, 50, RuleGroup.CARTOGRAPHY, "Rings of fogged frontier cells drawn around the known world")
    wide_water_min_cells: int = rule(40, 1, 100000, RuleGroup.CARTOGRAPHY, "Cells a body of water needs to count as open water for water-region seeds")
    seed_attempts: int = rule(80, 1, 2000, RuleGroup.CARTOGRAPHY, "Candidate cells tried when placing a new region seed")
    seed_spacing: int = rule(300, 10, 5000, RuleGroup.CARTOGRAPHY, "Preferred distance of a new region seed from the nearest existing seed (map units)")
    seed_spacing_jitter: int = rule(40, 0, 1000, RuleGroup.CARTOGRAPHY, "Random score added when spacing a new region seed (map units)")
    first_seed_jitter: int = rule(80, 0, 1000, RuleGroup.CARTOGRAPHY, "Random score added when placing the first region seed near the centre (map units)")
    seed_relocation_rings: int = rule(40, 1, 1000, RuleGroup.CARTOGRAPHY, "Neighbour rings searched when a region seed sits on the wrong terrain")
    point_attempts: int = rule(24, 1, 1000, RuleGroup.CARTOGRAPHY, "Candidate cells tried when placing a marker")
    point_parent_rings: int = rule(2, 0, 20, RuleGroup.CARTOGRAPHY, "Neighbour rings around a parent marker in which a child marker is placed")
    point_parent_depth: int = rule(8, 1, 100, RuleGroup.CARTOGRAPHY, "Deepest parent chain followed when placing markers")
    point_score_jitter_pct: int = rule(50, 0, 1000, RuleGroup.CARTOGRAPHY, "Random share added to a marker's site score (%)")
    settlement_coast_score_pct: int = rule(100, 0, 1000, RuleGroup.CARTOGRAPHY, "Settlement site score for touching water (%)")
    settlement_lowland_score_pct: int = rule(150, 0, 1000, RuleGroup.CARTOGRAPHY, "Settlement site score lost per unit of elevation (%)")
    resource_highland_score_pct: int = rule(100, 0, 1000, RuleGroup.CARTOGRAPHY, "Resource site score gained per unit of elevation (%)")
    sea_level_samples: int = rule(4000, 100, 100000, RuleGroup.CARTOGRAPHY, "Elevation samples used to find the sea level")
    sea_level_sample_trim: int = rule(
        20, 0, 1000, RuleGroup.CARTOGRAPHY, "Extreme elevation samples ignored at each end when finding the lowest and highest ground"
    )
    min_extent_width: int = rule(200, 10, 10000, RuleGroup.CARTOGRAPHY, "Narrowest framing of the known world (map units)")
    min_extent_height: int = rule(140, 10, 10000, RuleGroup.CARTOGRAPHY, "Shortest framing of the known world (map units)")
    flood_elevation_cost: int = rule(40, 0, 1000, RuleGroup.CARTOGRAPHY, "Region growth: cost per unit of elevation change between cells")
    flood_coast_cost: int = rule(30, 0, 1000, RuleGroup.CARTOGRAPHY, "Region growth: cost of crossing a coastline")
    climate_biome_count: int = rule(3, 1, 10, RuleGroup.CARTOGRAPHY, "Biomes listed in a region's climate")
    climate_min_share_pct: int = rule(12, 0, 100, RuleGroup.CARTOGRAPHY, "Smallest share of a region a biome must cover to be listed in its climate (%)")
    mountainous_elevation_pct: int = rule(45, 0, 100, RuleGroup.CARTOGRAPHY, "Average elevation above which a region counts as mountainous (%)")
    hilly_elevation_pct: int = rule(22, 0, 100, RuleGroup.CARTOGRAPHY, "Average elevation above which a region counts as hilly (%)")
    deep_water_depth_pct: int = rule(35, 0, 100, RuleGroup.CARTOGRAPHY, "Depth below which water counts as deep (%)")
    shore_elevation_pct: int = rule(5, 0, 100, RuleGroup.CARTOGRAPHY, "Land below this elevation is shore (%)")
    lowland_elevation_pct: int = rule(32, 0, 100, RuleGroup.CARTOGRAPHY, "Land below this elevation is lowland (%)")
    hill_elevation_pct: int = rule(58, 0, 100, RuleGroup.CARTOGRAPHY, "Land below this elevation is hills (%)")
    mountain_elevation_pct: int = rule(80, 0, 100, RuleGroup.CARTOGRAPHY, "Land below this elevation is mountains; above it, peaks (%)")
    wet_lowland_moisture_pct: int = rule(56, 0, 200, RuleGroup.CARTOGRAPHY, "Lowland moisture above which the wet lowland biome grows (%)")
    mid_lowland_moisture_pct: int = rule(44, 0, 200, RuleGroup.CARTOGRAPHY, "Lowland moisture above which the middle lowland biome grows (%)")
    wet_hill_moisture_pct: int = rule(50, 0, 200, RuleGroup.CARTOGRAPHY, "Hill moisture above which the wet hill biome grows (%)")
