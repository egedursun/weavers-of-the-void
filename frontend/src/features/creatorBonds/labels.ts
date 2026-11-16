import {
  Ban,
  BookOpen,
  Crown,
  Eye,
  EyeOff,
  Feather,
  Flame,
  Gavel,
  Gift,
  Handshake,
  HeartPulse,
  HelpCircle,
  Infinity as Forever,
  Layers,
  Scale,
  Shield,
  Sparkles,
  Sun,
  Users,
  Wheat,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const CREATOR_ICON = Sparkles

export const STANCES: Record<Schema['CreatorStance'], Named> = {
  worship: { label: 'Worship', icon: Sun, tone: 'gold' },
  reverence: { label: 'Reverence', icon: Crown, tone: 'info' },
  indifference: { label: 'Indifference', icon: HelpCircle, tone: 'muted' },
  fear: { label: 'Fear', icon: Flame, tone: 'warning' },
  rejection: { label: 'Rejection', icon: Ban, tone: 'danger' },
  denial: { label: 'Denial', icon: EyeOff, tone: 'danger' },
}

export const HERESIES: Record<Schema['CreatorHeresy'], Named> = {
  none: { label: 'No heresy', icon: Shield, tone: 'success' },
  anti_god: { label: 'Against all gods', icon: Ban, tone: 'danger' },
  rival_creator: { label: 'A rival maker', icon: Scale, tone: 'warning' },
  denial: { label: 'There is no maker', icon: EyeOff, tone: 'danger' },
  many_creators: { label: 'Many makers', icon: Layers, tone: 'info' },
  absent_creator: {
    label: 'The maker has gone',
    icon: HelpCircle,
    tone: 'warning',
  },
}

export const DUTIES: Record<Schema['CovenantDuty'], Named> = {
  worship: { label: 'To worship', icon: Sun, tone: 'gold' },
  peace: { label: 'To keep the peace', icon: Handshake, tone: 'success' },
  offerings: { label: 'To bring offerings', icon: Gift, tone: 'gold' },
  keep_law: { label: 'To keep the law', icon: Gavel, tone: 'info' },
  protect_the_weak: {
    label: 'To shelter the weak',
    icon: Shield,
    tone: 'success',
  },
  seek_knowledge: { label: 'To seek knowledge', icon: BookOpen, tone: 'info' },
}

export const PROMISES: Record<Schema['CreatorPromise'], Named> = {
  protection: { label: 'Protection', icon: Shield, tone: 'info' },
  plenty: { label: 'Plenty', icon: Wheat, tone: 'success' },
  guidance: { label: 'Guidance', icon: BookOpen, tone: 'info' },
  presence: { label: 'Presence', icon: Eye, tone: 'gold' },
  long_life: { label: 'Long life', icon: HeartPulse, tone: 'success' },
}

export const COVENANT_STATES: Record<Schema['CovenantState'], Named> = {
  offered: { label: 'Offered', icon: Feather, tone: 'info' },
  sealed: { label: 'Sealed', icon: Handshake, tone: 'gold' },
  kept: { label: 'Kept to its end', icon: Sun, tone: 'success' },
  broken: { label: 'Broken', icon: Ban, tone: 'danger' },
  ended: { label: 'Lapsed', icon: Forever, tone: 'muted' },
}

export const FAVOURS: Record<Schema['ChosenFavour'], Named> = {
  renown: { label: 'Renown', icon: Crown, tone: 'gold' },
  protection: { label: 'Protection', icon: Shield, tone: 'info' },
  long_life: { label: 'Long life', icon: HeartPulse, tone: 'success' },
  gift: { label: 'A gift', icon: Gift, tone: 'gold' },
  foresight: { label: 'Foresight', icon: Eye, tone: 'verdigris' },
}

export const NATURES: Record<Schema['CreatorNature'], Named> = {
  maker: { label: 'A maker', icon: Sparkles, tone: 'gold' },
  judge: { label: 'A judge', icon: Gavel, tone: 'info' },
  absent_one: { label: 'One who has gone', icon: HelpCircle, tone: 'muted' },
  source: { label: 'The source of all', icon: Sun, tone: 'gold' },
  many_faced: { label: 'Many-faced', icon: Users, tone: 'verdigris' },
  unknowable: { label: 'Beyond knowing', icon: EyeOff, tone: 'muted' },
}
