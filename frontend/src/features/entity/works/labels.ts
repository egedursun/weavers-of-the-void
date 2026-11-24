import {
  Anvil,
  Atom,
  Axe,
  BatteryCharging,
  Beef,
  BicepsFlexed,
  BookCopy,
  Cable,
  Church,
  CircleDashed,
  Cloud,
  Droplets,
  Egg,
  Factory,
  Fish,
  Flame,
  FlaskConical,
  Fuel,
  Gem,
  Grape,
  Hammer,
  HandCoins,
  KeyRound,
  Lamp,
  Leaf,
  Lightbulb,
  Milk,
  Mountain,
  Orbit,
  Palette,
  Pickaxe,
  Printer,
  Radiation,
  Scissors,
  ScrollText,
  Shirt,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  SunMedium,
  Thermometer,
  Trees,
  TriangleAlert,
  Volume2,
  Waves,
  Wheat,
  Wind,
  Wine,
  Zap,
  FlameKindling,
  Sparkle,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export const WORKS_ICON = Factory
export const POWER_ICON = BicepsFlexed
export const STORES_ICON = Snowflake
export const LAND_ICON = Leaf

export const ENERGY: Record<components['schemas']['EnergyKind'], Named> = {
  muscle: { label: 'Muscle', icon: BicepsFlexed, tone: 'gold' },
  water: { label: 'Water', icon: Waves, tone: 'info' },
  wind: { label: 'Wind', icon: Wind, tone: 'verdigris' },
  heat: { label: 'Heat', icon: Flame, tone: 'warning' },
  magic: { label: 'Magic', icon: Sparkles, tone: 'info' },
  divine: { label: 'Divine', icon: Sun, tone: 'gold' },
  fuel: { label: 'Fuel', icon: Fuel, tone: 'warning' },
  electric: { label: 'Electric', icon: Zap, tone: 'info' },
  stored: { label: 'Stored', icon: BatteryCharging, tone: 'info' },
  solar: { label: 'Solar', icon: SunMedium, tone: 'gold' },
  geothermal: { label: 'Geothermal', icon: Mountain, tone: 'warning' },
  tidal: { label: 'Tidal', icon: Droplets, tone: 'info' },
  fission: { label: 'Fission', icon: Atom, tone: 'danger' },
  fusion: { label: 'Fusion', icon: Orbit, tone: 'gold' },
  stellar: { label: 'Stellar', icon: Star, tone: 'gold' },
  source: {
    label: 'From a source of power',
    icon: Sparkle,
    tone: 'verdigris',
  },
  feed: { label: 'Living feed', icon: Sprout, tone: 'success' },
  belief: { label: 'Belief', icon: Church, tone: 'gold' },
  void: { label: 'Drawn from the leak', icon: CircleDashed, tone: 'muted' },
}

export const PROCESSES: Record<string, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
  mining: { label: 'Mining and quarrying', icon: Pickaxe, tone: 'muted' },
  milling: { label: 'Milling and baking', icon: Sprout, tone: 'gold' },
  weaving: { label: 'Spinning and weaving', icon: Shirt, tone: 'verdigris' },
  smelting: { label: 'Smelting and forging', icon: Anvil, tone: 'warning' },
  tanning: { label: 'Tanning', icon: Beef, tone: 'muted' },
  brewing: { label: 'Brewing', icon: Wine, tone: 'gold' },
  distilling: {
    label: 'Distilling remedies',
    icon: FlaskConical,
    tone: 'info',
  },
  masonry: { label: 'Dressing stone', icon: Mountain, tone: 'muted' },
  charcoal: { label: 'Charcoal burning', icon: Flame, tone: 'warning' },
  preserving: { label: 'Preserving food', icon: Snowflake, tone: 'info' },
  lighting: { label: 'Lighting', icon: Lamp, tone: 'gold' },
  butchery: { label: 'Butchery', icon: Beef, tone: 'danger' },
  dairy: { label: 'Dairy', icon: Milk, tone: 'info' },
  pressing: { label: 'Pressing fruit', icon: Grape, tone: 'gold' },
  milking: { label: 'Milking', icon: Milk, tone: 'info' },
  shearing: { label: 'Shearing', icon: Scissors, tone: 'verdigris' },
  egg_laying: { label: 'Keeping laying birds', icon: Egg, tone: 'gold' },
  smithing: { label: 'Smithing', icon: Hammer, tone: 'warning' },
  carpentry: { label: 'Carpentry', icon: Axe, tone: 'success' },
  firing: {
    label: 'Firing clay and glass',
    icon: FlameKindling,
    tone: 'danger',
  },
  dyeing: { label: 'Dyeing', icon: Palette, tone: 'verdigris' },
  copying: { label: 'Copying writings', icon: BookCopy, tone: 'info' },
  evaporating: { label: 'Making salt', icon: Waves, tone: 'muted' },
  papermaking: { label: 'Making paper', icon: ScrollText, tone: 'muted' },
  printing: { label: 'Printing', icon: Printer, tone: 'info' },
  ropemaking: { label: 'Making rope', icon: Cable, tone: 'muted' },
}

export const POLLUTANTS: Record<string, Named> = {
  air: { label: 'Air', icon: Cloud, tone: 'muted' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  soil: { label: 'Soil', icon: Mountain, tone: 'warning' },
  radiation: { label: 'Radiation', icon: Radiation, tone: 'danger' },
  noise: { label: 'Noise', icon: Volume2, tone: 'warning' },
  light: { label: 'Light at night', icon: Lightbulb, tone: 'gold' },
  heat: { label: 'Heat in the waters', icon: Thermometer, tone: 'danger' },
}

export const TIER_TONE: Record<string, Named['tone']> = {
  poor: 'danger',
  common: 'muted',
  fine: 'verdigris',
  superior: 'info',
  exceptional: 'success',
  masterwork: 'gold',
  artifact: 'gold',
}

export const TIER_ICON = Gem
export const TOOL_ICON = Hammer
export const OWNER_ICON = KeyRound
export const LEDGER_ICON = HandCoins
export const SHOCK_ICON = TriangleAlert
export const LIGHT_ICON = Lamp
