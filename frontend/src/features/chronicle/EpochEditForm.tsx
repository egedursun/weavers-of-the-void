import { useState } from 'react'
import { PenLine } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

export function EpochEditForm({
  epoch,
  name,
  narrative,
}: {
  epoch: number
  name: string | null
  narrative: string | null
}) {
  const [draftName, setDraftName] = useState(name ?? '')
  const [draftNarrative, setDraftNarrative] = useState(narrative ?? '')
  const { reason } = useGodGate()
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/epoch:edit', {
          body: {
            epoch,
            name: draftName === (name ?? '') ? null : draftName,
            narrative:
              draftNarrative === (narrative ?? '') ? null : draftNarrative,
          },
        })
      ),
    success: `Epoch ${epoch} was rewritten`,
  })
  const unchanged =
    draftName === (name ?? '') && draftNarrative === (narrative ?? '')
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='self-start'>
          <PenLine />
          Edit this epoch
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <FormRow label='Name of the epoch'>
          {(id) => (
            <Input
              id={id}
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Narrative'>
          {(id) => (
            <Textarea
              id={id}
              value={draftNarrative}
              onChange={(event) => setDraftNarrative(event.target.value)}
            />
          )}
        </FormRow>
        <div>
          <ActionButton
            label='Save'
            variant='default'
            blocked={reason() ?? (unchanged ? 'Nothing changed.' : null)}
            pending={save.isPending}
            onRun={() => save.mutate()}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
