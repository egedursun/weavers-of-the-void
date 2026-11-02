import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type CouncilRecord = components['schemas']['CouncilRecord']
export type CouncilVote = components['schemas']['CouncilVote']

export const councilKeys = {
  list: [...queryKeys.world.all, 'councils'] as const,
}

export function useCouncils() {
  return useQuery({
    queryKey: councilKeys.list,
    queryFn: () => unwrap(api.GET('/api/councils')),
  })
}
