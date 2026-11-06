import { useState } from 'react'
import { Ghost } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { domainValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { type Domain, useWorldState } from '@/features/pantheon/api'
import { RELATION_SCALE, STAT_SCALE } from '@/features/pantheon/constants'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useLabels } from '@/features/pantheon/labels'

const NONE = 'none'

const IMAGE_PROMPT_MAX = 900

export function PlaceForeignGodForm() {
  const state = useWorldState()
  const worlds = state.data?.worlds ?? []
  const { domain } = useLabels()
  const { reason } = useGodGate()
  const [name, setName] = useState('')
  const [title, setTitle] = useState('')
  const [worldId, setWorldId] = useState('')
  const [primary, setPrimary] = useState<Domain>('earth')
  const [secondary, setSecondary] = useState<string>(NONE)
  const [stance, setStance] = useState('0')
  const [power, setPower] = useState('')
  const [description, setDescription] = useState('')
  const [imagePrompt, setImagePrompt] = useState('')
  const chosenWorld = worldId || String(worlds[0]?.id ?? '')
  const place = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/foreign-gods', {
          body: {
            world_id: Number(chosenWorld),
            name: name.trim(),
            title: title.trim() || null,
            description: description.trim() || null,
            domain_primary: primary,
            domain_secondary: secondary === NONE ? null : (secondary as Domain),
            stance: Number(stance),
            power: power === '' ? null : Number(power),
            image_prompt: imagePrompt.trim() || null,
          },
        })
      ),
    success: 'An old god takes a place in the world and is being deepened',
    onDone: () => {
      setName('')
      setTitle('')
      setDescription('')
      setImagePrompt('')
      setPower('')
    },
  })
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' className='self-start'>
          <Ghost />
          Place an old god
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <FormRow label='Name'>
          {(id) => (
            <Input
              id={id}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Title'>
          {(id) => (
            <Input
              id={id}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='World'>
          {(id) => (
            <Select value={chosenWorld} onValueChange={setWorldId}>
              <SelectTrigger id={id} className='w-56'>
                <SelectValue placeholder='Pick a world' />
              </SelectTrigger>
              <SelectContent>
                {worlds.map((world) => (
                  <SelectItem key={world.id} value={String(world.id)}>
                    {world.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow label='Domains'>
          {(id) => (
            <>
              <Select
                value={primary}
                onValueChange={(value) => setPrimary(value as Domain)}
              >
                <SelectTrigger
                  id={id}
                  aria-label='First domain'
                  className='w-44'
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {domainValues.map((item) => (
                    <SelectItem key={item} value={item}>
                      {domain(item)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={secondary} onValueChange={setSecondary}>
                <SelectTrigger aria-label='Second domain' className='w-44'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>No second domain</SelectItem>
                  {domainValues.map((item) => (
                    <SelectItem key={item} value={item}>
                      {domain(item)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </FormRow>
        <FormRow label='Attitude' description='From enemy to friend.'>
          {(id) => (
            <Input
              id={id}
              type='number'
              min={-RELATION_SCALE}
              max={RELATION_SCALE}
              value={stance}
              className='w-32'
              onChange={(event) => setStance(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Power' description='Leave blank and the dice decide.'>
          {(id) => (
            <Input
              id={id}
              type='number'
              min={0}
              max={STAT_SCALE}
              value={power}
              className='w-32'
              onChange={(event) => setPower(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Description'>
          {(id) => (
            <Textarea
              id={id}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow
          label='Image prompt'
          description='Optional; used when drawing its picture. Leave blank and it is written for you.'
        >
          {(id) => (
            <Textarea
              id={id}
              maxLength={IMAGE_PROMPT_MAX}
              value={imagePrompt}
              placeholder='How this god looks: form, materials, colours, light'
              onChange={(event) => setImagePrompt(event.target.value)}
            />
          )}
        </FormRow>
        <Muted variant='caption'>
          After placing, the god is deepened in the background: personality,
          existence, powers and depth.
        </Muted>
        <div>
          <ActionButton
            label='Place the god'
            variant='default'
            blocked={
              reason() ??
              (!name.trim()
                ? 'A name is needed.'
                : !chosenWorld
                  ? 'Pick a world.'
                  : null)
            }
            pending={place.isPending}
            onRun={() => place.mutate()}
          />
        </div>
        <ActionJob
          jobId={place.jobId}
          title='Placing an old god'
          onDismiss={place.clearJob}
        />
      </CollapsibleContent>
    </Collapsible>
  )
}
