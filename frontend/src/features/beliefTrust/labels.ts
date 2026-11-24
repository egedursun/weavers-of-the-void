import {
  Antenna,
  BookOpen,
  Brain,
  Cctv,
  Eye,
  Footprints,
  KeyRound,
  Mail,
  MessageCircle,
  Moon,
  Network,
  Sparkles,
  Telescope,
  UserSearch,
  VenetianMask,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

export const TRUST_ICON = KeyRound

export const BELIEF_SOURCES: Record<
  components['schemas']['BeliefSource'],
  Named
> = {
  observation: { label: 'Their own eyes', icon: Eye, tone: 'success' },
  message: { label: 'Messages', icon: Mail, tone: 'info' },
  rumour: { label: 'Rumour', icon: MessageCircle, tone: 'muted' },
  spy: { label: 'Spies', icon: UserSearch, tone: 'warning' },
  scout: { label: 'Scouts', icon: Footprints, tone: 'info' },
  records: { label: 'Records', icon: BookOpen, tone: 'info' },
  deception: { label: 'A deceiver', icon: VenetianMask, tone: 'danger' },
  network: { label: 'A network', icon: Network, tone: 'verdigris' },
  foresight: { label: 'Foresight', icon: Telescope, tone: 'gold' },
  mind_reading: { label: 'Reading minds', icon: Brain, tone: 'gold' },
  intrusion: { label: 'Intrusion', icon: KeyRound, tone: 'danger' },
  surveillance: { label: 'Watchers', icon: Cctv, tone: 'warning' },
  made_mind_report: {
    label: 'A made mind’s report',
    icon: Antenna,
    tone: 'verdigris',
  },
  dream: { label: 'Seen in a dream', icon: Moon, tone: 'success' },
  omen: { label: 'Read in an omen', icon: Sparkles, tone: 'success' },
}
