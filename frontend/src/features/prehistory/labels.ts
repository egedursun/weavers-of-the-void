import {
  Anchor,
  BookOpen,
  CircleCheck,
  CirclePause,
  CirclePlay,
  Cloud,
  Copy,
  Crown,
  FlipHorizontal,
  Ghost,
  Globe,
  Hourglass,
  type LucideIcon,
  Orbit,
  PenLine,
  Rocket,
  Skull,
  Sparkles,
  TreeDeciduous,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const PREHISTORY_ICON: LucideIcon = Hourglass
export const DEEP_TIME_ICON: LucideIcon = Orbit

export const PREHISTORY_KINDS: Record<Schema['PrehistoryKind'], Named> = {
  full: { label: 'The full run', icon: Globe, tone: 'info' },
  living: {
    label: 'The full run and the world’s own moods',
    icon: TreeDeciduous,
    tone: 'success',
  },
  souls: { label: 'Arrival of the dead', icon: Ghost, tone: 'muted' },
  dreamt: { label: 'A dreamt past', icon: Cloud, tone: 'verdigris' },
  mirrored: {
    label: 'The twin’s past, mirrored',
    icon: FlipHorizontal,
    tone: 'info',
  },
  palace: { label: 'The deeds of its god', icon: Crown, tone: 'gold' },
  voyage: { label: 'The voyage', icon: Rocket, tone: 'info' },
  phenomenon: {
    label: 'The phenomenon it grew from',
    icon: Sparkles,
    tone: 'warning',
  },
  corpse: {
    label: 'The god’s life, death and body',
    icon: Skull,
    tone: 'danger',
  },
}

export const PREHISTORY_STATES: Record<Schema['PrehistoryState'], Named> = {
  planned: { label: 'Planned', icon: PenLine, tone: 'muted' },
  running: { label: 'Running', icon: CirclePlay, tone: 'warning' },
  done: { label: 'Done', icon: CircleCheck, tone: 'success' },
  aborted: { label: 'Stopped', icon: CirclePause, tone: 'danger' },
}

export const PREHISTORY_SOURCES: Record<Schema['PrehistorySource'], Named> = {
  simulated: { label: 'Simulated', icon: Globe, tone: 'info' },
  backfilled: { label: 'From written lore', icon: BookOpen, tone: 'gold' },
  mirrored: { label: 'Mirrored from the twin', icon: Copy, tone: 'info' },
  dreamt: { label: 'Dreamt', icon: Cloud, tone: 'verdigris' },
  derived: { label: 'Borrowed from its source', icon: Anchor, tone: 'muted' },
}

export const DEEP_TIME_STATES: Record<Schema['DeepTimeState'], Named> = {
  running: { label: 'Running', icon: CirclePlay, tone: 'warning' },
  done: { label: 'Done', icon: CircleCheck, tone: 'success' },
  stopped: { label: 'Stopped', icon: CirclePause, tone: 'danger' },
}
