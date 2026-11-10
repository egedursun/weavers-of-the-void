import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { ApiError, unwrap } from '@/api/errors'
import { ENTITY_PAGE_MAX, NAMES_STALE_MS } from '../constants'
import { loreKeys } from './keys'
import { type EntitySummary } from './types'

export function useEntity(id: number | null) {
  return useQuery({
    queryKey: loreKeys.entity(id ?? 0),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}', {
          params: { path: { entity_id: id ?? 0 } },
        })
      ),
    enabled: id !== null && id > 0,
  })
}

const NOT_FOUND = 404

export function useEntityNote(id: number, enabled: boolean) {
  return useQuery({
    queryKey: loreKeys.note(id),
    queryFn: async () => {
      try {
        return await unwrap(
          api.GET('/api/entities/{entity_id}/note', {
            params: { path: { entity_id: id } },
          })
        )
      } catch (error) {
        if (error instanceof ApiError && error.status === NOT_FOUND) return null
        throw error
      }
    },
    enabled,
  })
}

export function useEntityBonds(
  id: number,
  offset: number,
  limit: number,
  enabled = true
) {
  return useQuery({
    queryKey: loreKeys.entityBonds(id, offset, limit),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/bonds', {
          params: { path: { entity_id: id }, query: { offset, limit } },
        })
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useEntityChronicle(
  id: number,
  offset: number,
  limit: number,
  enabled = true
) {
  return useQuery({
    queryKey: loreKeys.entityChronicle(id, offset, limit),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/chronicle', {
          params: { path: { entity_id: id }, query: { offset, limit } },
        })
      ),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export async function fetchAllEntities(
  status: string,
  hideArchived = false
): Promise<EntitySummary[]> {
  const items: EntitySummary[] = []
  let offset = 0
  for (;;) {
    const page = await unwrap(
      api.GET('/api/entities', {
        params: {
          query: {
            status,
            offset,
            limit: ENTITY_PAGE_MAX,
            hide_archived: hideArchived,
          },
        },
      })
    )
    items.push(...page.items)
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) return items
  }
}

export function useAllEntities(status: string, hideArchived = false) {
  return useQuery({
    queryKey: loreKeys.entityAll(
      `${status}:${hideArchived ? 'atlas' : 'history'}`
    ),
    queryFn: () => fetchAllEntities(status, hideArchived),
    placeholderData: keepPreviousData,
  })
}

export function useNames(enabled = true) {
  return useQuery({
    queryKey: loreKeys.names,
    queryFn: () => unwrap(api.GET('/api/names')),
    staleTime: NAMES_STALE_MS,
    enabled,
  })
}

export function useCatalogue() {
  return useQuery({
    queryKey: loreKeys.catalogue,
    queryFn: () => unwrap(api.GET('/api/catalogue')),
    staleTime: Infinity,
  })
}

export function useActionCatalogue() {
  return useQuery({
    queryKey: loreKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    staleTime: Infinity,
  })
}

export function useWorldState() {
  return useQuery({
    queryKey: loreKeys.state,
    queryFn: () => unwrap(api.GET('/api/state')),
  })
}

export function useCosmos() {
  return useQuery({
    queryKey: loreKeys.cosmos,
    queryFn: () => unwrap(api.GET('/api/cosmos')),
  })
}

export function useKnowledge(enabled = true) {
  return useQuery({
    queryKey: loreKeys.knowledge,
    queryFn: () => unwrap(api.GET('/api/knowledge')),
    enabled,
  })
}

export function useForeignGods() {
  return useQuery({
    queryKey: loreKeys.foreignGods,
    queryFn: () => unwrap(api.GET('/api/foreign-gods')),
  })
}

export function useThreads() {
  return useQuery({
    queryKey: loreKeys.threads,
    queryFn: () => unwrap(api.GET('/api/threads')),
  })
}

export function useFavorites() {
  return useQuery({
    queryKey: loreKeys.favorites,
    queryFn: () => unwrap(api.GET('/api/favorites')),
  })
}

export function usePath(from: number, to: number | null) {
  return useQuery({
    queryKey: loreKeys.path(from, to ?? 0),
    queryFn: () =>
      unwrap(
        api.GET('/api/graph/path', {
          params: { query: { a: from, b: to ?? 0 } },
        })
      ),
    enabled: to !== null && to > 0 && to !== from,
  })
}

export function useLanguageViews(enabled = true) {
  return useQuery({
    queryKey: loreKeys.languages,
    queryFn: () => unwrap(api.GET('/api/languages')),
    enabled,
  })
}

export function useLanguageTree() {
  return useQuery({
    queryKey: loreKeys.languageTree,
    queryFn: () => unwrap(api.GET('/api/languages/tree')),
  })
}

export function useEntityOpportunities(id: number, enabled = true) {
  return useQuery({
    queryKey: [...loreKeys.entity(id), 'opportunities'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/opportunities', {
          params: { path: { entity_id: id } },
        })
      ),
    enabled,
  })
}

export function useEntityAgentContext(id: number, enabled: boolean) {
  return useQuery({
    queryKey: [...loreKeys.entity(id), 'agent-context'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/agent-context', {
          params: { path: { entity_id: id } },
        })
      ),
    enabled,
  })
}

export function useEntityDreams(id: number) {
  return useQuery({
    queryKey: [...loreKeys.entity(id), 'dreams'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/dreams', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}
