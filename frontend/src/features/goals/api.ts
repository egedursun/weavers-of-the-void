import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schemas = components['schemas']

export type GoalsOverview = NonNullable<ReturnType<typeof useGoals>['data']>
export type ScenarioKey = Schemas['ScenarioKey']
export type ScenarioStatus = Schemas['ScenarioStatus']
export type GoalCategory = Schemas['GoalCategory']
export type GoalMetric = Schemas['GoalMetric']
export type GoalComparator = Schemas['GoalComparator']
export type GoalBasis = Schemas['GoalBasis']
export type ScoreComponent = Schemas['ScoreComponent']
export type AchievementKey = Schemas['AchievementKey']
export type AchievementView = Schemas['AchievementView']
export type ScenarioView = Schemas['ScenarioView']
export type RunningScenario = Schemas['RunningScenario']
export type ScenarioHistory = Schemas['ScenarioHistory']
export type MetricView = Schemas['MetricView']
export type GoalQuote = Schemas['GoalQuote']

export type QuoteRequest = {
  key: ScenarioKey
  target?: number
  deadline_epochs?: number
  metric?: GoalMetric
  comparator?: GoalComparator
  basis?: GoalBasis
  hold_epochs?: number
}

export const goalKeys = {
  overview: [...queryKeys.world.all, 'goals'] as const,
  quote: (request: QuoteRequest) =>
    [...queryKeys.world.all, 'goals', 'quote', request] as const,
}

export function useGoals() {
  return useQuery({
    queryKey: goalKeys.overview,
    queryFn: () => unwrap(api.GET('/api/goals')),
  })
}

export function useGoalQuote(request: QuoteRequest | null) {
  return useQuery({
    queryKey: goalKeys.quote(request ?? { key: 'doom_far' }),
    queryFn: () =>
      unwrap(api.GET('/api/goals/quote', { params: { query: request ?? {} } })),
    enabled: request !== null,
    placeholderData: (previous) => previous,
  })
}

export const SCORE_PART_LABEL: Record<ScoreComponent, string> = {
  population: 'Population',
  diversity: 'Diversity',
  languages: 'Languages',
  worlds: 'Worlds',
  civilization: 'Civilization',
  life: 'Life',
  faith: 'Faith',
  culture: 'Culture',
  knowledge: 'Knowledge',
  wonders: 'Wonders',
  scales: 'Scales',
  exploration: 'Exploration',
  doomsday: 'Apocalypse',
  achievements: 'Achievements',
  scenarios: 'Goals',
}

export const SCENARIO_STATUS_LABEL: Record<ScenarioStatus, string> = {
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  abandoned: 'Abandoned',
}

export const COMPARATOR_LABEL: Record<GoalComparator, string> = {
  at_least: 'At least',
  at_most: 'At most',
}

export const BASIS_LABEL: Record<GoalBasis, string> = {
  total: 'In all',
  gained: 'Gained from now',
}

const NUMERALS: [number, string][] = [
  [1000, 'M'],
  [900, 'CM'],
  [500, 'D'],
  [400, 'CD'],
  [100, 'C'],
  [90, 'XC'],
  [50, 'L'],
  [40, 'XL'],
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
]

export function roman(value: number): string {
  let left = Math.max(1, Math.floor(value))
  let text = ''
  for (const [amount, symbol] of NUMERALS) {
    while (left >= amount) {
      text += symbol
      left -= amount
    }
  }
  return text
}
