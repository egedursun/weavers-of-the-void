import {
  CloudFog,
  Compass,
  Hourglass,
  Mountain,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Telescope,
  Wind,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NamedRecord } from '@/features/entity/NamedRecord'
import { CosmicActionButton } from './CosmicActionButton'
import { useDiscoverySummary, useSensedWorlds } from './api'
import { type CosmosIndex, crowdedRegions } from './model/cosmosModel'
import { HORIZON_STATUS_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const CROWDED_LIST_LENGTH = 4
const STEP_STATUS: Record<string, string> = {
  pending: 'Waiting',
  running: 'Being born',
  done: 'Born',
  failed: 'Failed',
  held: 'Held',
}

function SensedBirths() {
  const { data } = useSensedWorlds()
  const request = useCosmicAction({
    run: (intuitionId: number) =>
      unwrap(
        api.POST('/api/actions/sensed_world:request', {
          body: { intuition_id: intuitionId },
        })
      ),
  })
  const hold = useCosmicAction({
    run: ({ stepId, value }: { stepId: number; value: boolean }) =>
      unwrap(
        api.POST('/api/actions/sensed_world:hold', {
          body: { step_id: stepId, hold: value },
        })
      ),
  })
  const retry = useCosmicAction({
    run: (stepId: number) =>
      unwrap(
        api.POST('/api/actions/sensed_world:retry', {
          body: { step_id: stepId },
        })
      ),
  })
  const cancel = useCosmicAction({
    run: (stepId: number) =>
      unwrap(
        api.POST('/api/actions/sensed_world:cancel', {
          body: { step_id: stepId },
        })
      ),
  })
  if (!data || (data.steps.length === 0 && data.intuitions.length === 0))
    return null
  const open = data.steps.filter((step) => step.status !== 'done')
  const unqueued = data.intuitions.filter((item) => !item.queued)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Text weight='semibold'>Sensed worlds waiting to be born</Text>
      {open.length === 0 && unqueued.length === 0 && (
        <Muted variant='caption'>
          Every sensed world has been born or let go.
        </Muted>
      )}
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={open} as='li'>
          {(step) => (
            <li
              key={step.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Hourglass
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
              <Text as='span' variant='caption'>
                {step.seeker
                  ? `Sensed by ${step.seeker.name}`
                  : 'A sensed world'}
                {` · epoch ${step.epoch}${step.attempts ? ` · ${plural(step.attempts, 'attempt')}` : ''}`}
              </Text>
              <Badge
                size='sm'
                variant={step.status === 'failed' ? 'destructive' : 'outline'}
              >
                {STEP_STATUS[step.status] ?? step.status}
              </Badge>
              {step.result_world !== null && (
                <Text as='span' variant='caption'>
                  {'Became '}
                  <NamedRecord id={step.result_world} fallback='a world' />
                </Text>
              )}
              {(step.status === 'pending' || step.status === 'held') && (
                <CosmicActionButton
                  actionId='sensed_world:hold'
                  label={step.status === 'held' ? 'Release' : 'Hold'}
                  icon={step.status === 'held' ? Play : Pause}
                  variant='ghost'
                  size='sm'
                  pending={hold.isPending && hold.variables?.stepId === step.id}
                  onRun={() =>
                    hold.mutate({
                      stepId: step.id,
                      value: step.status !== 'held',
                    })
                  }
                />
              )}
              {step.status === 'failed' && (
                <CosmicActionButton
                  actionId='sensed_world:retry'
                  label='Try again'
                  icon={RotateCcw}
                  variant='ghost'
                  size='sm'
                  pending={retry.isPending && retry.variables === step.id}
                  onRun={() => retry.mutate(step.id)}
                />
              )}
              {step.status !== 'running' && (
                <CosmicActionButton
                  actionId='sensed_world:cancel'
                  label='Call off'
                  icon={X}
                  variant='ghost'
                  size='sm'
                  pending={cancel.isPending && cancel.variables === step.id}
                  onRun={() => cancel.mutate(step.id)}
                />
              )}
            </li>
          )}
        </Paged>
        <Paged items={unqueued} as='li'>
          {(item) => (
            <li
              key={`intuition-${item.id}`}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Telescope
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
              <Text as='span' variant='caption'>
                {item.seeker
                  ? `Sensed by ${item.seeker.name}`
                  : 'A sensed world'}
                {` · epoch ${item.epoch}`}
              </Text>
              <CosmicActionButton
                actionId='sensed_world:request'
                label='Bring it to birth'
                icon={Sparkles}
                variant='ghost'
                size='sm'
                pending={request.isPending && request.variables === item.id}
                onRun={() => request.mutate(item.id)}
              />
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}
const FOUND_LIST_LENGTH = 8

type HorizonSectionProps = {
  worldId: number
  index: CosmosIndex
  rules: RuleBook
}

export function HorizonSection({ worldId, index, rules }: HorizonSectionProps) {
  const { data, isLoading, error } = useDiscoverySummary()
  const round = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/worlds/{world_id}/discovery-round', {
          params: { path: { world_id: worldId } },
        })
      ),
    success: 'Exploration round finished',
  })
  const discard = useCosmicAction({
    run: (intuitionId: number) =>
      unwrap(
        api.POST('/api/actions/intuition:discard', {
          body: { intuition_id: intuitionId },
        })
      ),
  })
  const discardAll = useCosmicAction({
    run: () => unwrap(api.POST('/api/actions/intuition:discard_all')),
  })
  const world = index.world(worldId)
  const summary = data?.worlds.find((item) => item.world_id === worldId)
  const crowdedAt = rules.get('crowdedPerRegion')
  const cap = rules.get('explorationCap')
  const ratio =
    summary && summary.regions > 0 ? summary.communities / summary.regions : 0
  const cramped = crowdedAt !== undefined && ratio >= crowdedAt
  const places = index.placesOf(worldId)
  const crowded = crowdedRegions(
    places,
    index.communitiesOf(worldId),
    CROWDED_LIST_LENGTH
  )
  const found = places
    .filter(
      (place) =>
        place.pending_name ||
        (world && place.birth_epoch > world.world.created_epoch)
    )
    .sort((a, b) => b.birth_epoch - a.birth_epoch || b.id - a.id)
    .slice(0, FOUND_LIST_LENGTH)
  const sensed = (data?.sensed ?? []).filter(
    (item) =>
      item.world_id === worldId &&
      (item.status === 'pending' || item.status === 'processing')
  )
  const waiting = (data?.sensed ?? []).filter(
    (item) => item.status === 'pending'
  ).length
  return (
    <Section title='Horizon and exploration' level={3}>
      {isLoading && <Skeleton className='h-control-lg w-full' />}
      {error && <Text tone='destructive'>{error.message}</Text>}
      {summary && (
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge variant='outline'>{`${plural(summary.regions, 'region', 'regions')}`}</Badge>
          <Badge variant='outline'>{`${plural(summary.places, 'place')}`}</Badge>
          <Badge
            variant='outline'
            title={`Land counts as cramped at ${ruleText(crowdedAt)} communities per region or more.`}
          >
            {`${formatDecimal(ratio, 1)} ${ratio === 1 ? 'community' : 'communities'} per region`}
          </Badge>
          <Badge variant={cramped ? 'warning' : 'success'}>
            {cramped ? 'Cramped lands' : 'Enough land'}
          </Badge>
        </div>
      )}
      {crowded.length > 0 && (
        <Muted>
          {'Most crowded regions: '}
          {crowded.map((entry, position) => (
            <span key={entry.region.id}>
              {position > 0 && ', '}
              <EntityLink kind='entity' id={String(entry.region.id)}>
                {entry.region.name}
              </EntityLink>
              {` (${entry.count})`}
            </span>
          ))}
        </Muted>
      )}
      {found.length === 0 ? (
        <Muted>No land has been discovered in this world yet.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={found} as='li'>
            {(place) => (
              <li
                key={place.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Mountain
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
                <EntityLink kind='entity' id={String(place.id)}>
                  {place.name}
                </EntityLink>
                <Muted as='span' variant='caption'>
                  {`${place.entity_type === 'region' ? 'Region' : 'Place'} · epoch ${place.birth_epoch}`}
                </Muted>
                {place.pending_name && (
                  <Badge size='sm' variant='secondary'>
                    Fate will name it
                  </Badge>
                )}
              </li>
            )}
          </Paged>
        </ul>
      )}
      {sensed.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={sensed} as='li'>
            {(item) => (
              <li
                key={item.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Telescope
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-primary'
                />
                <Text as='span' variant='caption'>
                  {'Sensed by '}
                  <EntityLink kind='entity' id={String(item.mortal_entity_id)}>
                    {index.entityName(item.mortal_entity_id) ?? 'a mortal'}
                  </EntityLink>
                  {` in epoch ${item.epoch}${item.how ? `: ${item.how}` : ''}`}
                </Text>
                <Badge size='sm' variant='outline'>
                  {HORIZON_STATUS_LABEL[item.status]}
                </Badge>
                {item.result_world_id !== null && (
                  <Text as='span' variant='caption'>
                    {'Found as '}
                    <NamedRecord id={item.result_world_id} fallback='a world' />
                  </Text>
                )}
                {item.status === 'pending' && (
                  <CosmicActionButton
                    actionId='intuition:discard'
                    label='Let it go'
                    icon={Wind}
                    variant='ghost'
                    size='sm'
                    pending={discard.isPending && discard.variables === item.id}
                    onRun={() => discard.mutate(item.id)}
                  />
                )}
              </li>
            )}
          </Paged>
        </ul>
      )}
      <SensedBirths />
      <Muted variant='caption'>
        {`Each epoch a community or explorer sets out on its own with a ${ruleText(rules.get('explorationBase'))}% chance, at most ${ruleText(cap)} new lands per world; cramped land pushes harder. Tune these in World rules › Exploration.`}
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CosmicActionButton
          actionId='discovery_round'
          label='Exploration round'
          icon={Compass}
          pending={round.isPending}
          blockedReason={
            cap === 0
              ? 'Exploration is off (Exploration › per-epoch cap is 0).'
              : undefined
          }
          onRun={() => round.mutate()}
        />
        <Muted variant='caption'>
          The engine rolls this world's exploration dice now.
        </Muted>
      </div>
      {waiting > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <CosmicActionButton
            actionId='intuition:discard_all'
            label='Let every intuition go'
            icon={CloudFog}
            pending={discardAll.isPending}
            confirm={{
              title: 'Let every waiting intuition go?',
              description: `${plural(waiting, 'sensed world')} in every world will stay legends; Fate will not give them birth.`,
              confirmText: 'Let them go',
            }}
            onRun={() => discardAll.mutate()}
          />
          <Muted variant='caption'>
            {`${plural(waiting, 'intuition')} still wait for Fate in the whole cosmos.`}
          </Muted>
        </div>
      )}
    </Section>
  )
}
