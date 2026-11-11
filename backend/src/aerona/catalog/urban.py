from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import CargoClass, HousingLevel, Morphology, RacketKind, UrbanService

K = StructureKind
V = UrbanService
C = CommodityKind
D = DistrictKind

SERVICE_OF: MappingProxyType[StructureKind, UrbanService] = MappingProxyType(
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
AMENITIES = frozenset(
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
NUISANCES = frozenset({K.TANNERY, K.PRISON, K.FORGE, K.MILL, K.MINE, K.QUARRY, K.SLAUGHTERHOUSE, K.CHARCOAL_KILN, K.FISHERY, K.SAWMILL})
NUISANCE_DISTRICTS = frozenset({D.SLUMS, D.NECROPOLIS})
HOME_DISTRICT: MappingProxyType[StructureKind, DistrictKind] = MappingProxyType(
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
    }
)
NEEDS = (V.WATER, V.FAITH, V.MARKET)
HOUSING_ORDER = tuple(HousingLevel)
FINE_HOMES = frozenset({HousingLevel.TOWNHOUSE, HousingLevel.MANOR})
REACH_RULE = {Morphology.PLANNED: "planned_reach", Morphology.CONCENTRIC: "concentric_reach", Morphology.ORGANIC: "organic_reach"}
FIRE_RULE = {Morphology.PLANNED: "planned_fire_pct", Morphology.ORGANIC: "organic_fire_pct"}
HAULING_RULE = {Morphology.PLANNED: "planned_hauling_pct", Morphology.ORGANIC: "organic_hauling_pct"}
HOUSING_RULE = {HousingLevel.HUT: "hut_pct", HousingLevel.COTTAGE: "cottage_pct", HousingLevel.TOWNHOUSE: "townhouse_pct", HousingLevel.MANOR: "manor_pct"}

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
