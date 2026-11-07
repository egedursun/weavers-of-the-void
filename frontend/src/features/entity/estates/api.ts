import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Estates = components['schemas']['EstatesView']
export type Estate = components['schemas']['EstateView']
export type Movement = components['schemas']['PoliticalMovementView']
export type Company = components['schemas']['CompanyView']
export type HolyOrder = components['schemas']['HolyOrderView']
export type Guild = components['schemas']['GuildView']
export type EstatePrivilege = components['schemas']['EstatePrivilege']
export type MovementCause = components['schemas']['MovementCause']
export type SocialClass = components['schemas']['SocialClass']
export type Technique = components['schemas']['Technique']

export function estatesKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'estates'] as const
}

export function useEstates(nodeId: number) {
  return useQuery({
    queryKey: estatesKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/estates/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
