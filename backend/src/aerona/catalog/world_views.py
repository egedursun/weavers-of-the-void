from dataclasses import dataclass, replace
from types import MappingProxyType

from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight

W = WorldType


@dataclass(frozen=True)
class WorldViewSpec:
    light: WorldLight = WorldLight.STAR
    seasons: bool = True
    nights: bool = True
    fire: bool = True
    soil: bool = True
    timber_pct: int = 100
    food_need_pct: int = 100
    need: BindingNeed = BindingNeed.NONE
    settle: SettleMode = SettleMode.GROUND
    war: WarTerrain = WarTerrain.LAND
    sea_pct: int | None = None


ORDINARY_VIEW = WorldViewSpec()
SKY_WORLD = WorldViewSpec(soil=False, timber_pct=0, settle=SettleMode.FLOATING, war=WarTerrain.SKY)
SEALED_WORLD = WorldViewSpec(soil=False, timber_pct=0, need=BindingNeed.AIR, settle=SettleMode.HABITAT)

WORLD_VIEWS: MappingProxyType[WorldType, WorldViewSpec] = MappingProxyType(
    {
        W.ORDINARY: ORDINARY_VIEW,
        W.OCEAN: WorldViewSpec(timber_pct=30, settle=SettleMode.STILT, war=WarTerrain.NAVAL, sea_pct=70),
        W.SAND: WorldViewSpec(timber_pct=20, need=BindingNeed.WATER, settle=SettleMode.OASIS),
        W.ICE: WorldViewSpec(timber_pct=10, need=BindingNeed.HEAT, settle=SettleMode.VENT),
        W.LAVA: WorldViewSpec(light=WorldLight.LAVA_GLOW, timber_pct=40),
        W.CRYSTAL: WorldViewSpec(soil=False, timber_pct=10),
        W.LIVING: ORDINARY_VIEW,
        W.DEAD: WorldViewSpec(light=WorldLight.MAGIC, seasons=False, soil=False, timber_pct=0, need=BindingNeed.OFFERINGS, war=WarTerrain.STRATA),
        W.DREAM: WorldViewSpec(light=WorldLight.MAGIC, need=BindingNeed.BELIEF),
        W.MIRROR: ORDINARY_VIEW,
        W.GAS: SKY_WORLD,
        W.RINGED: ORDINARY_VIEW,
        W.ASTEROID_BELT: replace(SEALED_WORLD, seasons=False, fire=False, war=WarTerrain.BOARDING),
        W.TIDALLY_LOCKED: WorldViewSpec(seasons=False, nights=False, settle=SettleMode.BAND),
        W.VOID_POCKET: replace(SEALED_WORLD, light=WorldLight.MAGIC, seasons=False, war=WarTerrain.SPACE),
        W.GODS_PALACE: WorldViewSpec(light=WorldLight.DIVINE, seasons=False),
        W.GENERATION_SHIP: replace(SEALED_WORLD, light=WorldLight.SHIP_CYCLE, seasons=False, settle=SettleMode.DECK, war=WarTerrain.BOARDING),
        W.CORPSE_WORLD: WorldViewSpec(light=WorldLight.FADING_GOD),
        W.SUPER_EARTH: WorldViewSpec(food_need_pct=120),
        W.ICE_GIANT: SKY_WORLD,
        W.HOT_GIANT: replace(SKY_WORLD, seasons=False, nights=False),
        W.IRON: WorldViewSpec(timber_pct=20),
        W.CARBON: WorldViewSpec(timber_pct=30),
        W.GREENHOUSE: WorldViewSpec(seasons=False, timber_pct=10, need=BindingNeed.WATER, settle=SettleMode.HABITAT),
        W.DWARF_PLANET: replace(SEALED_WORLD, fire=False),
        W.CHTHONIAN: replace(SEALED_WORLD, seasons=False, nights=False, fire=False, war=WarTerrain.UNDERGROUND),
        W.HYCEAN: WorldViewSpec(timber_pct=20, settle=SettleMode.FLOATING, war=WarTerrain.NAVAL, sea_pct=70),
        W.JUNGLE: WorldViewSpec(timber_pct=150),
        W.FORGE: WorldViewSpec(timber_pct=50),
        W.FUNGAL: WorldViewSpec(timber_pct=40),
        W.SHATTERED: WorldViewSpec(war=WarTerrain.SKY),
        W.HOLLOW: WorldViewSpec(light=WorldLight.INNER_SUN, seasons=False, nights=False),
        W.ICE_SHELL: WorldViewSpec(soil=False, timber_pct=0, fire=False, need=BindingNeed.HEAT, settle=SettleMode.VENT, war=WarTerrain.UNDER_WATER, sea_pct=60),
        W.METHANE: WorldViewSpec(timber_pct=0, fire=False, need=BindingNeed.HEAT),
    }
)
