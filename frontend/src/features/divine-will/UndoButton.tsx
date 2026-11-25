import { Undo2 } from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { useUndo } from '@/features/ledger/api'

export function UndoButton({ entryId }: { entryId: number }) {
  const undo = useUndo()
  const reason = isReadOnly()
    ? READ_ONLY_MESSAGE
    : undo.isPending
      ? 'Undoing the act.'
      : null
  return (
    <Button
      variant='outline'
      size='sm'
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      onClick={() =>
        undo.mutate(entryId, {
          onSuccess: () => toast.success('The act is undone.'),
          onError: (error) => toast.error(error.message),
        })
      }
    >
      <Undo2 />
      Undo
    </Button>
  )
}
