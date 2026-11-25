import { type KeyboardEvent, useEffect, useId, useRef } from 'react'
import { SendHorizontal, Square } from 'lucide-react'
import { toast } from 'sonner'
import { READ_ONLY_MESSAGE, isReadOnly } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Textarea } from '@/components/ui/textarea'
import { Muted } from '@/components/typography'
import { useCancelExchange, useSendExchange } from './api'
import { NO_MODEL } from './looks'
import { usePresence } from './presenceStore'
import { type PresenceRecord } from './types'

const NO_DRAFT = ''

export function PresenceComposer({
  sessionId,
  nodeId,
  name,
  runningId,
  modelEnabled,
  record,
}: {
  record: PresenceRecord
  sessionId: number
  nodeId: number
  name: string
  runningId: number | null
  modelEnabled: boolean
}) {
  const draft = usePresence((state) => state.drafts[nodeId] ?? NO_DRAFT)
  const setDraft = usePresence((state) => state.setDraft)
  const send = useSendExchange(sessionId, record)
  const cancel = useCancelExchange()
  const field = useRef<HTMLTextAreaElement>(null)
  const hintId = useId()
  const running = runningId !== null

  useEffect(() => {
    field.current?.focus()
  }, [sessionId])

  const blocked = isReadOnly()
    ? READ_ONLY_MESSAGE
    : !modelEnabled
      ? NO_MODEL
      : running || send.isPending
        ? `${name} is still answering; stop it or wait for the answer.`
        : !draft.trim()
          ? 'Write what you wish to say first.'
          : null

  const submit = () => {
    if (blocked) return
    send.mutate(draft.trim(), {
      onSuccess: () => setDraft(nodeId, ''),
      onError: (error) => toast.error(error.message),
    })
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.nativeEvent.isComposing || event.key !== 'Enter') return
    if (event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return
    event.preventDefault()
    submit()
  }

  return (
    <div
      data-domain='presence-composer'
      className='flex min-w-0 flex-col gap-2'
    >
      <div className='max-h-64 min-w-0 overflow-y-auto'>
        <Textarea
          ref={field}
          value={draft}
          rows={2}
          aria-label={`Your words to ${name}`}
          aria-describedby={hintId}
          placeholder={`Speak to ${name}`}
          onChange={(event) => setDraft(nodeId, event.target.value)}
          onKeyDown={onKeyDown}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Muted
          id={hintId}
          as='span'
          variant='caption'
          className='flex min-w-0 flex-1 items-center gap-1 max-sm:hidden'
        >
          <Kbd>Enter</Kbd> send <Kbd>Shift Enter</Kbd> new line
        </Muted>
        <span aria-hidden='true' className='flex-1 sm:hidden' />
        {running ? (
          <Button
            act={cancel}
            type='button'
            variant='destructive'
            size='sm'
            disabled={cancel.isPending}
            disabledReason={`Stopping ${name}.`}
            onClick={() =>
              cancel.mutate(runningId, {
                onError: (error) => toast.error(error.message),
              })
            }
          >
            <Square />
            Stop
          </Button>
        ) : (
          <Button
            act={send}
            type='button'
            size='sm'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={submit}
          >
            <SendHorizontal />
            Speak
          </Button>
        )}
      </div>
    </div>
  )
}
