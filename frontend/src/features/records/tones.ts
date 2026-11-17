import type { KpiTone, TimelineTone } from '@/components/domain'
import { named } from '@/features/entity/environment/labels'
import { INCIDENT_ROLE } from './labels'

const TIMELINE_OF: Partial<Record<KpiTone, TimelineTone>> = {
  gold: 'primary',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
}

export function timelineTone(tone: KpiTone | undefined): TimelineTone {
  return (tone && TIMELINE_OF[tone]) ?? 'default'
}

export function roleTimelineTone(role: string): TimelineTone {
  return timelineTone(named(INCIDENT_ROLE, role).tone)
}
