import { type KindRecord } from './api'
import { NUCLEI } from './labels'

type Nucleus = keyof typeof NUCLEI

const NUCLEUS_KEYS: readonly Nucleus[] = [
  'none',
  'dormant',
  'active',
  'quasar',
  'devoured',
]
const PERCENT = 100

export function armRange(effects: KindRecord['effects']): [number, number] {
  const low = effects?.arms_min ?? 0
  return [low, Math.max(low, effects?.arms_max ?? low)]
}

export function armText(effects: KindRecord['effects']): string {
  const [low, high] = armRange(effects)
  return low === high ? String(low) : `${low}–${high}`
}

export function nucleusOdds(
  effects: KindRecord['effects']
): [Nucleus, number][] {
  const weights = NUCLEUS_KEYS.map(
    (key) => [key, effects?.[`nucleus_${key}`] ?? 0] as [Nucleus, number]
  )
  const total = weights.reduce((sum, [, weight]) => sum + weight, 0)
  if (total <= 0) return [['dormant', PERCENT]]
  return weights
    .filter(([, weight]) => weight > 0)
    .map(
      ([key, weight]) =>
        [key, Math.round((weight * PERCENT) / total)] as [Nucleus, number]
    )
    .sort((first, second) => second[1] - first[1])
}

export function nucleusText(effects: KindRecord['effects']): string {
  return nucleusOdds(effects)
    .map(([key, share]) => `${NUCLEI[key].label} ${share}%`)
    .join(' · ')
}

export function isKindShape(key: string): boolean {
  return key.startsWith('arms_') || key.startsWith('nucleus_')
}
