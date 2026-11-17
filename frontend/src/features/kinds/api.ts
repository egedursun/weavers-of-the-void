import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type KindConcept = components['schemas']['KindConcept']
export type KindConceptInfo = components['schemas']['KindConceptInfo']
export type KindRecord = components['schemas']['AuthoredKindRecord']
export type KindHoldingView = components['schemas']['KindHoldingView']
export type KindStance = components['schemas']['KindStance']
export type KindSpread = components['schemas']['KindSpread']
export type WaysOfLifeView = components['schemas']['WaysOfLifeView']

const KINDS_KEY = [...queryKeys.world.all, 'kinds'] as const

export function useKindConcepts() {
  return useQuery({
    queryKey: [...KINDS_KEY, 'concepts'] as const,
    queryFn: () => unwrap(api.GET('/api/kinds/concepts')),
    staleTime: Infinity,
  })
}

export function useKinds(concept: KindConcept | null, worldId: number | null) {
  return useQuery({
    queryKey: [...KINDS_KEY, 'of-concept', concept, worldId] as const,
    enabled: concept !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/kinds/{concept}', {
          params: {
            path: { concept: concept ?? 'good' },
            query: { world_id: worldId },
          },
        })
      ),
  })
}

export function useWaysOfLife(nodeId: number) {
  return useQuery({
    queryKey: [...KINDS_KEY, 'of-node', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/kinds/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useKindTable(
  concept: KindConcept,
  worldId: number | null
): Record<string, string> {
  const kinds = useKinds(concept, worldId)
  return Object.fromEntries(
    (kinds.data ?? [])
      .filter((kind) => !kind.retired)
      .map((kind) => [String(kind.id), kind.name])
  )
}
