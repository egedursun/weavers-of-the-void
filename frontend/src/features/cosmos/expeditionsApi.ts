import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type GreatExpedition = components['schemas']['GreatExpedition']
export type EpochStarView = components['schemas']['EpochStarView']
export type EpochStarWorld = components['schemas']['EpochStarWorld']
export type EpochStarEntry = components['schemas']['EpochStarEntry']

export const expeditionKeys = {
  list: [...queryKeys.world.all, 'expeditions'] as const,
  epochStar: [...queryKeys.world.all, 'epoch-star'] as const,
}

export function useExpeditions() {
  return useQuery({
    queryKey: expeditionKeys.list,
    queryFn: () => unwrap(api.GET('/api/expeditions')),
  })
}

export function useEpochStar() {
  return useQuery({
    queryKey: expeditionKeys.epochStar,
    queryFn: () => unwrap(api.GET('/api/cosmos/epoch-star')),
  })
}

export function useExpeditionOfThread(
  threadId: number
): GreatExpedition | undefined {
  const expeditions = useExpeditions()
  return expeditions.data?.find((item) => item.thread_id === threadId)
}
