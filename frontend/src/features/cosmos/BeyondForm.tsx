import { useState } from 'react'
import {
  Archive,
  BookOpenText,
  Biohazard,
  Eye,
  Hourglass,
  Skull,
  Undo2,
  UsersRound,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { OuterBargainForm } from '@/features/son/OuterBargainForm'
import { ChoiceField } from '@/features/wars/military/parts'
import { CosmicActionButton } from './CosmicActionButton'
import { EntityPicker } from './EntityPicker'
import { OrderBlock, OrderFields } from './OrderBlock'
import { type ActionResponse, useCosmosState } from './api'
import { HORROR_DEFAULT, HORROR_PARTS, type HorrorSpec } from './horrorParts'
import { type CosmosIndex } from './model/cosmosModel'
import { useCosmicAction } from './useCosmicAction'

const COMMUNITY_TYPES = ['people', 'settlement', 'cult', 'faction'] as const
const PLACE_TYPES = ['region', 'place'] as const
const CULT_TYPES = ['cult'] as const

type BeyondFormProps = { index: CosmosIndex; worldId: number | undefined }

export function BeyondForm({ index, worldId }: BeyondFormProps) {
  const order = useCosmicAction({
    writes: [
      { lever: 'archive:raise' },
      { lever: 'archive:read' },
      { lever: 'horror:cult' },
      { lever: 'horror:event' },
      { lever: 'horror:suppress_cult' },
      { lever: 'plague:cosmic' },
      { lever: 'quest:abandon' },
      { lever: 'sky:time_echo' },
    ],
    run: (call: () => Promise<ActionResponse>) => call(),
  })
  const { data: state } = useCosmosState()
  const threads = state?.threads ?? []
  const [reader, setReader] = useState<number | null>(null)
  const [plagueAt, setPlagueAt] = useState<number | null>(null)
  const [horrorWorld, setHorrorWorld] = useState('')
  const [horror, setHorror] = useState<HorrorSpec>(HORROR_DEFAULT)
  const [seeded, setSeeded] = useState<number | null>(null)
  const [cult, setCult] = useState<number | null>(null)
  const [thread, setThread] = useState('')
  const world =
    horrorWorld || String(worldId ?? index.worlds[0]?.world.id ?? '')
  const threadId = thread || String(threads[0]?.id ?? '')
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <OrderBlock
        title='The Cosmic Archive'
        description='Raise the archive of everything that was, or let a community read from it.'
      >
        <OrderFields>
          <EntityPicker
            types={COMMUNITY_TYPES}
            value={reader}
            onChange={setReader}
            placeholder='Reader (for reading)'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='archive:raise'
            label='Raise the Archive'
            icon={Archive}
            pending={order.isPending}
            onRun={() =>
              order.mutate(() => unwrap(api.POST('/api/actions/archive:raise')))
            }
          />
          <CosmicActionButton
            act={order}
            actionId='archive:read'
            label='Let them read'
            icon={BookOpenText}
            pending={order.isPending}
            blockedReason={
              reader === null ? 'Choose a community first.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/archive:read', {
                    body: { community_id: reader ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Loose the cosmic plague'
        description='A sickness from the void takes hold in a region or place and travels with voyages.'
      >
        <OrderFields>
          <EntityPicker
            types={PLACE_TYPES}
            value={plagueAt}
            onChange={setPlagueAt}
            placeholder='Where it starts'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='plague:cosmic'
            label='Loose the plague'
            icon={Biohazard}
            variant='destructive'
            pending={order.isPending}
            blockedReason={
              plagueAt === null ? 'Choose a place first.' : undefined
            }
            confirm={{
              title: 'Loose the cosmic plague?',
              description: `It begins in ${index.entityName(plagueAt) ?? 'the chosen land'} and spreads along the routes.`,
              confirmText: 'Loose it',
            }}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/plague:cosmic', {
                    body: { place_id: plagueAt ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Order a horror'
        description='A horror touches one thing a world holds and does one thing to it; those who perceive it lose sanity while it lingers.'
      >
        <OrderFields>
          <Select value={world} onValueChange={setHorrorWorld}>
            <SelectTrigger aria-label='World' className='w-full'>
              <SelectValue placeholder='Which world' />
            </SelectTrigger>
            <SelectContent>
              {index.worlds.map((item) => (
                <SelectItem key={item.world.id} value={String(item.world.id)}>
                  {item.world.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {HORROR_PARTS.map((part) => (
            <ChoiceField
              key={part.key}
              label={part.label}
              value={horror[part.key]}
              table={part.table}
              blocked={null}
              onPick={(value) => setHorror({ ...horror, [part.key]: value })}
            />
          ))}
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='horror:event'
            label='Let it happen'
            icon={Eye}
            variant='destructive'
            pending={order.isPending}
            blockedReason={world === '' ? 'Choose a world.' : undefined}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/horror:event', {
                    body: { world_id: Number(world), ...horror },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Outer cults'
        description='Seed a cult of the outside in a community, or scatter one that already gathers.'
      >
        <OrderFields>
          <EntityPicker
            types={COMMUNITY_TYPES}
            value={seeded}
            onChange={setSeeded}
            placeholder='Where to seed it'
            worldName={index.worldName}
          />
          <EntityPicker
            types={CULT_TYPES}
            value={cult}
            onChange={setCult}
            placeholder='Which cult to scatter'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='horror:cult'
            label='Seed the cult'
            icon={Skull}
            variant='destructive'
            pending={order.isPending}
            blockedReason={
              seeded === null ? 'Choose a community first.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/horror:cult', {
                    body: { entity_id: seeded ?? 0 },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='horror:suppress_cult'
            label='Scatter the cult'
            icon={UsersRound}
            pending={order.isPending}
            blockedReason={cult === null ? 'Choose a cult first.' : undefined}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/horror:suppress_cult', {
                    body: { cult_id: cult ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Storylines in the sky'
        description='Send an echo of an open storyline back through time, or abandon a legendary quest.'
      >
        <OrderFields>
          <Select
            value={threadId}
            onValueChange={setThread}
            disabled={threads.length === 0}
          >
            <SelectTrigger aria-label='Storyline' className='w-full'>
              <SelectValue placeholder='No open storyline' />
            </SelectTrigger>
            <SelectContent>
              {threads.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  {item.text}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            act={order}
            actionId='sky:time_echo'
            label='Order a time echo'
            icon={Hourglass}
            pending={order.isPending}
            blockedReason={
              threadId === '' ? 'There is no open storyline.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/sky:time_echo', {
                    body: { thread_id: Number(threadId) },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            act={order}
            actionId='quest:abandon'
            label='Abandon the quest'
            icon={Undo2}
            variant='destructive'
            pending={order.isPending}
            blockedReason={
              threadId === '' ? 'There is no open storyline.' : undefined
            }
            confirm={{
              title: 'Abandon this quest?',
              description:
                'The quest ends unfinished; Fate counts it as a failure.',
              confirmText: 'Abandon',
            }}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/quest:abandon', {
                    body: { thread_id: Number(threadId) },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Bargains with the outside'
        description='Make a son strike a bargain with a thing beyond the stars, or forbid them to bargain at all.'
      >
        <OuterBargainForm sons={(state?.sons ?? []).map((item) => item.son)} />
      </OrderBlock>
    </div>
  )
}
