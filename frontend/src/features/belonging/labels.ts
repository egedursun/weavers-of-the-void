import {
  type LucideIcon,
  Baby,
  Ban,
  Banknote,
  BookOpen,
  Castle,
  Church,
  Compass,
  Crown,
  Dna,
  DoorOpen,
  Drama,
  Feather,
  Fingerprint,
  Flag,
  Flame,
  Footprints,
  Gamepad2,
  Gavel,
  Hammer,
  Handshake,
  Heart,
  HeartCrack,
  Home,
  Landmark,
  Languages,
  Laugh,
  Map as MapIcon,
  Megaphone,
  Minus,
  Music,
  Newspaper,
  Palette,
  Scale,
  Shield,
  ShieldAlert,
  Ship,
  Sparkles,
  Swords,
  Target,
  Tent,
  Trees,
  TriangleAlert,
  Trophy,
  Unlink,
  Unlock,
  UserRound,
  Users,
  Vote,
  Wheat,
  Building2,
  Siren,
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
  language: { label: 'Tongue', icon: Languages, tone: 'info' },
  kind: { label: 'Kind of being', icon: Dna, tone: 'verdigris' },
  cause: { label: 'Cause', icon: Flag, tone: 'warning' },
  calling: { label: 'Calling', icon: Compass, tone: 'gold' },
  gift: { label: 'Gift', icon: Sparkles, tone: 'gold' },
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
  persecution: { label: 'Persecution', icon: Siren, tone: 'danger' },
  commemoration: {
    label: 'Remembering the past',
    icon: Landmark,
    tone: 'muted',
  },
  election: { label: 'A vote', icon: Vote, tone: 'info' },
  contest: { label: 'A match', icon: Trophy, tone: 'warning' },
  arrivals: { label: 'Newcomers', icon: DoorOpen, tone: 'info' },
  disaster: { label: 'A shared disaster', icon: TriangleAlert, tone: 'danger' },
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
  wilds: { label: 'The wilds', icon: Trees, tone: 'success' },
  free_city: { label: 'Free city', icon: Landmark, tone: 'gold' },
  embassy: { label: 'Embassy', icon: Flag, tone: 'info' },
  ship: { label: 'Ship sanctuary', icon: Ship, tone: 'gold' },
  trade_hall: { label: 'Hall sanctuary', icon: Building2, tone: 'gold' },
}

export const FUGITIVES: Record<Schema['FugitiveKind'], Named> = {
  outlaw: { label: 'Outlaw', icon: Flame, tone: 'danger' },
  accused: { label: 'Accused', icon: Gavel, tone: 'warning' },
  defector: { label: 'Defector', icon: Scale, tone: 'info' },
  runaway: { label: 'Runaway from bondage', icon: Unlink, tone: 'warning' },
  deserter: { label: 'Deserter', icon: Footprints, tone: 'danger' },
  heretic: { label: 'Fled persecution', icon: Church, tone: 'verdigris' },
  escaped_captive: { label: 'Escaped captive', icon: Unlock, tone: 'danger' },
  debtor: { label: 'Fleeing debtor', icon: Banknote, tone: 'danger' },
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
  crowd: { label: 'Songs and chants of a crowd', icon: Users, tone: 'warning' },
  outlet: { label: 'An outlet', icon: Newspaper, tone: 'info' },
}
