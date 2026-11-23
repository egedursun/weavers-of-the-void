import { useNavigate } from '@tanstack/react-router'
import { BookOpen, Compass, MapPinned, Mountain, Users } from 'lucide-react'
import { entityTypeValues } from '@/api/generated/schema'
import { formatCompact, formatDecimal } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  KeyValueList,
  PagedList,
  PageHeader,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { DialectDetails } from './DialectDetails'
import { RouteStatusChips } from './RouteStatusChips'
import { useCosmos, useWorldGuide } from './api'
import { indexCosmos } from './model/cosmosModel'
import { CLIMATE_LABEL, DISCOVERY_LABEL, humanize } from './model/labels'
import { useRuleBook } from './model/rules'

const LEAK_MAX = 100

function timeText(factor: number): string {
  if (factor === 1) return 'Normal flow'
  return factor < 1
    ? `Slow (×${formatDecimal(factor)})`
    : `Fast (×${formatDecimal(factor)})`
}

export function TravellersGuide({ id }: DrawerPageProps) {
  const worldId = Number(id)
  const valid = Number.isInteger(worldId) && worldId > 0
  const guide = useWorldGuide(valid ? worldId : null)
  const cosmos = useCosmos()
  const rules = useRuleBook()
  const navigate = useNavigate()
  if (!valid)
    return (
      <EmptyState
        icon={Compass}
        title='No such world'
        description='This link does not point to a world.'
      />
    )
  if (guide.isPending)
    return (
      <div className='flex flex-col gap-4'>
        <Skeleton className='h-control-lg w-2/3' />
        <Skeleton className='h-textarea w-full' />
      </div>
    )
  if (guide.isError)
    return (
      <Alert variant='destructive'>
        <Compass />
        <AlertTitle>The guide could not be read</AlertTitle>
        <AlertDescription>{guide.error.message}</AlertDescription>
      </Alert>
    )
  const data = guide.data
  const world = data.world
  const index = cosmos.data ? indexCosmos(cosmos.data) : undefined
  const climate = data.climate
    ? `${world.climate_era ? CLIMATE_LABEL[world.climate_era] : data.climate}${data.climate_epochs_left ? ` (${plural(data.climate_epochs_left, 'epoch', 'epochs')} left)` : ''}`
    : 'Mild, uncertain'
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <PageHeader
        title={world.name}
        eyebrow="Traveller's guide"
        icon={Compass}
        description={world.description ?? undefined}
        meta={
          <>
            <Badge variant='outline'>{data.type_label}</Badge>
            <Badge
              variant={world.discovery === 'known' ? 'success' : 'secondary'}
            >
              {DISCOVERY_LABEL[world.discovery]}
            </Badge>
          </>
        }
        actions={
          <>
            <Button
              onClick={() => void navigate({ href: `/map?world=${world.id}` })}
            >
              <MapPinned />
              Its map
            </Button>
            <Button variant='outline' asChild>
              <a href='/api/codex.zip' download>
                <BookOpen />
                Codex
              </a>
            </Button>
          </>
        }
      />
      <KeyValueList
        items={[
          {
            label: 'Star',
            value: data.star
              ? `${data.star}${data.star_type ? ` · ${data.star_type}` : ''}`
              : 'Starless',
          },
          ...(data.parent ? [{ label: 'Moon of', value: data.parent }] : []),
          { label: 'Time', value: timeText(world.time_factor) },
          { label: 'Atmosphere', value: humanize(data.atmosphere) },
          { label: 'Gravity', value: humanize(data.gravity) },
          { label: 'Climate', value: climate },
        ]}
      />
      <StatBar
        label='Leakage'
        value={world.leakage}
        max={LEAK_MAX}
        tone='warning'
        showMax={false}
      />
      {world.cosmology && (
        <Section title='Cosmology' level={3}>
          <Text variant='prose' italic>
            {world.cosmology}
          </Text>
        </Section>
      )}
      {world.phonology && (
        <Section
          title='Local dialect'
          description='How names are born here; a name that breaks it is judged by Fate.'
          level={3}
        >
          <DialectDetails phonology={world.phonology} />
        </Section>
      )}
      <Section title='Dangers' level={3}>
        {data.dangers.length === 0 ? (
          <Muted>Nothing here is known to hunt travellers.</Muted>
        ) : (
          <PagedList
            items={data.dangers}
            initial={5}
            noun={['danger', 'dangers']}
            className='flex min-w-0 flex-col gap-1.5'
            itemKey={(danger) => `${danger.id ?? danger.name}`}
          >
            {(danger) => (
              <li className='flex min-w-0 flex-wrap items-baseline gap-2'>
                {danger.id !== null ? (
                  <EntityLink kind='entity' id={String(danger.id)}>
                    {danger.name}
                  </EntityLink>
                ) : (
                  <Text as='span' weight='medium'>
                    {danger.name}
                  </Text>
                )}
                <Muted as='span' variant='caption'>
                  {danger.reason}
                </Muted>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      <Section title='Peoples' level={3}>
        {data.peoples.length === 0 ? (
          <Muted>No people lives here yet.</Muted>
        ) : (
          <PagedList
            items={data.peoples}
            initial={8}
            noun={['people', 'peoples']}
            className='flex min-w-0 flex-col gap-1.5'
            itemKey={(people) => people.id}
          >
            {(people) => (
              <li className='flex min-w-0 flex-wrap items-center gap-2'>
                <Users
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
                <EntityLink kind='entity' id={String(people.id)}>
                  {people.name}
                </EntityLink>
                <Muted as='span' variant='caption'>
                  {[
                    wordOf(entityTypeValues, people.entity_type),
                    `${formatCompact(people.population)} ${agree(people.population, 'soul', 'souls')}`,
                    people.language,
                    people.god ? `worships ${people.god}` : null,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </Muted>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      <Section title='Resources' level={3}>
        {data.resources.length === 0 ? (
          <Muted>No resource is recorded.</Muted>
        ) : (
          <PagedList
            items={data.resources}
            initial={8}
            noun={['resource', 'resources']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(resource) => resource.id}
          >
            {(resource) => (
              <li className='flex min-w-0 flex-col gap-1'>
                <span className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Mountain
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 text-muted-foreground'
                  />
                  <EntityLink kind='entity' id={String(resource.id)}>
                    {resource.name}
                  </EntityLink>
                  {resource.mechanics && (
                    <Badge size='sm' variant='outline'>
                      {humanize(resource.mechanics)}
                    </Badge>
                  )}
                  {resource.original && (
                    <Badge size='sm' variant='secondary'>
                      Unique to this world
                    </Badge>
                  )}
                </span>
                {resource.description && (
                  <Muted variant='caption'>{resource.description}</Muted>
                )}
              </li>
            )}
          </PagedList>
        )}
      </Section>
      <Section title='Roads' level={3}>
        {data.routes.length === 0 ? (
          <Muted>No known road leads here.</Muted>
        ) : (
          <PagedList
            items={data.routes}
            initial={6}
            noun={['route', 'routes']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(line) => line.id}
          >
            {(line) => {
              const live = index?.route(line.id)
              return (
                <li className='flex min-w-0 flex-col gap-1'>
                  <Text weight='medium'>{`${line.method} → ${line.target}`}</Text>
                  <Muted variant='caption'>{`${plural(line.duration, 'epoch', 'epochs')} · danger ${line.danger}${line.known ? '' : ' · hidden'}`}</Muted>
                  {live ? (
                    <RouteStatusChips route={live} rules={rules} />
                  ) : (
                    <Badge
                      size='sm'
                      variant={line.active ? 'success' : 'outline'}
                    >
                      {line.active ? 'Open' : 'Closed'}
                    </Badge>
                  )}
                </li>
              )
            }}
          </PagedList>
        )}
      </Section>
      <Section title='Native gods' level={3}>
        {data.foreign_gods.length === 0 ? (
          <Muted>No old god is known here.</Muted>
        ) : (
          <PagedList
            items={data.foreign_gods}
            initial={6}
            noun={['god', 'gods']}
            className='flex min-w-0 flex-col gap-1.5'
            itemKey={(god) => god.id}
          >
            {(god) => (
              <li className='flex min-w-0 flex-wrap items-center gap-2'>
                <EntityLink kind='foreign-god' id={String(god.id)}>
                  {god.name}
                </EntityLink>
                <Muted as='span' variant='caption'>
                  {[
                    god.title,
                    humanize(god.status),
                    `attitude ${god.attitude > 0 ? '+' : ''}${god.attitude}`,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </Muted>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      <Section title='Sky' level={3}>
        {data.sky.length === 0 ? (
          <Muted>The sky of this world holds nothing named.</Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Paged items={data.sky}>
              {(body) => (
                <EntityLink key={body.id} kind='entity' id={String(body.id)}>
                  {body.name}
                </EntityLink>
              )}
            </Paged>
          </div>
        )}
      </Section>
    </div>
  )
}
