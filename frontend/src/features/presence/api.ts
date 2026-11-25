import {
  type QueryClient,
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { ApiError, unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import {
  type PresenceGuise,
  type PresenceRecord,
  type PresenceSessionView,
  type SpeakerGroup,
} from './types'

export const SPEAKER_PAGE = 24

const HTTP_NOT_FOUND = 404
const SPEAKER_RETRIES = 2
const RUNNING_POLL_MS = 4000

export type SpeakerFilters = {
  q: string
  group: SpeakerGroup | null
  dead: boolean
}

export const presenceKeys = {
  speakers: (filters: SpeakerFilters) =>
    [...queryKeys.presence.all, 'speakers', filters] as const,
  speaker: (nodeId: number) =>
    [...queryKeys.presence.all, 'speaker', nodeId] as const,
  session: (id: number) => [...queryKeys.presence.all, 'session', id] as const,
}

function refreshPresence(client: QueryClient) {
  void client.invalidateQueries({ queryKey: queryKeys.presence.all })
}

function refreshWorld(client: QueryClient) {
  void client.invalidateQueries({ queryKey: queryKeys.world.all })
  void client.invalidateQueries({ queryKey: queryKeys.ledger.all })
}

export function isNotSpeaker(error: unknown): boolean {
  return error instanceof ApiError && error.status === HTTP_NOT_FOUND
}

export function useSpeakers(filters: SpeakerFilters) {
  return useInfiniteQuery({
    queryKey: presenceKeys.speakers(filters),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/presence/speakers', {
          params: {
            query: {
              q: filters.q.trim() || undefined,
              group: filters.group,
              dead: filters.dead,
              offset: pageParam,
              limit: SPEAKER_PAGE,
            },
          },
        })
      ),
    getNextPageParam: (page) =>
      page.has_more ? page.offset + page.speakers.length : undefined,
    placeholderData: keepPreviousData,
  })
}

export function useSpeaker(nodeId: number | null) {
  return useQuery({
    queryKey: presenceKeys.speaker(nodeId ?? -1),
    queryFn: () =>
      unwrap(
        api.GET('/api/presence/speakers/{node_id}', {
          params: { path: { node_id: nodeId ?? -1 } },
        })
      ),
    enabled: nodeId !== null,
    retry: (failures, error) =>
      !isNotSpeaker(error) && failures < SPEAKER_RETRIES,
  })
}

function isRunning(view: PresenceSessionView | undefined): boolean {
  return view !== undefined && view.running_exchange_id !== null
}

export function useSession(id: number) {
  return useQuery({
    queryKey: presenceKeys.session(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/presence/sessions/{session_id}', {
          params: { path: { session_id: id } },
        })
      ),
    refetchInterval: (query) =>
      isRunning(query.state.data) ? RUNNING_POLL_MS : false,
  })
}

export type OpenRequest = {
  node_id: number
  guise: PresenceGuise
  record: PresenceRecord
}

export function useOpenSession() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: OpenRequest) =>
      unwrap(api.POST('/api/presence/sessions', { body })),
    onSuccess: (view) => {
      client.setQueryData(presenceKeys.session(view.session.id), view)
      refreshPresence(client)
    },
  })
}

export function useSendExchange(sessionId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (text: string) =>
      unwrap(
        api.POST('/api/presence/sessions/{session_id}/exchanges', {
          params: { path: { session_id: sessionId } },
          body: { text },
        })
      ),
    onSuccess: (accepted) =>
      void client.invalidateQueries({
        queryKey: presenceKeys.session(accepted.session_id),
      }),
  })
}

export function useCancelExchange() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (exchangeId: number) =>
      unwrap(
        api.POST('/api/presence/exchanges/{exchange_id}/cancel', {
          params: { path: { exchange_id: exchangeId } },
        })
      ),
    onSuccess: () => {
      refreshPresence(client)
      refreshWorld(client)
    },
  })
}

export function useCloseSession() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: number) =>
      unwrap(
        api.POST('/api/presence/sessions/{session_id}/close', {
          params: { path: { session_id: sessionId } },
        })
      ),
    onSuccess: () => refreshPresence(client),
  })
}
