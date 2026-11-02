import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type GoalsOverview = components['schemas']['GoalsOverview']
export type ScenarioKey = components['schemas']['ScenarioKey']
export type ScenarioStatus = components['schemas']['ScenarioStatus']

export const goalKeys = {
  overview: [...queryKeys.world.all, 'goals'] as const,
}

export function useGoals() {
  return useQuery({
    queryKey: goalKeys.overview,
    queryFn: () => unwrap(api.GET('/api/goals')),
  })
}

export const SCORE_PART_LABEL: Record<string, string> = {
  population: 'Population',
  diversity: 'Diversity',
  languages: 'Languages',
  worlds: 'Worlds',
  civilization: 'Civilization',
  doomsday: 'Apocalypse',
  achievements: 'Achievements',
  scenarios: 'Scenarios',
}

export const SCENARIO_STATUS_LABEL: Record<ScenarioStatus, string> = {
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  abandoned: 'Abandoned',
}
