import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'
import {
  HORROR_EFFECTS,
  HORROR_SCOPES,
  HORROR_SENSES,
  HORROR_SOURCES,
  HORROR_TARGETS,
} from '@/features/typedModels/labels'

type Schema = components['schemas']

export type HorrorSpec = {
  target: Schema['HorrorTarget']
  effect: Schema['HorrorEffect']
  scope: Schema['HorrorScope']
  sense: Schema['HorrorSense']
  source: Schema['HorrorSource']
}

export const HORROR_DEFAULT: HorrorSpec = {
  target: 'minds',
  effect: 'mark',
  scope: 'world',
  sense: 'seen',
  source: 'unknown',
}

export const HORROR_PARTS: readonly {
  key: keyof HorrorSpec
  label: string
  table: Record<string, Named>
}[] = [
  { key: 'target', label: 'What it touches', table: HORROR_TARGETS },
  { key: 'effect', label: 'What it does', table: HORROR_EFFECTS },
  { key: 'scope', label: 'How far it reaches', table: HORROR_SCOPES },
  { key: 'sense', label: 'How it is perceived', table: HORROR_SENSES },
  { key: 'source', label: 'Where it comes from', table: HORROR_SOURCES },
]
