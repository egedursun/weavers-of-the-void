import { type SonPublic, type SonRecord, type StatKey } from './api'
import { type BadgeVariant } from './badgeVariant'
import { REPUTATION_LABEL, isReputationLabel } from './labels'

export type StatusChip = {
  key: string
  label: string
  variant: BadgeVariant
  hint?: string
}

export function statValue(son: SonRecord, key: StatKey): number {
  return son[key]
}

export function isDead(son: SonRecord): boolean {
  return son.status === 'dead'
}

export function starText(stars: number): string {
  return stars > 0 ? '★'.repeat(stars) : 'No star'
}

export function fadingLeft(
  son: SonRecord,
  fadingEpochs: number | undefined
): number | null {
  if (son.fading_epochs <= 0 || son.status === 'dead') return null
  if (fadingEpochs === undefined) return null
  return Math.max(0, fadingEpochs - son.fading_epochs)
}

export function statusChips(
  view: SonPublic,
  ready: boolean,
  fadingEpochs: number | undefined
): StatusChip[] {
  const son = view.son
  const chips: StatusChip[] = []
  if (son.status === 'dead') {
    chips.push({
      key: 'dead',
      label:
        son.death_epoch !== null ? `Died · Epoch ${son.death_epoch}` : 'Dead',
      variant: 'destructive',
    })
    return chips
  }
  if (son.status === 'asleep')
    chips.push({
      key: 'asleep',
      label: `Asleep · ${son.sleep_epochs_left} epochs`,
      variant: 'secondary',
    })
  if (son.status === 'exiled')
    chips.push({ key: 'exiled', label: 'In exile', variant: 'warning' })
  if (son.chained)
    chips.push({ key: 'chained', label: 'Chained', variant: 'warning' })
  if (son.status === 'active' && !son.chained)
    chips.push(
      ready
        ? { key: 'ready', label: 'Ready', variant: 'success' }
        : { key: 'acted', label: 'Acted', variant: 'outline' }
    )
  if (son.rebel)
    chips.push({
      key: 'rebel',
      label: 'Rebel',
      variant: 'destructive',
      hint: 'Rebelled against his father: ignores orders and steals essence each epoch.',
    })
  const left = fadingLeft(son, fadingEpochs)
  if (left !== null)
    chips.push({
      key: 'fading',
      label: `Being forgotten · fades in ${left} epochs`,
      variant: 'destructive',
      hint: `Existence ${son.existence}. Worship, fame and a living anchor keep him remembered.`,
    })
  return chips
}

export function reputationOf(view: SonPublic): string | null {
  const raw = view.son.reputation_label ?? view.card.reputation
  if (!raw) return null
  return isReputationLabel(raw) ? REPUTATION_LABEL[raw] : raw
}

export function xpNeeded(
  level: number,
  perLevel: number | undefined
): number | null {
  return perLevel === undefined ? null : level * perLevel
}

export const RARITY_ORDER = [
  'common',
  'uncommon',
  'rare',
  'epic',
  'legendary',
  'mythic',
] as const

export function sortSons(sons: SonPublic[]): SonPublic[] {
  return [...sons].sort((left, right) => {
    const rarity =
      RARITY_ORDER.indexOf(right.son.rarity) -
      RARITY_ORDER.indexOf(left.son.rarity)
    if (rarity !== 0) return rarity
    if (right.son.stars !== left.son.stars)
      return right.son.stars - left.son.stars
    return left.son.id - right.son.id
  })
}
