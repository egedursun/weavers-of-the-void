import {
  Ban,
  BookOpenText,
  Flame,
  Gem,
  Handshake,
  Landmark,
  Languages,
  Lightbulb,
  type LucideIcon,
  Route,
  ScrollText,
  Skull,
  Swords,
  Users,
  Hourglass,
  Star,
  Atom,
  ChevronsUp,
  HandHeart,
  Shield,
  Footprints,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { type EpochStatsData } from './api'

export type NumericStat = Exclude<
  keyof EpochStatsData,
  | 'sons'
  | 'doom_items'
  | 'leak_items'
  | 'population_items'
  | 'essence_items'
  | 'flow_items'
>

export const STAT_LABEL: Record<NumericStat, string> = {
  population: 'Population',
  followers: 'Followers',
  entities: 'Records',
  words: 'Words',
  knowledge: 'Knowledge',
  languages: 'Languages',
  wars: 'Wars',
  trade_routes: 'Trade routes',
  alliances: 'Alliances',
  structures: 'Structures',
  items: 'Items',
  dead: 'Dead',
  godless: 'Godless communities',
  doom: 'Doom clock',
  soldiers: 'Soldiers under arms',
  travelling: 'On the road between worlds',
}

export const STAT_FIELDS = Object.keys(STAT_LABEL) as NumericStat[]

export const HARMFUL_STATS: ReadonlySet<NumericStat> = new Set([
  'wars',
  'dead',
  'godless',
  'doom',
])

export const SON_STAT_LABEL: Record<string, string> = {
  faith: 'Faith',
  fame: 'Fame',
  existence: 'Existence',
  level: 'Level',
}

export function humanize(key: string): string {
  const words = key.replaceAll('_', ' ').replaceAll('.', ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export const STAT_ICON: Record<NumericStat, LucideIcon> = {
  population: Users,
  followers: Flame,
  entities: ScrollText,
  words: BookOpenText,
  knowledge: Lightbulb,
  languages: Languages,
  wars: Swords,
  trade_routes: Route,
  alliances: Handshake,
  structures: Landmark,
  items: Gem,
  dead: Skull,
  godless: Ban,
  doom: Hourglass,
  soldiers: Shield,
  travelling: Footprints,
}

export const STAT_TONE: Record<NumericStat, KpiTone> = {
  population: 'gold',
  followers: 'warning',
  entities: 'verdigris',
  words: 'info',
  knowledge: 'gold',
  languages: 'info',
  wars: 'danger',
  trade_routes: 'verdigris',
  alliances: 'success',
  structures: 'gold',
  items: 'verdigris',
  dead: 'muted',
  godless: 'muted',
  doom: 'danger',
  soldiers: 'danger',
  travelling: 'info',
}

export const SON_STAT_ICON: Record<string, LucideIcon> = {
  faith: HandHeart,
  fame: Star,
  existence: Atom,
  level: ChevronsUp,
}
