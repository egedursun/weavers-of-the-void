import { type EnginePhase, type PhaseStage } from './api'

export const STAGE_ORDER: PhaseStage[] = [
  'tick',
  'pre_transition',
  'transition',
  'post_transition',
]

export const STAGE_TITLE: Record<PhaseStage, string> = {
  tick: 'Engine tick',
  pre_transition: 'Before the epoch turns',
  transition: 'Epoch transition',
  post_transition: 'After the epoch turns',
}

export const STAGE_DESCRIPTION: Record<PhaseStage, string> = {
  tick: 'The steps the world engine runs, in order, every epoch.',
  pre_transition: 'Steps that settle local gods before the epoch closes.',
  transition: 'Growth, the fate of the gods and the closing of the epoch.',
  post_transition: 'Steps that run once the new epoch has begun.',
}

export function phaseLabel(name: string): string {
  const text = name.replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function phasesByStage(
  phases: EnginePhase[]
): Map<PhaseStage, EnginePhase[]> {
  const grouped = new Map<PhaseStage, EnginePhase[]>()
  for (const stage of STAGE_ORDER) grouped.set(stage, [])
  for (const phase of phases) grouped.get(phase.stage)?.push(phase)
  return grouped
}

export function matchesQuery(phase: EnginePhase, query: string): boolean {
  const needle = query.trim().toLowerCase()
  return needle === '' || phaseLabel(phase.name).toLowerCase().includes(needle)
}
