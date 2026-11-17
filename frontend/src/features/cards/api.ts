import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type CharacterCard = components['schemas']['CharacterCard']
export type CharacterCardStat = components['schemas']['CharacterCardStat']
export type CharacterCardPage = components['schemas']['CharacterCardPage']
export type CharacterDeckCount = components['schemas']['CharacterDeckCount']
export type CardOrder = components['schemas']['CardOrder']
export type NodeKind = components['schemas']['NodeKind']
export type EntityType = components['schemas']['EntityType']

export type CardFilters = {
  q: string
  nodeKind: NodeKind | null
  entityType: EntityType | null
  rarity: components['schemas']['Rarity'] | null
  worldId: number | null
  fallen: boolean | null
  order: CardOrder
}

export const CARD_PAGE_SIZE = 48

export const cardKeys = {
  list: (filters: CardFilters) =>
    [...queryKeys.world.all, 'cards', filters] as const,
}

export function useCharacterCards(filters: CardFilters) {
  return useInfiniteQuery({
    queryKey: cardKeys.list(filters),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/cards', {
          params: {
            query: {
              q: filters.q || undefined,
              node_kind: filters.nodeKind ?? undefined,
              entity_type: filters.entityType ?? undefined,
              rarity: filters.rarity ?? undefined,
              world_id: filters.worldId ?? undefined,
              fallen: filters.fallen ?? undefined,
              order: filters.order,
              offset: pageParam,
              limit: CARD_PAGE_SIZE,
            },
          },
        })
      ),
    getNextPageParam: (last: CharacterCardPage) => {
      const next = last.offset + last.items.length
      return next < last.total ? next : undefined
    },
    placeholderData: keepPreviousData,
  })
}
