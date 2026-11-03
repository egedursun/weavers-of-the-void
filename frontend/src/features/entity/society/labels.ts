import {
  Anchor,
  Baby,
  BookOpen,
  Castle,
  Church,
  Coins,
  Crown,
  Fish,
  Flame,
  Ghost,
  Gem,
  Globe,
  Hammer,
  HandCoins,
  HeartPulse,
  Landmark,
  Link,
  Mountain,
  Pickaxe,
  Shield,
  Skull,
  Sprout,
  Store,
  Swords,
  Tent,
  TreePine,
  User,
  UserRound,
  Users,
  Wheat,
  Wind,
  Droplets,
  Bug,
  Sparkles,
  Orbit,
  ScrollText,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'

type Schemas = components['schemas']
export type SocialClass = Schemas['SocialClass']
export type Job = Schemas['Job']
export type AgeBand = Schemas['AgeBand']
export type DistrictKind = Schemas['DistrictKind']
export type DiseaseVector = Schemas['DiseaseVector']

type Spec = { label: string; icon: LucideIcon }

export const CLASS_SPEC: Record<SocialClass, Spec> = {
  farmer: { label: 'Farmers', icon: Wheat },
  artisan: { label: 'Artisans', icon: Hammer },
  merchant: { label: 'Merchants', icon: Coins },
  priest: { label: 'Priests', icon: Church },
  warrior: { label: 'Warriors', icon: Swords },
  scribe: { label: 'Scribes', icon: BookOpen },
  noble: { label: 'Nobles', icon: Crown },
  serf_or_slave: { label: 'Serfs and slaves', icon: Link },
  outcast: { label: 'Outcasts', icon: Tent },
  monastic: { label: 'Monastics', icon: ScrollText },
}
export const CLASS_ORDER = Object.keys(CLASS_SPEC) as SocialClass[]

export const JOB_SPEC: Record<Job, Spec> = {
  farming: { label: 'Farming', icon: Wheat },
  herding: { label: 'Herding', icon: Sprout },
  fishing: { label: 'Fishing', icon: Fish },
  mining: { label: 'Mining', icon: Pickaxe },
  crafting: { label: 'Crafting', icon: Hammer },
  trade: { label: 'Trade', icon: Store },
  soldiering: { label: 'Soldiering', icon: Shield },
  clergy: { label: 'Clergy', icon: Church },
  scholarship: { label: 'Scholarship', icon: BookOpen },
  building: { label: 'Building', icon: TreePine },
  idle: { label: 'No work', icon: User },
}

export const AGE_SPEC: Record<AgeBand, Spec> = {
  child: { label: 'Children', icon: Baby },
  adult: { label: 'Adults', icon: UserRound },
  elder: { label: 'Elders', icon: Users },
}
export const AGE_ORDER: AgeBand[] = ['elder', 'adult', 'child']

export const DISTRICT_SPEC: Record<DistrictKind, Spec> = {
  farmland: { label: 'Farmland', icon: Wheat },
  market: { label: 'Market', icon: Store },
  craft_quarter: { label: 'Craft quarter', icon: Hammer },
  temple_quarter: { label: 'Temple quarter', icon: Church },
  harbour: { label: 'Harbour', icon: Anchor },
  citadel: { label: 'Citadel', icon: Castle },
  slums: { label: 'Slums', icon: Tent },
  palace: { label: 'Palace', icon: Crown },
  foreign_quarter: { label: 'Foreign quarter', icon: Globe },
  necropolis: { label: 'Necropolis', icon: Skull },
}

export const VECTOR_SPEC: Record<DiseaseVector, Spec> = {
  air: { label: 'Breath and air', icon: Wind },
  water: { label: 'Water', icon: Droplets },
  touch: { label: 'Touch', icon: HeartPulse },
  bite: { label: 'Bites of beasts', icon: Bug },
  spirit: { label: 'Spirits', icon: Ghost },
  void: { label: 'The void', icon: Orbit },
  curse: { label: 'A curse', icon: Sparkles },
}

export const TREASURY_ICON: LucideIcon = HandCoins
export const SETTLEMENT_ICON: LucideIcon = Landmark
export const FIRE_ICON: LucideIcon = Flame
export const GEM_ICON: LucideIcon = Gem
export const MOUNTAIN_ICON: LucideIcon = Mountain

export function words(value: string): string {
  return value.replaceAll('_', ' ')
}

export function choices(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}
