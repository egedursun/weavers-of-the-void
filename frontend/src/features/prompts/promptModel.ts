import { type ProgressTone } from '@/components/ui/progress'
import {
  type ContextBlockKind,
  type PromptArea,
  type PromptEntry,
  type SummarySection,
} from './api'

const WARNING_RATIO = 0.85

export function budgetTone(used: number, limit: number): ProgressTone {
  if (limit <= 0) return 'muted'
  if (used > limit) return 'destructive'
  if (used >= limit * WARNING_RATIO) return 'warning'
  return 'default'
}

export function sectionLabel(value: string): string {
  const spaced = value.replace(/[_-]+/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export const SUMMARY_SECTIONS: readonly SummarySection[] = [
  'pantheon',
  'threads',
  'events',
  'cosmos',
  'geography',
  'languages',
  'map',
  'legends',
]

export type BlockOption = 'short' | 'full' | 'section'

export const BLOCK_OPTIONS: Partial<Record<ContextBlockKind, BlockOption>> = {
  'world-header': 'short',
  'son-memory': 'full',
  'world-summary': 'section',
}

export const AREA_LABEL: Record<PromptArea, string> = {
  shared: 'Shared',
  context: 'Context',
  genesis: 'Genesis',
  son_turn: 'Son turn',
  fate: 'Fate',
  chronicler: 'Chronicler',
  naming: 'Naming',
  voices: 'Voices',
  deepening: 'Deepening',
  image_prompts: 'Image prompts',
  council: 'Council',
  translation: 'Translation',
  world_birth: 'World birth',
  network_repair: 'Network repair',
  mortal: 'Mortal',
  opportunities: 'Opportunities',
  agent: 'Agent',
  localisation: 'Localisation',
  divine_will: 'Divine Will',
  presence: 'Summon to Presence',
}

export function matchesPrompt(entry: PromptEntry, query: string): boolean {
  const needle = query.trim().toLowerCase()
  if (needle === '') return true
  return [
    entry.prompt_id,
    entry.template_path,
    entry.context,
    entry.output ?? '',
    ...entry.variables.map((variable) => variable.name),
  ].some((text) => text.toLowerCase().includes(needle))
}

export function schemaText(schema: Record<string, unknown> | null | undefined) {
  return schema ? JSON.stringify(schema, null, 2) : ''
}
