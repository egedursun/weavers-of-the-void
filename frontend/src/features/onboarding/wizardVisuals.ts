import {
  Anchor,
  AudioLines,
  Axe,
  Castle,
  Cloudy,
  Cog,
  Crown,
  Flame,
  Gem,
  Globe,
  Hammer,
  Landmark,
  Languages,
  LayoutTemplate,
  Lightbulb,
  type LucideIcon,
  Moon,
  Mountain,
  Orbit,
  Palette,
  ScrollText,
  Shell,
  Skull,
  Snowflake,
  Sparkles,
  Star,
  Sun,
  Sunrise,
  Swords,
  Waves,
  Wind,
  Sparkle,
  Telescope,
  TreePine,
  Users,
  Wand2,
} from 'lucide-react'
import {
  type CosmosSize,
  type LanguageTexture,
  type LoreLanguage,
  type TechnologyEra,
  type WizardTemplate,
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
const DARKNESS_LEVELS = ['Bright', 'Hopeful', 'Balanced', 'Grim', 'Pitch black']
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

export function darknessLevel(value: number): string {
  return levelOf(DARKNESS_LEVELS, value)
}

export const MAGIC_ICON = Wand2
export const DARKNESS_ICON = Moon
export const SEED_ICON = Sparkles
export const PEOPLE_ICON = Users
