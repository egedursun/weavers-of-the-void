import { type EntityType } from './api/types'

export const RELATION_PAGE_MAX = 1000
export const ENTITY_PAGE_MAX = 2000
export const BOND_PAGE_SIZE = 40
export const CHRONICLE_PAGE_SIZE = 25
export const CONTENTS_SHOWN = 50
export const NOTE_MAX_LENGTH = 4000
export const NOTE_AUTOSAVE_MS = 900
export const FACT_PREDICATE_MAX = 80
export const FACT_OBJECT_MAX = 200
export const BOND_DESCRIPTION_MAX = 200
export const NAME_MAX = 80
export const SUBTYPE_MAX = 60
export const DREAM_MIN_LENGTH = 5
export const DREAM_MAX_LENGTH = 600
export const MERGE_WORD = 'MERGE'
export const NAMES_STALE_MS = 30_000
export const PERCENT_MAX = 100

export const COMMUNITY_TYPES: readonly EntityType[] = [
  'people',
  'settlement',
  'cult',
  'faction',
]

export const THINKING_TYPES: readonly EntityType[] = [
  ...COMMUNITY_TYPES,
  'mortal',
  'species',
]

export const LAND_TYPES: readonly EntityType[] = ['region', 'place']

export const DISASTER_TYPES: readonly EntityType[] = [
  'region',
  'place',
  'settlement',
]

export const NO_INTERVENTION_TYPES: readonly EntityType[] = [
  'law',
  'language',
  'natural_law',
]

export const COUNT_STATS: ReadonlySet<string> = new Set([
  'population',
  'hp',
  'age',
  'lifespan',
  'death_year',
  'followers',
  'crew',
  'size',
  'devotion',
  'level',
])

export const HIDDEN_STAT_KEYS: ReadonlySet<string> = new Set(['kind'])
