import {
  Ban,
  CircleCheck,
  CircleDashed,
  CircleSlash,
  CircleX,
  Coins,
  FilePen,
  Loader2,
  type LucideIcon,
  Pause,
  ShieldCheck,
  SkipForward,
  Trash2,
  Undo2,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import {
  type ForecastStatus,
  type PlanStatus,
  type StepImpact,
  type StepStatus,
} from './types'

type BadgeTone =
  'default' | 'success' | 'warning' | 'destructive' | 'info' | 'outline'

export type StatusLook = {
  label: string
  icon: LucideIcon
  badge: BadgeTone
  tone: KpiTone
}

export const PLAN_STATUS_LOOK: Record<PlanStatus, StatusLook> = {
  draft: { label: 'Draft', icon: FilePen, badge: 'outline', tone: 'muted' },
  approved: {
    label: 'Approved',
    icon: ShieldCheck,
    badge: 'info',
    tone: 'info',
  },
  running: { label: 'Running', icon: Loader2, badge: 'default', tone: 'gold' },
  paused: { label: 'Paused', icon: Pause, badge: 'warning', tone: 'warning' },
  done: { label: 'Done', icon: CircleCheck, badge: 'success', tone: 'success' },
  failed: {
    label: 'Stopped by a failure',
    icon: CircleX,
    badge: 'destructive',
    tone: 'danger',
  },
  abandoned: {
    label: 'Abandoned',
    icon: Ban,
    badge: 'outline',
    tone: 'muted',
  },
}

export const STEP_STATUS_LOOK: Record<StepStatus, StatusLook> = {
  pending: {
    label: 'Waiting',
    icon: CircleDashed,
    badge: 'outline',
    tone: 'muted',
  },
  running: { label: 'Running', icon: Loader2, badge: 'default', tone: 'gold' },
  done: { label: 'Done', icon: CircleCheck, badge: 'success', tone: 'success' },
  skipped: {
    label: 'Skipped',
    icon: SkipForward,
    badge: 'outline',
    tone: 'muted',
  },
  failed: {
    label: 'Failed',
    icon: CircleX,
    badge: 'destructive',
    tone: 'danger',
  },
  undone: { label: 'Undone', icon: Undo2, badge: 'outline', tone: 'muted' },
}

export const IMPACT_LOOK: Record<StepImpact, StatusLook & { hint: string }> = {
  safe: {
    label: 'Safe',
    icon: ShieldCheck,
    badge: 'success',
    tone: 'success',
    hint: 'Neither deletes nor ends anything and spends little essence.',
  },
  costly: {
    label: 'Costly',
    icon: Coins,
    badge: 'warning',
    tone: 'warning',
    hint: 'Spends a great deal of essence.',
  },
  destructive: {
    label: 'Destructive',
    icon: Trash2,
    badge: 'destructive',
    tone: 'danger',
    hint: 'Deletes or ends something in the world.',
  },
}

export const FORECAST_STATUS_LOOK: Record<ForecastStatus, StatusLook> = {
  queued: {
    label: 'Queued',
    icon: CircleDashed,
    badge: 'outline',
    tone: 'muted',
  },
  running: {
    label: 'Living ahead',
    icon: Loader2,
    badge: 'default',
    tone: 'gold',
  },
  done: { label: 'Done', icon: CircleCheck, badge: 'success', tone: 'success' },
  failed: {
    label: 'Failed',
    icon: CircleX,
    badge: 'destructive',
    tone: 'danger',
  },
  cancelled: {
    label: 'Cancelled',
    icon: CircleSlash,
    badge: 'outline',
    tone: 'muted',
  },
}
