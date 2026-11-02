import { CloudFog, Compass, Mountain, Telescope, Wind } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { useDiscoverySummary } from './api'
import { type CosmosIndex, crowdedRegions } from './model/cosmosModel'
import { HORIZON_STATUS_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const CROWDED_LIST_LENGTH = 4
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
          <Badge variant='outline'>{`${summary.regions} regions`}</Badge>
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
          {found.map((place) => (
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
          ))}
        </ul>
      )}
      {sensed.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-1.5'>
          {sensed.map((item) => (
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
          ))}
        </ul>
      )}
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
