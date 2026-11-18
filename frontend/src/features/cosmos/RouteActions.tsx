import { useId, useState } from 'react'
import { Eye, Link2, Lock, Scissors, ShieldAlert } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Muted } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type RouteRecord } from './api'
import {
  type CosmosIndex,
  RESTORABLE_ROUTE_STATES,
  routeState,
} from './model/cosmosModel'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction, useCosmicGate } from './useCosmicAction'

const DANGER_MAX = 100

type RouteActionsProps = {
  route: RouteRecord
  index: CosmosIndex
  rules: RuleBook
}

export function RouteActions({ route, index, rules }: RouteActionsProps) {
  const state = routeState(route)
  const defaultEpochs = rules.get('severEpochs')
  const [epochs, setEpochs] = useState(() => {
    const known = rules.get('severEpochs')
    return known === undefined ? '' : String(known)
  })
  const [danger, setDanger] = useState(String(route.danger))
  const epochsId = useId()
  const dangerId = useId()
  const gate = useCosmicGate()
  const seal = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/cosmic/seal-gate', { body: { route_id: route.id } })
      ),
    success: 'Route sealed',
  })
  const sever = useCosmicAction({
    run: (duration: number | undefined) =>
      unwrap(
        api.POST('/api/routes/{route_id}/sever', {
          params: { path: { route_id: route.id } },
          body: duration === undefined ? {} : { duration },
        })
      ),
    success: 'Route severed',
  })
  const reopen = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/routes/{route_id}/restore', {
          params: { path: { route_id: route.id } },
        })
      ),
    success: 'Route opened again',
  })
  const reveal = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/routes/{route_id}/reveal', {
          params: { path: { route_id: route.id } },
        })
      ),
    success: 'Hidden route revealed',
  })
  const setRouteDanger = useCosmicAction({
    run: (value: number) =>
      unwrap(
        api.POST('/api/actions/route:danger', {
          body: { route_id: route.id, danger: value },
        })
      ),
    success: 'Route danger set',
  })
  const parsedEpochs = epochs.trim() === '' ? undefined : Number(epochs)
  const dangerValue = Number(danger)
  const dangerValid =
    Number.isInteger(dangerValue) &&
    dangerValue >= 0 &&
    dangerValue <= DANGER_MAX
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      {state.open && (
        <CosmicActionButton
          actionId='cosmic:seal_gate'
          label='Seal'
          icon={Lock}
          size='sm'
          cost={rules.get('sealGate')}
          pending={seal.isPending}
          onRun={() => seal.mutate()}
        />
      )}
      {state.open && (
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant='outline'
              size='sm'
              disabled={gate.reasonFor(rules.get('severCost')) !== undefined}
              disabledReason={gate.reasonFor(rules.get('severCost'))}
            >
              <Scissors />
              Sever
            </Button>
          </PopoverTrigger>
          <PopoverContent align='start' className='flex flex-col gap-3'>
            <div className='flex min-w-0 flex-col gap-2'>
              <FieldLabel htmlFor={epochsId}>
                Closed for how many epochs
              </FieldLabel>
              <Input
                id={epochsId}
                type='number'
                min={1}
                inputMode='numeric'
                placeholder={ruleText(defaultEpochs)}
                value={epochs}
                onChange={(event) => setEpochs(event.target.value)}
              />
              <Muted variant='caption'>
                Voyages on it fall into uncertainty. Leave blank for the rule
                default.
              </Muted>
            </div>
            <CosmicActionButton
              actionId='route'
              label='Sever the route'
              variant='destructive'
              icon={Scissors}
              size='sm'
              cost={rules.get('severCost')}
              pending={sever.isPending}
              blockedReason={
                parsedEpochs !== undefined &&
                (!Number.isInteger(parsedEpochs) || parsedEpochs < 1)
                  ? 'Enter a whole number of epochs, at least 1.'
                  : undefined
              }
              confirm={{
                title: 'Sever this route?',
                description: `The route between ${index.worldName(route.world_a_id)} and ${index.worldName(route.world_b_id)} closes for ${parsedEpochs ?? ruleText(defaultEpochs)} epochs.`,
                confirmText: 'Sever',
              }}
              onRun={() => sever.mutate(parsedEpochs)}
            />
          </PopoverContent>
        </Popover>
      )}
      {!state.open && RESTORABLE_ROUTE_STATES.has(state.key) && (
        <CosmicActionButton
          actionId='route'
          label='Open it again'
          icon={Link2}
          size='sm'
          cost={rules.get('reopenCost')}
          pending={reopen.isPending}
          onRun={() => reopen.mutate()}
        />
      )}
      {!route.known && (
        <CosmicActionButton
          actionId='route'
          label='Reveal'
          icon={Eye}
          size='sm'
          cost={rules.get('revealCost')}
          pending={reveal.isPending}
          onRun={() => reveal.mutate()}
        />
      )}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant='ghost' size='sm'>
            <ShieldAlert />
            Danger
          </Button>
        </PopoverTrigger>
        <PopoverContent align='start' className='flex flex-col gap-3'>
          <div className='flex min-w-0 flex-col gap-2'>
            <FieldLabel htmlFor={dangerId}>
              Danger of this route (0 to 100)
            </FieldLabel>
            <Input
              id={dangerId}
              type='number'
              min={0}
              max={DANGER_MAX}
              inputMode='numeric'
              value={danger}
              onChange={(event) => setDanger(event.target.value)}
            />
          </div>
          <CosmicActionButton
            actionId='route:danger'
            label='Set danger'
            size='sm'
            pending={setRouteDanger.isPending}
            blockedReason={
              dangerValid ? undefined : 'Enter a whole number from 0 to 100.'
            }
            onRun={() => setRouteDanger.mutate(dangerValue)}
          />
        </PopoverContent>
      </Popover>
      <TeachRoute route={route} index={index} />
    </div>
  )
}

function TeachRoute({
  route,
  index,
}: {
  route: RouteRecord
  index: CosmosIndex
}) {
  const [community, setCommunity] = useState('')
  const communities = [
    ...index.communitiesOf(route.world_a_id),
    ...index.communitiesOf(route.world_b_id),
  ]
  const teach = useCosmicAction({
    run: (communityId: number) =>
      unwrap(
        api.POST('/api/actions/route:teach', {
          body: { community_id: communityId, route_id: route.id },
        })
      ),
    success: 'The road was taught',
  })
  if (communities.length === 0) return null
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant='ghost' size='sm'>
          Teach the road
        </Button>
      </PopoverTrigger>
      <PopoverContent align='start' className='flex flex-col gap-3'>
        <Muted variant='caption'>
          A community at either end learns this road and may set out on it.
        </Muted>
        <Select value={community} onValueChange={setCommunity}>
          <SelectTrigger aria-label='Community' className='w-full'>
            <SelectValue placeholder='Choose a community' />
          </SelectTrigger>
          <SelectContent>
            {communities.map((item) => (
              <SelectItem key={item.id} value={String(item.id)}>
                {`${item.name} · ${index.worldName(item.world_id)}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <CosmicActionButton
          actionId='route:teach'
          label='Teach'
          size='sm'
          pending={teach.isPending}
          blockedReason={
            community === '' ? 'Choose a community first.' : undefined
          }
          onRun={() => teach.mutate(Number(community))}
        />
      </PopoverContent>
    </Popover>
  )
}
