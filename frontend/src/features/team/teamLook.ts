import {
  Ban,
  BookLock,
  CircleCheck,
  CircleX,
  Clock,
  FileLock2,
  Hourglass,
  Lock,
  LockOpen,
  type LucideIcon,
  MessageSquareText,
  ScrollText,
  Sparkles,
  Undo2,
  Wand2,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { crestTone } from '@/features/universes/universeLook'
import {
  type CanonTouch,
  type ProposalStatus,
  type QueuedActSource,
  type QueuedActStatus,
} from './types'

export type Look = { label: string; icon: LucideIcon; tone: KpiTone }

export const QUEUE_STATUS: Record<QueuedActStatus, Look> = {
  queued: { label: 'Waiting', icon: Hourglass, tone: 'warning' },
  applied: { label: 'Applied', icon: CircleCheck, tone: 'success' },
  proposed: { label: 'Sent for review', icon: BookLock, tone: 'info' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
  cancelled: { label: 'Cancelled', icon: Ban, tone: 'muted' },
}

export const QUEUE_SOURCE: Record<QueuedActSource, Look> = {
  lever: { label: 'A god lever', icon: Wand2, tone: 'gold' },
  undo: { label: 'An undo', icon: Undo2, tone: 'verdigris' },
  rules: { label: 'A rule change', icon: ScrollText, tone: 'info' },
  divine_will: { label: 'The Divine Will', icon: Sparkles, tone: 'gold' },
  presence: {
    label: 'Summon to Presence',
    icon: MessageSquareText,
    tone: 'info',
  },
}

export const PROPOSAL_STATUS: Record<ProposalStatus, Look> = {
  pending: { label: 'Waiting for review', icon: Clock, tone: 'warning' },
  approved: { label: 'Approved', icon: CircleCheck, tone: 'success' },
  rejected: { label: 'Rejected', icon: CircleX, tone: 'danger' },
  withdrawn: { label: 'Withdrawn', icon: Ban, tone: 'muted' },
}

export const CANON_TOUCH: Record<CanonTouch, Look> = {
  held_thing: { label: 'Changes a held thing', icon: Lock, tone: 'warning' },
  canon_status: {
    label: 'Strikes or restores canon',
    icon: BookLock,
    tone: 'danger',
  },
  canon_fact: {
    label: 'Changes a canon fact',
    icon: FileLock2,
    tone: 'warning',
  },
  hold_changed: {
    label: 'Holds or releases a thing',
    icon: Lock,
    tone: 'info',
  },
  lock_changed: {
    label: 'Locks or unlocks a value',
    icon: LockOpen,
    tone: 'info',
  },
  locked_field: {
    label: 'Changes a locked value',
    icon: FileLock2,
    tone: 'warning',
  },
}

export function personTone(name: string): KpiTone {
  return crestTone(name)
}

export function spokenField(name: string): string {
  const words = name.replaceAll('_', ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}
