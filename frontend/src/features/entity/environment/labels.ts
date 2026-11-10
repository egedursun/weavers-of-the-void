import {
  Anchor,
  Bird,
  Bomb,
  Biohazard,
  Bug,
  Castle,
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudHail,
  CloudLightning,
  CloudRain,
  CloudSun,
  Droplets,
  Eclipse,
  Factory,
  Fence,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Hexagon,
  Landmark,
  Leaf,
  Mountain,
  MountainSnow,
  Pickaxe,
  Rabbit,
  Route,
  Sailboat,
  Shovel,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Sun,
  SunSnow,
  Swords,
  Tent,
  Thermometer,
  ThermometerSun,
  Tornado,
  Tractor,
  Trees,
  Truck,
  Wheat,
  Wind,
  type LucideIcon,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'

export type Named = { label: string; icon: LucideIcon; tone?: KpiTone }

export const TERRAIN: Record<string, Named> = {
  plain: { label: 'Plains', icon: Wheat },
  steppe: { label: 'Steppe', icon: Wind },
  forest: { label: 'Forest', icon: Trees, tone: 'success' },
  jungle: { label: 'Jungle', icon: Leaf, tone: 'success' },
  marsh: { label: 'Marsh', icon: Droplets, tone: 'verdigris' },
  hills: { label: 'Hills', icon: Mountain },
  mountains: { label: 'Mountains', icon: MountainSnow },
  high_pass: { label: 'High pass', icon: MountainSnow },
  desert: { label: 'Desert', icon: Sun, tone: 'warning' },
  tundra: { label: 'Tundra', icon: Snowflake, tone: 'info' },
  ice_sheet: { label: 'Ice sheet', icon: Snowflake, tone: 'info' },
  volcanic: { label: 'Volcanic land', icon: Flame, tone: 'danger' },
  coast: { label: 'Coast', icon: Anchor, tone: 'info' },
  island: { label: 'Islands', icon: Anchor, tone: 'info' },
  river_valley: { label: 'River valley', icon: Sprout, tone: 'success' },
  canyon: { label: 'Canyon', icon: Mountain, tone: 'warning' },
  underground: { label: 'Underground', icon: Pickaxe },
  crystal_field: { label: 'Crystal field', icon: Gem, tone: 'verdigris' },
  flesh: { label: 'Living flesh', icon: Biohazard, tone: 'danger' },
  void_shore: { label: 'Void shore', icon: Eclipse, tone: 'danger' },
  ruin_field: { label: 'Ruin field', icon: Landmark, tone: 'muted' },
  urban: { label: 'City', icon: Castle, tone: 'gold' },
  sea: { label: 'Sea', icon: Sailboat, tone: 'info' },
}

export const SOIL: Record<string, string> = {
  thin: 'Thin soil',
  loam: 'Loam',
  clay: 'Clay',
  sand: 'Sand',
  volcanic: 'Volcanic soil',
  peat: 'Peat',
  salt: 'Salt flats',
  ash: 'Ash',
  crystal: 'Crystal grit',
  bone: 'Bone meal',
}

export const BAND: Record<string, Named> = {
  frozen: { label: 'Frozen', icon: Snowflake, tone: 'info' },
  cold: { label: 'Cold', icon: Snowflake, tone: 'info' },
  temperate: { label: 'Temperate', icon: CloudSun, tone: 'success' },
  warm: { label: 'Warm', icon: Sun, tone: 'gold' },
  hot: { label: 'Hot', icon: ThermometerSun, tone: 'warning' },
  searing: { label: 'Searing', icon: Flame, tone: 'danger' },
}

export const RIVER: Record<string, string> = {
  none: 'No river',
  stream: 'Stream',
  river: 'River',
  great_river: 'Great river',
}

export const COAST: Record<string, string> = {
  none: 'Landlocked',
  cliff: 'Cliffs',
  beach: 'Beaches',
  harbour_site: 'Natural harbour',
  reef: 'Reefs',
}

export const COVER: Record<string, string> = {
  open: 'Open ground',
  light: 'Light cover',
  heavy: 'Heavy cover',
}

export const WATER: Record<string, string> = {
  none: 'No water',
  spring: 'Spring',
  well: 'Well',
  river: 'River',
  lake: 'Lake',
  sea: 'Sea',
}

export const WEATHER: Record<string, Named> = {
  clear: { label: 'Clear sky', icon: Sun, tone: 'gold' },
  overcast: { label: 'Overcast', icon: Cloud, tone: 'muted' },
  rain: { label: 'Rain', icon: CloudDrizzle, tone: 'info' },
  downpour: { label: 'Downpour', icon: CloudRain, tone: 'info' },
  storm: { label: 'Storm', icon: CloudLightning, tone: 'warning' },
  fog: { label: 'Fog', icon: CloudFog, tone: 'muted' },
  snow: { label: 'Snow', icon: Snowflake, tone: 'info' },
  blizzard: { label: 'Blizzard', icon: Snowflake, tone: 'danger' },
  heat_wave: { label: 'Heat wave', icon: ThermometerSun, tone: 'warning' },
  drought_wind: { label: 'Drought wind', icon: Wind, tone: 'warning' },
  sandstorm: { label: 'Sandstorm', icon: Tornado, tone: 'danger' },
  hail: { label: 'Hail', icon: CloudHail, tone: 'warning' },
  magic_storm: { label: 'Magic storm', icon: Sparkles, tone: 'verdigris' },
  ash_fall: { label: 'Ash fall', icon: Flame, tone: 'danger' },
  void_rain: { label: 'Void rain', icon: Eclipse, tone: 'danger' },
  eclipse_dark: { label: 'Eclipse darkness', icon: Eclipse, tone: 'muted' },
  aurora: { label: 'Aurora', icon: Sparkles, tone: 'info' },
}

export const WEATHER_EFFECTS: Record<string, string> = {
  visibility: 'Visibility',
  footing: 'Footing',
  cold: 'Cold',
  heat: 'Heat',
  wet: 'Wet',
  wind: 'Wind',
  morale: 'Omen',
  growth: 'Crop growth',
}

export const SCARS: Record<components['schemas']['ScarKind'], Named> = {
  battlefield: { label: 'Battlefield', icon: Swords, tone: 'danger' },
  plague_ground: { label: 'Plague ground', icon: Biohazard, tone: 'danger' },
  salted_earth: { label: 'Salted earth', icon: Hexagon, tone: 'warning' },
  burned: { label: 'Burned land', icon: Flame, tone: 'warning' },
  crater: { label: 'Crater', icon: Mountain, tone: 'warning' },
  haunted: { label: 'Haunted ground', icon: Ghost, tone: 'verdigris' },
  blighted: { label: 'Blight', icon: Bug, tone: 'danger' },
  leak_wound: { label: 'Leak wound', icon: Eclipse, tone: 'danger' },
  plundered: { label: 'Plundered', icon: Wheat, tone: 'warning' },
  earthworks: { label: 'Earthworks', icon: Shovel, tone: 'verdigris' },
  military_road: { label: 'Military road', icon: Route, tone: 'gold' },
  bridge_down: { label: 'Bridge down', icon: Bomb, tone: 'danger' },
}

export const MODES: Record<string, Named> = {
  on_foot: { label: 'On foot', icon: Footprints },
  mounted: { label: 'Mounted', icon: Rabbit },
  wheeled: { label: 'Wagons', icon: Truck },
  boat: { label: 'By boat', icon: Sailboat },
  flying: { label: 'Flying', icon: Bird },
  burrowing: { label: 'Burrowing', icon: Shovel },
}

export const LAND_USE: Record<string, Named> = {
  cleared: { label: 'Cleared', icon: Fence },
  farmed: { label: 'Farmland', icon: Tractor },
  grazed: { label: 'Pasture', icon: Tent },
  mined: { label: 'Mines', icon: Pickaxe },
  built: { label: 'Built up', icon: Factory },
}

export const MINERALS: Record<string, string> = {
  stone: 'Stone',
  flint: 'Flint',
  obsidian: 'Obsidian',
  copper: 'Copper',
  tin: 'Tin',
  iron: 'Iron',
  silver: 'Silver',
  gold: 'Gold',
  crystal: 'Crystal',
  salt: 'Salt',
  amber: 'Amber',
  lead: 'Lead',
  sulfur: 'Sulfur',
  clay: 'Clay',
  gems: 'Gems',
  star_metal: 'Star metal',
  void_glass: 'Void glass',
}

export const CLIMATE_AGE: Record<string, Named> = {
  temperate: { label: 'Temperate age', icon: CloudSun, tone: 'success' },
  drought: { label: 'Drought century', icon: Sun, tone: 'warning' },
  rain: { label: 'Rain age', icon: CloudRain, tone: 'info' },
  ice_age: { label: 'Ice age', icon: Snowflake, tone: 'info' },
  scorching: { label: 'Scorching age', icon: Flame, tone: 'danger' },
}

export const NOTABLE: Record<string, Named> = {
  hunger: { label: 'Hungry year', icon: Wheat, tone: 'danger' },
  plenty: { label: 'Year of plenty', icon: Wheat, tone: 'success' },
  weather: { label: 'Wild weather', icon: CloudLightning, tone: 'warning' },
  pestilence: { label: 'Pestilence', icon: Skull, tone: 'danger' },
}

export const FIELD_LABELS: Record<string, string> = {
  leak: 'Leak from other dimensions',
  current: 'Sea current',
  temperature_shift: 'Heat shift',
  rainfall_shift: 'Rain shift',
  temperature: 'Temperature',
  rainfall: 'Rainfall',
  seasonality: 'Seasonality',
  latitude: 'Latitude',
  elevation_mean: 'Elevation',
  roughness: 'Roughness',
  moisture: 'Moisture',
  base_forest: 'Natural woodland',
  forest_cover: 'Forest cover',
  base_wetland: 'Natural wetland',
  wetland: 'Wetland',
  soil_fertility: 'Soil fertility',
  soil_base: 'Natural soil fertility',
  disease_load: 'Disease load',
  magic_density: 'Magic density',
  defensibility: 'Defensibility',
  erosion: 'Erosion',
  harvest_pct: 'Last harvest',
  dominant_terrain: 'Terrain',
  soil: 'Soil',
  river_class: 'River',
  coast_kind: 'Coast',
  temperature_band: 'Climate band',
  sacredness: 'Sacredness',
  derived_fertility: 'Fertility the land last gave',
  biome_mix: 'Biomes',
  cleared: 'Cleared land',
}

export const THERMOMETER_ICON = Thermometer
export const SEASONALITY_ICON = SunSnow

export function fieldLabel(key: string): string {
  if (key.startsWith('scar.'))
    return `${named(SCARS, key.slice('scar.'.length)).label} scar`
  if (key.startsWith('seam.'))
    return `${MINERALS[key.slice('seam.'.length)] ?? 'Mineral'} seam`
  if (key.startsWith('passability.'))
    return `${MODES[key.slice('passability.'.length)]?.label ?? key} passability`
  return (
    FIELD_LABELS[key] ??
    LAND_USE[key]?.label ??
    key.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())
  )
}

export function named(table: Record<string, Named>, key: string): Named {
  return (
    table[key] ?? {
      label: key
        .replaceAll('_', ' ')
        .replace(/^./, (first) => first.toUpperCase()),
      icon: Sparkles,
    }
  )
}

export function plain(table: Record<string, string>, key: string): string {
  return (
    table[key] ??
    key.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())
  )
}
