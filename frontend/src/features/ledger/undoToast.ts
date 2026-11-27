import { type QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { gateReason } from '@/api/teamGate'
import { plural } from '@/lib/units'
import { announceWaiting } from '@/features/team/outcome'
import { isUndone, refreshAfterUndo, undoEntry } from './api'

export const UNDO_TOAST_MS = 7000

export function undoMessage(applied: number, conflicts: number): string {
  if (conflicts > 0)
    return `Undone: ${plural(applied, 'change')} reverted, ${plural(conflicts, 'conflict')} skipped`
  return `Ledger page undone: ${plural(applied, 'change')} reversed`
}

export function toastWithUndo(
  queryClient: QueryClient,
  message: string,
  entryId: number | null | undefined
): void {
  if (entryId === null || entryId === undefined) {
    toast.success(message)
    return
  }
  toast.success(message, {
    duration: UNDO_TOAST_MS,
    action: {
      label: 'Undo',
      onClick: () => {
        const refusal = gateReason('undo_own')
        if (refusal !== null) {
          toast.error(refusal)
          return
        }
        undoEntry(entryId)
          .then((result) => {
            if (isUndone(result))
              toast.success(
                undoMessage(
                  result.applied?.length ?? 0,
                  result.conflicts?.length ?? 0
                )
              )
            else announceWaiting({ queued: result })
            refreshAfterUndo(queryClient)
          })
          .catch((error: unknown) =>
            toast.error(error instanceof Error ? error.message : String(error))
          )
      },
    },
  })
}
