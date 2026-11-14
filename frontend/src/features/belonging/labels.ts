import {
  Ban,
  Baby,
  BookOpen,
  Castle,
  Church,
  Crown,
  Drama,
  Feather,
  Fingerprint,
  Flame,
  Gamepad2,
  Gavel,
  Handshake,
  Hammer,
  Heart,
  HeartCrack,
  Home,
  Landmark,
  Laugh,
  type LucideIcon,
  Map as MapIcon,
  Megaphone,
  Minus,
  Music,
  Palette,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Swords,
  Target,
  Tent,
  UserRound,
  Users,
  Wheat,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const BELONGING_ICON: LucideIcon = Fingerprint

export const TAB_ICONS = {
  identities: Fingerprint,
  peers: Baby,
  sanctuary: Landmark,
  satire: Laugh,
} as const

export const LAYERS: Record<Schema['IdentityLayer'], Named> = {
  people: { label: 'People', icon: Users, tone: 'verdigris' },
  faith: { label: 'Faith', icon: Church, tone: 'gold' },
  class: { label: 'Rank', icon: Crown, tone: 'warning' },
  locality: { label: 'Home place', icon: MapIcon, tone: 'info' },
  house: { label: 'House', icon: Home, tone: 'gold' },
  profession: { label: 'Craft or calling', icon: Hammer, tone: 'info' },
  generation: { label: 'Generation', icon: UserRound, tone: 'muted' },
  polity: { label: 'Realm', icon: Castle, tone: 'success' },
  circle: { label: 'Circle', icon: Handshake, tone: 'verdigris' },
}

export const DRIVERS: Record<Schema['SalienceDriver'], Named> = {
  baseline: { label: 'At rest', icon: Minus, tone: 'muted' },
  holy_war: { label: 'Holy war', icon: Swords, tone: 'danger' },
  famine: { label: 'Hunger', icon: Wheat, tone: 'warning' },
  invasion: { label: 'Invasion', icon: ShieldAlert, tone: 'danger' },
  strike: { label: 'Strike', icon: Hammer, tone: 'warning' },
  rhetoric: { label: 'Preaching', icon: Megaphone, tone: 'info' },
  segregation: { label: 'Kept apart', icon: Ban, tone: 'warning' },
  crossing: { label: 'Mixed marriages', icon: Heart, tone: 'success' },
  god: { label: 'A god', icon: Sparkles, tone: 'gold' },
}

export const PLAYS: Record<Schema['PlayKind'], Named> = {
  games: { label: 'Games', icon: Gamepad2, tone: 'info' },
  mock_fights: { label: 'Mock fights', icon: Swords, tone: 'warning' },
  imitation: {
    label: 'Playing at grown-up work',
    icon: Palette,
    tone: 'verdigris',
  },
  riding: { label: 'Riding', icon: Feather, tone: 'gold' },
  archery: { label: 'Archery', icon: Target, tone: 'warning' },
  songs: { label: 'Songs', icon: Music, tone: 'success' },
}

export const SANCTUARY_KINDS: Record<Schema['SanctuaryKind'], Named> = {
  temple: { label: 'Temple sanctuary', icon: Church, tone: 'gold' },
  hospitality: { label: 'Guest right', icon: Tent, tone: 'verdigris' },
  asylum: { label: 'Asylum in a realm', icon: Castle, tone: 'info' },
}

export const FUGITIVES: Record<Schema['FugitiveKind'], Named> = {
  outlaw: { label: 'Outlaw', icon: Flame, tone: 'danger' },
  accused: { label: 'Accused', icon: Gavel, tone: 'warning' },
  defector: { label: 'Defector', icon: Scale, tone: 'info' },
}

export const STATES: Record<Schema['SanctuaryState'], Named> = {
  sheltered: { label: 'Sheltered', icon: Shield, tone: 'success' },
  negotiating: { label: 'Bargaining', icon: Handshake, tone: 'info' },
  besieged: { label: 'Besieged', icon: ShieldAlert, tone: 'warning' },
  violated: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
  ended: { label: 'Ended', icon: Minus, tone: 'muted' },
}

export const SOURCES: Record<Schema['SatireSource'], Named> = {
  jester: { label: 'Court jester', icon: Drama, tone: 'gold' },
  artwork: { label: 'A work of art', icon: BookOpen, tone: 'verdigris' },
  mortal: { label: 'A mortal', icon: UserRound, tone: 'info' },
  god: { label: 'A god', icon: Sparkles, tone: 'gold' },
}
