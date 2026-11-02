import { useState } from 'react'
import {
  type QueryClient,
  type QueryKey,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { type ActionResponse } from './api'

const UNDONE_MESSAGE = 'Undone'

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
    toast.error(error instanceof Error ? error.message : String(error))
  }
}

type GodActionOptions<TVariables, TResult> = {
  run: (variables: TVariables) => Promise<TResult>
  success?: string | ((result: TResult, variables: TVariables) => string)
  invalidate?: QueryKey[]
  onDone?: (result: TResult, variables: TVariables) => void
}

function responseOf(result: unknown): Partial<ActionResponse> {
  return result && typeof result === 'object'
    ? (result as Partial<ActionResponse>)
    : {}
}

export function useGodAction<TVariables = void, TResult = ActionResponse>(
  options: GodActionOptions<TVariables, TResult>
) {
  const queryClient = useQueryClient()
  const [jobId, setJobId] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: options.run,
    onSuccess: (result, variables) => {
      const response = responseOf(result)
      const message =
        typeof options.success === 'function'
          ? options.success(result, variables)
          : (options.success ?? response.message ?? 'Done')
      const entry = response.ledger_entry_id
      toast.success(message, {
        action:
          typeof entry === 'number'
            ? {
                label: 'Undo',
                onClick: () => void undoLedgerEntry(queryClient, entry),
              }
            : undefined,
      })
      if (response.job_id) setJobId(response.job_id)
      refreshWorld(queryClient, options.invalidate)
      options.onDone?.(result, variables)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : String(error))
    },
  })
  return { ...mutation, jobId, clearJob: () => setJobId(null) }
}
