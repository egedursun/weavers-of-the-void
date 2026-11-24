import { plural } from '@/lib/units'
import { KIN_KINDS } from '../labels'
import { type CareKind, type PartnerKind } from './familyLayout'

export const PARTNER_LOOK: Record<
  PartnerKind,
  { stroke: string; dash?: string; label: string }
> = {
  spouse_of: { stroke: 'stroke-gild', label: 'Marriage' },
  concubine_of: {
    stroke: 'stroke-brand-magenta',
    dash: '7 5',
    label: KIN_KINDS.concubine_of.label,
  },
  betrothed_to: {
    stroke: 'stroke-brand-azure',
    dash: '1 6',
    label: KIN_KINDS.betrothed_to.label,
  },
}

export const CARE_LOOK: Record<
  CareKind,
  { stroke: string; dash: string; label: string }
> = {
  parent_of: {
    stroke: 'stroke-gild',
    dash: '6 6',
    label: 'A further parent',
  },
  fostered_by: {
    stroke: 'stroke-brand-verdigris',
    dash: '9 5',
    label: KIN_KINDS.fostered_by.label,
  },
  godparent_of: {
    stroke: 'stroke-info',
    dash: '2 6',
    label: KIN_KINDS.godparent_of.label,
  },
  sworn_kin: {
    stroke: 'stroke-warning',
    dash: '12 4 2 4',
    label: KIN_KINDS.sworn_kin.label,
  },
}

export const ENDED_DASH = '5 6'

export function generationWord(generation: number): string {
  if (generation === 0) return 'Their generation'
  const steps = Math.abs(generation)
  return `${plural(steps, 'generation', 'generations')} ${generation < 0 ? 'up' : 'down'}`
}
