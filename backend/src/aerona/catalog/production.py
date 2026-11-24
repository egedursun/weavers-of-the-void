from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, ExtractionKind, HazardKind, WorkshopKind
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch

C = CommodityKind
W = WorkshopKind
B = KnowledgeBranch
S = SkillKind
T = Technique
E = EnergyKind


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
    technique: Technique | None = None
    energy: EnergyKind | None = None
    energy_need: int = 0

    @property
    def yield_per_input(self) -> float:
        return self.output_qty / max(1, sum(amount for _, amount in self.inputs))


CHAIN_STEPS: tuple[ChainStep, ...] = (
    ChainStep("charcoal", "Fuel making", W.CHARCOAL_KILN, ((C.TIMBER, 2),), C.FUEL, 2, S.CARPENTRY),
    ChainStep("forge_tools", "Forging tools", W.FORGE, ((C.ORE, 1), (C.FUEL, 1)), C.TOOLS, 2, S.SMITHING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("forge_weapons", "Forging weapons", W.FORGE, ((C.ORE, 2), (C.FUEL, 1)), C.WEAPONS, 1, S.SMITHING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("forge_armour", "Forging armour", W.FORGE, ((C.ORE, 3), (C.FUEL, 1)), C.ARMOUR, 1, S.SMITHING, B.METALLURGY, 2, keeps_material=C.ORE),
    ChainStep("jewellery", "Working precious metal and stones", W.FORGE, ((C.ORE, 1),), C.LUXURIES, 1, S.JEWELLING, B.METALLURGY, 1, keeps_material=C.ORE),
    ChainStep("tan_hides", "Tanning hides", W.TANNERY, ((C.LIVESTOCK, 1),), C.CLOTH, 1, S.WEAVING, material=MaterialKind.LEATHER),
    ChainStep("leather_armour", "Sewing leather armour", W.TANNERY, ((C.CLOTH, 2),), C.ARMOUR, 1, S.WEAVING, material=MaterialKind.LEATHER),
    ChainStep("weave", "Weaving", W.WEAVERY, ((C.LIVESTOCK, 1),), C.CLOTH, 2, S.WEAVING, material=MaterialKind.CLOTH),
    ChainStep("mill", "Milling and baking", W.MILL, ((C.GRAIN, 3),), C.BREAD, 3, S.CARPENTRY, B.AGRICULTURE, 1),
    ChainStep("butcher", "Butchering livestock", None, ((C.LIVESTOCK, 1),), C.MEAT, 2, S.BEAST_HANDLING),
    ChainStep("cheese", "Making cheese from milk", None, ((C.MILK, 3),), C.CHEESE, 1, S.BEAST_HANDLING, B.AGRICULTURE, 1),
    ChainStep("press_fruit", "Pressing fruit into wine", W.BREWERY, ((C.FRUIT, 3),), C.LUXURIES, 1, S.ALCHEMY, B.AGRICULTURE, 1),
    ChainStep("brew", "Brewing ale from grain", W.BREWERY, ((C.GRAIN, 2),), C.LUXURIES, 1, S.ALCHEMY, B.AGRICULTURE, 2),
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
    ChainStep("weave_wool", "Weaving wool", W.WEAVERY, ((C.WOOL, 2),), C.CLOTH, 2, S.WEAVING, material=MaterialKind.CLOTH, quality_gain=10),
    ChainStep("weave_fibre", "Weaving plant fibre", W.WEAVERY, ((C.FIBRE, 2),), C.CLOTH, 2, S.WEAVING, material=MaterialKind.CLOTH),
    ChainStep("dye_cloth", "Dyeing cloth", W.WEAVERY, ((C.CLOTH, 1), (C.DYE, 1)), C.LUXURIES, 1, S.WEAVING, B.AGRICULTURE, 1, quality_gain=20),
    ChainStep(
        "smith_tools",
        "Smithing tools at the anvil",
        W.FORGE,
        ((C.ORE, 1), (C.FUEL, 1)),
        C.TOOLS,
        2,
        S.SMITHING,
        B.METALLURGY,
        2,
        keeps_material=C.ORE,
        quality_gain=10,
    ),
    ChainStep("joinery", "Joining timber into furnishings", W.LUMBER_CAMP, ((C.TIMBER, 2),), C.LUXURIES, 1, S.CARPENTRY, B.ARCHITECTURE, 1),
    ChainStep(
        "fire_pottery", "Firing clay into pottery", W.POTTERY, ((C.STONE, 2), (C.FUEL, 1)), C.POTTERY, 3, S.POTTERY, None, 0, material=MaterialKind.CERAMIC
    ),
    ChainStep("blow_glass", "Blowing glass", W.GLASSWORKS, ((C.STONE, 2), (C.FUEL, 2)), C.LUXURIES, 1, S.POTTERY, B.METALLURGY, 2, material=MaterialKind.GLASS),
    ChainStep("dye_works", "Dyeing cloth in vats", W.DYEWORKS, ((C.CLOTH, 2), (C.DYE, 1)), C.LUXURIES, 2, S.WEAVING, B.AGRICULTURE, 1, quality_gain=25),
    ChainStep("copy_books", "Copying books", W.SCRIPTORIUM, ((C.TIMBER, 1), (C.DYE, 1)), C.BOOKS, 2, S.WRITING, B.WRITING, 1),
    ChainStep("copy_books_rag", "Copying books on rag paper", W.SCRIPTORIUM, ((C.CLOTH, 1), (C.DYE, 1)), C.BOOKS, 3, S.WRITING, B.WRITING, 2),
    ChainStep("make_paper", "Making paper from fibre", W.PAPER_MILL, ((C.FIBRE, 2),), C.PAPER, 3, S.WEAVING, B.WRITING, 1, technique=T.PAPER),
    ChainStep("make_rag_paper", "Making paper from rags", W.PAPER_MILL, ((C.CLOTH, 1),), C.PAPER, 3, S.WEAVING, B.WRITING, 2, technique=T.PAPER),
    ChainStep("print_books", "Printing books", W.PRINTING_HOUSE, ((C.PAPER, 1), (C.INK, 1)), C.BOOKS, 4, S.WRITING, B.WRITING, 2, technique=T.PRINTING),
    ChainStep("make_ink", "Making ink", W.DYEWORKS, ((C.DYE, 1), (C.OIL, 1)), C.INK, 3, S.ALCHEMY, B.WRITING, 1),
    ChainStep("boil_soap", "Boiling soap", W.ALCHEMIST, ((C.OIL, 1), (C.FUEL, 1)), C.SOAP, 2, S.ALCHEMY, B.MEDICINE, 1),
    ChainStep(
        "chemical_soap",
        "Making soap from chemical stock",
        W.ALCHEMIST,
        ((C.OIL, 1),),
        C.SOAP,
        4,
        S.ALCHEMY,
        B.MEDICINE,
        2,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "blow_glassware",
        "Blowing glassware",
        W.GLASSWORKS,
        ((C.STONE, 2), (C.FUEL, 2)),
        C.GLASSWARE,
        2,
        S.POTTERY,
        B.METALLURGY,
        2,
        material=MaterialKind.GLASS,
    ),
    ChainStep("lay_rope", "Laying rope", W.ROPEWALK, ((C.FIBRE, 2),), C.TOOLS, 1, S.WEAVING, None, 0),
    ChainStep("evaporate_salt", "Drawing salt from brine", W.EVAPORATION_WORKS, ((C.FUEL, 1),), C.HALITE, 3, S.ENGINEERING, None, 0),
    ChainStep("press_oil", "Pressing oil from fruit and seed", W.BREWERY, ((C.FRUIT, 2),), C.OIL, 1, S.ALCHEMY, B.AGRICULTURE, 1),
    ChainStep("render_wax", "Rendering wax from honeycomb", W.WAREHOUSE, ((C.HONEY, 2),), C.WAX, 1, S.ALCHEMY, None, 0),
    ChainStep("brew_base", "Brewing from a brew base", W.BREWERY, ((C.BREW_BASE, 2),), C.LUXURIES, 1, S.ALCHEMY, B.AGRICULTURE, 1),
    ChainStep("herbal_remedies", "Making remedies from herbs", None, ((C.HERBS, 2),), C.MEDICINE, 1, S.ALCHEMY, B.MEDICINE, 1),
    ChainStep("coke_fuel", "Baking coal into coke", W.CHARCOAL_KILN, ((C.COAL, 1),), C.FUEL, 2, S.ENGINEERING, technique=T.COKE_SMELTING),
    ChainStep(
        "coal_fuel",
        "Refining coal into gas and liquid fuel",
        W.CHARCOAL_KILN,
        ((C.COAL, 1),),
        C.FUEL,
        3,
        S.ALCHEMY,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.HEAT,
        energy_need=2,
    ),
    ChainStep(
        "crop_fuel",
        "Distilling fuel from crops",
        W.CHARCOAL_KILN,
        ((C.FODDER, 2),),
        C.FUEL,
        2,
        S.ALCHEMY,
        technique=T.COMBUSTION_ENGINE,
        energy=E.ELECTRIC,
        energy_need=2,
    ),
    ChainStep(
        "factory_wool",
        "Spinning and weaving wool in mills",
        W.WEAVERY,
        ((C.WOOL, 1),),
        C.CLOTH,
        2,
        S.WEAVING,
        material=MaterialKind.CLOTH,
        quality_gain=10,
        technique=T.STEAM_POWER,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "factory_fibre",
        "Spinning and weaving plant fibre in mills",
        W.WEAVERY,
        ((C.FIBRE, 1),),
        C.CLOTH,
        2,
        S.WEAVING,
        material=MaterialKind.CLOTH,
        technique=T.STEAM_POWER,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "synthetic_cloth",
        "Making synthetic fibre and cloth",
        W.WEAVERY,
        ((C.FUEL, 1),),
        C.CLOTH,
        3,
        S.WEAVING,
        material=MaterialKind.CLOTH,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.ELECTRIC,
        energy_need=2,
    ),
    ChainStep(
        "electric_tools",
        "Making tools in electric furnaces and machine shops",
        W.FORGE,
        ((C.ORE, 1),),
        C.TOOLS,
        3,
        S.ENGINEERING,
        B.METALLURGY,
        1,
        keeps_material=C.ORE,
        technique=T.ELECTRICITY,
        energy=E.ELECTRIC,
        energy_need=3,
    ),
    ChainStep(
        "electric_weapons",
        "Making weapons in electric furnaces and factories",
        W.FORGE,
        ((C.ORE, 1),),
        C.WEAPONS,
        2,
        S.ENGINEERING,
        B.METALLURGY,
        1,
        keeps_material=C.ORE,
        technique=T.ELECTRICITY,
        energy=E.ELECTRIC,
        energy_need=3,
    ),
    ChainStep(
        "electric_armour",
        "Rolling armour plate in electric works",
        W.FORGE,
        ((C.ORE, 2),),
        C.ARMOUR,
        2,
        S.ENGINEERING,
        B.METALLURGY,
        2,
        keeps_material=C.ORE,
        technique=T.ELECTRICITY,
        energy=E.ELECTRIC,
        energy_need=3,
    ),
    ChainStep(
        "factory_goods",
        "Making goods in factories",
        W.FORGE,
        ((C.ORE, 1), (C.FUEL, 1)),
        C.LUXURIES,
        3,
        S.ENGINEERING,
        technique=T.FACTORY_PRODUCTION,
        energy=E.HEAT,
        energy_need=2,
    ),
    ChainStep(
        "electronics", "Making electronics", W.FORGE, ((C.ORE, 1),), C.LUXURIES, 3, S.ENGINEERING, technique=T.COMPUTATION, energy=E.ELECTRIC, energy_need=4
    ),
    ChainStep(
        "factory_bread",
        "Milling and baking in factories",
        W.MILL,
        ((C.GRAIN, 2),),
        C.BREAD,
        3,
        S.ENGINEERING,
        B.AGRICULTURE,
        1,
        technique=T.FACTORY_PRODUCTION,
        energy=E.HEAT,
        energy_need=2,
    ),
    ChainStep(
        "concrete",
        "Making concrete",
        W.MASON_YARD,
        ((C.STONE, 1), (C.FUEL, 1)),
        C.STONE,
        3,
        S.MASONRY,
        B.ARCHITECTURE,
        1,
        material=MaterialKind.HYDRAULIC_CONCRETE,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.HEAT,
        energy_need=2,
    ),
    ChainStep("artillery", "Casting artillery", W.SIEGE_YARD, ((C.ORE, 2), (C.FUEL, 1)), C.SIEGE_MATERIEL, 2, S.ENGINEERING, B.WARFARE, 1, technique=T.CANNON),
    ChainStep(
        "rocket_ordnance",
        "Building rockets and guided ordnance",
        W.SIEGE_YARD,
        ((C.ORE, 2), (C.FUEL, 2)),
        C.SIEGE_MATERIEL,
        3,
        S.ENGINEERING,
        B.WARFARE,
        1,
        technique=T.ROCKETRY,
        energy=E.ELECTRIC,
        energy_need=4,
    ),
    ChainStep(
        "aroma_incense",
        "Making incense from chemical aromatics",
        W.SHRINE_WORKSHOP,
        ((C.FUEL, 1),),
        C.INCENSE,
        2,
        S.RITUAL,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "factory_sacred_goods",
        "Making sacred goods in factories",
        W.SHRINE_WORKSHOP,
        ((C.LUXURIES, 1),),
        C.SACRED_GOODS,
        1,
        S.RITUAL,
        technique=T.FACTORY_PRODUCTION,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "pharmacy",
        "Making medicine in chemical works",
        W.ALCHEMIST,
        ((C.HERBS, 1),),
        C.MEDICINE,
        3,
        S.MEDICINE,
        B.MEDICINE,
        1,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.HEAT,
        energy_need=1,
    ),
    ChainStep(
        "synthetic_medicine",
        "Making medicine from chemical stock",
        W.ALCHEMIST,
        ((C.FUEL, 1),),
        C.MEDICINE,
        2,
        S.MEDICINE,
        B.MEDICINE,
        2,
        technique=T.INDUSTRIAL_CHEMISTRY,
        energy=E.ELECTRIC,
        energy_need=2,
    ),
    ChainStep(
        "antibiotics",
        "Growing antibiotics",
        W.ALCHEMIST,
        ((C.GRAIN, 1),),
        C.MEDICINE,
        4,
        S.MEDICINE,
        B.MEDICINE,
        2,
        technique=T.ANTIBIOTICS,
        energy=E.ELECTRIC,
        energy_need=2,
    ),
)
STEPS: MappingProxyType[str, ChainStep] = MappingProxyType({step.key: step for step in CHAIN_STEPS})
SHIP_HULLS: tuple[tuple[Technique | None, tuple[tuple[CommodityKind, int], ...]], ...] = (
    (T.STEAMSHIPS, ((C.ORE, 4), (C.FUEL, 2))),
    (None, ((C.TIMBER, 4), (C.CLOTH, 1))),
)


def chain_depth(output: CommodityKind, seen: frozenset[CommodityKind] = frozenset()) -> int:
    made = {step.output for step in CHAIN_STEPS}
    feeds = {commodity for step in CHAIN_STEPS if step.output is output for commodity, _ in step.inputs if commodity is not output and commodity in made}
    return 1 + max((chain_depth(commodity, seen | {output}) for commodity in sorted(feeds) if commodity not in seen), default=0)


RECIPES: MappingProxyType[CommodityKind, tuple[ChainStep, ...]] = MappingProxyType(
    {
        output: tuple(step for step in CHAIN_STEPS if step.output is output)
        for output in sorted(
            dict.fromkeys(step.output for step in CHAIN_STEPS),
            key=lambda output: (chain_depth(output), next(index for index, step in enumerate(CHAIN_STEPS) if step.output is output)),
        )
    }
)


@dataclass(frozen=True)
class ExtractionSpec:
    kind: ExtractionKind
    workshop: WorkshopKind | None
    skill: SkillKind
    hazard: HazardKind | None
    season_key: str | None


EXTRACTION: MappingProxyType[ExtractionKind, ExtractionSpec] = total(
    ExtractionKind,
    {
        ExtractionKind.MINING: ExtractionSpec(ExtractionKind.MINING, W.MINE, S.ENGINEERING, HazardKind.CAVE_IN, None),
        ExtractionKind.QUARRYING: ExtractionSpec(ExtractionKind.QUARRYING, W.MINE, S.MASONRY, HazardKind.CAVE_IN, None),
        ExtractionKind.LOGGING: ExtractionSpec(ExtractionKind.LOGGING, W.LUMBER_CAMP, S.CARPENTRY, HazardKind.FELLING_ACCIDENT, "winter"),
        ExtractionKind.FISHING: ExtractionSpec(ExtractionKind.FISHING, W.FISHERY, S.SAILING, HazardKind.DROWNING, "summer"),
        ExtractionKind.HERDING: ExtractionSpec(ExtractionKind.HERDING, None, S.BEAST_HANDLING, HazardKind.GORING, None),
        ExtractionKind.FARMING: ExtractionSpec(ExtractionKind.FARMING, None, S.FORAGING, None, None),
        ExtractionKind.GATHERING: ExtractionSpec(ExtractionKind.GATHERING, None, S.FORAGING, None, None),
        ExtractionKind.DRILLING: ExtractionSpec(ExtractionKind.DRILLING, W.MINE, S.ENGINEERING, HazardKind.BLOWOUT, None),
        ExtractionKind.PUMPING: ExtractionSpec(ExtractionKind.PUMPING, W.MINE, S.ENGINEERING, HazardKind.SUBSIDENCE, None),
        ExtractionKind.DREDGING: ExtractionSpec(ExtractionKind.DREDGING, W.MASON_YARD, S.SAILING, HazardKind.DROWNING, "summer"),
        ExtractionKind.DEEP_SEA: ExtractionSpec(ExtractionKind.DEEP_SEA, W.SHIPYARD, S.SAILING, HazardKind.DECOMPRESSION, None),
        ExtractionKind.ATMOSPHERIC: ExtractionSpec(ExtractionKind.ATMOSPHERIC, W.MINE, S.ENGINEERING, HazardKind.EXPLOSION, None),
        ExtractionKind.ASTEROID: ExtractionSpec(ExtractionKind.ASTEROID, W.MINE, S.ENGINEERING, HazardKind.DECOMPRESSION, None),
        ExtractionKind.STELLAR: ExtractionSpec(ExtractionKind.STELLAR, W.MINE, S.ENGINEERING, HazardKind.RADIATION_EXPOSURE, None),
        ExtractionKind.SOURCE_HARVEST: ExtractionSpec(ExtractionKind.SOURCE_HARVEST, W.ALCHEMIST, S.SPELLCRAFT, HazardKind.SOURCE_BACKLASH, None),
        ExtractionKind.SALVAGE: ExtractionSpec(ExtractionKind.SALVAGE, W.FORGE, S.ENGINEERING, HazardKind.MACHINE_ACCIDENT, None),
        ExtractionKind.LIVING_HARVEST: ExtractionSpec(ExtractionKind.LIVING_HARVEST, W.TANNERY, S.BEAST_HANDLING, HazardKind.BEAST_ATTACK, None),
        ExtractionKind.DISTILLATION: ExtractionSpec(ExtractionKind.DISTILLATION, W.ALCHEMIST, S.ALCHEMY, HazardKind.TOXIC_RELEASE, None),
        ExtractionKind.EVAPORATING: ExtractionSpec(ExtractionKind.EVAPORATING, W.EVAPORATION_WORKS, S.ENGINEERING, HazardKind.BURNS, "summer"),
    },
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
        C.TUBERS: ExtractionKind.FARMING,
        C.FRUIT: ExtractionKind.GATHERING,
        C.MEAT: ExtractionKind.HERDING,
        C.MILK: ExtractionKind.HERDING,
        C.DUNG: ExtractionKind.HERDING,
        C.COAL: ExtractionKind.MINING,
        C.PEAT: ExtractionKind.GATHERING,
        C.FUEL: ExtractionKind.DRILLING,
        C.MAGICAL_REAGENTS: ExtractionKind.SOURCE_HARVEST,
        C.POISON: ExtractionKind.LIVING_HARVEST,
        C.WOOL: ExtractionKind.HERDING,
        C.EGGS: ExtractionKind.HERDING,
        C.FIBRE: ExtractionKind.FARMING,
        C.HERBS: ExtractionKind.GATHERING,
        C.DYE: ExtractionKind.GATHERING,
        C.INCENSE: ExtractionKind.DISTILLATION,
    }
)
WORKSHOP_LABELS: MappingProxyType[WorkshopKind, str] = MappingProxyType(
    {
        W.MARKET: "Market",
        W.GRANARY: "Grain store",
        W.WAREHOUSE: "Warehouse",
        W.MINE: "Mine",
        W.LUMBER_CAMP: "Logging site",
        W.FISHERY: "Fishery",
        W.CHARCOAL_KILN: "Fuel works",
        W.FORGE: "Metal works",
        W.TANNERY: "Leather works",
        W.MILL: "Mill",
        W.BREWERY: "Brewery",
        W.WEAVERY: "Textile works",
        W.STABLE: "Stable",
        W.MASON_YARD: "Stone works",
        W.SHIPYARD: "Shipyard",
        W.SIEGE_YARD: "Arms works",
        W.ALCHEMIST: "Chemical works",
        W.SHRINE_WORKSHOP: "Sacred works",
        W.MINT: "Mint",
        W.POTTERY: "Pottery",
        W.GLASSWORKS: "Glassworks",
        W.DYEWORKS: "Dyeworks",
        W.SCRIPTORIUM: "Scriptorium",
        W.EVAPORATION_WORKS: "Salt works",
        W.PAPER_MILL: "Paper mill",
        W.PRINTING_HOUSE: "Printing house",
        W.ROPEWALK: "Ropewalk",
    }
)

OPEN_GROUND_WORKSHOPS = frozenset({WorkshopKind.EVAPORATION_WORKS})
