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
import { Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type CreatorRecord } from './api'

type Draft = {
  title: string
  appearance: string
  temperament: string
  image_prompt: string
}

function draftOf(creator: CreatorRecord): Draft {
  return {
    title: creator.title ?? '',
    appearance: creator.appearance ?? '',
    temperament: creator.temperament ?? '',
    image_prompt: creator.image_prompt ?? '',
  }
}

export function CreatorEditForm({ creator }: { creator: CreatorRecord }) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(creator))
  const { reason } = useGodGate()
  const save = useGodAction({
    writes: [{ lever: 'creator:edit' }],
    run: (body: Draft) => unwrap(api.PATCH('/api/creator', { body })),
    success: "The Creator's likeness was updated",
  })
  const field = (key: keyof Draft) => ({
    value: draft[key],
    onChange: (event: { target: { value: string } }) =>
      setDraft({ ...draft, [key]: event.target.value }),
  })
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button act={save} variant='outline' className='self-start'>
          <PenLine />
          Edit title, appearance and temperament
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <FormRow label='Title'>
          {(id) => <Input id={id} maxLength={120} {...field('title')} />}
        </FormRow>
        <FormRow label='Appearance'>
          {(id) => <Textarea id={id} {...field('appearance')} />}
        </FormRow>
        <FormRow label='Temperament'>
          {(id) => <Textarea id={id} {...field('temperament')} />}
        </FormRow>
        <FormRow label='Image prompt'>
          {(id) => <Textarea id={id} {...field('image_prompt')} />}
        </FormRow>
        <Muted variant='caption'>A field left empty is deleted.</Muted>
        <div>
          <ActionButton
            act={save}
            label='Save'
            variant='default'
            blocked={reason()}
            pending={save.isPending}
            onRun={() => save.mutate(draft)}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
