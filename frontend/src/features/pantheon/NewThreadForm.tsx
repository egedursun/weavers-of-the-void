import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, PagedList } from '@/components/domain'
import { Muted } from '@/components/typography'
import { ActionButton } from './ActionButton'
import { NamePicker } from './NamePicker'
import { type NameEntry, godKeys } from './api'
import { useGodGate } from './gate'
import { useGodAction } from './godAction'

export function NewThreadForm() {
  const [text, setText] = useState('')
  const [related, setRelated] = useState<NameEntry[]>([])
  const { reason } = useGodGate()
  const open = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/threads', {
          body: {
            text: text.trim(),
            related_ids: related.map((entry) => entry.id),
          },
        })
      ),
    success: 'A new story is open; Fate will follow it',
    invalidate: [godKeys.threads],
    onDone: () => {
      setText('')
      setRelated([])
    },
  })
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' className='self-start'>
          <Plus />
          Open a new story
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <FormRow label='The story'>
          {(id) => (
            <Textarea
              id={id}
              value={text}
              placeholder='The story that has begun and the question it leaves open…'
              onChange={(event) => setText(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Related records'>
          {(id) => (
            <NamePicker
              id={id}
              value={null}
              kinds={['entity', 'son']}
              exclude={related.map((entry) => entry.id)}
              placeholder='Add a related record'
              onChange={(_value, entry) =>
                entry && setRelated([...related, entry])
              }
            />
          )}
        </FormRow>
        {related.length > 0 && (
          <PagedList
            items={related}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(entry) => entry.id}
          >
            {(entry) => (
              <Button
                key={entry.id}
                variant='outline'
                size='sm'
                aria-label={`Remove ${entry.name}`}
                onClick={() =>
                  setRelated(related.filter((item) => item.id !== entry.id))
                }
              >
                {entry.name}
                <X />
              </Button>
            )}
          </PagedList>
        )}
        <Muted variant='caption'>
          Fate tracks open stories and advances or closes them as epochs pass.
        </Muted>
        <div>
          <ActionButton
            label='Open the story'
            variant='default'
            blocked={
              reason() ?? (text.trim() ? null : 'Write the story first.')
            }
            pending={open.isPending}
            onRun={() => open.mutate()}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
