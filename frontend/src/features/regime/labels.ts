import {
  Award,
  BookOpenCheck,
  Building2,
  Church,
  Crown,
  Eye,
  Flame,
  GitBranch,
  GraduationCap,
  Handshake,
  HardHat,
  Landmark,
  type LucideIcon,
  Network,
  ScrollText,
  Shield,
  ShieldAlert,
  Sparkles,
  Split,
  Swords,
  Tent,
  TreePine,
  UserCheck,
  Users,
  Vote,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const REGIME_ICON: LucideIcon = Landmark

export const SELECTORATES: Record<Schema['SelectorateKind'], Named> = {
  tribe: {
    label: 'The grown folk of the tribe',
    icon: Tent,
    tone: 'verdigris',
  },
  nobles: { label: 'The nobles', icon: Crown, tone: 'gold' },
  council: { label: 'A ruling council', icon: Users, tone: 'info' },
  army: { label: 'The army', icon: Swords, tone: 'danger' },
  priests: { label: 'The priests', icon: Church, tone: 'verdigris' },
  citizens: { label: 'The citizens', icon: Vote, tone: 'success' },
}

export const LEGITIMACY_KINDS: Record<Schema['LegitimacyType'], Named> = {
  traditional: { label: 'Custom and descent', icon: ScrollText, tone: 'gold' },
  charismatic: { label: 'Charisma', icon: Sparkles, tone: 'verdigris' },
  rational: { label: 'Law and office', icon: Landmark, tone: 'info' },
}

export const ROUTINISATION: Record<Schema['Routinisation'], Named> = {
  none: { label: 'No founder to mourn', icon: Shield, tone: 'muted' },
  pending: {
    label: "In crisis over the founder's legacy",
    icon: Flame,
    tone: 'danger',
  },
  dynasty: { label: 'Turned into a dynasty', icon: Crown, tone: 'gold' },
  institution: {
    label: 'Turned into rules and offices',
    icon: Building2,
    tone: 'info',
  },
  schism: { label: 'Split by schism', icon: Split, tone: 'danger' },
}

export const LEADERSHIP: Record<Schema['LeadershipMode'], Named> = {
  achieved: {
    label: 'A big-man followed for gifts and feasts',
    icon: Handshake,
    tone: 'verdigris',
  },
  ascribed: { label: 'A chief by descent', icon: TreePine, tone: 'gold' },
  state: { label: 'Offices of the state', icon: Landmark, tone: 'info' },
}

export const CLIENT_ROLES: Record<Schema['ClientRole'], Named> = {
  household: { label: 'Of the household', icon: Users, tone: 'muted' },
  retainer: { label: 'Retainer', icon: Handshake, tone: 'verdigris' },
  official: { label: 'Official', icon: ScrollText, tone: 'info' },
  commander: { label: 'Commander', icon: Swords, tone: 'danger' },
}

export const STANCES: Record<Schema['PowerStance'], Named> = {
  loyal: { label: 'Loyal', icon: UserCheck, tone: 'success' },
  defiant: { label: 'Defiant', icon: ShieldAlert, tone: 'warning' },
  extorting: { label: 'Extorting the throne', icon: Landmark, tone: 'danger' },
  plotting: { label: 'Plotting for the throne', icon: Eye, tone: 'danger' },
}

export const SEGMENT_LEVELS: Record<Schema['SegmentLevel'], Named> = {
  lineage: { label: 'Lineage', icon: GitBranch, tone: 'verdigris' },
  clan: { label: 'Clan', icon: Network, tone: 'gold' },
  tribe: { label: 'Tribe', icon: Tent, tone: 'info' },
}

export const CREDENTIALS: Record<Schema['CredentialKind'], Named> = {
  examination: {
    label: 'Passed the examinations',
    icon: BookOpenCheck,
    tone: 'info',
  },
  master: { label: 'Master', icon: GraduationCap, tone: 'verdigris' },
  doctor: { label: 'Doctor', icon: Award, tone: 'gold' },
  ordination: { label: 'Ordained', icon: Church, tone: 'verdigris' },
}

export const PROOFING: Record<
  'rotation' | 'parallel_guard' | 'loyalty_promotion' | 'hostages',
  Named
> = {
  rotation: { label: 'Commanders rotated', icon: HardHat, tone: 'warning' },
  parallel_guard: {
    label: 'A guard beside the army',
    icon: Shield,
    tone: 'info',
  },
  loyalty_promotion: {
    label: 'Promotion by loyalty',
    icon: UserCheck,
    tone: 'gold',
  },
  hostages: { label: 'Hostages kept', icon: Users, tone: 'danger' },
}

export const TAB_ICONS = {
  rule: Crown,
  patronage: Handshake,
  lineages: GitBranch,
  learning: GraduationCap,
} as const
