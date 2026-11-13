from types import MappingProxyType

from aerona.catalog.structures import acting, acting_set
from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import CargoClass, HousingLevel, Morphology, RacketKind, UrbanService

K = StructureKind
V = UrbanService
C = CommodityKind
D = DistrictKind

SERVICE_OF: MappingProxyType[StructureKind, UrbanService] = acting(
    {
        K.AQUEDUCT: V.WATER,
        K.FOUNTAIN: V.WATER,
        K.TEMPLE: V.FAITH,
        K.SHRINE: V.FAITH,
        K.MONASTERY: V.FAITH,
        K.WATCHTOWER: V.WATCH,
        K.FORT: V.WATCH,
        K.CITADEL: V.WATCH,
        K.COURT: V.WATCH,
        K.HOSPITAL: V.HEALING,
        K.MARKET: V.MARKET,
        K.CARAVANSERAI: V.MARKET,
        K.SCHOOL: V.SCHOOL,
        K.ACADEMY: V.SCHOOL,
        K.LIBRARY: V.SCHOOL,
        K.BATHHOUSE: V.BATH,
        K.FIREHOUSE: V.FIRE,
        K.APOTHECARY: V.HEALING,
        K.BARRACKS: V.WATCH,
    }
)
AMENITIES = acting_set(
    frozenset(
        {
            K.TEMPLE,
            K.SHRINE,
            K.MARKET,
            K.BATHHOUSE,
            K.MONUMENT,
            K.THEATRE,
            K.ARENA,
            K.AQUEDUCT,
            K.LIBRARY,
            K.WONDER,
            K.FOUNTAIN,
            K.PARK,
            K.TAVERN,
            K.MUSEUM,
            K.PLAZA,
        }
    )
)
NUISANCES = acting_set(frozenset({K.TANNERY, K.PRISON, K.FORGE, K.MILL, K.MINE, K.QUARRY, K.SLAUGHTERHOUSE, K.CHARCOAL_KILN, K.FISHERY, K.SAWMILL}))
NUISANCE_DISTRICTS = frozenset({D.SLUMS, D.NECROPOLIS})
HOME_DISTRICT: MappingProxyType[StructureKind, DistrictKind] = acting(
    {
        K.TEMPLE: D.TEMPLE_QUARTER,
        K.SHRINE: D.TEMPLE_QUARTER,
        K.MONASTERY: D.TEMPLE_QUARTER,
        K.MARKET: D.MARKET,
        K.CARAVANSERAI: D.MARKET,
        K.KONTOR: D.MARKET,
        K.HARBOUR: D.HARBOUR,
        K.WAREHOUSE: D.HARBOUR,
        K.FORGE: D.CRAFT_QUARTER,
        K.TANNERY: D.CRAFT_QUARTER,
        K.SLAUGHTERHOUSE: D.CRAFT_QUARTER,
        K.WORKSHOP: D.CRAFT_QUARTER,
        K.CITADEL: D.CITADEL,
        K.PALACE: D.PALACE,
        K.NECROPOLIS: D.NECROPOLIS,
        K.TOMB: D.NECROPOLIS,
        K.COURT: D.PALACE,
        K.TOWN_HALL: D.PALACE,
        K.PRISON: D.CITADEL,
        K.BARRACKS: D.CITADEL,
        K.SIEGE_WORKSHOP: D.CITADEL,
        K.BREWERY: D.CRAFT_QUARTER,
        K.SAWMILL: D.CRAFT_QUARTER,
        K.CHARCOAL_KILN: D.CRAFT_QUARTER,
        K.GUILDHALL: D.CRAFT_QUARTER,
        K.FISHERY: D.HARBOUR,
        K.SHIPYARD: D.HARBOUR,
        K.MINT: D.MARKET,
        K.BANK: D.MARKET,
        K.TAVERN: D.RESIDENTIAL,
        K.STABLES: D.FARMLAND,
        K.GRANARY: D.FARMLAND,
        K.MILL: D.FARMLAND,
        K.SCHOOL: D.CIVIC_QUARTER,
        K.LIBRARY: D.CIVIC_QUARTER,
        K.ACADEMY: D.CIVIC_QUARTER,
        K.HOSPITAL: D.CIVIC_QUARTER,
        K.APOTHECARY: D.CIVIC_QUARTER,
        K.BATHHOUSE: D.CIVIC_QUARTER,
        K.THEATRE: D.CIVIC_QUARTER,
        K.ARENA: D.CIVIC_QUARTER,
        K.MUSEUM: D.CIVIC_QUARTER,
        K.ALMSHOUSE: D.CIVIC_QUARTER,
        K.ORPHANAGE: D.CIVIC_QUARTER,
        K.TRAINING_GROUND: D.CIVIC_QUARTER,
        K.PARK: D.GARDENS,
        K.FOUNTAIN: D.GARDENS,
        K.PLAZA: D.GARDENS,
        K.FOUNDRY: D.INDUSTRIAL,
        K.SMELTER: D.INDUSTRIAL,
        K.REFINERY: D.INDUSTRIAL,
        K.POWER_PLANT: D.INDUSTRIAL,
        K.TEXTILE_MILL: D.INDUSTRIAL,
        K.GLASSWORKS: D.INDUSTRIAL,
        K.PAPER_MILL: D.INDUSTRIAL,
        K.DYE_WORKS: D.INDUSTRIAL,
        K.EXCHANGE: D.BUSINESS,
        K.LABORATORY: D.RESEARCH,
        K.UNIVERSITY: D.UNIVERSITY,
        K.RAIL_STATION: D.TRANSPORT_HUB,
        K.AIRFIELD: D.TRANSPORT_HUB,
        K.SPACEPORT: D.TRANSPORT_HUB,
        K.ARSENAL: D.MILITARY_BASE,
        K.STADIUM: D.ENTERTAINMENT,
        K.OPERA_HOUSE: D.ENTERTAINMENT,
        K.GALLERY: D.ENTERTAINMENT,
        K.CONSERVATORY: D.ENTERTAINMENT,
    }
)
NEEDS = (V.WATER, V.FAITH, V.MARKET)
QUARTER_WORKS: MappingProxyType[DistrictKind, frozenset[StructureKind]] = MappingProxyType(
    {
        D.INDUSTRIAL: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.INDUSTRIAL),
        D.BUSINESS: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.BUSINESS),
        D.RESEARCH: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.RESEARCH),
        D.UNIVERSITY: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.UNIVERSITY),
        D.TRANSPORT_HUB: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.TRANSPORT_HUB),
        D.MILITARY_BASE: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.MILITARY_BASE),
        D.ENTERTAINMENT: frozenset(kind for kind, home in HOME_DISTRICT.items() if home is D.ENTERTAINMENT),
    }
)
H = HousingLevel
HOUSING_ORDER = (H.HUT, H.SHIP_BERTH, H.TENEMENT, H.COTTAGE, H.HOUSE, H.HABITAT_MODULE, H.APARTMENT, H.TOWNHOUSE, H.TOWER_BLOCK, H.ARCOLOGY_UNIT, H.MANOR)
HOUSING_GATES = MappingProxyType(
    {
        H.TENEMENT: (KnowledgeBranch.ARCHITECTURE, 3),
        H.APARTMENT: (KnowledgeBranch.ARCHITECTURE, 4),
        H.TOWER_BLOCK: (KnowledgeBranch.ARCHITECTURE, 6),
        H.ARCOLOGY_UNIT: (KnowledgeBranch.ARCHITECTURE, 8),
        H.HABITAT_MODULE: (KnowledgeBranch.VOID_LIVING, 1),
        H.SHIP_BERTH: (KnowledgeBranch.VOID_LIVING, 1),
    }
)
FINE_HOMES = frozenset({H.TOWNHOUSE, H.ARCOLOGY_UNIT, H.MANOR})
TALL_HOMES = frozenset({H.TOWER_BLOCK, H.ARCOLOGY_UNIT})
M = Morphology
REACH_RULE = total(
    Morphology,
    {
        M.PLANNED: "planned_reach",
        M.CONCENTRIC: "concentric_reach",
        M.ORGANIC: "organic_reach",
        M.GRID: "grid_reach",
        M.VERTICAL: "vertical_reach",
        M.SPRAWL: "sprawl_reach",
    },
)
FIRE_RULE = {
    M.PLANNED: "planned_fire_pct",
    M.ORGANIC: "organic_fire_pct",
    M.GRID: "grid_fire_pct",
    M.VERTICAL: "vertical_fire_pct",
    M.SPRAWL: "sprawl_fire_pct",
}
HAULING_RULE = {
    M.PLANNED: "planned_hauling_pct",
    M.ORGANIC: "organic_hauling_pct",
    M.GRID: "grid_hauling_pct",
    M.VERTICAL: "vertical_hauling_pct",
    M.SPRAWL: "sprawl_hauling_pct",
}
DENSITY_RULE = total(
    DistrictKind,
    {
        D.FARMLAND: "farmland_housing_pct",
        D.MARKET: "market_housing_pct",
        D.CRAFT_QUARTER: "craft_quarter_housing_pct",
        D.TEMPLE_QUARTER: "temple_quarter_housing_pct",
        D.HARBOUR: "harbour_housing_pct",
        D.CITADEL: "citadel_housing_pct",
        D.SLUMS: "slums_housing_pct",
        D.PALACE: "palace_housing_pct",
        D.FOREIGN_QUARTER: "foreign_quarter_housing_pct",
        D.NECROPOLIS: "necropolis_housing_pct",
        D.RESIDENTIAL: "residential_housing_pct",
        D.CIVIC_QUARTER: "civic_quarter_housing_pct",
        D.GARDENS: "gardens_housing_pct",
        D.ARCOLOGY: "arcology_housing_pct",
        D.BUSINESS: "business_housing_pct",
        D.ENTERTAINMENT: "entertainment_housing_pct",
        D.INDUSTRIAL: "industrial_housing_pct",
        D.MILITARY_BASE: "military_base_housing_pct",
        D.RESEARCH: "research_housing_pct",
        D.SUBURB: "suburb_housing_pct",
        D.TRANSPORT_HUB: "transport_hub_housing_pct",
        D.UNIVERSITY: "university_housing_pct",
    },
)
HOUSING_RULE = {
    H.HUT: "hut_pct",
    H.COTTAGE: "cottage_pct",
    H.TOWNHOUSE: "townhouse_pct",
    H.MANOR: "manor_pct",
    H.APARTMENT: "apartment_pct",
    H.TENEMENT: "tenement_pct",
    H.TOWER_BLOCK: "tower_block_pct",
    H.ARCOLOGY_UNIT: "arcology_unit_pct",
    H.HABITAT_MODULE: "habitat_module_pct",
    H.SHIP_BERTH: "ship_berth_pct",
}

PERISHABLES = frozenset({C.FISH, C.BREAD, C.MEAT, C.MILK, C.CHEESE, C.FRUIT, C.EGGS, C.HERBS})
WALKING = frozenset({C.LIVESTOCK, C.MOUNTS})
BULK = frozenset({C.GRAIN, C.FODDER, C.TIMBER, C.FUEL, C.ORE, C.STONE, C.COAL, C.PEAT, C.DUNG, C.TUBERS, C.SIEGE_MATERIEL})


def cargo_class(commodity: CommodityKind) -> CargoClass:
    if commodity in PERISHABLES:
        return CargoClass.PERISHABLE
    if commodity in WALKING:
        return CargoClass.LIVESTOCK
    if commodity in BULK:
        return CargoClass.BULK
    return CargoClass.FINE


RACKETS_OF: MappingProxyType[FactionKind, tuple[RacketKind, ...]] = MappingProxyType(
    {
        FactionKind.CRIME_FAMILY: (RacketKind.PROTECTION, RacketKind.GAMBLING, RacketKind.KIDNAPPING),
        FactionKind.THIEVES_GUILD: (RacketKind.FENCING, RacketKind.PROTECTION),
        FactionKind.SMUGGLING_RING: (RacketKind.SMUGGLING, RacketKind.COUNTERFEITING),
        FactionKind.PIRATE_CONFEDERACY: (RacketKind.SMUGGLING, RacketKind.KIDNAPPING),
    }
)
MERCHANT_HOUSES = frozenset({FactionKind.CHARTERED_COMPANY, FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET})
