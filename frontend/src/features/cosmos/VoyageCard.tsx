import {
  Anchor,
  ArrowRight,
  CalendarDays,
  CircleCheck,
  CircleX,
  Hourglass,
  type LucideIcon,
  Rocket,
  Route,
  Ship,
  Target,
  Undo2,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { EntityLink, type KpiTone, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { JourneyLoadEditor } from '@/features/cosmography/FlowEditors'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { CosmicActionButton } from './CosmicActionButton'
import { type JourneyRecord, type JourneyStatus } from './api'
import {
  type CosmosIndex,
  isUnderway,
  journeyProgress,
  routeState,
} from './model/cosmosModel'
import {
  JOURNEY_INTENT_LABEL,
  JOURNEY_STATUS_LABEL,
  TRAVEL_METHOD_LABEL,
} from './model/labels'
import { useCosmicAction } from './useCosmicAction'

const PERCENT = 100
const MIN_PROGRESS = 0.04

const STATUS_VARIANT: Record<
  JourneyStatus,
  'default' | 'success' | 'destructive' | 'secondary' | 'warning' | 'outline'
> = {
  underway: 'default',
  waiting: 'warning',
  stranded: 'warning',
  arrived: 'success',
  lost: 'destructive',
  recalled: 'secondary',
}

const STATUS_ICON: Record<JourneyStatus, LucideIcon> = {
  underway: Rocket,
  waiting: Hourglass,
  stranded: Anchor,
  arrived: CircleCheck,
  lost: CircleX,
  recalled: Undo2,
}

const STATUS_TONE: Record<JourneyStatus, KpiTone> = {
  underway: 'gold',
  waiting: 'warning',
  stranded: 'warning',
  arrived: 'success',
  lost: 'danger',
  recalled: 'muted',
}

type VoyageCardProps = {
  journey: JourneyRecord
  index: CosmosIndex
}

export function VoyageCard({ journey, index }: VoyageCardProps) {
  const route = index.route(journey.route_id)
  const progress = journeyProgress(journey, route)
  const underway = isUnderway(journey)
  const routeClosed = route ? !routeState(route).open : false
  const traveller =
    index.entityName(journey.traveller_entity_id) ?? 'Travellers'
  const recall = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/voyages/{journey_id}/recall', {
          params: { path: { journey_id: journey.id } },
        })
      ),
    success: 'Voyage recalled',
  })
  return (
    <article
      data-journey-id={journey.id}
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Medallion
          icon={STATUS_ICON[journey.status]}
          tone={STATUS_TONE[journey.status]}
          size='sm'
        />
        <NodeAvatar id={journey.traveller_entity_id} name={traveller} />
        <EntityLink kind='entity' id={String(journey.traveller_entity_id)}>
          {traveller}
        </EntityLink>
        <ArrowRight
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <Text as='span' weight='medium' truncate>
          {index.worldName(journey.destination_world_id)}
        </Text>
        <Badge size='sm' variant={STATUS_VARIANT[journey.status]}>
          {JOURNEY_STATUS_LABEL[journey.status]}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {underway && routeClosed && (
          <Badge
            size='sm'
            variant='warning'
            title='A storm cut the route; the voyage is not lost and waits at the route mouth.'
          >
            Waiting for the seam to close
          </Badge>
        )}
        <Badge size='sm' variant='outline'>
          <Target />
          {JOURNEY_INTENT_LABEL[journey.intent]}
        </Badge>
        {journey.population > 0 && (
          <Badge size='sm' variant='outline'>
            <Users />
            {`${formatInteger(journey.population)} souls`}
          </Badge>
        )}
        {journey.vehicle_entity_id !== null && (
          <Badge size='sm' variant='outline'>
            <Ship />
            <EntityLink kind='entity' id={String(journey.vehicle_entity_id)}>
              {index.entityName(journey.vehicle_entity_id) ?? 'Vessel'}
            </EntityLink>
          </Badge>
        )}
        {route && (
          <Badge size='sm' variant='outline'>
            <Route />
            {TRAVEL_METHOD_LABEL[route.method]}
          </Badge>
        )}
        <Badge size='sm' variant='outline'>
          <CalendarDays />
          {`Set out in epoch ${journey.start_epoch}`}
        </Badge>
        {journey.memory_lost && (
          <Badge size='sm' variant='secondary'>
            Memory lost on the river
          </Badge>
        )}
      </div>
      {(underway || journey.status === 'arrived') && (
        <Progress
          value={Math.max(progress, underway ? MIN_PROGRESS : 0) * PERCENT}
          size='sm'
          tone={journey.status === 'arrived' ? 'success' : 'default'}
          aria-label='Voyage progress'
        />
      )}
      {underway && (
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <Muted variant='caption'>
            {journey.epochs_left > 0
              ? `Arrives in ${journey.epochs_left} epochs`
              : 'Arrives this epoch'}
          </Muted>
          <div className='flex shrink-0 items-center gap-1'>
            <JourneyLoadEditor journey={journey} />
            <CosmicActionButton
              actionId='journey:recall'
              label='Recall'
              icon={Undo2}
              variant='ghost'
              size='sm'
              pending={recall.isPending}
              confirm={{
                title: 'Recall this voyage?',
                description: `${traveller} turns back and returns home.`,
                confirmText: 'Recall',
              }}
              onRun={() => recall.mutate()}
            />
          </div>
        </div>
      )}
      {journey.status === 'recalled' && (
        <Muted variant='caption'>
          The god recalled the voyage; the travellers returned home.
        </Muted>
      )}
      {journey.status === 'arrived' && journey.result_entity_id !== null && (
        <Muted variant='caption'>
          {'They arrived and founded '}
          <EntityLink kind='entity' id={String(journey.result_entity_id)}>
            {index.entityName(journey.result_entity_id) ?? 'a new home'}
          </EntityLink>
          .
        </Muted>
      )}
      {journey.events.length > 0 && (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm'>
              {`What happened on the road (${journey.events.length})`}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul className='flex min-w-0 flex-col gap-1 pt-1'>
              {journey.events.map((event, position) => (
                <li key={`${event.epoch}-${position}`}>
                  <Muted variant='caption'>
                    {`Epoch ${event.epoch}: ${event.text}${event.loss > 0 ? ` (−${formatInteger(event.loss)})` : ''}`}
                  </Muted>
                </li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      )}
    </article>
  )
}
