import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'

export type NotificationList = components['schemas']['NotificationList']
export type NotificationRecord = components['schemas']['NotificationRecord']
export type NotificationCategory = components['schemas']['NotificationCategory']
export type MarkReadRequest = components['schemas']['MarkReadRequest']

export type NotificationQuery = {
  category: NotificationCategory | null
  unreadOnly: boolean
  limit: number | null
  before: number | null
  exclude?: NotificationCategory[]
}

export const notificationKeys = {
  list: (query: NotificationQuery) =>
    [...queryKeys.notifications.all, 'list', query] as const,
  feed: (
    category: NotificationCategory | null,
    unreadOnly: boolean,
    exclude: NotificationCategory[]
  ) =>
    [
      ...queryKeys.notifications.all,
      'feed',
      category,
      unreadOnly,
      exclude.join(','),
    ] as const,
}

function fetchNotifications(
  query: NotificationQuery
): Promise<NotificationList> {
  return unwrap(
    api.GET('/api/notifications', {
      params: {
        query: {
          category: query.category ?? undefined,
          unread_only: query.unreadOnly,
          limit: query.limit ?? undefined,
          before: query.before ?? undefined,
          exclude: query.exclude?.length ? query.exclude : undefined,
        },
      },
    })
  )
}

export function useNotifications(query: NotificationQuery) {
  return useQuery({
    queryKey: notificationKeys.list(query),
    placeholderData: keepPreviousData,
    queryFn: () => fetchNotifications(query),
  })
}

export function useNotificationPages(
  category: NotificationCategory | null,
  unreadOnly: boolean,
  pageSize: number,
  exclude: NotificationCategory[] = []
) {
  return useInfiniteQuery({
    queryKey: [
      ...notificationKeys.feed(category, unreadOnly, exclude),
      pageSize,
    ],
    placeholderData: keepPreviousData,
    queryFn: ({ pageParam }) =>
      fetchNotifications({
        category,
        unreadOnly,
        limit: pageSize,
        before: pageParam,
        exclude,
      }),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => {
      const lastItem = last.items.at(-1)
      if (!lastItem || last.items.length < pageSize) return undefined
      return lastItem.id
    },
  })
}

function useRefresh() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notifications.all,
    })
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
  }
}

export function useMarkRead() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/notifications/read' }],
    mutationFn: (body: MarkReadRequest) =>
      unwrap(api.POST('/api/notifications/read', { body })),
    onSuccess: refresh,
  })
}

export function useAddNote() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/notifications' }],
    mutationFn: (body: { title: string; body: string | null }) =>
      unwrap(api.POST('/api/notifications', { body })),
    onSuccess: refresh,
  })
}

export function useSaveNotificationSettings() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'PUT', path: '/api/notifications/settings' }],
    mutationFn: (body: Partial<Record<NotificationCategory, boolean>>) =>
      unwrap(api.PUT('/api/notifications/settings', { body })),
    onSuccess: refresh,
  })
}
