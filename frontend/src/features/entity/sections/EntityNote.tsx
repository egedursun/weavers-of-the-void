import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { deleteEntityNote, useLoreMutation } from '../api/mutations'
import { useEntityNote } from '../api/queries'
import { NOTE_AUTOSAVE_MS, NOTE_MAX_LENGTH } from '../constants'

type Status = 'idle' | 'typing' | 'saving' | 'saved' | 'failed'

const STATUS_TEXT: Record<Status, string> = {
  idle: 'Only for you; saved by itself.',
  typing: 'Typing…',
  saving: 'Saving…',
  saved: 'Saved',
  failed: 'Could not save',
}

export function EntityNote({
  entityId,
  note,
  readOnlyReason,
}: {
  entityId: number
  note: string | null
  readOnlyReason: string | null
}) {
  const queryClient = useQueryClient()
  const stored = useEntityNote(entityId, note !== null && note !== '')
  const current = stored.data?.text ?? note ?? ''
  const [text, setText] = useState(current)
  const [status, setStatus] = useState<Status>('idle')
  const [confirming, setConfirming] = useState(false)
  const saved = useRef(current)
  const timer = useRef<number | null>(null)
  const save = useMutation({
    mutationFn: (value: string) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/note', {
          params: { path: { entity_id: entityId } },
          body: { text: value },
        })
      ),
    onMutate: () => setStatus('saving'),
    onSuccess: (_result, value) => {
      saved.current = value
      setStatus('saved')
      void queryClient.invalidateQueries({
        queryKey: loreKeys.entity(entityId),
      })
      void queryClient.invalidateQueries({ queryKey: loreKeys.note(entityId) })
    },
    onError: (error) => {
      setStatus('failed')
      toast.error(error instanceof Error ? error.message : String(error))
    },
  })
  const remove = useLoreMutation({
    run: () => deleteEntityNote(entityId),
    success: 'Note deleted',
    onDone: () => {
      saved.current = ''
      setText('')
      setStatus('idle')
    },
  })
  const flush = (value: string) => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
    if (value !== saved.current) save.mutate(value)
  }
  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current)
    },
    []
  )
  return (
    <Section
      id='section-note'
      title='My notes'
      actions={
        <Button
          variant='outline'
          size='sm'
          disabled={readOnlyReason !== null || (text === '' && current === '')}
          disabledReason={readOnlyReason ?? 'There is no note to delete.'}
          onClick={() => setConfirming(true)}
        >
          <Trash2 />
          Delete note
        </Button>
      }
    >
      <Textarea
        aria-label='My notes'
        maxLength={NOTE_MAX_LENGTH}
        value={text}
        disabled={readOnlyReason !== null}
        placeholder='Anything you want to remember about it'
        onChange={(event) => {
          const value = event.target.value
          setText(value)
          setStatus('typing')
          if (timer.current !== null) window.clearTimeout(timer.current)
          timer.current = window.setTimeout(
            () => flush(value),
            NOTE_AUTOSAVE_MS
          )
        }}
        onBlur={() => flush(text)}
      />
      <Muted variant='caption' aria-live='polite'>
        {readOnlyReason ?? STATUS_TEXT[status]}
      </Muted>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title='Delete this note?'
        desc='Only your own note is removed. You can undo it right after.'
        destructive
        confirmText='Delete note'
        isLoading={remove.isPending}
        handleConfirm={() => {
          setConfirming(false)
          remove.mutate()
        }}
      />
    </Section>
  )
}
