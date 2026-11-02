import { type EpochStatistics } from './api'

export const DELTA_FIELDS = [
  'population',
  'followers',
  'entities',
  'words',
  'knowledge',
  'languages',
  'wars',
  'trade_routes',
  'alliances',
  'structures',
  'items',
  'dead',
  'godless',
  'doom',
] as const

export type DeltaField = (typeof DELTA_FIELDS)[number]

export const DELTA_LABEL: Record<DeltaField, string> = {
  population: 'Population',
  followers: 'Disciples',
  entities: 'Records',
  words: 'Words',
  knowledge: 'Knowledge',
  languages: 'Languages',
  wars: 'Wars',
  trade_routes: 'Trade roads',
  alliances: 'Alliances',
  structures: 'Structures',
  items: 'Items',
  dead: 'Dead',
  godless: 'Godless',
  doom: 'Doom',
}

export function deltaOf(
  field: DeltaField,
  current: EpochStatistics,
  previous: EpochStatistics
) {
  return {
    field,
    label: DELTA_LABEL[field],
    value: current.data[field] - previous.data[field],
  }
}

export function sonFaithTotal(stats: EpochStatistics): number {
  return Object.values(stats.data.sons ?? {}).reduce(
    (sum, son) => sum + son.faith,
    0
  )
}
