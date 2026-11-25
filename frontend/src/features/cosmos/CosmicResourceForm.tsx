import { useState } from 'react'
import { Gem, Pickaxe } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { entityTypeValues } from '@/api/generated/schema'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { CosmicActionButton } from './CosmicActionButton'
import { type TravelResource } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { useCosmicAction } from './useCosmicAction'

const NAME_MAX = 60

type CosmicResourceFormProps = {
  index: CosmosIndex
  resource: TravelResource | null | undefined
  worldId: number | undefined
}

export function CosmicResourceForm({
  index,
  resource,
  worldId,
}: CosmicResourceFormProps) {
  const [name, setName] = useState(resource?.name ?? '')
  const [rule, setRule] = useState(resource?.rule ?? '')
  const [description, setDescription] = useState(resource?.description ?? '')
  const [sideEffect, setSideEffect] = useState(resource?.side_effect ?? '')
  const define = useCosmicAction({
    writes: [{ lever: 'cosmos:resource' }],
    run: () =>
      unwrap(
        api.PUT('/api/cosmic-resource', {
          body: {
            name: name.trim(),
            rule,
            description,
            side_effect: sideEffect,
          },
        })
      ),
    success: "The cosmos's travel resource was defined",
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        The substance that fuels travel between worlds. Space folding and some
        vessels burn it; its deposits are fought over.
      </Muted>
      <FormRow label='Name'>
        {(id) => (
          <Input
            id={id}
            value={name}
            maxLength={NAME_MAX}
            placeholder='The name of the resource'
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Rule'>
        {(id) => (
          <Input
            id={id}
            value={rule}
            placeholder='Only gathered in one season'
            onChange={(event) => setRule(event.target.value)}
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
      <FormRow label='Side effect'>
        {(id) => (
          <Input
            id={id}
            value={sideEffect}
            placeholder='What long use does, if anything'
            onChange={(event) => setSideEffect(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          act={define}
          actionId='cosmos:resource'
          label={resource ? 'Update' : 'Define'}
          icon={Gem}
          variant='default'
          pending={define.isPending}
          blockedReason={
            name.trim() === '' ? 'The resource needs a name.' : undefined
          }
          onRun={() => define.mutate()}
        />
      </div>
      {resource && (
        <DepositForm
          index={index}
          resourceName={resource.name}
          worldId={worldId}
        />
      )}
    </div>
  )
}

function DepositForm({
  index,
  resourceName,
  worldId,
}: {
  index: CosmosIndex
  resourceName: string
  worldId: number | undefined
}) {
  const [worldChoice, setWorld] = useState('')
  const [place, setPlace] = useState('')
  const world =
    worldChoice || String(worldId ?? index.worlds[0]?.world.id ?? '')
  const places = index.placesOf(Number(world))
  const open = useCosmicAction({
    writes: [{ lever: 'cosmos:deposit' }],
    run: () =>
      unwrap(
        api.POST('/api/cosmic-resource/deposits', {
          body: { place_id: Number(place) },
        })
      ),
    success: `A new ${resourceName} deposit was opened`,
    onDone: () => setPlace(''),
  })
  return (
    <Section title={`Open a new ${resourceName} deposit`} level={3}>
      <FormRow label='World'>
        {(id) => (
          <Select
            value={world}
            onValueChange={(value) => {
              setWorld(value)
              setPlace('')
            }}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='Choose a world' />
            </SelectTrigger>
            <SelectContent>
              {index.worlds.map((item) => (
                <SelectItem key={item.world.id} value={String(item.world.id)}>
                  {item.world.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Region or place'>
        {(id) => (
          <Select
            value={place}
            onValueChange={setPlace}
            disabled={places.length === 0}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue
                placeholder={
                  places.length ? 'Choose a land' : 'No region in this world'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {places.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  {`${item.name} · ${wordOf(entityTypeValues, item.entity_type)}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          act={open}
          actionId='cosmos:deposit'
          label='Open the deposit'
          icon={Pickaxe}
          pending={open.isPending}
          blockedReason={
            places.length === 0
              ? 'This world has no region yet.'
              : place === ''
                ? 'Choose a region or place first.'
                : undefined
          }
          onRun={() => open.mutate()}
        />
      </div>
    </Section>
  )
}
