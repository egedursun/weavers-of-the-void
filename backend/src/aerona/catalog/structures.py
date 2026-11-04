from dataclasses import dataclass
from types import MappingProxyType

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


STRUCTURES: MappingProxyType[StructureKind, StructureSpec] = MappingProxyType(
    {
        item.kind: item
        for item in (
            spec((K.TEMPLE, G.FAITH, "Temple"), (S.PRIEST, W.SOME), U.WORSHIPPERS, (B.MAJOR, C.INCENSE, T.VILLAGE), ley=True),
            spec((K.SHRINE, G.FAITH, "Shrine"), (S.PRIEST, W.FEW), U.WORSHIPPERS, (B.MINOR, C.INCENSE, T.HAMLET), ley=True),
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
                (K.ALCHEMIST_LAB, G.PRODUCTION, "Alchemist's laboratory"),
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
        )
    }
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
WORKSHOP_STRUCTURES: MappingProxyType[WorkshopKind, StructureKind] = MappingProxyType(
    {item.workshop: item.kind for item in STRUCTURES.values() if item.workshop is not None}
)
GROUP_LABELS: MappingProxyType[StructureGroup, str] = MappingProxyType(
    {
        G.FAITH: "Faith",
        G.KNOWLEDGE: "Knowledge",
        G.DEFENCE: "Defence",
        G.CIVIC: "Civic",
        G.COMMERCE: "Commerce",
        G.PRODUCTION: "Production",
        G.INFRASTRUCTURE: "Infrastructure",
        G.MEMORY: "Memory and wonders",
        G.COSMIC: "Cosmic",
    }
)
KNOWLEDGE_KEEPERS = frozenset({K.LIBRARY, K.SCHOOL, K.OBSERVATORY, K.ACADEMY, K.MONASTERY, K.COSMIC_ARCHIVE})
BOOK_HOUSES = frozenset({K.LIBRARY, K.SCHOOL, K.ACADEMY, K.MONASTERY})
RESEARCH_HOUSES = frozenset({K.LIBRARY, K.SCHOOL, K.OBSERVATORY, K.ACADEMY})
HOLY_HOUSES = frozenset({K.TEMPLE, K.SHRINE, K.MONASTERY, K.WONDER})
RITE_HOUSES = frozenset({K.NECROPOLIS, K.TOMB, K.TEMPLE})


def structure_spec(kind: StructureKind) -> StructureSpec:
    return STRUCTURES[kind]
