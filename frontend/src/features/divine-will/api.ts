import {
  type QueryClient,
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { errorFromResponse, unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { READ_ONLY_MESSAGE, isReadOnly } from '@/api/readOnly'
import { UNIVERSE_HEADER, currentUniverse } from '@/api/universeStore'
import { apiUrl } from '@/api/url'
import { WILL_MODE_PERMISSION } from '@/features/team/permissions'
import {
  type ArtifactFormat,
  type ArtifactKind,
  type ArtifactStatus,
  type DivineWillMode,
  type ExportFormat,
  type LibrarySort,
  type WillArtifactPatch,
  type WillPlanStepInput,
  type WillUpload,
} from './types'

const HTTP_OK_MIN = 200
const HTTP_OK_MAX = 300

export const SESSION_PAGE = 12
export const ARTIFACT_PAGE = 24

export type ArtifactFilters = {
  q: string
  kind: ArtifactKind | null
  status: ArtifactStatus | null
  format: ArtifactFormat | null
  language: string | null
  mode: DivineWillMode | null
  tag: string | null
  nodeId: number | null
  sort: LibrarySort | null
}

export const NO_ARTIFACT_FILTERS: ArtifactFilters = {
  q: '',
  kind: null,
  status: null,
  format: null,
  language: null,
  mode: null,
  tag: null,
  nodeId: null,
  sort: null,
}

export const willKeys = {
  session: queryKeys.divineWill.session,
  sessions: [...queryKeys.divineWill.all, 'sessions'] as const,
  pastSession: (id: number) =>
    [...queryKeys.divineWill.all, 'sessions', id] as const,
  cycle: queryKeys.divineWill.cycle,
  modes: [...queryKeys.divineWill.all, 'modes'] as const,
  index: queryKeys.divineWill.index,
  attachment: (id: number) =>
    [...queryKeys.divineWill.all, 'attachment', id] as const,
  artifacts: (filters: ArtifactFilters) =>
    [...queryKeys.divineWill.artifacts, 'list', filters] as const,
  artifact: (id: number) =>
    [...queryKeys.divineWill.artifacts, 'detail', id] as const,
  version: (id: number, version: number) =>
    [
      ...queryKeys.divineWill.artifacts,
      'detail',
      id,
      'version',
      version,
    ] as const,
  diff: (id: number, a: number, b: number) =>
    [...queryKeys.divineWill.artifacts, 'detail', id, 'diff', a, b] as const,
  plan: queryKeys.divineWill.plan,
  forecast: queryKeys.divineWill.forecast,
}

function refreshWill(client: QueryClient) {
  void client.invalidateQueries({ queryKey: queryKeys.divineWill.all })
}

function refreshWorld(client: QueryClient) {
  void client.invalidateQueries({ queryKey: queryKeys.world.all })
  void client.invalidateQueries({ queryKey: queryKeys.ledger.all })
}

export function useWillSession() {
  return useInfiniteQuery({
    queryKey: willKeys.session,
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/divine-will/session', {
          params: { query: { before: pageParam, limit: SESSION_PAGE } },
        })
      ),
    getNextPageParam: (page) =>
      page.has_earlier && page.cycles.length > 0
        ? page.cycles[0].ordinal
        : undefined,
  })
}

export function useWillSessions() {
  return useQuery({
    queryKey: willKeys.sessions,
    queryFn: () => unwrap(api.GET('/api/divine-will/sessions')),
  })
}

export function usePastSession(id: number) {
  return useQuery({
    queryKey: willKeys.pastSession(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/sessions/{session_id}', {
          params: { path: { session_id: id } },
        })
      ),
  })
}

export function useWillCycle(id: number | null) {
  return useQuery({
    queryKey: willKeys.cycle(id ?? -1),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/cycles/{cycle_id}', {
          params: { path: { cycle_id: id ?? -1 } },
        })
      ),
    enabled: id !== null,
  })
}

export function useWillModes() {
  return useQuery({
    queryKey: willKeys.modes,
    queryFn: () => unwrap(api.GET('/api/divine-will/modes')),
    staleTime: Infinity,
  })
}

export function useWillIndex() {
  return useQuery({
    queryKey: willKeys.index,
    queryFn: () => unwrap(api.GET('/api/divine-will/index')),
  })
}

export type CycleRequest = {
  text: string
  mode: DivineWillMode
  attachment_ids: number[]
}

export function useSendCycle(mode: DivineWillMode) {
  const client = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/divine-will/cycles' }],
    permission: WILL_MODE_PERMISSION[mode],
    mutationFn: (body: CycleRequest) =>
      unwrap(api.POST('/api/divine-will/cycles', { body })),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: willKeys.session }),
  })
}

export function useCancelCycle() {
  const client = useQueryClient()
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/divine-will/cycles/{cycle_id}/cancel' },
    ],
    mutationFn: (cycleId: number) =>
      unwrap(
        api.POST('/api/divine-will/cycles/{cycle_id}/cancel', {
          params: { path: { cycle_id: cycleId } },
        })
      ),
    onSuccess: () => refreshWill(client),
  })
}

export function useDecideConfirmation() {
  const client = useQueryClient()
  return useMutation({
    writes: [
      {
        method: 'POST',
        path: '/api/divine-will/confirmations/{confirmation_id}',
      },
    ],
    mutationFn: ({
      id,
      decision,
    }: {
      id: number
      decision: 'approve' | 'decline'
    }) =>
      unwrap(
        api.POST('/api/divine-will/confirmations/{confirmation_id}', {
          params: { path: { confirmation_id: id } },
          body: { decision },
        })
      ),
    onSuccess: () => {
      refreshWill(client)
      refreshWorld(client)
    },
  })
}

export function useResetSession() {
  const client = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/divine-will/session/reset' }],
    mutationFn: () => unwrap(api.POST('/api/divine-will/session/reset')),
    onSuccess: () => refreshWill(client),
  })
}

export function uploadAttachment(
  file: File,
  onProgress: (fraction: number) => void,
  signal: AbortSignal
): Promise<WillUpload> {
  return new Promise((resolve, reject) => {
    if (isReadOnly()) {
      reject(new Error(READ_ONLY_MESSAGE))
      return
    }
    const request = new XMLHttpRequest()
    const form = new FormData()
    form.append('files', file, file.name)
    request.open('POST', apiUrl('/api/divine-will/attachments'))
    const universe = currentUniverse()
    if (universe !== null) request.setRequestHeader(UNIVERSE_HEADER, universe)
    request.responseType = 'json'
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    request.onload = () => {
      const body = request.response as { attachments?: WillUpload[] } | null
      const stored = body?.attachments?.[0]
      if (
        request.status >= HTTP_OK_MIN &&
        request.status < HTTP_OK_MAX &&
        stored
      ) {
        resolve(stored)
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

export function attachmentFileUrl(id: number): string {
  return apiUrl(`/api/divine-will/attachments/${String(id)}/file`)
}

export function useAttachment(id: number | null) {
  return useQuery({
    queryKey: willKeys.attachment(id ?? -1),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/attachments/{attachment_id}', {
          params: { path: { attachment_id: id ?? -1 } },
        })
      ),
    enabled: id !== null,
  })
}

export function useArtifacts(filters: ArtifactFilters) {
  return useInfiniteQuery({
    queryKey: willKeys.artifacts(filters),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/divine-will/artifacts', {
          params: {
            query: {
              q: filters.q.trim() || undefined,
              kind: filters.kind,
              status: filters.status,
              format: filters.format,
              language: filters.language,
              mode: filters.mode,
              tag: filters.tag,
              node_id: filters.nodeId,
              sort: filters.sort,
              offset: pageParam,
              limit: ARTIFACT_PAGE,
            },
          },
        })
      ),
    getNextPageParam: (page) => {
      const next = page.offset + page.items.length
      return next < page.total ? next : undefined
    },
    placeholderData: keepPreviousData,
  })
}

export function useArtifact(id: number) {
  return useQuery({
    queryKey: willKeys.artifact(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/artifacts/{artifact_id}', {
          params: { path: { artifact_id: id } },
        })
      ),
  })
}

export function useArtifactVersion(id: number, version: number | null) {
  return useQuery({
    queryKey: willKeys.version(id, version ?? -1),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/artifacts/{artifact_id}/versions/{version}', {
          params: { path: { artifact_id: id, version: version ?? -1 } },
        })
      ),
    enabled: version !== null,
  })
}

export function useArtifactDiff(
  id: number,
  a: number | null,
  b: number | null
) {
  return useQuery({
    queryKey: willKeys.diff(id, a ?? -1, b ?? -1),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/artifacts/{artifact_id}/diff', {
          params: {
            path: { artifact_id: id },
            query: { a: a ?? -1, b: b ?? -1 },
          },
        })
      ),
    enabled: a !== null && b !== null && a !== b,
  })
}

export function usePatchArtifact(id: number) {
  const client = useQueryClient()
  return useMutation({
    writes: [
      { method: 'PATCH', path: '/api/divine-will/artifacts/{artifact_id}' },
    ],
    mutationFn: (body: WillArtifactPatch) =>
      unwrap(
        api.PATCH('/api/divine-will/artifacts/{artifact_id}', {
          params: { path: { artifact_id: id } },
          body,
        })
      ),
    onSuccess: () =>
      void client.invalidateQueries({
        queryKey: queryKeys.divineWill.artifacts,
      }),
  })
}

export function useDeleteArtifact() {
  const client = useQueryClient()
  return useMutation({
    writes: [
      { method: 'DELETE', path: '/api/divine-will/artifacts/{artifact_id}' },
    ],
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE('/api/divine-will/artifacts/{artifact_id}', {
          params: { path: { artifact_id: id } },
        })
      ),
    onSuccess: () =>
      void client.invalidateQueries({
        queryKey: queryKeys.divineWill.artifacts,
      }),
  })
}

export function artifactExportUrl(
  id: number,
  format: ExportFormat,
  version: number | null
): string {
  return apiUrl(`/api/divine-will/artifacts/${String(id)}/export`, {
    format,
    version,
  })
}

export function usePlan(id: number) {
  return useQuery({
    queryKey: willKeys.plan(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/plans/{plan_id}', {
          params: { path: { plan_id: id } },
        })
      ),
  })
}

function useRefreshPlan(id: number) {
  const client = useQueryClient()
  return () => {
    void client.invalidateQueries({ queryKey: willKeys.plan(id) })
    void client.invalidateQueries({ queryKey: willKeys.session })
    void client.invalidateQueries({ queryKey: queryKeys.divineWill.artifacts })
    refreshWorld(client)
  }
}

export type PlanVerb = 'approve' | 'execute' | 'pause' | 'resume' | 'abandon'
export type StepVerb = 'skip' | 'undo'

export function useSavePlanSteps(id: number) {
  const refresh = useRefreshPlan(id)
  return useMutation({
    writes: [{ method: 'PUT', path: '/api/divine-will/plans/{plan_id}/steps' }],
    mutationFn: ({
      steps,
      title,
    }: {
      steps: WillPlanStepInput[]
      title: string
    }) =>
      unwrap(
        api.PUT('/api/divine-will/plans/{plan_id}/steps', {
          params: { path: { plan_id: id } },
          body: { steps, title },
        })
      ),
    onSuccess: refresh,
  })
}

function planCommand(id: number, verb: PlanVerb) {
  const params = { params: { path: { plan_id: id } } }
  switch (verb) {
    case 'approve':
      return api.POST('/api/divine-will/plans/{plan_id}/approve', params)
    case 'execute':
      return api.POST('/api/divine-will/plans/{plan_id}/execute', params)
    case 'pause':
      return api.POST('/api/divine-will/plans/{plan_id}/pause', params)
    case 'resume':
      return api.POST('/api/divine-will/plans/{plan_id}/resume', params)
    case 'abandon':
      return api.POST('/api/divine-will/plans/{plan_id}/abandon', params)
  }
}

export function usePlanCommand(id: number) {
  const refresh = useRefreshPlan(id)
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/divine-will/plans/{plan_id}/abandon' },
      { method: 'POST', path: '/api/divine-will/plans/{plan_id}/approve' },
      { method: 'POST', path: '/api/divine-will/plans/{plan_id}/execute' },
      { method: 'POST', path: '/api/divine-will/plans/{plan_id}/pause' },
      { method: 'POST', path: '/api/divine-will/plans/{plan_id}/resume' },
    ],
    mutationFn: (verb: PlanVerb) => unwrap(planCommand(id, verb)),
    onSuccess: refresh,
  })
}

export function useStepCommand(id: number) {
  const refresh = useRefreshPlan(id)
  return useMutation({
    writes: [
      {
        method: 'POST',
        path: '/api/divine-will/plans/{plan_id}/steps/{ordinal}/skip',
      },
      {
        method: 'POST',
        path: '/api/divine-will/plans/{plan_id}/steps/{ordinal}/undo',
      },
    ],
    mutationFn: ({ ordinal, verb }: { ordinal: number; verb: StepVerb }) => {
      const params = { params: { path: { plan_id: id, ordinal } } }
      return unwrap(
        verb === 'skip'
          ? api.POST(
              '/api/divine-will/plans/{plan_id}/steps/{ordinal}/skip',
              params
            )
          : api.POST(
              '/api/divine-will/plans/{plan_id}/steps/{ordinal}/undo',
              params
            )
      )
    },
    onSuccess: refresh,
  })
}

export function useForecast(id: number) {
  return useQuery({
    queryKey: willKeys.forecast(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/divine-will/forecasts/{forecast_id}', {
          params: { path: { forecast_id: id } },
        })
      ),
  })
}

export function useCancelForecast(id: number) {
  const client = useQueryClient()
  return useMutation({
    writes: [
      {
        method: 'POST',
        path: '/api/divine-will/forecasts/{forecast_id}/cancel',
      },
    ],
    mutationFn: () =>
      unwrap(
        api.POST('/api/divine-will/forecasts/{forecast_id}/cancel', {
          params: { path: { forecast_id: id } },
        })
      ),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: willKeys.forecast(id) }),
  })
}
