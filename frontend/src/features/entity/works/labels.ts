import {
  Anvil,
  Beef,
  BicepsFlexed,
  Cloud,
  Droplets,
  Factory,
  Fish,
  Flame,
  FlaskConical,
  Gem,
  HandCoins,
  KeyRound,
  Lamp,
  TriangleAlert,
  Hammer,
  Leaf,
  Mountain,
  Pickaxe,
  Shirt,
  Snowflake,
  Sparkles,
  Sun,
  Trees,
  Waves,
  Wheat,
  Wind,
  Wine,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const WORKS_ICON = Factory
export const POWER_ICON = BicepsFlexed
export const STORES_ICON = Snowflake
export const LAND_ICON = Leaf

export const ENERGY: Record<string, Named> = {
  muscle: { label: 'Muscle', icon: BicepsFlexed, tone: 'gold' },
  water: { label: 'Water', icon: Waves, tone: 'info' },
  wind: { label: 'Wind', icon: Wind, tone: 'verdigris' },
  heat: { label: 'Heat', icon: Flame, tone: 'warning' },
  magic: { label: 'Magic', icon: Sparkles, tone: 'info' },
  divine: { label: 'Divine', icon: Sun, tone: 'gold' },
}

export const PROCESSES: Record<string, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
  mining: { label: 'Mining and quarrying', icon: Pickaxe, tone: 'muted' },
  milling: { label: 'Milling and baking', icon: Wheat, tone: 'gold' },
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
}

export const POLLUTANTS: Record<string, Named> = {
  air: { label: 'Air', icon: Cloud, tone: 'muted' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  soil: { label: 'Soil', icon: Mountain, tone: 'warning' },
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
