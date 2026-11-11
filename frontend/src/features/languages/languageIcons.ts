import {
  Anvil,
  Box,
  Cable,
  CaseSensitive,
  Coins,
  Compass,
  Crown,
  Dna,
  DoorOpen,
  Feather,
  Hash,
  HeartPulse,
  Infinity as InfinityIcon,
  Landmark,
  Languages,
  type LucideIcon,
  MapPin,
  MessageCircle,
  MessageSquareQuote,
  Orbit,
  Palette,
  Puzzle,
  Route,
  Sailboat,
  Scale,
  Shapes,
  Ship,
  Skull,
  Sparkles,
  Swords,
  Telescope,
  User,
  Wheat,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'

type Schemas = components['schemas']
export type KnowledgeBranch = Schemas['KnowledgeBranch']
export type WritingSystem = Schemas['WritingSystem']
export type PartOfSpeech = Schemas['PartOfSpeech']

export const BRANCH_ICON: Record<KnowledgeBranch, LucideIcon> = {
  agriculture: Wheat,
  metallurgy: Anvil,
  seafaring: Sailboat,
  writing: Feather,
  architecture: Landmark,
  medicine: HeartPulse,
  magic: Sparkles,
  warfare: Swords,
  astronomy: Telescope,
  trade: Coins,
  sky_navigation: Compass,
  shipbuilding: Ship,
  gate_lore: DoorOpen,
  pathfinding: Route,
  void_living: Orbit,
  immortality: InfinityIcon,
  biomancy: Dna,
  forbidden: Skull,
  civics: Scale,
}

export const COSMIC_BRANCHES: readonly KnowledgeBranch[] = [
  'sky_navigation',
  'shipbuilding',
  'gate_lore',
  'pathfinding',
  'void_living',
  'immortality',
  'biomancy',
  'forbidden',
]

export const SCRIPT_ICON: Record<WritingSystem, LucideIcon> = {
  alphabet: CaseSensitive,
  syllabary: Languages,
  pictographic: Shapes,
  knot: Cable,
  notch: Hash,
  logographic: Landmark,
  mixed: Puzzle,
  abjad: Feather,
}

export const UNWRITTEN_ICON: LucideIcon = MessageCircle

export const PART_ICON: Record<PartOfSpeech, LucideIcon> = {
  noun: Box,
  verb: Zap,
  adjective: Palette,
  affix: Puzzle,
  title: Crown,
  place_name: MapPin,
  proper_name: User,
  number: Hash,
  interjection: MessageSquareQuote,
}

const ROMAN: readonly [number, string][] = [
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
]

export function tierNumeral(level: number): string {
  let rest = Math.max(1, Math.floor(level))
  let text = ''
  for (const [value, symbol] of ROMAN)
    while (rest >= value) {
      text += symbol
      rest -= value
    }
  return text
}
