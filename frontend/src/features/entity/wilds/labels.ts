import {
  Angry,
  Baby,
  Beef,
  Biohazard,
  Bird,
  Blend,
  Bone,
  Brain,
  Bug,
  Crosshair,
  Dna,
  Dog,
  Drama,
  Droplets,
  Drumstick,
  Ear,
  Eclipse,
  Egg,
  Eye,
  EyeOff,
  Fence,
  Fish,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Hand,
  HandHeart,
  HeartPulse,
  Hexagon,
  History,
  Hourglass,
  House,
  Infinity as InfinityIcon,
  Leaf,
  Link2,
  Lock,
  Minus,
  Moon,
  Mountain,
  MountainSnow,
  Network,
  Nut,
  PawPrint,
  Rabbit,
  Radar,
  Repeat,
  ScanEye,
  Shield,
  ShieldHalf,
  Shovel,
  Shrimp,
  Snowflake,
  Sparkles,
  Split,
  Sprout,
  Sun,
  Swords,
  Syringe,
  Tractor,
  Trees,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  Utensils,
  WandSparkles,
  Waves,
  WheatOff,
  type LucideIcon,
} from 'lucide-react'
import { type ProgressTone } from '@/components/ui/progress'
import { type KpiTone } from '@/components/domain'
import { type Named, named, plain } from '../environment/labels'

export { named, plain }
export type { Named }

export type BadgeTone =
  'secondary' | 'info' | 'success' | 'warning' | 'destructive' | 'default'

const PERCENT = 100

export const BADGE_OF: Record<KpiTone, BadgeTone> = {
  gold: 'default',
  verdigris: 'info',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'secondary',
}

export const BAR_OF: Record<KpiTone, ProgressTone> = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export const ECOLOGY_ICON = Leaf
export const BEAST_ICON = Footprints
export const HERDS_ICON = Fence
export const WEB_ICON = Network

export const SIZE: Record<string, Named & { rank: number; hint: string }> = {
  tiny: {
    label: 'Tiny',
    icon: Bug,
    tone: 'muted',
    rank: 1,
    hint: 'Fits in a hand',
  },
  small: {
    label: 'Small',
    icon: Rabbit,
    tone: 'success',
    rank: 2,
    hint: 'Hare to hound',
  },
  medium: {
    label: 'Medium',
    icon: Dog,
    tone: 'info',
    rank: 3,
    hint: 'Wolf to deer',
  },
  large: {
    label: 'Large',
    icon: PawPrint,
    tone: 'gold',
    rank: 4,
    hint: 'Horse to bear',
  },
  huge: {
    label: 'Huge',
    icon: Mountain,
    tone: 'warning',
    rank: 5,
    hint: 'Towers over riders',
  },
  colossal: {
    label: 'Colossal',
    icon: MountainSnow,
    tone: 'danger',
    rank: 6,
    hint: 'Shakes the ground it walks',
  },
}

export const SIZE_STEPS = 6

export const DIET: Record<string, Named> = {
  herbivore: { label: 'Grazer', icon: Leaf, tone: 'success' },
  carnivore: { label: 'Hunter', icon: Beef, tone: 'danger' },
  omnivore: { label: 'Omnivore', icon: Utensils, tone: 'gold' },
  scavenger: { label: 'Scavenger', icon: Bone, tone: 'muted' },
  filter: { label: 'Filterer', icon: Shrimp, tone: 'info' },
  photosynthetic: { label: 'Sun-fed', icon: Sun, tone: 'success' },
  mineral: { label: 'Stone-fed', icon: Gem, tone: 'verdigris' },
  soul: { label: 'Soul-fed', icon: Ghost, tone: 'verdigris' },
  void: { label: 'Void-fed', icon: Eclipse, tone: 'danger' },
}

export const SOCIALITY: Record<string, Named> = {
  solitary: { label: 'Lives alone', icon: User, tone: 'muted' },
  pack: { label: 'Runs in packs', icon: PawPrint, tone: 'warning' },
  herd: { label: 'Lives in herds', icon: Users, tone: 'success' },
  hive: { label: 'Lives in a hive', icon: Hexagon, tone: 'gold' },
}

export const STAGE: Record<string, Named & { step: number; hint: string }> = {
  wild: {
    label: 'Wild',
    icon: Trees,
    tone: 'muted',
    step: 0,
    hint: 'No one keeps it',
  },
  tamed: {
    label: 'Tamed',
    icon: Hand,
    tone: 'info',
    step: 1,
    hint: 'Caught and gentled one by one',
  },
  herded: {
    label: 'Herded',
    icon: Fence,
    tone: 'verdigris',
    step: 2,
    hint: 'Kept and fed in herds',
  },
  domesticated: {
    label: 'Domesticated',
    icon: House,
    tone: 'success',
    step: 3,
    hint: 'Bred by people for generations',
  },
  breed: {
    label: 'A breed of its own',
    icon: Dna,
    tone: 'gold',
    step: 4,
    hint: 'A kind people made',
  },
}

export const USE: Record<string, Named> = {
  food: { label: 'Food', icon: Drumstick, tone: 'warning' },
  labour: { label: 'Labour', icon: Tractor, tone: 'gold' },
  mount: { label: 'Mount', icon: Footprints, tone: 'info' },
  war: { label: 'War beast', icon: Swords, tone: 'danger' },
  guard: { label: 'Guard', icon: Shield, tone: 'info' },
  companion: { label: 'Companion', icon: HandHeart, tone: 'success' },
  sacrifice: { label: 'Sacrifice', icon: Flame, tone: 'gold' },
  magic: { label: 'Magic', icon: WandSparkles, tone: 'verdigris' },
}

export const TREND: Record<string, Named & { badge: BadgeTone }> = {
  rising: {
    label: 'Rising',
    icon: TrendingUp,
    tone: 'success',
    badge: 'success',
  },
  steady: { label: 'Steady', icon: Minus, tone: 'muted', badge: 'secondary' },
  falling: {
    label: 'Falling',
    icon: TrendingDown,
    tone: 'danger',
    badge: 'destructive',
  },
}

export const TEMPER: Record<string, Named & { hint: string }> = {
  hungry: {
    label: 'Hungry',
    icon: Drumstick,
    tone: 'warning',
    hint: 'Awake and raiding for food',
  },
  territorial: {
    label: 'Territorial',
    icon: Shield,
    tone: 'warning',
    hint: 'Guards its lair against all comers',
  },
  sleeping: {
    label: 'Sleeping',
    icon: Moon,
    tone: 'muted',
    hint: 'Dormant in its lair',
  },
  enraged: {
    label: 'Enraged',
    icon: Angry,
    tone: 'danger',
    hint: 'Raging across the land',
  },
  bound: {
    label: 'Bound',
    icon: Lock,
    tone: 'verdigris',
    hint: 'Held by a master or a place',
  },
  tamed: {
    label: 'Tamed',
    icon: Hand,
    tone: 'success',
    hint: 'Ridden or kept by a master',
  },
}

export const TRAIT: Record<string, Named> = {
  flying: { label: 'Flies', icon: Bird, tone: 'info' },
  venomous: { label: 'Venomous', icon: Syringe, tone: 'danger' },
  soul_eater: { label: 'Eats souls', icon: Ghost, tone: 'danger' },
  radiant: { label: 'Radiant', icon: Sun, tone: 'gold' },
  fissiparous: { label: 'Splits to breed', icon: Split, tone: 'verdigris' },
  hive_mind: { label: 'Hive mind', icon: Network, tone: 'gold' },
  stoneskin: { label: 'Stone skin', icon: Mountain, tone: 'muted' },
  time_rewinder: { label: 'Turns back time', icon: History, tone: 'verdigris' },
  shapeshifter: { label: 'Shapeshifter', icon: Blend, tone: 'verdigris' },
  mind_reader: { label: 'Reads minds', icon: Brain, tone: 'info' },
  armoured: { label: 'Armoured', icon: ShieldHalf, tone: 'muted' },
  burrowing: { label: 'Burrows', icon: Shovel, tone: 'warning' },
  aquatic: { label: 'Lives in water', icon: Fish, tone: 'info' },
  amphibious: { label: 'Amphibious', icon: Waves, tone: 'info' },
  pack_hunter: { label: 'Hunts in packs', icon: PawPrint, tone: 'danger' },
  ambush_predator: { label: 'Ambush hunter', icon: Crosshair, tone: 'danger' },
  regenerating: { label: 'Regrows wounds', icon: HeartPulse, tone: 'success' },
  poisonous_flesh: {
    label: 'Poisonous flesh',
    icon: Biohazard,
    tone: 'warning',
  },
  fire_breathing: { label: 'Breathes fire', icon: Flame, tone: 'danger' },
  cold_breathing: { label: 'Breathes frost', icon: Snowflake, tone: 'info' },
  echolocation: { label: 'Hears its way', icon: Radar, tone: 'info' },
  camouflage: { label: 'Camouflaged', icon: EyeOff, tone: 'verdigris' },
  swarm_breeder: { label: 'Breeds in swarms', icon: Egg, tone: 'warning' },
  long_lived: { label: 'Long-lived', icon: InfinityIcon, tone: 'gold' },
  mimic: { label: 'Mimic', icon: Drama, tone: 'verdigris' },
  spirit_sight: { label: 'Sees spirits', icon: ScanEye, tone: 'verdigris' },
  iron_eating: { label: 'Eats iron', icon: Nut, tone: 'muted' },
  crop_pest: { label: 'Crop pest', icon: WheatOff, tone: 'warning' },
  plague_bearer: { label: 'Plague bearer', icon: Biohazard, tone: 'danger' },
  sacred_animal: { label: 'Sacred', icon: Sparkles, tone: 'gold' },
}

export const MATERIAL: Record<string, string> = {
  wood: 'Wood',
  bone: 'Bone',
  hide: 'Hide',
  leather: 'Leather',
  cloth: 'Cloth',
  stone: 'Stone',
  flint: 'Flint',
  obsidian: 'Obsidian',
  copper: 'Copper',
  tin: 'Tin',
  bronze: 'Bronze',
  iron: 'Iron',
  steel: 'Steel',
  silver: 'Silver',
  gold: 'Gold',
  glass: 'Glass',
  crystal: 'Crystal',
  ivory: 'Ivory',
  chitin: 'Chitin',
  dragonbone: 'Dragonbone',
  star_metal: 'Star metal',
  void_glass: 'Void glass',
  godflesh: 'Godflesh',
  living_wood: 'Living wood',
  salt: 'Salt',
  amber: 'Amber',
  lead: 'Lead',
  skysteel: 'Skysteel',
  sulfur: 'Sulfur',
  clay: 'Clay',
  gems: 'Gems',
}

export const TEMPERAMENT: {
  key: 'aggression' | 'territoriality' | 'cunning' | 'fear_of_people'
  label: string
  icon: LucideIcon
  tone: ProgressTone
}[] = [
  { key: 'aggression', label: 'Aggression', icon: Swords, tone: 'destructive' },
  {
    key: 'territoriality',
    label: 'Territoriality',
    icon: Shield,
    tone: 'warning',
  },
  { key: 'cunning', label: 'Cunning', icon: Brain, tone: 'info' },
  {
    key: 'fear_of_people',
    label: 'Fear of people',
    icon: Ghost,
    tone: 'muted',
  },
]

export const MIGHT: {
  key: 'endurance' | 'perception' | 'willpower' | 'intelligence'
  label: string
  icon: LucideIcon
  tone: ProgressTone
}[] = [
  { key: 'endurance', label: 'Endurance', icon: HeartPulse, tone: 'success' },
  { key: 'perception', label: 'Perception', icon: Eye, tone: 'info' },
  { key: 'willpower', label: 'Willpower', icon: Flame, tone: 'warning' },
  { key: 'intelligence', label: 'Cunning', icon: Brain, tone: 'verdigris' },
]

export const FIELD_LABELS: Record<string, string> = {
  size_class: 'Size',
  diet: 'Diet',
  sociality: 'Social life',
  stage: 'Taming stage',
  body_plan: 'Body plan',
  lifespan_years: 'Lifespan in years',
  maturity_years: 'Years to grow up',
  litter_size: 'Young per litter',
  breeding_seasons: 'Litters a year',
  metabolism: 'Metabolism',
  temperature_min: 'Coldest it bears',
  temperature_max: 'Hottest it bears',
  water_need: 'Water need',
  altitude_min: 'Lowest ground',
  altitude_max: 'Highest ground',
  aggression: 'Aggression',
  territoriality: 'Territoriality',
  cunning: 'Cunning',
  fear_of_people: 'Fear of people',
  tameability: 'Tameability',
  nocturnal: 'Active at night',
  migratory: 'Migrates',
  habitat: 'Lands it loves',
  temper: 'Temper',
  endurance: 'Endurance',
  perception: 'Perception',
  willpower: 'Willpower',
  intelligence: 'Cunning',
  age: 'Age in years',
  lifespan: 'Lifespan in years',
  raids: 'Raids',
  hoard: 'Hoard',
  abundance: 'Abundance',
  trend: 'Trend',
  fit: 'Fit to the land',
  hunted: 'Hunting pressure',
  head: 'Head count',
  fed_epochs: 'Epochs fed',
}

export function fieldLabel(key: string): string {
  return plain(FIELD_LABELS, key)
}

export function labelsOf(
  table: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

export function titled(value: string): string {
  return plain({}, value)
}

export const LIFE_ICONS = {
  lifespan: Hourglass,
  maturity: Sprout,
  litter: Baby,
  seasons: Repeat,
  metabolism: Flame,
  water: Droplets,
  bound: Link2,
  hearing: Ear,
  herd: PawPrint,
}

export function barTone(value: number, tone: KpiTone = 'gold'): ProgressTone {
  return value >= PERCENT / 2
    ? BAR_OF[tone]
    : value >= PERCENT / 5
      ? 'warning'
      : 'destructive'
}
