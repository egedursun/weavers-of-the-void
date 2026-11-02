import { useState } from 'react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Label as FieldLabel } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Section } from '@/components/domain'
import { Label } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

export function CreatorNote({ note }: { note: string | null }) {
  const saved = note ?? ''
  const [text, setText] = useState(saved)
  const { reason } = useGodGate()
  const write = useGodAction({
    run: (value: string) =>
      unwrap(api.PUT('/api/creator/note', { body: { text: value } })),
    success: 'Written into canon',
  })
  const status = write.isPending
    ? 'Writing...'
    : write.isError
      ? 'Could not write'
      : text === saved
        ? 'In canon'
        : 'Not saved'
  return (
    <Section
      title='Your own word'
      description='Everything written here is canon: every son, mortal, Fate and the chronicler sees it each turn.'
      surface='card'
      level={3}
    >
      <FieldLabel htmlFor='creator-note' className='sr-only'>
        Your own word
      </FieldLabel>
      <Textarea
        id='creator-note'
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <ActionButton
          label='Write into canon'
          variant='default'
          blocked={reason() ?? (text === saved ? 'Nothing changed.' : null)}
          pending={write.isPending}
          onRun={() => write.mutate(text)}
        />
        <Label aria-live='polite'>{status}</Label>
      </div>
    </Section>
  )
}
