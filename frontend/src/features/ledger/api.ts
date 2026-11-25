import {
  type QueryClient,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { type Permission } from '@/api/teamGate'
import { useTeamContext } from '@/features/team/teamContext'

export type LedgerPage = components['schemas']['LedgerPage']
export type LedgerEntryView = components['schemas']['LedgerEntryView']
export type UndoResult = components['schemas']['UndoResult']
export type UndoOutcome = UndoResult | components['schemas']['QueuedActView']
export type EntityNoteRecord = components['schemas']['EntityNoteRecord']
export type ActorKind = components['schemas']['ActorKind']
export type EntitySummary = components['schemas']['EntitySummary']
export type FavoriteCard = components['schemas']['FavoriteCard']

export type ActionKind = components['schemas']['ActionKind']

export type LedgerQuery = {
  epoch: number | null
  actorKind: ActorKind | null
  actorId: number | null
  limit: number | null
  authorId: number | null
  actionKind: ActionKind | null
  since: string | null
  until: string | null
}

export const ledgerKeys = {
  page: (query: LedgerQuery) =>
    [...queryKeys.ledger.all, 'page', query] as const,
  favorites: [...queryKeys.world.all, 'favorites'] as const,
  board: [...queryKeys.world.all, 'favorites', 'board'] as const,
  notes: [...queryKeys.world.all, 'notes'] as const,
}

export function useLedger(query: LedgerQuery) {
  return useQuery({
    queryKey: ledgerKeys.page(query),
    queryFn: () =>
      unwrap(
        api.GET('/api/ledger', {
          params: {
            query: {
              epoch: query.epoch ?? undefined,
              actor_kind: query.actorKind ?? undefined,
              actor_id: query.actorId ?? undefined,
              limit: query.limit ?? undefined,
              author_account_id: query.authorId ?? undefined,
              action_kind: query.actionKind ?? undefined,
              since: query.since ?? undefined,
              until: query.until ?? undefined,
            },
          },
        })
      ),
    placeholderData: (previous) => previous,
  })
}

export function refreshAfterUndo(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.ledger.all })
  void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
}

export function undoEntry(entryId: number): Promise<UndoOutcome> {
  return unwrap(
    api.POST('/api/ledger/{entry_id}/undo', {
      params: { path: { entry_id: entryId } },
    })
  )
}

export function isUndone(outcome: UndoOutcome): outcome is UndoResult {
  return 'entry_id' in outcome
}

export function undoPermission(
  authorId: number | null | undefined,
  me: number | null
): Permission {
  return authorId !== null && authorId !== undefined && authorId === me
    ? 'undo_own'
    : 'undo_any'
}

export function useUndo(authorId: number | null | undefined) {
  const queryClient = useQueryClient()
  const me = useTeamContext()?.me ?? null
  return useMutation({
    writes: [{ method: 'POST', path: '/api/ledger/{entry_id}/undo' }],
    permission: undoPermission(authorId, me),
    mutationFn: undoEntry,
    onSuccess: () => refreshAfterUndo(queryClient),
  })
}

export function useFavorites() {
  return useQuery({
    queryKey: ledgerKeys.favorites,
    queryFn: () => unwrap(api.GET('/api/favorites')),
  })
}

export function useFavoriteBoard() {
  return useQuery({
    queryKey: ledgerKeys.board,
    queryFn: () => unwrap(api.GET('/api/favorites/board')),
  })
}

export function setFavorite(entityId: number, favorite: boolean) {
  return unwrap(
    api.PUT('/api/entities/{entity_id}/favorite', {
      params: { path: { entity_id: entityId } },
      body: { favorite },
    })
  )
}

export function useEnumCatalogue() {
  return useQuery({
    queryKey: [...queryKeys.catalogue.all, 'enums'] as const,
    queryFn: () => unwrap(api.GET('/api/catalogue/enums')),
    staleTime: Infinity,
  })
}

export function useNotes() {
  return useQuery({
    queryKey: ledgerKeys.notes,
    queryFn: () => unwrap(api.GET('/api/notes')),
  })
}
