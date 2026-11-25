import { useEffect, useState } from 'react'
import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
} from '@tanstack/react-query'
import { type EventSourceLike } from '@/realtime/eventStream'
import { api } from '@/api/client'
import { errorFromResponse, unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { dropQueryClient, libraryQueryClient } from '@/api/queryClients'
import { UNIVERSE_HEADER, UNIVERSE_PARAM } from '@/api/universeStore'
import { apiUrl, typedPath } from '@/api/url'
import {
  type ImportStarted,
  type ImportUploadField,
  type LibraryJob,
  type LibraryJobKind,
  type UniverseDetail,
  type UniverseDraft,
  type UniverseEdit,
  type UniverseFilters,
  type UniverseSummary,
  libraryStreamKindValues,
} from './types'

export const LIBRARY_PAGE = 24
export const SHELF_REACH = 200
const EVENTS_PAGE = 8
const TRASH_PAGE = 24
const JOB_POLL_MS = 900
const STREAM_SETTLE_MS = 400
const HTTP_OK_MIN = 200
const HTTP_OK_MAX = 300
const UPLOAD_FIELD: ImportUploadField = 'file'
const LIBRARY_STREAM = '/api/library/events/stream'

type LibraryStreamEvent = components['schemas']['LibraryStreamEvent']

export const NO_UNIVERSE_FILTERS: UniverseFilters = {
  q: '',
  status: 'active',
  origin: null,
  tag: null,
  sort: 'opened',
}

export type JobRoute = 'exports' | 'imports'

const LIBRARY_KEY = ['library'] as const

export const libraryKeys = {
  all: LIBRARY_KEY,
  universes: (filters: UniverseFilters) =>
    [...LIBRARY_KEY, 'universes', filters] as const,
  shelf: [...LIBRARY_KEY, 'shelf'] as const,
  archived: [...LIBRARY_KEY, 'archived-count'] as const,
  universe: (id: string) => [...LIBRARY_KEY, 'universe', id] as const,
  events: [...LIBRARY_KEY, 'events'] as const,
  trash: [...LIBRARY_KEY, 'trash'] as const,
  jobs: [...LIBRARY_KEY, 'jobs'] as const,
  job: (route: JobRoute, id: string) =>
    [...LIBRARY_KEY, 'job', route, id] as const,
  images: (id: string) => [...LIBRARY_KEY, 'images', id] as const,
  coverPrompt: (id: string) => [...LIBRARY_KEY, 'cover-prompt', id] as const,
  imageModel: (id: string) => [...LIBRARY_KEY, 'image-model', id] as const,
}

export function jobRoute(kind: LibraryJobKind): JobRoute {
  return kind === 'export' ? 'exports' : 'imports'
}

function refreshLibrary(): Promise<void> {
  return libraryQueryClient.invalidateQueries({ queryKey: libraryKeys.all })
}

function nextOffset(last: {
  offset: number
  total: number
  items: unknown[]
}): number | undefined {
  const next = last.offset + last.items.length
  return next < last.total ? next : undefined
}

export function coverUrl(universe: UniverseSummary): string | null {
  if (!universe.cover_path) return null
  return apiUrl(
    typedPath('/api/library/universes/{universe_id}/cover', {
      universe_id: universe.id,
    }),
    { v: universe.updated_at }
  )
}

export function exportFileUrl(jobId: string): string {
  return apiUrl(
    typedPath('/api/library/exports/{job_id}/file', { job_id: jobId })
  )
}

export function universeMediaUrl(universeId: string, fileName: string): string {
  return apiUrl(typedPath('/api/media/{file_name}', { file_name: fileName }), {
    w: 320,
    [UNIVERSE_PARAM]: universeId,
  })
}

export function useUniverses(filters: UniverseFilters) {
  return useInfiniteQuery(
    {
      queryKey: libraryKeys.universes(filters),
      queryFn: ({ pageParam }) =>
        unwrap(
          api.GET('/api/library/universes', {
            params: {
              query: {
                q: filters.q.trim() || undefined,
                status: filters.status,
                include_archived: filters.status === null,
                origin: filters.origin,
                tag: filters.tag,
                sort: filters.sort,
                offset: pageParam,
                limit: LIBRARY_PAGE,
              },
            },
          })
        ),
      initialPageParam: 0,
      getNextPageParam: nextOffset,
      placeholderData: keepPreviousData,
    },
    libraryQueryClient
  )
}

export function useShelf() {
  return useQuery(
    {
      queryKey: libraryKeys.shelf,
      queryFn: () =>
        unwrap(
          api.GET('/api/library/universes', {
            params: {
              query: { status: 'active', sort: 'opened', limit: SHELF_REACH },
            },
          })
        ),
    },
    libraryQueryClient
  )
}

export function useArchivedCount() {
  return useQuery(
    {
      queryKey: libraryKeys.archived,
      queryFn: async () =>
        (
          await unwrap(
            api.GET('/api/library/universes', {
              params: { query: { status: 'archived', limit: 1 } },
            })
          )
        ).total,
    },
    libraryQueryClient
  )
}

export function useUniverse(id: string | null) {
  return useQuery(
    {
      queryKey: libraryKeys.universe(id ?? ''),
      queryFn: () =>
        unwrap(
          api.GET('/api/library/universes/{universe_id}', {
            params: { path: { universe_id: id ?? '' } },
          })
        ),
      enabled: id !== null,
    },
    libraryQueryClient
  )
}

export function useLibraryEvents() {
  return useInfiniteQuery(
    {
      queryKey: libraryKeys.events,
      queryFn: ({ pageParam }) =>
        unwrap(
          api.GET('/api/library/events', {
            params: { query: { offset: pageParam, limit: EVENTS_PAGE } },
          })
        ),
      initialPageParam: 0,
      getNextPageParam: nextOffset,
    },
    libraryQueryClient
  )
}

export function useTrash() {
  return useInfiniteQuery(
    {
      queryKey: libraryKeys.trash,
      queryFn: ({ pageParam }) =>
        unwrap(
          api.GET('/api/library/trash', {
            params: { query: { offset: pageParam, limit: TRASH_PAGE } },
          })
        ),
      initialPageParam: 0,
      getNextPageParam: nextOffset,
    },
    libraryQueryClient
  )
}

export function useLibraryJobs() {
  return useQuery(
    {
      queryKey: libraryKeys.jobs,
      queryFn: () => unwrap(api.GET('/api/library/jobs')),
      refetchInterval: (query) =>
        (query.state.data ?? []).some((job) => job.status === 'running')
          ? JOB_POLL_MS
          : false,
    },
    libraryQueryClient
  )
}

export function useUniverseImages(universeId: string | null) {
  return useQuery(
    {
      queryKey: libraryKeys.images(universeId ?? ''),
      queryFn: () =>
        unwrap(
          api.GET('/api/images', {
            headers: { [UNIVERSE_HEADER]: universeId ?? '' },
          })
        ),
      enabled: universeId !== null,
    },
    libraryQueryClient
  )
}

function libraryMutation<A, R>(
  run: (args: A) => Promise<R>,
  after: (result: R, args: A) => void = () => undefined
) {
  return {
    mutationFn: run,
    onSuccess: (result: R, args: A) => {
      after(result, args)
      return refreshLibrary()
    },
  }
}

export function useCreateUniverse() {
  return useMutation(
    libraryMutation((draft: UniverseDraft) =>
      unwrap(api.POST('/api/library/universes', { body: draft }))
    ),
    libraryQueryClient
  )
}

export function useEditUniverse() {
  return useMutation(
    libraryMutation(({ id, edit }: { id: string; edit: UniverseEdit }) =>
      unwrap(
        api.PATCH('/api/library/universes/{universe_id}', {
          params: { path: { universe_id: id } },
          body: edit,
        })
      )
    ),
    libraryQueryClient
  )
}

export function useOpenUniverse() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.POST('/api/library/universes/{universe_id}/open', {
          params: { path: { universe_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useCloseUniverse() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.POST('/api/library/universes/{universe_id}/close', {
          params: { path: { universe_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useDuplicateUniverse() {
  return useMutation(
    libraryMutation(({ id, name }: { id: string; name: string }) =>
      unwrap(
        api.POST('/api/library/universes/{universe_id}/duplicate', {
          params: { path: { universe_id: id } },
          body: { name },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useArchiveUniverse() {
  return useMutation(
    libraryMutation(
      ({ id, archive }: { id: string; archive: boolean }) =>
        unwrap(
          archive
            ? api.POST('/api/library/universes/{universe_id}/archive', {
                params: { path: { universe_id: id } },
              })
            : api.POST('/api/library/universes/{universe_id}/restore', {
                params: { path: { universe_id: id } },
              })
        ),
      (_, { id, archive }) => {
        if (archive) dropQueryClient(id)
      }
    ),
    libraryQueryClient
  )
}

export function useDeleteUniverse() {
  return useMutation(
    libraryMutation(
      (id: string) =>
        unwrap(
          api.DELETE('/api/library/universes/{universe_id}', {
            params: { path: { universe_id: id } },
          })
        ),
      (_, id) => dropQueryClient(id)
    ),
    libraryQueryClient
  )
}

export function useRestoreTrash() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.POST('/api/library/trash/{entry_id}/restore', {
          params: { path: { entry_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function usePurgeTrash() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.DELETE('/api/library/trash/{entry_id}', {
          params: { path: { entry_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useEmptyTrash() {
  return useMutation(
    libraryMutation(() => unwrap(api.DELETE('/api/library/trash'))),
    libraryQueryClient
  )
}

export function useSetCover() {
  return useMutation(
    libraryMutation(({ id, file }: { id: string; file: File }) =>
      unwrap(
        api.PUT('/api/library/universes/{universe_id}/cover', {
          params: { path: { universe_id: id } },
          body: { file: '' },
          bodySerializer: () => {
            const form = new FormData()
            form.append(UPLOAD_FIELD, file, file.name)
            return form
          },
        })
      )
    ),
    libraryQueryClient
  )
}

const COVER_FILE = 'painted-cover.png'

export function useCoverPrompt(universeId: string) {
  return useQuery(
    {
      queryKey: libraryKeys.coverPrompt(universeId),
      queryFn: () =>
        unwrap(
          api.GET('/api/library/universes/{universe_id}/cover/paint', {
            params: { path: { universe_id: universeId } },
          })
        ),
      staleTime: Number.POSITIVE_INFINITY,
    },
    libraryQueryClient
  )
}

export function useUniverseImageModel(universeId: string) {
  return useQuery(
    {
      queryKey: libraryKeys.imageModel(universeId),
      queryFn: () =>
        unwrap(
          api.GET('/api/image-gen', {
            headers: { [UNIVERSE_HEADER]: universeId },
          })
        ),
    },
    libraryQueryClient
  )
}

export function usePaintCover() {
  return useMutation(
    {
      mutationFn: async ({ id, prompt }: { id: string; prompt: string }) => {
        const painted = await unwrap(
          api.POST('/api/library/universes/{universe_id}/cover/paint', {
            params: { path: { universe_id: id } },
            body: { prompt },
            parseAs: 'blob',
          })
        )
        return new File([painted], COVER_FILE, { type: painted.type })
      },
    },
    libraryQueryClient
  )
}

export function useCoverFromMedia() {
  return useMutation(
    libraryMutation(({ id, fileName }: { id: string; fileName: string }) =>
      unwrap(
        api.PUT('/api/library/universes/{universe_id}/cover/from-media', {
          params: { path: { universe_id: id } },
          body: { file_name: fileName },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useClearCover() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.DELETE('/api/library/universes/{universe_id}/cover', {
          params: { path: { universe_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useStartExport() {
  return useMutation(
    libraryMutation((id: string) =>
      unwrap(
        api.POST('/api/library/universes/{universe_id}/export', {
          params: { path: { universe_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useStopJob() {
  return useMutation(
    libraryMutation(
      (job: Pick<LibraryJob, 'id' | 'kind' | 'status'>) =>
        unwrap(
          job.kind === 'export'
            ? api.DELETE('/api/library/exports/{job_id}', {
                params: { path: { job_id: job.id } },
              })
            : api.DELETE('/api/library/imports/{job_id}', {
                params: { path: { job_id: job.id } },
              })
        ),
      (_result, job) => {
        if (!jobSettled(job)) return
        libraryQueryClient.setQueryData<LibraryJob[]>(
          libraryKeys.jobs,
          (held) => held?.filter((item) => item.id !== job.id)
        )
        libraryQueryClient.removeQueries({
          queryKey: libraryKeys.job(jobRoute(job.kind), job.id),
        })
      }
    ),
    libraryQueryClient
  )
}

export function jobSettled(
  job: Pick<LibraryJob, 'status'> | undefined
): boolean {
  return (
    job?.status === 'done' ||
    job?.status === 'failed' ||
    job?.status === 'cancelled'
  )
}

export function useLibraryJob(route: JobRoute, id: string | null) {
  return useQuery(
    {
      queryKey: libraryKeys.job(route, id ?? ''),
      queryFn: () =>
        unwrap(
          route === 'exports'
            ? api.GET('/api/library/exports/{job_id}', {
                params: { path: { job_id: id ?? '' } },
              })
            : api.GET('/api/library/imports/{job_id}', {
                params: { path: { job_id: id ?? '' } },
              })
        ),
      enabled: id !== null,
      refetchInterval: (query) =>
        query.state.data?.status === 'running' || query.state.data === undefined
          ? JOB_POLL_MS
          : false,
    },
    libraryQueryClient
  )
}

export function useConfirmImport() {
  return useMutation(
    libraryMutation(
      ({ jobId, name }: { jobId: string; name: string }) =>
        unwrap(
          api.POST('/api/library/imports/{job_id}/confirm', {
            params: { path: { job_id: jobId } },
            body: { name },
          })
        ),
      (job) =>
        libraryQueryClient.setQueryData(libraryKeys.job('imports', job.id), job)
    ),
    libraryQueryClient
  )
}

export function cancelImport(jobId: string): Promise<LibraryJob | null> {
  return unwrap(
    api.DELETE('/api/library/imports/{job_id}', {
      params: { path: { job_id: jobId } },
    })
  ).catch(() => null)
}

export function uploadUniverse(
  file: File,
  onProgress: (fraction: number) => void,
  signal: AbortSignal
): Promise<ImportStarted> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    const form = new FormData()
    form.append(UPLOAD_FIELD, file, file.name)
    request.open('POST', apiUrl('/api/library/imports'))
    request.responseType = 'json'
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    request.onload = () => {
      const body = request.response as ImportStarted | null
      if (
        request.status >= HTTP_OK_MIN &&
        request.status < HTTP_OK_MAX &&
        body
      ) {
        void refreshLibrary()
        resolve(body)
        return
      }
      reject(
        errorFromResponse(new Response(null, { status: request.status }), body)
      )
    }
    request.onerror = () => reject(errorFromResponse(undefined, null))
    request.onabort = () => reject(new DOMException('Aborted', 'AbortError'))
    signal.addEventListener('abort', () => request.abort())
    request.send(form)
  })
}

function openEventSource(url: string): EventSourceLike {
  return new EventSource(url) as EventSourceLike
}

function parsedNotice(data: string): LibraryStreamEvent | null {
  try {
    return JSON.parse(data) as LibraryStreamEvent
  } catch {
    return null
  }
}

export type LibraryPulse = { id: number; at: string } | null

export function useLibraryStream(
  createSource: (url: string) => EventSourceLike = openEventSource
): LibraryPulse {
  const [pulse, setPulse] = useState<LibraryPulse>(null)
  useEffect(() => {
    const source = createSource(apiUrl(LIBRARY_STREAM))
    let timer: ReturnType<typeof setTimeout> | null = null
    const settle = () => {
      if (timer !== null) return
      timer = setTimeout(() => {
        timer = null
        void refreshLibrary()
      }, STREAM_SETTLE_MS)
    }
    const receive = (message: MessageEvent<string>) => {
      const notice = parsedNotice(message.data)
      if (notice === null) return
      setPulse({ id: notice.id, at: notice.at })
      if (notice.job !== null)
        libraryQueryClient.setQueryData(
          libraryKeys.job(jobRoute(notice.job.kind), notice.job.id),
          notice.job
        )
      if (notice.universe !== null && notice.universe_id !== null)
        libraryQueryClient.setQueryData(
          libraryKeys.universe(notice.universe_id),
          (known: UniverseDetail | undefined) =>
            known ? { ...known, ...notice.universe } : known
        )
      if (notice.kind !== 'hello') settle()
    }
    source.onmessage = receive
    for (const kind of libraryStreamKindValues)
      source.addEventListener(kind, receive)
    return () => {
      if (timer !== null) clearTimeout(timer)
      source.close()
    }
  }, [createSource])
  return pulse
}
