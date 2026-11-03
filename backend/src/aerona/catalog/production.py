from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind, ExtractionKind, HazardKind, WorkshopKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch

C = CommodityKind
W = WorkshopKind
B = KnowledgeBranch
S = SkillKind


@dataclass(frozen=True)
class ChainStep:
    key: str
    label: str
    workshop: WorkshopKind | None
    inputs: tuple[tuple[CommodityKind, int], ...]
    output: CommodityKind
    output_qty: int
    skill: SkillKind
    branch: KnowledgeBranch | None = None
    level: int = 0
    keeps_material: CommodityKind | None = None
    material: MaterialKind | None = None
    quality_gain: int = 0


CHAIN_STEPS: tuple[ChainStep, ...] = (
    ChainStep("charcoal", "Charcoal burning", W.CHARCOAL_KILN, ((C.TIMBER, 2),), C.FUEL, 2, S.CARPENTRY),
    ChainStep("forge_tools", "Forging tools", W.FORGE, ((C.ORE, 1), (C.FUEL, 1)), C.TOOLS, 2, S.SMITHING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("forge_weapons", "Forging weapons", W.FORGE, ((C.ORE, 2), (C.FUEL, 1)), C.WEAPONS, 1, S.SMITHING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("forge_armour", "Forging armour", W.FORGE, ((C.ORE, 3), (C.FUEL, 1)), C.ARMOUR, 1, S.SMITHING, B.METALLURGY, 2, keeps_material=C.ORE),
    ChainStep("jewellery", "Working precious metal and stones", W.FORGE, ((C.ORE, 1),), C.LUXURIES, 1, S.JEWELLING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("tan_hides", "Tanning hides", W.TANNERY, ((C.LIVESTOCK, 1),), C.CLOTH, 1, S.WEAVING, material=MaterialKind.LEATHER),
    ChainStep("leather_armour", "Sewing leather armour", W.TANNERY, ((C.CLOTH, 2),), C.ARMOUR, 1, S.WEAVING, material=MaterialKind.LEATHER),
    ChainStep("weave", "Weaving", W.WEAVERY, ((C.LIVESTOCK, 1),), C.CLOTH, 2, S.WEAVING, material=MaterialKind.CLOTH),
    ChainStep("mill", "Milling and baking", W.MILL, ((C.GRAIN, 3),), C.BREAD, 3, S.CARPENTRY, B.AGRICULTURE, 1),
    ChainStep("brew", "Brewing and wine-making", W.BREWERY, ((C.GRAIN, 2),), C.LUXURIES, 1, S.ALCHEMY, B.AGRICULTURE, 2),
    ChainStep("breed_mounts", "Breeding mounts", W.STABLE, ((C.LIVESTOCK, 1), (C.FODDER, 2)), C.MOUNTS, 1, S.BEAST_HANDLING),
    ChainStep(
        "dress_stone", "Dressing stone", W.MASON_YARD, ((C.STONE, 2),), C.STONE, 1, S.MASONRY, B.ARCHITECTURE, 1, keeps_material=C.STONE, quality_gain=30
    ),
    ChainStep("siege_engines", "Building siege engines", W.SIEGE_YARD, ((C.TIMBER, 3), (C.ORE, 1)), C.SIEGE_MATERIEL, 1, S.ENGINEERING, B.WARFARE, 1),
    ChainStep("potions", "Brewing potions", W.ALCHEMIST, ((C.MAGICAL_REAGENTS, 1),), C.MEDICINE, 2, S.ALCHEMY, B.MEDICINE, 1),
    ChainStep("incense", "Rendering incense", W.SHRINE_WORKSHOP, ((C.TIMBER, 1),), C.INCENSE, 1, S.RITUAL),
    ChainStep("sacred_goods", "Making sacred goods", W.SHRINE_WORKSHOP, ((C.LUXURIES, 1), (C.TIMBER, 1)), C.SACRED_GOODS, 1, S.RITUAL),
    ChainStep("knap_tools", "Knapping stone tools", None, ((C.STONE, 1),), C.TOOLS, 1, S.MASONRY, keeps_material=C.STONE),
    ChainStep("gather_fuel", "Gathering firewood", None, ((C.TIMBER, 1),), C.FUEL, 1, S.FORAGING),
    ChainStep("spin", "Spinning and sewing at home", None, ((C.LIVESTOCK, 1),), C.CLOTH, 1, S.WEAVING, material=MaterialKind.HIDE),
)
STEPS: MappingProxyType[str, ChainStep] = MappingProxyType({step.key: step for step in CHAIN_STEPS})
SHIP_INPUTS: tuple[tuple[CommodityKind, int], ...] = ((C.TIMBER, 4), (C.CLOTH, 1))
MINT_INPUT = C.ORE


@dataclass(frozen=True)
class ExtractionSpec:
    kind: ExtractionKind
    workshop: WorkshopKind | None
    skill: SkillKind
    hazard: HazardKind | None
    season_key: str | None


EXTRACTION: MappingProxyType[ExtractionKind, ExtractionSpec] = MappingProxyType(
    {
        ExtractionKind.MINING: ExtractionSpec(ExtractionKind.MINING, W.MINE, S.ENGINEERING, HazardKind.CAVE_IN, None),
        ExtractionKind.QUARRYING: ExtractionSpec(ExtractionKind.QUARRYING, W.MINE, S.MASONRY, HazardKind.CAVE_IN, None),
        ExtractionKind.LOGGING: ExtractionSpec(ExtractionKind.LOGGING, W.LUMBER_CAMP, S.CARPENTRY, HazardKind.FELLING_ACCIDENT, "winter"),
        ExtractionKind.FISHING: ExtractionSpec(ExtractionKind.FISHING, W.FISHERY, S.SAILING, HazardKind.DROWNING, "summer"),
        ExtractionKind.HERDING: ExtractionSpec(ExtractionKind.HERDING, None, S.BEAST_HANDLING, HazardKind.GORING, None),
        ExtractionKind.FARMING: ExtractionSpec(ExtractionKind.FARMING, None, S.FORAGING, None, None),
        ExtractionKind.GATHERING: ExtractionSpec(ExtractionKind.GATHERING, None, S.FORAGING, None, None),
    }
)
EXTRACTION_OF: MappingProxyType[CommodityKind, ExtractionKind] = MappingProxyType(
    {
        C.ORE: ExtractionKind.MINING,
        C.STONE: ExtractionKind.QUARRYING,
        C.TIMBER: ExtractionKind.LOGGING,
        C.FISH: ExtractionKind.FISHING,
        C.LIVESTOCK: ExtractionKind.HERDING,
        C.MOUNTS: ExtractionKind.HERDING,
        C.GRAIN: ExtractionKind.FARMING,
        C.FODDER: ExtractionKind.FARMING,
    }
)
WORKSHOP_LABELS: MappingProxyType[WorkshopKind, str] = MappingProxyType(
    {
        W.MARKET: "Market",
        W.GRANARY: "Granary",
        W.WAREHOUSE: "Warehouse",
        W.MINE: "Mine",
        W.LUMBER_CAMP: "Lumber camp",
        W.FISHERY: "Fishery",
        W.CHARCOAL_KILN: "Charcoal kiln",
        W.FORGE: "Forge",
        W.TANNERY: "Tannery",
        W.MILL: "Mill",
        W.BREWERY: "Brewery",
        W.WEAVERY: "Weavery",
        W.STABLE: "Stable",
        W.MASON_YARD: "Mason yard",
        W.SHIPYARD: "Shipyard",
        W.SIEGE_YARD: "Siege yard",
        W.ALCHEMIST: "Alchemist",
        W.SHRINE_WORKSHOP: "Shrine workshop",
        W.MINT: "Mint",
    }
)
