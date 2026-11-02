import { useState } from 'react'
import {
  type QueryClient,
  type QueryKey,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { fetchJob, fetchJobs } from '@/api/system'
import { TERMINAL_JOB_STATUSES, isJobStatus } from '@/constants/jobs'
import { type ActionResponse } from './types'

export const ACTIVE_JOB_LIMIT = 50
const UNDO_LABEL = 'Undo'
const UNDONE_MESSAGE = 'Undone'
const DONE_MESSAGE = 'Done'

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function refreshWorld(queryClient: QueryClient, extra: QueryKey[] = []) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
  void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
  for (const queryKey of extra) void queryClient.invalidateQueries({ queryKey })
}

export async function undoLedgerEntry(
  queryClient: QueryClient,
  entryId: number
): Promise<void> {
  try {
    await unwrap(
      api.POST('/api/ledger/{entry_id}/undo', {
        params: { path: { entry_id: entryId } },
      })
    )
    toast.success(UNDONE_MESSAGE)
    refreshWorld(queryClient)
  } catch (error) {
    toast.error(errorText(error))
  }
}

export function deleteEntityNote(entityId: number): Promise<ActionResponse> {
  return unwrap(
    api.DELETE('/api/entities/{entity_id}/note', {
      params: { path: { entity_id: entityId } },
    })
  )
}

function responseOf(result: unknown): Partial<ActionResponse> {
  return result && typeof result === 'object'
    ? (result as Partial<ActionResponse>)
    : {}
}

type LoreMutationOptions<TVariables, TResult> = {
  run: (variables: TVariables) => Promise<TResult>
  success?: string | ((result: TResult, variables: TVariables) => string)
  invalidate?: QueryKey[]
  quiet?: boolean
  onDone?: (result: TResult, variables: TVariables) => void
}

export function useLoreMutation<TVariables = void, TResult = ActionResponse>(
  options: LoreMutationOptions<TVariables, TResult>
) {
  const queryClient = useQueryClient()
  const [jobId, setJobId] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: options.run,
    onSuccess: (result, variables) => {
      const response = responseOf(result)
      if (!options.quiet) {
        const message =
          typeof options.success === 'function'
            ? options.success(result, variables)
            : (options.success ?? response.message ?? DONE_MESSAGE)
        const entry = response.ledger_entry_id
        toast.success(message, {
          action:
            typeof entry === 'number'
              ? {
                  label: UNDO_LABEL,
                  onClick: () => void undoLedgerEntry(queryClient, entry),
                }
              : undefined,
        })
      }
      if (response.job_id) setJobId(response.job_id)
      refreshWorld(queryClient, options.invalidate)
      options.onDone?.(result, variables)
    },
    onError: (error) => {
      toast.error(errorText(error))
    },
  })
  return { ...mutation, jobId, clearJob: () => setJobId(null) }
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: queryKeys.jobs.detail(jobId ?? ''),
    queryFn: () => fetchJob(jobId ?? ''),
    enabled: jobId !== null,
  })
}

export function useActiveJobs() {
  return useQuery({
    queryKey: queryKeys.jobs.list(ACTIVE_JOB_LIMIT),
    queryFn: () => fetchJobs(ACTIVE_JOB_LIMIT),
  })
}

export function isJobActive(status: string): boolean {
  return isJobStatus(status) && !TERMINAL_JOB_STATUSES.has(status)
}

export function useRunningJob(kind: string, param: string, value: unknown) {
  const jobs = useActiveJobs()
  return (jobs.data ?? []).find(
    (job) =>
      job.kind === kind &&
      isJobActive(job.status) &&
      job.params[param] === value
  )
}
