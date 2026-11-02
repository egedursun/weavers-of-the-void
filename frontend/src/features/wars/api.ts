import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type WarSummary = components['schemas']['WarSummary']
export type WarStatus = components['schemas']['WarStatus']
export type ArmyView = components['schemas']['ArmyView']
export type BattleView = components['schemas']['BattleView']
export type SiegeView = components['schemas']['SiegeView']
export type CaptiveView = components['schemas']['CaptiveView']
export type CaptiveStatus = components['schemas']['CaptiveStatus']
export type TributeView = components['schemas']['TributeView']
export type TributeStatus = components['schemas']['TributeStatus']
export type HeroView = components['schemas']['HeroView']
export type NodeRef = components['schemas']['NodeRef']

export const WAR_PAGE_SIZE = 20

export type WarPart = 'armies' | 'battles' | 'sieges'

export const warKeys = {
  all: [...queryKeys.world.all, 'wars'] as const,
  list: (status: WarStatus | null, offset: number) =>
    [...queryKeys.world.all, 'wars', 'list', status, offset] as const,
  detail: (warId: number) =>
    [...queryKeys.world.all, 'wars', warId, 'detail'] as const,
  part: (warId: number, part: WarPart, offset: number) =>
    [...queryKeys.world.all, 'wars', warId, part, offset] as const,
  captives: (
    communityId: number | null,
    status: CaptiveStatus | null,
    offset: number
  ) =>
    [
      ...queryKeys.world.all,
      'wars',
      'captives',
      communityId,
      status,
      offset,
    ] as const,
  tributes: (
    communityId: number | null,
    status: TributeStatus | null,
    offset: number
  ) =>
    [
      ...queryKeys.world.all,
      'wars',
      'tributes',
      communityId,
      status,
      offset,
    ] as const,
  community: (entityId: number, offset: number) =>
    [...queryKeys.world.all, 'wars', 'community', entityId, offset] as const,
  heroes: (entityId: number) =>
    [...queryKeys.world.all, 'wars', 'heroes', entityId] as const,
}

export function useWars(status: WarStatus | null, offset: number) {
  return useQuery({
    queryKey: warKeys.list(status, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars', {
          params: {
            query: {
              status: status ?? undefined,
              offset,
              limit: WAR_PAGE_SIZE,
            },
          },
        })
      ),
    placeholderData: keepPreviousData,
  })
}

export function useWar(warId: number) {
  return useQuery({
    queryKey: warKeys.detail(warId),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}', {
          params: { path: { war_id: warId } },
        })
      ),
  })
}

export function useCommunityWars(entityId: number, offset: number) {
  return useQuery({
    queryKey: warKeys.community(entityId, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/wars', {
          params: {
            path: { entity_id: entityId },
            query: { offset, limit: WAR_PAGE_SIZE },
          },
        })
      ),
    placeholderData: keepPreviousData,
  })
}

export function useCommunityHeroes(entityId: number) {
  return useQuery({
    queryKey: warKeys.heroes(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/heroes', {
          params: { path: { entity_id: entityId } },
        })
      ),
  })
}

export function useArmies(warId: number, offset: number, enabled: boolean) {
  return useQuery({
    queryKey: warKeys.part(warId, 'armies', offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}/armies', {
          params: {
            path: { war_id: warId },
            query: { offset, limit: WAR_PAGE_SIZE },
          },
        })
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useBattles(warId: number, offset: number, enabled: boolean) {
  return useQuery({
    queryKey: warKeys.part(warId, 'battles', offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}/battles', {
          params: {
            path: { war_id: warId },
            query: { offset, limit: WAR_PAGE_SIZE },
          },
        })
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useSieges(warId: number, offset: number, enabled: boolean) {
  return useQuery({
    queryKey: warKeys.part(warId, 'sieges', offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}/sieges', {
          params: {
            path: { war_id: warId },
            query: { offset, limit: WAR_PAGE_SIZE },
          },
        })
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useCaptives(
  communityId: number | null,
  status: CaptiveStatus | null,
  offset: number
) {
  return useQuery({
    queryKey: warKeys.captives(communityId, status, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/captives', {
          params: {
            query: {
              community_id: communityId ?? undefined,
              status: status ?? undefined,
              offset,
              limit: WAR_PAGE_SIZE,
            },
          },
        })
      ),
    placeholderData: keepPreviousData,
  })
}

export function useTributes(
  communityId: number | null,
  status: TributeStatus | null,
  offset: number
) {
  return useQuery({
    queryKey: warKeys.tributes(communityId, status, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/tributes', {
          params: {
            query: {
              community_id: communityId ?? undefined,
              status: status ?? undefined,
              offset,
              limit: WAR_PAGE_SIZE,
            },
          },
        })
      ),
    placeholderData: keepPreviousData,
  })
}
