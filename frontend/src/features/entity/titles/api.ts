import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Titles = components['schemas']['TitlesView']
export type TitleDetail = components['schemas']['TitleDetail']
export type TitleSummary = components['schemas']['TitleSummary']
export type TitleTier = components['schemas']['TitleTier']

export function titlesKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'titles'] as const
}

export function useTitles(nodeId: number) {
  return useQuery({
    queryKey: titlesKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/titles/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
