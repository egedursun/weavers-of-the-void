import {
  Anchor,
  AudioLines,
  Axe,
  Castle,
  CircleDot,
  CircleOff,
  CloudMoon,
  Cloudy,
  Cog,
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
} from 'lucide-react'
import {
  type ClimateEra,
  type CosmosShape,
  type CosmosSize,
  type LanguageTexture,
  type LoreLanguage,
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
  renaissance: Palette,
  steam: Cog,
}

export const TECHNOLOGY_HINT: Record<TechnologyEra, string> = {
  stone: 'Flint, fire and first words',
  bronze: 'The first cities and their kings',
  iron: 'Hard blades, wide empires',
  medieval: 'Castles, guilds and crowns',
  renaissance: 'Ink, lenses and new ideas',
  steam: 'Engines and smoke',
}

export const LANGUAGE_ICON: Record<LanguageTexture, LucideIcon> = {
  flowing: Waves,
  hard: Mountain,
  guttural: AudioLines,
  sibilant: Wind,
  long: ScrollText,
  free: Sparkle,
}

export const LANGUAGE_HINT: Record<LanguageTexture, string> = {
  flowing: 'Soft vowels, liquid sounds',
  hard: 'Sharp stops and stone edges',
  guttural: 'Deep throat sounds',
  sibilant: 'Whispers and hisses',
  long: 'Long, many-syllabled names',
  free: 'Let the seed decide',
}

export const COSMOS_ICON: Record<CosmosSize, LucideIcon> = {
  single: Sun,
  small: Orbit,
  large: Telescope,
}

export const STORYTELLER_ICON: Record<StorytellerProfile, LucideIcon> = {
  steady: Minus,
  rising: TrendingUp,
  cyclic: Repeat,
  chaotic: Shuffle,
}

export const STORYTELLER_HINT: Record<StorytellerProfile, string> = {
  steady: 'Tension held near one level all along',
  rising: 'Tension grows with the ages',
  cyclic: 'Hard years and quiet years in turn',
  chaotic: 'Tension rises and falls without warning',
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
