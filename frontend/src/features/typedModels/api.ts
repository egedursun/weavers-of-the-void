import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type TypedModelsView = components['schemas']['TypedModelsView']
export type HorrorEventView = components['schemas']['HorrorEventView']
export type CreatureAttackRecord = components['schemas']['CreatureAttackRecord']
export type HeroQuestView = components['schemas']['HeroQuestView']
export type AspectView = components['schemas']['AspectView']

export function useTypedModels(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'typed-models-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/typed/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
