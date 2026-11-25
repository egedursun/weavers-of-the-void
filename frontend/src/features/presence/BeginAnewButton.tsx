import { useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { READ_ONLY_MESSAGE, isReadOnly } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/domain'
import { useCloseSession } from './api'
import { type PresenceSessionSummary } from './types'

export function BeginAnewButton({
  session,
  name,
  busy,
}: {
  session: PresenceSessionSummary
  name: string
  busy: boolean
}) {
  const [open, setOpen] = useState(false)
  const close = useCloseSession()
  const onRecord = session.record === 'on_record'
  const reason = isReadOnly()
    ? READ_ONLY_MESSAGE
    : busy
      ? `Wait until ${name} has answered, or stop it first.`
      : close.isPending
        ? 'Ending this audience.'
        : null
  return (
    <>
      <Button
        variant='outline'
        size='sm'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => setOpen(true)}
      >
        <RotateCcw />
        Begin anew
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title='Begin anew?'
        destructive={!onRecord}
        desc={
          <div className='flex flex-col gap-2'>
            <span>
              {`This audience with ${name} ends. You choose again how you appear and what is kept, and the next audience starts empty.`}
            </span>
            <span>
              {onRecord
                ? `It was on the record, so nothing is lost: it stays among the past audiences, in ${name}'s entry, the lore book and the Codex, and ${name} remembers it.`
                : `It was off the record, so every word of it is deleted now, and ${name} remembers none of it.`}
            </span>
          </div>
        }
        confirmText={onRecord ? 'Begin anew' : 'Delete and begin anew'}
        isLoading={close.isPending}
        handleConfirm={() =>
          close.mutate(session.id, {
            onSuccess: (closed) => {
              setOpen(false)
              toast.success(
                closed.kept
                  ? 'The audience is kept in the record.'
                  : 'The audience is gone, as if it never was.'
              )
            },
            onError: (error) => toast.error(error.message),
          })
        }
      />
    </>
  )
}
