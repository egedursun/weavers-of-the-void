export const HEAVENS_TABS = [
  'scale',
  'create',
  'rifts',
  'beings',
  'phenomena',
  'bodies',
  'events',
  'end',
] as const

export type HeavensTab = (typeof HEAVENS_TABS)[number]

export const SCALE_KINDS = ['dimension', 'cluster', 'galaxy'] as const

export type ScaleKind = (typeof SCALE_KINDS)[number]

export type HeavensSearch = {
  layer?: ScaleKind
  node?: number
  pane?: HeavensTab
}

function positiveInteger(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

function oneOf<T extends string>(
  items: readonly T[],
  value: unknown
): T | undefined {
  return items.find((item) => item === value)
}

export function validateHeavensSearch(
  search: Record<string, unknown>
): HeavensSearch {
  return {
    layer: oneOf(SCALE_KINDS, search.layer),
    node: positiveInteger(search.node),
    pane: oneOf(HEAVENS_TABS, search.pane),
  }
}
