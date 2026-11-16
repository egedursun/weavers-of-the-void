import {
  Ban,
  CircleDot,
  CircleOff,
  DoorOpen,
  Eye,
  Flag,
  Flame,
  HeartCrack,
  Hourglass,
  KeyRound,
  Lock,
  Megaphone,
  Brain,
  Utensils,
  Skull,
  Swords,
  Target,
  Tag,
  Unlock,
  Waves,
  Coins,
  Handshake,
  Hand,
  Scale,
  Sparkles,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const OUTER_AGENCY_ICON = Target
export const HERALD_ICON = Megaphone
export const PACT_ICON = Handshake
export const SEAL_ICON = Lock

export const GOALS: Record<Schema['OuterGoal'], Named> = {
  feed: { label: 'To feed', icon: Utensils, tone: 'danger' },
  enter: { label: 'To enter the cosmos', icon: DoorOpen, tone: 'danger' },
  be_worshipped: { label: 'To be worshipped', icon: Sparkles, tone: 'warning' },
  unmake_law: { label: 'To unmake a law', icon: Scale, tone: 'warning' },
  gain_name: { label: 'To gain a name', icon: Tag, tone: 'info' },
  open_rift: { label: 'To open a rift', icon: Waves, tone: 'danger' },
}

export const PLAN_STATES: Record<Schema['OuterPlanState'], Named> = {
  active: { label: 'Under way', icon: CircleDot, tone: 'warning' },
  achieved: { label: 'Achieved', icon: CheckCircle2, tone: 'danger' },
  thwarted: { label: 'Thwarted', icon: XCircle, tone: 'success' },
}

export const STAGES: Record<Schema['IncursionStage'], Named> = {
  probing: { label: 'Probing', icon: Eye, tone: 'info' },
  breach: { label: 'Breaking through', icon: Flame, tone: 'warning' },
  manifestation: { label: 'Manifest', icon: Skull, tone: 'danger' },
  receding: { label: 'Driven back', icon: CircleOff, tone: 'success' },
}

export const PRICES: Record<Schema['OuterPrice'], Named> = {
  sanity: { label: 'Their sanity', icon: Brain, tone: 'danger' },
  years: { label: 'Their years', icon: Hourglass, tone: 'warning' },
  memory: { label: 'Their memory', icon: HeartCrack, tone: 'warning' },
  name: { label: 'A name', icon: Tag, tone: 'info' },
  service: {
    label: 'Their service as a herald',
    icon: Megaphone,
    tone: 'danger',
  },
  offering: { label: 'Offerings', icon: Coins, tone: 'gold' },
}

export const RELATIONS: Record<Schema['OuterRelation'], Named> = {
  rival: { label: 'Rivals it', icon: Swords, tone: 'warning' },
  ignore: { label: 'Ignores it', icon: Ban, tone: 'muted' },
  feeds_on: { label: 'Feeds on it', icon: Utensils, tone: 'danger' },
}

export const SEAL_KINDS: Record<Schema['OuterSealKind'], Named> = {
  seal: { label: 'Sealed', icon: Lock, tone: 'info' },
  banish: { label: 'Banished', icon: Flag, tone: 'success' },
}

export const FATES: Record<Schema['OuterFate'], Named> = {
  active: { label: 'Free and hungry', icon: Unlock, tone: 'danger' },
  sealed: { label: 'Sealed', icon: Lock, tone: 'info' },
  banished: { label: 'Banished', icon: KeyRound, tone: 'success' },
  starved: { label: 'Starved', icon: Utensils, tone: 'muted' },
  destroyed: { label: 'Destroyed', icon: Hand, tone: 'gold' },
}
