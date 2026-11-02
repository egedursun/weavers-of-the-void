import { type GreatExpedition } from './expeditionsApi'

export const PERCENT = 100

export const OUTCOME_LABEL: Record<
  NonNullable<GreatExpedition['outcome']>,
  string
> = {
  completed: 'Completed',
  failed: 'Failed',
  invalidated: 'Void',
}

export const OUTCOME_VARIANT = {
  completed: 'success',
  failed: 'destructive',
  invalidated: 'secondary',
} as const

export const DECLARER_LABEL: Record<GreatExpedition['declared_by'], string> = {
  creator: 'the Creator',
  son: 'a son',
  mortal: 'mortals',
  foreign_god: 'a foreign god',
  fate: 'Fate',
  engine: 'the world',
  system: 'the world',
}

export function expeditionProgress(expedition: GreatExpedition): number {
  const span = Math.max(1, expedition.deadline_epoch - expedition.opened_epoch)
  const left = expedition.outcome === null ? expedition.epochs_remaining : 0
  return Math.min(1, Math.max(0, (span - left) / span))
}

export function countdownText(expedition: GreatExpedition): string {
  if (expedition.outcome !== null) return OUTCOME_LABEL[expedition.outcome]
  if (expedition.epochs_remaining === 0) return 'The deadline falls this epoch'
  return `${expedition.epochs_remaining} ${expedition.epochs_remaining === 1 ? 'epoch' : 'epochs'} remaining`
}
