import {
  Ban,
  Building,
  CalendarClock,
  Coins,
  Crown,
  Gavel,
  Ghost,
  Gift,
  GitBranch,
  GitFork,
  Hammer,
  Handshake,
  Heart,
  HeartHandshake,
  Home,
  Infinity as Forever,
  Landmark,
  Link,
  Repeat,
  ScrollText,
  Shuffle,
  Sparkles,
  Split,
  Users,
  UsersRound,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const UNION_FORMS: Record<Schema['UnionForm'], Named> = {
  pair: { label: 'Two partners', icon: HeartHandshake, tone: 'success' },
  plural: { label: 'One partner with several', icon: Users, tone: 'info' },
  group: { label: 'A group joined together', icon: UsersRound, tone: 'info' },
  serial: {
    label: 'One at a time, ended by custom',
    icon: Repeat,
    tone: 'warning',
  },
  contract: { label: 'For a set term', icon: CalendarClock, tone: 'warning' },
  posthumous: {
    label: 'Joined even with the dead',
    icon: Ghost,
    tone: 'verdigris',
  },
  none: { label: 'No unions at all', icon: Ban, tone: 'muted' },
}

export const UNION_PURPOSES: Record<Schema['UnionPurpose'], Named> = {
  kinship: { label: 'To join kin', icon: GitBranch, tone: 'success' },
  alliance: { label: 'To bind allies', icon: Handshake, tone: 'gold' },
  inheritance: { label: 'To keep an inheritance', icon: Coins, tone: 'gold' },
  love: { label: 'For love', icon: Heart, tone: 'danger' },
  faith: { label: 'For faith', icon: Sparkles, tone: 'verdigris' },
  labour: { label: 'To share labour', icon: Hammer, tone: 'muted' },
  status: { label: 'For standing', icon: Crown, tone: 'gold' },
}

export const UNION_RESIDENCES: Record<Schema['UnionResidence'], Named> = {
  with_first_family: {
    label: "With the first side's family",
    icon: Building,
    tone: 'info',
  },
  with_second_family: {
    label: "With the second side's family",
    icon: Building,
    tone: 'info',
  },
  new_household: {
    label: 'In a household of their own',
    icon: Home,
    tone: 'success',
  },
  separate: { label: 'Each in their own home', icon: Split, tone: 'muted' },
}

export const UNION_DESCENTS: Record<Schema['UnionDescent'], Named> = {
  through_first: {
    label: 'Through the first side',
    icon: GitBranch,
    tone: 'info',
  },
  through_second: {
    label: 'Through the second side',
    icon: GitBranch,
    tone: 'info',
  },
  through_both: { label: 'Through both sides', icon: GitFork, tone: 'success' },
  chosen: { label: 'As each child chooses', icon: Shuffle, tone: 'warning' },
  by_house_rule: {
    label: 'By the rule of the greater house',
    icon: Landmark,
    tone: 'gold',
  },
}

export const UNION_EXCHANGES: Record<Schema['UnionExchange'], Named> = {
  to_one_family: {
    label: "The first side pays the second's family",
    icon: Coins,
    tone: 'gold',
  },
  from_one_family: {
    label: "The second side's family pays the first",
    icon: Coins,
    tone: 'gold',
  },
  mutual: { label: 'Gifts pass both ways', icon: Gift, tone: 'success' },
  none: { label: 'Nothing passes', icon: Ban, tone: 'muted' },
}

export const UNION_ARRANGEMENTS: Record<Schema['UnionArrangement'], Named> = {
  arranged: {
    label: 'Arranged by the families',
    icon: ScrollText,
    tone: 'info',
  },
  chosen: {
    label: 'Chosen by the one who seeks',
    icon: Heart,
    tone: 'success',
  },
  both_consent: {
    label: 'Only when both consent',
    icon: HeartHandshake,
    tone: 'success',
  },
}

export const UNION_DISSOLUTIONS: Record<Schema['UnionDissolution'], Named> = {
  none: { label: 'Never ended', icon: Forever, tone: 'muted' },
  by_either: { label: 'By either partner', icon: Split, tone: 'warning' },
  by_court: { label: 'By a court', icon: Gavel, tone: 'info' },
  by_custom: { label: 'By custom', icon: ScrollText, tone: 'info' },
}

export const PARTNER_SCOPES: Record<Schema['PartnerScope'], Named> = {
  none: { label: 'No rule', icon: Link, tone: 'muted' },
  people: { label: 'People', icon: Users, tone: 'info' },
  class: { label: 'Class', icon: Crown, tone: 'gold' },
  caste: { label: 'Caste', icon: Landmark, tone: 'warning' },
  faith: { label: 'Faith', icon: Sparkles, tone: 'verdigris' },
  house: { label: 'House', icon: Building, tone: 'info' },
}
