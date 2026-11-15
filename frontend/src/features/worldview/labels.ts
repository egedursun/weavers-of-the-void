import {
  Anchor,
  Building2,
  CircleSlash,
  CloudRain,
  Droplets,
  Flame,
  Gem,
  Globe2,
  HandHeart,
  Layers,
  type LucideIcon,
  Moon,
  Mountain,
  Rocket,
  Ship,
  Sparkles,
  Sun,
  SunDim,
  Sunrise,
  Swords,
  Tent,
  Thermometer,
  Waves,
  Wind,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const WORLD_VIEW_ICON: LucideIcon = Globe2

export const LIGHTS: Record<Schema['WorldLight'], Named> = {
  star: { label: 'Its star', icon: Sun, tone: 'gold' },
  lava_glow: { label: 'The glow of lava', icon: Flame, tone: 'danger' },
  magic: { label: 'Light made by magic', icon: Sparkles, tone: 'info' },
  inner_sun: { label: 'A sun within', icon: Sunrise, tone: 'gold' },
  divine: { label: 'The light of a god', icon: Sparkles, tone: 'gold' },
  ship_cycle: { label: 'The cycles of a ship', icon: Rocket, tone: 'info' },
  fading_god: { label: 'A dead god fading', icon: SunDim, tone: 'muted' },
  none: { label: 'No light', icon: Moon, tone: 'muted' },
}

export const NEEDS: Record<Schema['BindingNeed'], Named> = {
  none: { label: 'Nothing beyond food', icon: CircleSlash, tone: 'muted' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  heat: { label: 'Heat', icon: Thermometer, tone: 'warning' },
  air: { label: 'Air', icon: Wind, tone: 'info' },
  offerings: { label: 'Offerings', icon: HandHeart, tone: 'gold' },
  belief: { label: 'Belief', icon: Sparkles, tone: 'verdigris' },
}

export const SETTLES: Record<Schema['SettleMode'], Named> = {
  ground: { label: 'On the ground', icon: Mountain, tone: 'muted' },
  floating: { label: 'Floating', icon: CloudRain, tone: 'info' },
  stilt: { label: 'On stilts', icon: Waves, tone: 'info' },
  oasis: { label: 'At oases', icon: Droplets, tone: 'success' },
  vent: { label: 'Around warm vents', icon: Flame, tone: 'warning' },
  habitat: { label: 'In sealed habitats', icon: Building2, tone: 'verdigris' },
  band: { label: 'In a habitable band', icon: Layers, tone: 'gold' },
  deck: { label: 'On decks', icon: Ship, tone: 'info' },
}

export const WARS: Record<Schema['WarTerrain'], Named> = {
  land: { label: 'On land', icon: Swords, tone: 'muted' },
  naval: { label: 'At sea', icon: Anchor, tone: 'info' },
  sky: { label: 'In the sky', icon: Wind, tone: 'info' },
  boarding: { label: 'By boarding', icon: Rocket, tone: 'warning' },
  strata: { label: 'Between strata', icon: Layers, tone: 'danger' },
}

export const SHARES = [
  { key: 'timber_pct', label: 'Timber', icon: Tent },
  { key: 'ore_yield_pct', label: 'Ore', icon: Gem },
  { key: 'food_need_pct', label: 'Food its people need', icon: HandHeart },
  { key: 'capacity_pct', label: 'Room for life', icon: Globe2 },
  { key: 'storm_pct', label: 'Storms', icon: Wind },
  { key: 'quake_pct', label: 'Quakes', icon: Mountain },
  { key: 'flood_pct', label: 'Floods', icon: Waves },
  { key: 'drought_pct', label: 'Droughts', icon: Sun },
  { key: 'plague_pct', label: 'Plagues', icon: CircleSlash },
] as const

export const NUMBERS = [
  { key: 'route_danger', label: 'Danger of its roads' },
  { key: 'leak', label: 'Leak it draws' },
  { key: 'leak_repair', label: 'Leak it mends' },
  { key: 'sanity_erosion', label: 'Sanity it wears away' },
  { key: 'fertility_decay', label: 'Fertility it loses' },
] as const

export const FLAGS = [
  { key: 'seasons', label: 'Seasons', icon: CloudRain },
  { key: 'nights', label: 'Nights', icon: Moon },
  { key: 'fire', label: 'Fire', icon: Flame },
  { key: 'soil', label: 'Soil', icon: Mountain },
] as const
