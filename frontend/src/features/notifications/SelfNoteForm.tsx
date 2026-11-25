import { useState } from 'react'
import { StickyNote } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section } from '@/components/domain'
import { useAddNote } from './api'

const TITLE_MAX = 200
const BODY_MAX = 4000

export function SelfNoteForm() {
  const add = useAddNote()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const empty = title.trim() === ''
  return (
    <Section
      title='Leave yourself a note'
      description='It is filed as a personal notification and kept under My notes.'
      surface='card'
      level={3}
    >
      <form
        className='flex min-w-0 flex-col gap-4'
        onSubmit={(event) => {
          event.preventDefault()
          if (empty) return
          add.mutate(
            { title: title.trim(), body: body.trim() || null },
            {
              onSuccess: () => {
                toast.success('Note added')
                setTitle('')
                setBody('')
              },
              onError: (error) => toast.error(error.message),
            }
          )
        }}
      >
        <FormRow label='Title'>
          {(id) => (
            <Input
              id={id}
              required
              maxLength={TITLE_MAX}
              placeholder='A note to yourself'
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Details' description='Optional.'>
          {(id) => (
            <Textarea
              id={id}
              maxLength={BODY_MAX}
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
          )}
        </FormRow>
        <div>
          <Button
            act={add}
            type='submit'
            variant='outline'
            disabled={empty || add.isPending}
            disabledReason={empty ? 'Give the note a title' : 'Saving'}
          >
            <StickyNote />
            Add the note
          </Button>
        </div>
      </form>
    </Section>
  )
}
