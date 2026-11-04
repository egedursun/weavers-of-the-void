import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type LoreCard = components['schemas']['LoreCard']
export type LearningCard = components['schemas']['LearningCard']
export type TechGraph = components['schemas']['TechGraph']
export type TongueAtlas = components['schemas']['TongueAtlas']
export type LoreValue = string | number | boolean | null

export const loreCardKeys = {
  card: (id: number) => [...loreKeys.entity(id), 'lore'] as const,
  learning: (id: number) => [...loreKeys.entity(id), 'learning'] as const,
  graph: ['techniques'] as const,
  tongues: (worldId: number) =>
    [...loreKeys.state, 'tongues', worldId] as const,
}

export function useLore(id: number) {
  return useQuery({
    queryKey: loreCardKeys.card(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/lore', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useLearning(id: number) {
  return useQuery({
    queryKey: loreCardKeys.learning(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/learning', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useTechGraph() {
  return useQuery({
    queryKey: loreCardKeys.graph,
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/techniques')),
  })
}

export function useTongues(worldId: number | null) {
  return useQuery({
    queryKey: loreCardKeys.tongues(worldId ?? 0),
    enabled: worldId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/tongues', {
          params: { path: { world_id: worldId ?? 0 } },
        })
      ),
  })
}

export function words(value: string): string {
  return value.replaceAll('_', ' ')
}

export function table(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}
