import { useState } from 'react'
import { Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { CopyButton } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { PROMPT_MAX_LENGTH } from './copyText'

type PromptBoxProps = {
  prompt: string | null
  onSave: (prompt: string | null) => void
  saving?: boolean
  readOnlyReason?: string | null
}

export function PromptBox({
  prompt,
  onSave,
  saving = false,
  readOnlyReason = null,
}: PromptBoxProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(prompt ?? '')
  const blocked = readOnlyReason ?? (saving ? 'Saving.' : null)
  return (
    <div data-domain='prompt-box' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Label variant='overline'>Image prompt</Label>
        <div className='flex items-center gap-2'>
          <CopyButton text={prompt ?? ''} label='Copy the prompt' />
          <Button
            variant='ghost'
            size='sm'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => {
              setDraft(prompt ?? '')
              setEditing((value) => !value)
            }}
          >
            <Pencil />
            {editing ? 'Cancel' : 'Edit'}
          </Button>
        </div>
      </div>
      {editing ? (
        <form
          className='flex min-w-0 flex-col gap-2'
          onSubmit={(event) => {
            event.preventDefault()
            const text = draft.trim()
            onSave(text ? text : null)
            setEditing(false)
          }}
        >
          <Textarea
            aria-label='Image prompt'
            maxLength={PROMPT_MAX_LENGTH}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <div className='flex justify-end gap-2'>
            <Button
              type='submit'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
            >
              Save prompt
            </Button>
          </div>
        </form>
      ) : prompt ? (
        <Text variant='caption' className='rounded-md bg-muted px-3 py-2'>
          {prompt}
        </Text>
      ) : (
        <Muted variant='caption'>
          No prompt yet. Write one, or let the scribe write it.
        </Muted>
      )}
    </div>
  )
}
