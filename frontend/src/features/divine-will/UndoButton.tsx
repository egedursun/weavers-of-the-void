import { Undo2 } from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { isUndone, useUndo } from '@/features/ledger/api'
import { announceWaiting } from '@/features/team/outcome'
import { useTeamContext } from '@/features/team/teamContext'

export function UndoButton({ entryId }: { entryId: number }) {
  const me = useTeamContext()?.me ?? null
  const undo = useUndo(me)
  const reason = isReadOnly()
    ? READ_ONLY_MESSAGE
    : undo.isPending
      ? 'Undoing the act.'
      : null
  return (
    <Button
      act={undo}
      variant='outline'
      size='sm'
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      onClick={() =>
        undo.mutate(entryId, {
          onSuccess: (outcome) => {
            if (
              announceWaiting({
                queued: isUndone(outcome) ? null : outcome,
              }) === 'done'
            )
              toast.success('The act is undone.')
          },
          onError: (error) => toast.error(error.message),
        })
      }
    >
      <Undo2 />
      Undo
    </Button>
  )
}
