from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, ExtractionKind, WorkshopKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.industry import EnergyKind, MethodKind, Pollutant, ProcessKind, QualityTier
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch

E = EnergyKind
M = MethodKind
P = ProcessKind
B = KnowledgeBranch
T = TemperatureBand
COLD = frozenset({T.FROZEN, T.COLD})
DRY_HEAT = frozenset({T.WARM, T.HOT, T.SEARING})


@dataclass(frozen=True)
class MethodSpec:
    kind: MethodKind
    process: ProcessKind
    label: str
    summary: str
    energy: EnergyKind
    energy_need: int
    output_pct: int = 100
    quality_bonus: int = 0
    air: int = 0
    water: int = 0
    soil: int = 0
    tool_wear: int = 1
    technique: Technique | None = None
    branch: KnowledgeBranch | None = None
    level: int = 0
    climate: frozenset[TemperatureBand] | None = None
    coast: bool = False
    labour_pct: int = 100
    inputs: tuple[tuple[CommodityKind, int, MaterialKind | None], ...] = ()

    @property
    def fouls(self) -> int:
        return max(0, self.air) + max(0, self.water) + max(0, self.soil)

    def pollution(self, pollutant: Pollutant) -> int:
        return {Pollutant.AIR: self.air, Pollutant.WATER: self.water, Pollutant.SOIL: self.soil}[pollutant]


m = MethodSpec
METHODS: MappingProxyType[MethodKind, MethodSpec] = MappingProxyType(
    {
        spec.kind: spec
        for spec in (
            m(M.HAND_SICKLE, P.FARMING, "Hand sickle", "Fields reaped by hand", E.MUSCLE, 2),
            m(
                M.OX_PLOUGH,
                P.FARMING,
                "Ox plough",
                "Draught beasts break the soil",
                E.MUSCLE,
                3,
                quality_bonus=5,
                soil=1,
                tool_wear=2,
                technique=Technique.PLOUGH,
                labour_pct=80,
            ),
            m(
                M.IRRIGATED_TERRACES,
                P.FARMING,
                "Irrigated terraces",
                "Channels carry water to stepped fields",
                E.WATER,
                2,
                quality_bonus=5,
                technique=Technique.IRRIGATION,
            ),
            m(
                M.CROP_ROTATION,
                P.FARMING,
                "Crop rotation",
                "Fields rest in turn and the soil recovers",
                E.MUSCLE,
                2,
                quality_bonus=5,
                soil=-2,
                technique=Technique.CROP_ROTATION,
            ),
            m(
                M.DIVINE_HARVEST,
                P.FARMING,
                "Divine harvest",
                "Rites call the harvest out of the ground",
                E.DIVINE,
                3,
                output_pct=125,
                quality_bonus=10,
                tool_wear=0,
                inputs=((CommodityKind.INCENSE, 1, None),),
            ),
            m(M.LINE_AND_NET, P.FISHING, "Line and net", "Fish taken from boats close to shore", E.MUSCLE, 2),
            m(M.FISH_WEIRS, P.FISHING, "Fish weirs", "Fences in the current trap the shoals", E.WATER, 1, output_pct=115),
            m(
                M.DEEP_SEA_FLEETS,
                P.FISHING,
                "Deep-sea fleets",
                "Sailing fleets follow the shoals far out",
                E.WIND,
                3,
                output_pct=135,
                tool_wear=2,
                technique=Technique.SAILING,
                coast=True,
            ),
            m(M.AXE_FELLING, P.LOGGING, "Axe felling", "Trees felled and split by hand", E.MUSCLE, 2, tool_wear=2),
            m(
                M.WATER_SAWMILL,
                P.LOGGING,
                "Water sawmill",
                "A wheel drives the saws",
                E.WATER,
                3,
                output_pct=140,
                branch=B.ARCHITECTURE,
                level=1,
                labour_pct=60,
            ),
            m(M.PICK_AND_SHOVEL, P.MINING, "Pick and shovel", "Seams dug out by hand", E.MUSCLE, 3, soil=2, tool_wear=3),
            m(
                M.FIRE_SETTING,
                P.MINING,
                "Fire-setting",
                "Fires crack the rock face",
                E.HEAT,
                3,
                output_pct=125,
                air=3,
                soil=2,
                tool_wear=2,
                inputs=((CommodityKind.TIMBER, 1, None),),
            ),
            m(
                M.PUMPED_SHAFTS,
                P.MINING,
                "Pumped shafts",
                "Wheels drain deep shafts",
                E.WATER,
                3,
                output_pct=150,
                water=2,
                soil=3,
                tool_wear=2,
                branch=B.ARCHITECTURE,
                level=2,
            ),
            m(M.EARTH_SHAPING, P.MINING, "Earth-shaping", "Magic opens the stone", E.MAGIC, 4, output_pct=140, soil=1, tool_wear=0, branch=B.MAGIC, level=2),
            m(M.HAND_QUERN, P.MILLING, "Hand quern", "Grain ground at home", E.MUSCLE, 2, output_pct=80, labour_pct=150),
            m(M.WATERMILL, P.MILLING, "Watermill", "A river turns the millstones", E.WATER, 2, output_pct=120, branch=B.ARCHITECTURE, level=1, labour_pct=50),
            m(M.WINDMILL, P.MILLING, "Windmill", "Sails turn the millstones", E.WIND, 2, output_pct=115, branch=B.ARCHITECTURE, level=1, labour_pct=60),
            m(M.HAND_LOOM, P.WEAVING, "Hand loom", "Cloth woven by hand", E.MUSCLE, 1, labour_pct=130),
            m(
                M.WATER_FRAME,
                P.WEAVING,
                "Water frame",
                "A wheel drives spindles and looms",
                E.WATER,
                3,
                output_pct=150,
                water=1,
                branch=B.ARCHITECTURE,
                level=2,
                labour_pct=50,
            ),
            m(M.BLOOMERY, P.SMELTING, "Bloomery", "Charcoal fires work the metal", E.HEAT, 2, air=2, soil=1),
            m(
                M.BLAST_FURNACE,
                P.SMELTING,
                "Blast furnace",
                "A roaring furnace runs metal by the ton",
                E.HEAT,
                4,
                output_pct=140,
                quality_bonus=10,
                air=4,
                soil=2,
                technique=Technique.STEEL,
                labour_pct=80,
                inputs=((CommodityKind.FUEL, 1, None),),
            ),
            m(
                M.DIVINE_FORGE,
                P.SMELTING,
                "Divine forge",
                "Holy fire works the metal",
                E.DIVINE,
                3,
                output_pct=110,
                quality_bonus=25,
                tool_wear=0,
                inputs=((CommodityKind.SACRED_GOODS, 1, None),),
            ),
            m(M.PIT_TANNING, P.TANNING, "Pit tanning", "Hides steeped in pits of bark", E.MUSCLE, 1, water=3, soil=1),
            m(
                M.OIL_CURING,
                P.TANNING,
                "Oil curing",
                "Hides cured over smoke with oils",
                E.HEAT,
                1,
                output_pct=90,
                quality_bonus=5,
                air=1,
                inputs=((CommodityKind.FISH, 1, None),),
            ),
            m(M.OPEN_VAT, P.BREWING, "Open vat", "Brewed in open vats", E.HEAT, 1),
            m(
                M.CELLAR_BREWING,
                P.BREWING,
                "Cellar brewing",
                "Aged slowly in cool cellars",
                E.HEAT,
                1,
                quality_bonus=10,
                branch=B.AGRICULTURE,
                level=3,
                labour_pct=120,
            ),
            m(M.HERBAL_STILL, P.DISTILLING, "Herbal still", "Remedies boiled from herbs", E.HEAT, 1),
            m(
                M.ARCANE_ALEMBIC,
                P.DISTILLING,
                "Arcane alembic",
                "Magic draws out the essence",
                E.MAGIC,
                2,
                output_pct=130,
                quality_bonus=10,
                air=1,
                technique=Technique.ALCHEMY,
                labour_pct=70,
            ),
            m(M.HAND_CHISEL, P.MASONRY, "Hand chisel", "Stone dressed by hand", E.MUSCLE, 2, air=1, tool_wear=2),
            m(M.WATER_SAW, P.MASONRY, "Water saw", "A wheel drives the stone saws", E.WATER, 2, output_pct=140, branch=B.ARCHITECTURE, level=2, labour_pct=60),
            m(M.CLAMP_KILN, P.CHARCOAL, "Clamp kiln", "Wood smoulders under turf", E.MUSCLE, 1, air=3),
            m(M.RETORT_KILN, P.CHARCOAL, "Retort kiln", "Sealed kilns waste little", E.MUSCLE, 1, output_pct=125, air=1, branch=B.METALLURGY, level=2),
            m(M.SALTING, P.PRESERVING, "Salting", "Packed in salt", E.MUSCLE, 1, tool_wear=0, inputs=((CommodityKind.ORE, 1, MaterialKind.SALT),)),
            m(M.SMOKING, P.PRESERVING, "Smoking", "Hung in smokehouses", E.HEAT, 1, air=1, tool_wear=0),
            m(M.DRYING, P.PRESERVING, "Drying", "Laid out in the sun and wind", E.WIND, 1, output_pct=80, tool_wear=0, climate=DRY_HEAT),
            m(M.ICING, P.PRESERVING, "Icing", "Kept in ice on cold land or in deep cellars", E.MUSCLE, 1, output_pct=130, tool_wear=0, climate=COLD),
            m(M.MAGIC_KEEPING, P.PRESERVING, "Magic keeping", "Spells hold back the rot", E.MAGIC, 2, output_pct=150, tool_wear=0, branch=B.MAGIC, level=1),
            m(
                M.TALLOW_CANDLES,
                P.LIGHTING,
                "Tallow candles",
                "Candles rendered from animal fat",
                E.MUSCLE,
                1,
                air=1,
                tool_wear=0,
                inputs=((CommodityKind.LIVESTOCK, 1, None),),
            ),
            m(
                M.OIL_LAMPS,
                P.LIGHTING,
                "Oil lamps",
                "Lamps burning oil pressed from fish",
                E.MUSCLE,
                1,
                output_pct=120,
                air=1,
                tool_wear=0,
                inputs=((CommodityKind.FISH, 1, None),),
            ),
            m(
                M.GLOW_MOSS,
                P.LIGHTING,
                "Glow-moss",
                "Moss that gives its own light, tended in wet places",
                E.MUSCLE,
                1,
                output_pct=90,
                tool_wear=0,
                branch=B.AGRICULTURE,
                level=2,
            ),
            m(M.MAGIC_LIGHT, P.LIGHTING, "Magic light", "Lights kindled and kept by spells", E.MAGIC, 2, output_pct=150, tool_wear=0, branch=B.MAGIC, level=1),
        )
    }
)
PROCESS_METHODS: MappingProxyType[ProcessKind, tuple[MethodSpec, ...]] = MappingProxyType(
    {process: tuple(spec for spec in METHODS.values() if spec.process is process) for process in ProcessKind}
)
PROCESS_LABELS: MappingProxyType[ProcessKind, str] = MappingProxyType(
    {
        P.FARMING: "Farming",
        P.FISHING: "Fishing",
        P.LOGGING: "Logging",
        P.MINING: "Mining and quarrying",
        P.MILLING: "Milling and baking",
        P.WEAVING: "Spinning and weaving",
        P.SMELTING: "Smelting and forging",
        P.TANNING: "Tanning",
        P.BREWING: "Brewing",
        P.DISTILLING: "Distilling remedies",
        P.MASONRY: "Dressing stone",
        P.CHARCOAL: "Charcoal burning",
        P.PRESERVING: "Preserving food",
        P.LIGHTING: "Lighting",
    }
)
STEP_PROCESS: MappingProxyType[str, ProcessKind] = MappingProxyType(
    {
        "charcoal": P.CHARCOAL,
        "forge_tools": P.SMELTING,
        "forge_weapons": P.SMELTING,
        "forge_armour": P.SMELTING,
        "jewellery": P.SMELTING,
        "tan_hides": P.TANNING,
        "leather_armour": P.TANNING,
        "weave": P.WEAVING,
        "spin": P.WEAVING,
        "mill": P.MILLING,
        "brew": P.BREWING,
        "potions": P.DISTILLING,
        "dress_stone": P.MASONRY,
    }
)
EXTRACTION_PROCESS: MappingProxyType[ExtractionKind, ProcessKind] = MappingProxyType(
    {
        ExtractionKind.FARMING: P.FARMING,
        ExtractionKind.FISHING: P.FISHING,
        ExtractionKind.LOGGING: P.LOGGING,
        ExtractionKind.MINING: P.MINING,
        ExtractionKind.QUARRYING: P.MINING,
    }
)
ENERGY_LABELS: MappingProxyType[EnergyKind, str] = MappingProxyType(
    {E.MUSCLE: "Muscle", E.WATER: "Water", E.WIND: "Wind", E.HEAT: "Heat", E.MAGIC: "Magic", E.DIVINE: "Divine"}
)
ENERGY_SOURCES: MappingProxyType[EnergyKind, str] = MappingProxyType(
    {
        E.MUSCLE: "labour and draught beasts",
        E.WATER: "rivers turning wheels",
        E.WIND: "coasts and high ground",
        E.HEAT: "fuel and timber burned",
        E.MAGIC: "ley lines and mages",
        E.DIVINE: "shrines, priests and rites",
    }
)
POLLUTANT_LABELS: MappingProxyType[Pollutant, str] = MappingProxyType({Pollutant.AIR: "Air", Pollutant.WATER: "Water", Pollutant.SOIL: "Soil"})
TIER_LABELS: MappingProxyType[QualityTier, str] = MappingProxyType(
    {
        QualityTier.POOR: "Poor",
        QualityTier.COMMON: "Common",
        QualityTier.FINE: "Fine",
        QualityTier.SUPERIOR: "Superior",
        QualityTier.EXCEPTIONAL: "Exceptional",
        QualityTier.MASTERWORK: "Masterwork",
        QualityTier.ARTIFACT: "Artifact",
    }
)
PERISHABLE: MappingProxyType[CommodityKind, str] = MappingProxyType(
    {CommodityKind.FISH: "fish_pct", CommodityKind.BREAD: "bread_pct", CommodityKind.GRAIN: "grain_pct", CommodityKind.MEDICINE: "medicine_pct"}
)
FUEL_FAMILY: tuple[CommodityKind, ...] = (CommodityKind.FUEL, CommodityKind.TIMBER)


def default_method(process: ProcessKind) -> MethodSpec:
    return PROCESS_METHODS[process][0]


PROCESS_OUTPUT: MappingProxyType[ProcessKind, CommodityKind] = MappingProxyType(
    {
        P.FARMING: CommodityKind.GRAIN,
        P.FISHING: CommodityKind.FISH,
        P.LOGGING: CommodityKind.TIMBER,
        P.MINING: CommodityKind.ORE,
        P.MILLING: CommodityKind.BREAD,
        P.WEAVING: CommodityKind.CLOTH,
        P.SMELTING: CommodityKind.TOOLS,
        P.TANNING: CommodityKind.CLOTH,
        P.BREWING: CommodityKind.LUXURIES,
        P.DISTILLING: CommodityKind.MEDICINE,
        P.MASONRY: CommodityKind.STONE,
        P.CHARCOAL: CommodityKind.FUEL,
        P.PRESERVING: CommodityKind.FISH,
        P.LIGHTING: CommodityKind.LUXURIES,
    }
)
PROCESS_JOB: MappingProxyType[ProcessKind, Job] = MappingProxyType(
    {P.FARMING: Job.FARMING, P.FISHING: Job.FISHING, P.LOGGING: Job.BUILDING, P.MINING: Job.MINING}
)
PROCESS_WORKSHOP: MappingProxyType[ProcessKind, WorkshopKind] = MappingProxyType(
    {
        P.FISHING: WorkshopKind.FISHERY,
        P.LOGGING: WorkshopKind.LUMBER_CAMP,
        P.MINING: WorkshopKind.MINE,
        P.MILLING: WorkshopKind.MILL,
        P.SMELTING: WorkshopKind.FORGE,
        P.TANNING: WorkshopKind.TANNERY,
        P.BREWING: WorkshopKind.BREWERY,
        P.DISTILLING: WorkshopKind.ALCHEMIST,
        P.MASONRY: WorkshopKind.MASON_YARD,
        P.CHARCOAL: WorkshopKind.CHARCOAL_KILN,
    }
)
ALWAYS_PRACTISED = frozenset({P.FARMING, P.WEAVING, P.PRESERVING, P.LIGHTING})
