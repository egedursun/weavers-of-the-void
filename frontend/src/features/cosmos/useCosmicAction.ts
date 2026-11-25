import { useCallback, useState } from 'react'
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { undoLedgerEntry } from '@/features/pantheon/godAction'
import { announceWaiting } from '@/features/team/outcome'
import { type WriteTarget } from '@/features/team/writeGate'
import { type ActionResponse, useCosmosState } from './api'

const UNDO_LABEL = 'Undo'

function refresh(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
  void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
}

type CosmicActionOptions<TVariables> = {
  run: (variables: TVariables) => Promise<ActionResponse>
  writes?: readonly WriteTarget[]
  success?:
    string | ((response: ActionResponse, variables: TVariables) => string)
  onDone?: (response: ActionResponse, variables: TVariables) => void
}

export function useCosmicAction<TVariables = void>(
  options: CosmicActionOptions<TVariables>
) {
  const queryClient = useQueryClient()
  const [jobId, setJobId] = useState<string | null>(null)
  const mutation = useMutation({
    writes: options.writes,
    mutationFn: options.run,
    onSuccess: (response, variables) => {
      const message =
        typeof options.success === 'function'
          ? options.success(response, variables)
          : (options.success ?? response.message)
      const entry = response.ledger_entry_id
      if (announceWaiting(response) === 'done')
        toast.success(message, {
          description: options.success ? response.message : undefined,
          action:
            typeof entry === 'number'
              ? {
                  label: UNDO_LABEL,
                  onClick: () => void undoLedgerEntry(queryClient, entry),
                }
              : undefined,
        })
      if (response.job_id) setJobId(response.job_id)
      refresh(queryClient)
      options.onDone?.(response, variables)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : String(error))
    },
  })
  const clearJob = useCallback(() => setJobId(null), [])
  return { ...mutation, jobId, clearJob }
}

export type CosmicGate = {
  essence: number | undefined
  busy: boolean
  epoch: number | undefined
  reasonFor: (cost: number | undefined) => string | undefined
}

export const BUSY_REASON = 'An epoch is running; this opens when it is done.'

export function useCosmicGate(): CosmicGate {
  const { data } = useCosmosState()
  const essence = data?.creator?.essence
  const busy = data?.epoch_running ?? false
  const readOnly = data?.read_only ?? false
  const reasonFor = useCallback(
    (cost: number | undefined) => {
      if (readOnly) return 'A guest world is open read-only.'
      if (busy) return BUSY_REASON
      if (cost !== undefined && essence !== undefined && essence < cost)
        return `${cost} essence needed; you have ${essence}.`
      return undefined
    },
    [busy, essence, readOnly]
  )
  return { essence, busy, epoch: data?.world?.epoch, reasonFor }
}
