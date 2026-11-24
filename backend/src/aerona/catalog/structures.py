from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.production import OPEN_GROUND_WORKSHOPS
from aerona.core.total import partial, total
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import BuildScale, CapacityUnit, StaffScale, StructureGroup, StructureKind

K = StructureKind
G = StructureGroup
S = SocialClass
U = CapacityUnit
B = BuildScale
W = StaffScale
C = CommodityKind
T = SizeTier


@dataclass(frozen=True)
class StructureSpec:
    kind: StructureKind
    group: StructureGroup
    label: str
    staff: SocialClass | None
    staff_scale: StaffScale
    capacity: CapacityUnit
    scale: BuildScale
    upkeep: CommodityKind
    min_tier: SizeTier
    ley: bool = False
    workshop: WorkshopKind | None = None
    branch: KnowledgeBranch | None = None


def spec(
    head: tuple[StructureKind, StructureGroup, str],
    staff: tuple[SocialClass | None, StaffScale],
    capacity: CapacityUnit,
    build: tuple[BuildScale, CommodityKind, SizeTier],
    *,
    ley: bool = False,
    workshop: WorkshopKind | None = None,
    branch: KnowledgeBranch | None = None,
) -> StructureSpec:
    kind, group, label = head
    scale, upkeep, tier = build
    return StructureSpec(kind, group, label, staff[0], staff[1], capacity, scale, upkeep, tier, ley, workshop, branch)


STRUCTURES: MappingProxyType[StructureKind, StructureSpec] = total(
    StructureKind,
    {
        item.kind: item
        for item in (
            spec((K.TEMPLE, G.FAITH, "Temple"), (S.PRIEST, W.SOME), U.WORSHIPPERS, (B.MAJOR, C.INCENSE, T.VILLAGE), ley=True),
            spec(
                (K.SHRINE, G.FAITH, "Shrine"), (S.PRIEST, W.FEW), U.WORSHIPPERS, (B.MINOR, C.INCENSE, T.HAMLET), ley=True, workshop=WorkshopKind.SHRINE_WORKSHOP
            ),
            spec((K.MONASTERY, G.FAITH, "Monastery"), (S.MONASTIC, W.MANY), U.VOLUMES, (B.MAJOR, C.GRAIN, T.VILLAGE), ley=True, branch=KnowledgeBranch.WRITING),
            spec((K.NECROPOLIS, G.FAITH, "Necropolis"), (S.PRIEST, W.FEW), U.WORSHIPPERS, (B.MAJOR, C.STONE, T.TOWN)),
            spec((K.LIBRARY, G.KNOWLEDGE, "Library"), (S.SCRIBE, W.SOME), U.VOLUMES, (B.MAJOR, C.CLOTH, T.VILLAGE), branch=KnowledgeBranch.WRITING),
            spec((K.SCHOOL, G.KNOWLEDGE, "School"), (S.SCRIBE, W.SOME), U.PUPILS, (B.MINOR, C.CLOTH, T.VILLAGE), branch=KnowledgeBranch.WRITING),
            spec(
                (K.OBSERVATORY, G.KNOWLEDGE, "Observatory"),
                (S.SCRIBE, W.FEW),
                U.VOLUMES,
                (B.MAJOR, C.TOOLS, T.TOWN),
                ley=True,
                branch=KnowledgeBranch.ASTRONOMY,
            ),
            spec((K.ACADEMY, G.KNOWLEDGE, "Academy"), (S.SCRIBE, W.MANY), U.PUPILS, (B.GRAND, C.CLOTH, T.CITY), ley=True, branch=KnowledgeBranch.WRITING),
            spec((K.HOSPITAL, G.KNOWLEDGE, "Hospital"), (S.PRIEST, W.SOME), U.BEDS, (B.MAJOR, C.MEDICINE, T.VILLAGE), branch=KnowledgeBranch.MEDICINE),
            spec((K.WALL, G.DEFENCE, "Walls"), (S.WARRIOR, W.SOME), U.GARRISON, (B.MAJOR, C.STONE, T.HAMLET)),
            spec((K.GATE, G.DEFENCE, "Gatehouse"), (S.WARRIOR, W.FEW), U.GARRISON, (B.MINOR, C.TIMBER, T.HAMLET), ley=True),
            spec((K.TOWER, G.DEFENCE, "Tower"), (S.WARRIOR, W.FEW), U.GARRISON, (B.MINOR, C.STONE, T.HAMLET), ley=True),
            spec((K.CITADEL, G.DEFENCE, "Citadel"), (S.WARRIOR, W.MANY), U.GARRISON, (B.GRAND, C.STONE, T.TOWN)),
            spec((K.WATCHTOWER, G.DEFENCE, "Watchtower"), (S.WARRIOR, W.FEW), U.GARRISON, (B.MINOR, C.TIMBER, T.HAMLET)),
            spec((K.FORT, G.DEFENCE, "Fort"), (S.WARRIOR, W.MANY), U.GARRISON, (B.MAJOR, C.WEAPONS, T.VILLAGE)),
            spec((K.PALACE, G.CIVIC, "Palace"), (S.NOBLE, W.SOME), U.SEATS, (B.GRAND, C.LUXURIES, T.TOWN)),
            spec((K.COURT, G.CIVIC, "Court"), (S.SCRIBE, W.FEW), U.SEATS, (B.MAJOR, C.CLOTH, T.VILLAGE)),
            spec((K.PRISON, G.CIVIC, "Prison"), (S.WARRIOR, W.FEW), U.CELLS, (B.MINOR, C.TOOLS, T.VILLAGE)),
            spec((K.MARKET, G.COMMERCE, "Market"), (S.MERCHANT, W.SOME), U.STALLS, (B.MINOR, C.TIMBER, T.HAMLET), workshop=WorkshopKind.MARKET),
            spec((K.HARBOUR, G.COMMERCE, "Harbour"), (S.MERCHANT, W.SOME), U.BERTHS, (B.MAJOR, C.TIMBER, T.VILLAGE)),
            spec((K.WAREHOUSE, G.COMMERCE, "Warehouse"), (S.MERCHANT, W.FEW), U.LOADS, (B.MINOR, C.TIMBER, T.VILLAGE), workshop=WorkshopKind.WAREHOUSE),
            spec((K.GRANARY, G.COMMERCE, "Granary"), (S.FARMER, W.FEW), U.TONS, (B.MINOR, C.TIMBER, T.HAMLET), workshop=WorkshopKind.GRANARY),
            spec((K.CARAVANSERAI, G.COMMERCE, "Caravanserai"), (S.MERCHANT, W.FEW), U.TRAVELLERS, (B.MAJOR, C.FODDER, T.HAMLET)),
            spec((K.BANK, G.COMMERCE, "Bank"), (S.MERCHANT, W.FEW), U.STALLS, (B.MAJOR, C.LUXURIES, T.TOWN)),
            spec((K.FORGE, G.PRODUCTION, "Forge"), (S.ARTISAN, W.SOME), U.HANDS, (B.MINOR, C.FUEL, T.HAMLET), workshop=WorkshopKind.FORGE),
            spec((K.MILL, G.PRODUCTION, "Mill"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.TIMBER, T.HAMLET), workshop=WorkshopKind.MILL),
            spec((K.TANNERY, G.PRODUCTION, "Tannery"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.HAMLET), workshop=WorkshopKind.TANNERY),
            spec((K.MINE, G.PRODUCTION, "Mine"), (S.SERF_OR_SLAVE, W.MANY), U.HANDS, (B.MAJOR, C.TIMBER, T.HAMLET), workshop=WorkshopKind.MINE),
            spec((K.QUARRY, G.PRODUCTION, "Quarry"), (S.SERF_OR_SLAVE, W.SOME), U.HANDS, (B.MINOR, C.TOOLS, T.HAMLET), workshop=WorkshopKind.MASON_YARD),
            spec((K.SHIPYARD, G.PRODUCTION, "Shipyard"), (S.ARTISAN, W.SOME), U.BERTHS, (B.MAJOR, C.TIMBER, T.VILLAGE), workshop=WorkshopKind.SHIPYARD),
            spec((K.WORKSHOP, G.PRODUCTION, "Workshop"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.TOOLS, T.HAMLET), workshop=WorkshopKind.WEAVERY),
            spec(
                (K.ALCHEMIST_LAB, G.PRODUCTION, "Reagent laboratory"),
                (S.SCRIBE, W.FEW),
                U.HANDS,
                (B.MAJOR, C.MAGICAL_REAGENTS, T.VILLAGE),
                ley=True,
                workshop=WorkshopKind.ALCHEMIST,
            ),
            spec((K.ROAD, G.INFRASTRUCTURE, "Road"), (S.ARTISAN, W.FEW), U.LOADS, (B.MINOR, C.STONE, T.HAMLET)),
            spec((K.BRIDGE, G.INFRASTRUCTURE, "Bridge"), (S.ARTISAN, W.FEW), U.LOADS, (B.MAJOR, C.STONE, T.HAMLET)),
            spec((K.AQUEDUCT, G.INFRASTRUCTURE, "Aqueduct"), (S.ARTISAN, W.SOME), U.TONS, (B.GRAND, C.STONE, T.TOWN)),
            spec((K.SEWER, G.INFRASTRUCTURE, "Sewers"), (S.SERF_OR_SLAVE, W.SOME), U.TONS, (B.MAJOR, C.STONE, T.TOWN)),
            spec((K.CANAL, G.INFRASTRUCTURE, "Canal"), (S.ARTISAN, W.SOME), U.LOADS, (B.GRAND, C.STONE, T.VILLAGE)),
            spec((K.IRRIGATION, G.INFRASTRUCTURE, "Irrigation works"), (S.FARMER, W.SOME), U.TONS, (B.MINOR, C.TOOLS, T.HAMLET)),
            spec((K.DAM, G.INFRASTRUCTURE, "Dam"), (S.ARTISAN, W.SOME), U.TONS, (B.GRAND, C.STONE, T.VILLAGE)),
            spec((K.MONUMENT, G.MEMORY, "Monument"), (None, W.NONE), U.NONE, (B.MINOR, C.STONE, T.HAMLET)),
            spec((K.TOMB, G.MEMORY, "Tomb"), (S.PRIEST, W.FEW), U.NONE, (B.MINOR, C.STONE, T.HAMLET)),
            spec((K.ARENA, G.MEMORY, "Arena"), (S.WARRIOR, W.SOME), U.SEATS, (B.GRAND, C.STONE, T.TOWN)),
            spec((K.THEATRE, G.MEMORY, "Theatre"), (S.ARTISAN, W.FEW), U.SEATS, (B.MAJOR, C.CLOTH, T.TOWN)),
            spec((K.WONDER, G.MEMORY, "Wonder"), (S.PRIEST, W.SOME), U.WORSHIPPERS, (B.WONDER, C.LUXURIES, T.CITY), ley=True),
            spec((K.COSMIC_GATE, G.COSMIC, "Cosmic gate"), (S.PRIEST, W.SOME), U.TRAVELLERS, (B.GRAND, C.MAGICAL_REAGENTS, T.HAMLET), ley=True),
            spec((K.COSMIC_ARCHIVE, G.COSMIC, "Cosmic archive"), (S.SCRIBE, W.SOME), U.VOLUMES, (B.GRAND, C.CLOTH, T.HAMLET), ley=True),
            spec((K.FIREHOUSE, G.CIVIC, "Firehouse"), (S.ARTISAN, W.FEW), U.GARRISON, (B.MINOR, C.TIMBER, T.VILLAGE)),
            spec((K.BATHHOUSE, G.CIVIC, "Bathhouse"), (S.ARTISAN, W.FEW), U.SEATS, (B.MINOR, C.FUEL, T.VILLAGE)),
            spec((K.FOUNTAIN, G.CIVIC, "Fountain"), (None, W.NONE), U.NONE, (B.MINOR, C.STONE, T.VILLAGE)),
            spec((K.PARK, G.CIVIC, "Park"), (S.ARTISAN, W.FEW), U.NONE, (B.MINOR, C.TIMBER, T.VILLAGE)),
            spec((K.SLAUGHTERHOUSE, G.PRODUCTION, "Slaughterhouse"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.VILLAGE)),
            spec((K.ALMSHOUSE, G.CIVIC, "Almshouse"), (S.PRIEST, W.FEW), U.SEATS, (B.MINOR, C.BREAD, T.VILLAGE)),
            spec((K.BREWERY, G.PRODUCTION, "Brewery"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.GRAIN, T.HAMLET), workshop=WorkshopKind.BREWERY),
            spec((K.SAWMILL, G.PRODUCTION, "Sawmill"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.TOOLS, T.HAMLET), workshop=WorkshopKind.LUMBER_CAMP),
            spec((K.FISHERY, G.PRODUCTION, "Fishery"), (S.FARMER, W.SOME), U.HANDS, (B.MINOR, C.TIMBER, T.HAMLET), workshop=WorkshopKind.FISHERY),
            spec(
                (K.CHARCOAL_KILN, G.PRODUCTION, "Charcoal kiln"),
                (S.SERF_OR_SLAVE, W.FEW),
                U.HANDS,
                (B.MINOR, C.TIMBER, T.HAMLET),
                workshop=WorkshopKind.CHARCOAL_KILN,
            ),
            spec((K.STABLES, G.PRODUCTION, "Stables"), (S.FARMER, W.FEW), U.HANDS, (B.MINOR, C.FODDER, T.HAMLET), workshop=WorkshopKind.STABLE),
            spec((K.SIEGE_WORKSHOP, G.DEFENCE, "Siege yard"), (S.ARTISAN, W.SOME), U.HANDS, (B.MAJOR, C.TIMBER, T.VILLAGE), workshop=WorkshopKind.SIEGE_YARD),
            spec((K.MINT, G.COMMERCE, "Mint"), (S.ARTISAN, W.FEW), U.HANDS, (B.MAJOR, C.ORE, T.TOWN), workshop=WorkshopKind.MINT),
            spec((K.TAVERN, G.COMMERCE, "Tavern"), (S.MERCHANT, W.FEW), U.TRAVELLERS, (B.MINOR, C.BREW_BASE, T.HAMLET)),
            spec((K.TOWN_HALL, G.CIVIC, "Town hall"), (S.SCRIBE, W.FEW), U.SEATS, (B.MAJOR, C.CLOTH, T.TOWN)),
            spec((K.GUILDHALL, G.COMMERCE, "Trade hall"), (S.ARTISAN, W.FEW), U.SEATS, (B.MAJOR, C.TOOLS, T.TOWN)),
            spec((K.BARRACKS, G.DEFENCE, "Barracks"), (S.WARRIOR, W.MANY), U.GARRISON, (B.MAJOR, C.WEAPONS, T.VILLAGE)),
            spec((K.ORPHANAGE, G.CIVIC, "Orphanage"), (S.PRIEST, W.FEW), U.BEDS, (B.MINOR, C.BREAD, T.TOWN)),
            spec((K.APOTHECARY, G.KNOWLEDGE, "Apothecary"), (S.SCRIBE, W.FEW), U.BEDS, (B.MINOR, C.HERBS, T.HAMLET), branch=KnowledgeBranch.MEDICINE),
            spec((K.TRAINING_GROUND, G.CIVIC, "Training ground"), (S.WARRIOR, W.FEW), U.GARRISON, (B.MINOR, C.TIMBER, T.TOWN)),
            spec((K.MUSEUM, G.MEMORY, "Museum"), (S.SCRIBE, W.FEW), U.VOLUMES, (B.MAJOR, C.CLOTH, T.CITY)),
            spec((K.PLAZA, G.CIVIC, "Plaza"), (None, W.NONE), U.NONE, (B.MINOR, C.STONE, T.TOWN)),
            spec((K.KONTOR, G.COMMERCE, "Trading post"), (S.MERCHANT, W.FEW), U.LOADS, (B.MINOR, C.TIMBER, T.VILLAGE)),
            spec((K.EMBASSY, G.CIVIC, "Embassy"), (S.NOBLE, W.FEW), U.SEATS, (B.MAJOR, C.LUXURIES, T.TOWN)),
            spec((K.LIGHTHOUSE, G.INFRASTRUCTURE, "Lighthouse"), (S.ARTISAN, W.FEW), U.NONE, (B.MAJOR, C.FUEL, T.VILLAGE), branch=KnowledgeBranch.SEAFARING),
            spec((K.SIGNAL_TOWER, G.DEFENCE, "Signal tower"), (S.WARRIOR, W.FEW), U.GARRISON, (B.MINOR, C.FUEL, T.HAMLET)),
            spec((K.CUSTOMS_HOUSE, G.COMMERCE, "Customs house"), (S.SCRIBE, W.FEW), U.LOADS, (B.MINOR, C.CLOTH, T.TOWN)),
            spec((K.TOLL_GATE, G.COMMERCE, "Toll gate"), (S.WARRIOR, W.FEW), U.LOADS, (B.MINOR, C.TIMBER, T.HAMLET)),
            spec((K.COURTHOUSE, G.CIVIC, "Courthouse"), (S.SCRIBE, W.SOME), U.SEATS, (B.MAJOR, C.CLOTH, T.TOWN)),
            spec(
                (K.ARCHIVE, G.KNOWLEDGE, "Archive"),
                (S.SCRIBE, W.FEW),
                U.VOLUMES,
                (B.MAJOR, C.CLOTH, T.TOWN),
                branch=KnowledgeBranch.WRITING,
                workshop=WorkshopKind.SCRIPTORIUM,
            ),
            spec(
                (K.PRINTING_HOUSE, G.KNOWLEDGE, "Printing house"),
                (S.ARTISAN, W.SOME),
                U.VOLUMES,
                (B.MAJOR, C.CLOTH, T.TOWN),
                branch=KnowledgeBranch.WRITING,
                workshop=WorkshopKind.PRINTING_HOUSE,
            ),
            spec((K.LABORATORY, G.KNOWLEDGE, "Laboratory"), (S.SCRIBE, W.FEW), U.HANDS, (B.MAJOR, C.TOOLS, T.TOWN), branch=KnowledgeBranch.MEDICINE),
            spec((K.FOUNDRY, G.PRODUCTION, "Foundry"), (S.ARTISAN, W.SOME), U.HANDS, (B.MAJOR, C.COAL, T.TOWN), branch=KnowledgeBranch.METALLURGY),
            spec((K.SMELTER, G.PRODUCTION, "Smelter"), (S.ARTISAN, W.SOME), U.HANDS, (B.MAJOR, C.FUEL, T.VILLAGE), branch=KnowledgeBranch.METALLURGY),
            spec((K.KILN, G.PRODUCTION, "Kiln"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.HAMLET), workshop=WorkshopKind.POTTERY),
            spec((K.GLASSWORKS, G.PRODUCTION, "Glassworks"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.VILLAGE), workshop=WorkshopKind.GLASSWORKS),
            spec((K.TEXTILE_MILL, G.PRODUCTION, "Textile mill"), (S.ARTISAN, W.SOME), U.HANDS, (B.MAJOR, C.FIBRE, T.TOWN), workshop=WorkshopKind.ROPEWALK),
            spec((K.DYE_WORKS, G.PRODUCTION, "Dye works"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.DYE, T.VILLAGE), workshop=WorkshopKind.DYEWORKS),
            spec(
                (K.PAPER_MILL, G.PRODUCTION, "Paper mill"),
                (S.ARTISAN, W.FEW),
                U.HANDS,
                (B.MINOR, C.TIMBER, T.TOWN),
                branch=KnowledgeBranch.WRITING,
                workshop=WorkshopKind.PAPER_MILL,
            ),
            spec((K.BAKERY, G.PRODUCTION, "Bakery"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.HAMLET)),
            spec((K.DAIRY, G.PRODUCTION, "Dairy"), (S.FARMER, W.FEW), U.HANDS, (B.MINOR, C.FODDER, T.HAMLET)),
            spec((K.DISTILLERY, G.PRODUCTION, "Distillery"), (S.ARTISAN, W.FEW), U.HANDS, (B.MINOR, C.FUEL, T.VILLAGE)),
            spec((K.REFINERY, G.PRODUCTION, "Refinery"), (S.ARTISAN, W.SOME), U.HANDS, (B.MAJOR, C.TOOLS, T.TOWN), branch=KnowledgeBranch.METALLURGY),
            spec(
                (K.POWER_PLANT, G.INFRASTRUCTURE, "Power plant"), (S.ARTISAN, W.SOME), U.HANDS, (B.GRAND, C.COAL, T.HAMLET), branch=KnowledgeBranch.METALLURGY
            ),
            spec((K.SILO, G.COMMERCE, "Silo"), (S.FARMER, W.FEW), U.TONS, (B.MINOR, C.TIMBER, T.HAMLET)),
            spec((K.CISTERN, G.INFRASTRUCTURE, "Cistern"), (S.ARTISAN, W.FEW), U.TONS, (B.MINOR, C.STONE, T.HAMLET)),
            spec((K.RESERVOIR, G.INFRASTRUCTURE, "Reservoir"), (S.ARTISAN, W.SOME), U.TONS, (B.MAJOR, C.STONE, T.VILLAGE)),
            spec((K.CANAL_LOCK, G.INFRASTRUCTURE, "Canal lock"), (S.ARTISAN, W.FEW), U.LOADS, (B.MAJOR, C.STONE, T.VILLAGE)),
            spec((K.TUNNEL, G.INFRASTRUCTURE, "Tunnel"), (S.SERF_OR_SLAVE, W.FEW), U.LOADS, (B.GRAND, C.STONE, T.HAMLET), branch=KnowledgeBranch.ARCHITECTURE),
            spec(
                (K.RAIL_STATION, G.INFRASTRUCTURE, "Rail station"),
                (S.ARTISAN, W.SOME),
                U.TRAVELLERS,
                (B.MAJOR, C.COAL, T.TOWN),
                branch=KnowledgeBranch.METALLURGY,
            ),
            spec((K.AIRFIELD, G.INFRASTRUCTURE, "Airfield"), (S.ARTISAN, W.SOME), U.BERTHS, (B.MAJOR, C.FUEL, T.TOWN), branch=KnowledgeBranch.SKY_NAVIGATION),
            spec((K.SPACEPORT, G.COSMIC, "Spaceport"), (S.ARTISAN, W.MANY), U.BERTHS, (B.GRAND, C.FUEL, T.CITY), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.DRY_DOCK, G.PRODUCTION, "Dry dock"), (S.ARTISAN, W.SOME), U.BERTHS, (B.MAJOR, C.TIMBER, T.TOWN), branch=KnowledgeBranch.SHIPBUILDING),
            spec((K.ARSENAL, G.DEFENCE, "Arsenal"), (S.ARTISAN, W.SOME), U.LOADS, (B.MAJOR, C.WEAPONS, T.TOWN), branch=KnowledgeBranch.WARFARE),
            spec((K.KENNEL, G.PRODUCTION, "Kennel"), (S.FARMER, W.FEW), U.HANDS, (B.MINOR, C.MEAT, T.HAMLET)),
            spec((K.MENAGERIE, G.MEMORY, "Menagerie"), (S.FARMER, W.FEW), U.SEATS, (B.MAJOR, C.MEAT, T.CITY)),
            spec((K.BOTANICAL_GARDEN, G.KNOWLEDGE, "Botanical garden"), (S.FARMER, W.FEW), U.NONE, (B.MAJOR, C.HERBS, T.TOWN), branch=KnowledgeBranch.MEDICINE),
            spec((K.CEMETERY, G.FAITH, "Cemetery"), (S.PRIEST, W.FEW), U.WORSHIPPERS, (B.MINOR, C.STONE, T.HAMLET)),
            spec((K.GYMNASIUM, G.CIVIC, "Gymnasium"), (S.WARRIOR, W.FEW), U.PUPILS, (B.MINOR, C.CLOTH, T.TOWN)),
            spec((K.ASYLUM, G.KNOWLEDGE, "Asylum"), (S.PRIEST, W.FEW), U.BEDS, (B.MINOR, C.MEDICINE, T.TOWN), branch=KnowledgeBranch.MEDICINE),
            spec(
                (K.QUARANTINE_HOUSE, G.KNOWLEDGE, "Quarantine house"),
                (S.PRIEST, W.FEW),
                U.BEDS,
                (B.MINOR, C.MEDICINE, T.VILLAGE),
                branch=KnowledgeBranch.MEDICINE,
            ),
            spec((K.INN, G.COMMERCE, "Inn"), (S.MERCHANT, W.FEW), U.TRAVELLERS, (B.MINOR, C.BREW_BASE, T.HAMLET)),
            spec((K.MARKET_HALL, G.COMMERCE, "Market hall"), (S.MERCHANT, W.SOME), U.STALLS, (B.MAJOR, C.TIMBER, T.TOWN)),
            spec((K.EXCHANGE, G.COMMERCE, "Exchange"), (S.MERCHANT, W.FEW), U.STALLS, (B.MAJOR, C.LUXURIES, T.CITY), branch=KnowledgeBranch.TRADE),
            spec((K.UNIVERSITY, G.KNOWLEDGE, "University"), (S.SCRIBE, W.MANY), U.PUPILS, (B.GRAND, C.CLOTH, T.CITY), branch=KnowledgeBranch.WRITING),
            spec((K.SEMINARY, G.FAITH, "Seminary"), (S.PRIEST, W.SOME), U.PUPILS, (B.MAJOR, C.CLOTH, T.TOWN), branch=KnowledgeBranch.WRITING),
            spec((K.CONSERVATORY, G.KNOWLEDGE, "Conservatory"), (S.ARTISAN, W.FEW), U.PUPILS, (B.MAJOR, C.CLOTH, T.CITY)),
            spec((K.OPERA_HOUSE, G.MEMORY, "Opera house"), (S.ARTISAN, W.SOME), U.SEATS, (B.GRAND, C.LUXURIES, T.CITY)),
            spec((K.GALLERY, G.MEMORY, "Gallery"), (S.SCRIBE, W.FEW), U.VOLUMES, (B.MAJOR, C.LUXURIES, T.TOWN)),
            spec((K.STADIUM, G.MEMORY, "Stadium"), (S.ARTISAN, W.SOME), U.SEATS, (B.GRAND, C.STONE, T.CITY)),
            spec((K.ORBITAL_RING, G.COSMIC, "Orbital ring"), (S.ARTISAN, W.MANY), U.BERTHS, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.SPACE_ELEVATOR, G.COSMIC, "Space elevator"), (S.ARTISAN, W.SOME), U.LOADS, (B.GRAND, C.TOOLS, T.CITY), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.SPACE_STATION, G.COSMIC, "Space station"), (S.ARTISAN, W.MANY), U.BERTHS, (B.GRAND, C.TOOLS, T.TOWN), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.STAR_COLLECTOR, G.COSMIC, "Star collector"), (S.ARTISAN, W.MANY), U.NONE, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.ASTRONOMY),
            spec((K.BEACON, G.COSMIC, "Beacon"), (S.ARTISAN, W.FEW), U.NONE, (B.GRAND, C.FUEL, T.TOWN), branch=KnowledgeBranch.PATHFINDING),
            spec(
                (K.PLANETARY_ENGINE, G.COSMIC, "Planetary engine"), (S.ARTISAN, W.MANY), U.NONE, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.ASTRONOMY
            ),
            spec((K.HABITAT_RING, G.COSMIC, "Habitat ring"), (S.ARTISAN, W.MANY), U.SEATS, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.FACTORY, G.PRODUCTION, "Factory"), (S.WORKER, W.MANY), U.HANDS, (B.GRAND, C.COAL, T.TOWN), branch=KnowledgeBranch.METALLURGY),
            spec((K.DATA_CENTRE, G.KNOWLEDGE, "Data centre"), (S.PROFESSIONAL, W.FEW), U.VOLUMES, (B.GRAND, C.FUEL, T.CITY), branch=KnowledgeBranch.WRITING),
            spec(
                (K.OFFICE_TOWER, G.COMMERCE, "Office tower"), (S.PROFESSIONAL, W.MANY), U.SEATS, (B.GRAND, C.TOOLS, T.CITY), branch=KnowledgeBranch.ARCHITECTURE
            ),
            spec((K.APARTMENT_BLOCK, G.CIVIC, "Apartment block"), (None, W.NONE), U.BEDS, (B.MAJOR, C.STONE, T.TOWN), branch=KnowledgeBranch.ARCHITECTURE),
            spec((K.MALL, G.COMMERCE, "Mall"), (S.MERCHANT, W.MANY), U.STALLS, (B.GRAND, C.TOOLS, T.CITY), branch=KnowledgeBranch.TRADE),
            spec(
                (K.BROADCAST_TOWER, G.KNOWLEDGE, "Broadcast tower"), (S.PROFESSIONAL, W.FEW), U.NONE, (B.MAJOR, C.TOOLS, T.TOWN), branch=KnowledgeBranch.WRITING
            ),
            spec(
                (K.SATELLITE_ARRAY, G.COSMIC, "Satellite array"), (S.PROFESSIONAL, W.FEW), U.NONE, (B.GRAND, C.TOOLS, T.CITY), branch=KnowledgeBranch.ASTRONOMY
            ),
            spec((K.MILITARY_BASE, G.DEFENCE, "Military base"), (S.WARRIOR, W.MANY), U.GARRISON, (B.GRAND, C.FUEL, T.TOWN), branch=KnowledgeBranch.WARFARE),
            spec((K.MISSILE_SILO, G.DEFENCE, "Missile silo"), (S.WARRIOR, W.FEW), U.GARRISON, (B.GRAND, C.FUEL, T.TOWN), branch=KnowledgeBranch.METALLURGY),
            spec(
                (K.SHIELD_GENERATOR, G.DEFENCE, "Shield generator"),
                (S.PROFESSIONAL, W.FEW),
                U.NONE,
                (B.GRAND, C.FUEL, T.CITY),
                branch=KnowledgeBranch.ASTRONOMY,
            ),
            spec((K.TERRAFORMER, G.COSMIC, "Terraformer"), (S.PROFESSIONAL, W.MANY), U.NONE, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.VOID_LIVING),
            spec((K.VERTICAL_FARM, G.PRODUCTION, "Vertical farm"), (S.WORKER, W.SOME), U.HANDS, (B.MAJOR, C.TOOLS, T.CITY), branch=KnowledgeBranch.AGRICULTURE),
            spec(
                (K.RECYCLING_PLANT, G.INFRASTRUCTURE, "Recycling plant"),
                (S.WORKER, W.SOME),
                U.HANDS,
                (B.MAJOR, C.TOOLS, T.TOWN),
                branch=KnowledgeBranch.METALLURGY,
            ),
            spec(
                (K.WATER_PURIFICATION, G.INFRASTRUCTURE, "Water purification"),
                (S.WORKER, W.FEW),
                U.TONS,
                (B.MAJOR, C.TOOLS, T.TOWN),
                branch=KnowledgeBranch.ARCHITECTURE,
            ),
            spec(
                (K.CLONING_FACILITY, G.CIVIC, "Cloning facility"),
                (S.PROFESSIONAL, W.SOME),
                U.BEDS,
                (B.GRAND, C.MEDICINE, T.CITY),
                branch=KnowledgeBranch.BIOMANCY,
            ),
            spec(
                (K.ROBOTICS_WORKS, G.PRODUCTION, "Robotics works"),
                (S.PROFESSIONAL, W.SOME),
                U.HANDS,
                (B.GRAND, C.TOOLS, T.CITY),
                branch=KnowledgeBranch.METALLURGY,
            ),
            spec(
                (K.AI_CORE, G.KNOWLEDGE, "Machine mind core"), (S.PROFESSIONAL, W.FEW), U.VOLUMES, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.WRITING
            ),
            spec((K.TELEPORTER, G.COSMIC, "Teleporter"), (S.PROFESSIONAL, W.FEW), U.TRAVELLERS, (B.WONDER, C.TOOLS, T.CITY), branch=KnowledgeBranch.GATE_LORE),
            spec(
                (K.COVENANT, G.KNOWLEDGE, "Covenant"),
                (S.SCRIBE, W.SOME),
                U.VOLUMES,
                (B.MAJOR, C.MAGICAL_REAGENTS, T.VILLAGE),
                ley=True,
                branch=KnowledgeBranch.MAGIC,
            ),
        )
    },
)

ENGINE_KIND_STRUCTURES: MappingProxyType[EngineKind, StructureKind] = MappingProxyType(
    {
        EngineKind.TEMPLE: K.TEMPLE,
        EngineKind.WALL: K.WALL,
        EngineKind.LIBRARY: K.LIBRARY,
        EngineKind.SCHOOL: K.SCHOOL,
        EngineKind.OBSERVATORY: K.OBSERVATORY,
        EngineKind.COSMIC_ARCHIVE: K.COSMIC_ARCHIVE,
        EngineKind.WONDER: K.WONDER,
    }
)
STRUCTURE_ENGINE_KINDS: MappingProxyType[StructureKind, EngineKind] = MappingProxyType({kind: engine for engine, kind in ENGINE_KIND_STRUCTURES.items()})
WORKSHOP_STRUCTURES: MappingProxyType[WorkshopKind, StructureKind] = partial(
    WorkshopKind, {item.workshop: item.kind for item in STRUCTURES.values() if item.workshop is not None}, without=OPEN_GROUND_WORKSHOPS
)
BASE_KNOWLEDGE_KEEPERS = frozenset({K.LIBRARY, K.SCHOOL, K.OBSERVATORY, K.ACADEMY, K.MONASTERY, K.COSMIC_ARCHIVE})
BASE_BOOK_HOUSES = frozenset({K.LIBRARY, K.SCHOOL, K.ACADEMY, K.MONASTERY})
BASE_RESEARCH_HOUSES = frozenset({K.LIBRARY, K.SCHOOL, K.OBSERVATORY, K.ACADEMY})
BASE_HOLY_HOUSES = frozenset({K.TEMPLE, K.SHRINE, K.MONASTERY, K.WONDER})
ACTS_AS: MappingProxyType[StructureKind, StructureKind] = MappingProxyType(
    {
        K.EMBASSY: K.COURT,
        K.LIGHTHOUSE: K.HARBOUR,
        K.SIGNAL_TOWER: K.WATCHTOWER,
        K.CUSTOMS_HOUSE: K.KONTOR,
        K.TOLL_GATE: K.GATE,
        K.COURTHOUSE: K.COURT,
        K.ARCHIVE: K.LIBRARY,
        K.PRINTING_HOUSE: K.LIBRARY,
        K.LABORATORY: K.ALCHEMIST_LAB,
        K.FOUNDRY: K.FORGE,
        K.SMELTER: K.FORGE,
        K.KILN: K.WORKSHOP,
        K.GLASSWORKS: K.WORKSHOP,
        K.TEXTILE_MILL: K.WORKSHOP,
        K.DYE_WORKS: K.TANNERY,
        K.PAPER_MILL: K.MILL,
        K.BAKERY: K.MILL,
        K.DAIRY: K.SLAUGHTERHOUSE,
        K.DISTILLERY: K.BREWERY,
        K.REFINERY: K.CHARCOAL_KILN,
        K.POWER_PLANT: K.CHARCOAL_KILN,
        K.SILO: K.GRANARY,
        K.CISTERN: K.FOUNTAIN,
        K.RESERVOIR: K.AQUEDUCT,
        K.CANAL_LOCK: K.CANAL,
        K.TUNNEL: K.ROAD,
        K.RAIL_STATION: K.ROAD,
        K.AIRFIELD: K.HARBOUR,
        K.SPACEPORT: K.HARBOUR,
        K.DRY_DOCK: K.SHIPYARD,
        K.ARSENAL: K.BARRACKS,
        K.KENNEL: K.STABLES,
        K.MENAGERIE: K.PARK,
        K.BOTANICAL_GARDEN: K.APOTHECARY,
        K.CEMETERY: K.NECROPOLIS,
        K.GYMNASIUM: K.TRAINING_GROUND,
        K.ASYLUM: K.HOSPITAL,
        K.QUARANTINE_HOUSE: K.HOSPITAL,
        K.INN: K.TAVERN,
        K.MARKET_HALL: K.MARKET,
        K.EXCHANGE: K.BANK,
        K.UNIVERSITY: K.ACADEMY,
        K.SEMINARY: K.MONASTERY,
        K.CONSERVATORY: K.SCHOOL,
        K.OPERA_HOUSE: K.THEATRE,
        K.GALLERY: K.MUSEUM,
        K.STADIUM: K.ARENA,
        K.SPACE_ELEVATOR: K.HARBOUR,
        K.SPACE_STATION: K.SHIPYARD,
        K.FACTORY: K.WORKSHOP,
        K.DATA_CENTRE: K.LIBRARY,
        K.OFFICE_TOWER: K.GUILDHALL,
        K.APARTMENT_BLOCK: K.ALMSHOUSE,
        K.MALL: K.MARKET,
        K.BROADCAST_TOWER: K.LIBRARY,
        K.SATELLITE_ARRAY: K.OBSERVATORY,
        K.MILITARY_BASE: K.BARRACKS,
        K.MISSILE_SILO: K.BARRACKS,
        K.SHIELD_GENERATOR: K.WALL,
        K.TERRAFORMER: K.IRRIGATION,
        K.VERTICAL_FARM: K.IRRIGATION,
        K.RECYCLING_PLANT: K.SEWER,
        K.WATER_PURIFICATION: K.AQUEDUCT,
        K.CLONING_FACILITY: K.HOSPITAL,
        K.ROBOTICS_WORKS: K.WORKSHOP,
        K.AI_CORE: K.ACADEMY,
        K.TELEPORTER: K.COSMIC_GATE,
    }
)
BRANCH_LEVELS: MappingProxyType[StructureKind, int] = MappingProxyType(
    {
        K.POWER_PLANT: 6,
        K.REFINERY: 5,
        K.FACTORY: 5,
        K.DATA_CENTRE: 7,
        K.OFFICE_TOWER: 6,
        K.APARTMENT_BLOCK: 4,
        K.MALL: 5,
        K.BROADCAST_TOWER: 6,
        K.SATELLITE_ARRAY: 6,
        K.MILITARY_BASE: 5,
        K.MISSILE_SILO: 7,
        K.SHIELD_GENERATOR: 8,
        K.TERRAFORMER: 3,
        K.VERTICAL_FARM: 6,
        K.RECYCLING_PLANT: 5,
        K.WATER_PURIFICATION: 5,
        K.CLONING_FACILITY: 3,
        K.ROBOTICS_WORKS: 7,
        K.AI_CORE: 9,
        K.TELEPORTER: 3,
    }
)
MEGASTRUCTURES = frozenset({K.ORBITAL_RING, K.SPACE_ELEVATOR, K.SPACE_STATION, K.STAR_COLLECTOR, K.BEACON, K.PLANETARY_ENGINE, K.HABITAT_RING})


def function_kind(kind: StructureKind) -> StructureKind:
    return ACTS_AS.get(kind, kind)


def acting[V](table: Mapping[StructureKind, V]) -> MappingProxyType[StructureKind, V]:
    return MappingProxyType({**table, **{kind: table[base] for kind, base in ACTS_AS.items() if base in table and kind not in table}})


def acting_set(kinds: frozenset[StructureKind]) -> frozenset[StructureKind]:
    return kinds | frozenset(kind for kind, base in ACTS_AS.items() if base in kinds)


KNOWLEDGE_KEEPERS = acting_set(BASE_KNOWLEDGE_KEEPERS)
BOOK_HOUSES = acting_set(BASE_BOOK_HOUSES)
RESEARCH_HOUSES = acting_set(BASE_RESEARCH_HOUSES)
HOLY_HOUSES = acting_set(BASE_HOLY_HOUSES)
