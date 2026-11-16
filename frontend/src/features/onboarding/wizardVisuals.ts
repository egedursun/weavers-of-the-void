import {
  Hand,
  Pointer,
  AudioWaveform,
  Sparkles,
  Pickaxe,
  BrainCircuit,
  Anchor,
  Atom,
  MoveRight,
  RefreshCcw,
  AudioLines,
  Axe,
  Castle,
  CircleDot,
  CircleOff,
  CloudMoon,
  Cloudy,
  Cog,
  Cpu,
  Crown,
  Droplets,
  Flame,
  Gem,
  Globe,
  Hammer,
  HeartPulse,
  Hourglass,
  Landmark,
  Languages,
  Layers,
  LayoutTemplate,
  Leaf,
  Lightbulb,
  type LucideIcon,
  Minus,
  Moon,
  Mountain,
  Orbit,
  Palette,
  Repeat,
  Rocket,
  ScrollText,
  Shell,
  Shuffle,
  Skull,
  Snowflake,
  Sprout,
  Star,
  Sun,
  SunMedium,
  Sunrise,
  Swords,
  Waves,
  Wind,
  Sparkle,
  Telescope,
  TreePine,
  TrendingUp,
  Users,
  Zap,
  Clapperboard,
} from 'lucide-react'
import {
  type ClimateEra,
  type CosmosShape,
  type CosmosSize,
  type LanguageTexture,
  type LoreLanguage,
  type AgeCycle,
  type StorytellerProfile,
  type TechnologyEra,
  type WizardTemplate,
  type WorldAge,
} from './api'
import { type WizardStep } from './wizardModel'

export const STEP_ICON: Record<WizardStep, LucideIcon> = {
  template: LayoutTemplate,
  creator: Crown,
  world: Globe,
  review: Users,
}

export const STEP_HINT: Record<WizardStep, string> = {
  template: 'Start from a myth or a blank canvas',
  creator: 'Who you are and the tongue of the lore',
  world: 'Seed, tone, magic and the shape of the cosmos',
  review: 'Your first sons and a last look',
}

export const TEMPLATE_ICON: Record<WizardTemplate['key'], LucideIcon> = {
  dark_fantasy: Swords,
  mythic_age: Castle,
  cosmic_horror: Skull,
  fairy_tale: TreePine,
  star_myth: Star,
  sand_and_ash: Flame,
  primordial_dawn: Sunrise,
  crowns_and_knives: Gem,
  drowned_world: Anchor,
  long_winter: Snowflake,
  after_the_fall: Landmark,
  sky_islands: Cloudy,
  age_of_engines: Lightbulb,
  many_suns: SunMedium,
  layered_realms: Layers,
  living_world: HeartPulse,
  dreaming_world: CloudMoon,
  generation_ship: Rocket,
  without_magic: CircleOff,
  electric_age: Zap,
  information_age: Cpu,
  advanced_age: Atom,
  made_minds: BrainCircuit,
  after_abundance: Pickaxe,
  gunpowder_age: Flame,
  interstellar_age: Rocket,
  beyond_age: Orbit,
}

export const SHAPE_ICON: Record<CosmosShape, LucideIcon> = {
  one_sun: CircleDot,
  many_suns: SunMedium,
  layered: Layers,
}

export const CLIMATE_ICON: Record<ClimateEra, LucideIcon> = {
  temperate: Leaf,
  drought: Sun,
  rain: Droplets,
  ice_age: Snowflake,
  scorching: Flame,
  hothouse: Leaf,
  snowball: Leaf,
  variable: Leaf,
  wet_cold: Leaf,
}

export const AGE_ICON: Record<WorldAge, LucideIcon> = {
  young: Sprout,
  mature: TreePine,
  old: Hourglass,
  dying: Moon,
}

export const TECHNOLOGY_ICON: Record<TechnologyEra, LucideIcon> = {
  stone: Axe,
  bronze: Shell,
  iron: Hammer,
  medieval: Castle,
  gunpowder: Flame,
  renaissance: Palette,
  steam: Cog,
  electrical: Zap,
  information: Cpu,
  advanced: Rocket,
  interstellar: Orbit,
  beyond: Sparkles,
}

export const TECHNOLOGY_HINT: Record<TechnologyEra, string> = {
  stone: 'Before metal is worked',
  bronze: 'Bronze is worked',
  iron: 'Iron is worked',
  medieval: 'Steel and written law',
  gunpowder: 'Powder, guns and star-shaped forts',
  renaissance: 'Printing and natural philosophy',
  steam: 'Steam power and machines',
  electrical: 'Electricity and messages by wire',
  information: 'Computation and mass media',
  advanced: 'Split matter, rockets and machines that think',
  interstellar: 'Travel between the stars',
  beyond: 'Matter shaped at will and works the size of stars',
}

export const LANGUAGE_ICON: Record<LanguageTexture, LucideIcon> = {
  flowing: Waves,
  hard: Mountain,
  guttural: AudioLines,
  sibilant: Wind,
  long: ScrollText,
  free: Sparkle,
  tonal: AudioWaveform,
  clicking: Pointer,
  whistled: Wind,
  non_vocal: Hand,
}

export const LANGUAGE_HINT: Record<LanguageTexture, string> = {
  flowing: 'Soft vowels, liquid sounds',
  hard: 'Hard consonants, short syllables',
  guttural: 'Deep throat sounds',
  sibilant: 'Hissing, fricative sounds',
  long: 'Long, many-syllabled names',
  free: 'Let the seed decide',
  tonal: 'Meaning carried by pitch',
  clicking: 'Clicks among its consonants',
  whistled: 'Whistled speech',
  non_vocal: 'Not spoken aloud',
}

export const COSMOS_ICON: Record<CosmosSize, LucideIcon> = {
  single: Globe,
  small: Orbit,
  large: Telescope,
}

export const STORYTELLER_ICON: Record<StorytellerProfile, LucideIcon> = {
  steady: Minus,
  rising: TrendingUp,
  cyclic: Repeat,
  chaotic: Shuffle,
  slow_burn: Flame,
  episodic: Clapperboard,
}

export const STORYTELLER_HINT: Record<StorytellerProfile, string> = {
  steady: 'Tension held near one level all along',
  rising: 'Tension grows with the ages',
  cyclic: 'Hard years and quiet years in turn',
  chaotic: 'Tension rises and falls without warning',
  slow_burn: 'Tension starts low and climbs a little every epoch',
  episodic: 'Quiet stretches broken by a sharp peak at the end of each episode',
}

export const AGE_CYCLE_ICON: Record<AgeCycle, LucideIcon> = {
  linear: MoveRight,
  cyclic: RefreshCcw,
}

export const AGE_CYCLE_HINT: Record<AgeCycle, string> = {
  linear: 'The cosmos runs on to its end; an apocalypse ruins a world',
  cyclic: 'Each end turns a new age that half-remembers the last',
}

export const LORE_LANGUAGE_ICON: Record<LoreLanguage, LucideIcon> = {
  english: Languages,
  turkish: Moon,
}

export const TONE_SUGGESTIONS = [
  'mythic',
  'hopeful',
  'epic',
  'whimsical',
  'pastoral',
  'adventurous',
  'romantic',
  'satirical',
  'folkloric',
  'melancholic',
  'grim',
  'cosmic horror',
] as const

const MAGIC_LEVELS = ['Faint', 'Rare', 'Present', 'Strong', 'Overwhelming']
const DANGER_LEVELS = ['Safe', 'Calm', 'Balanced', 'Perilous', 'Deadly']
const LEVEL_SPAN = 20

function levelOf(levels: string[], value: number): string {
  const index = Math.min(
    levels.length - 1,
    Math.max(0, Math.floor(value / LEVEL_SPAN))
  )
  return levels[index]
}

export function magicLevel(value: number): string {
  return levelOf(MAGIC_LEVELS, value)
}

export function dangerLevel(value: number): string {
  return levelOf(DANGER_LEVELS, value)
}
