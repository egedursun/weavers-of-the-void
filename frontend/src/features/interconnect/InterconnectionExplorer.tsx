import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { navItem } from '@/config/navigation'
import { Atom, Boxes, Network, Search, Waypoints } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  KpiTile,
  Medallion,
  PageHeader,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { named } from '@/features/entity/environment/labels'
import { badgeVariant } from '@/features/entity/realm/labels'
import { ChoiceCard } from '@/features/entity/realm/parts'
import { DIRECTION, EDGE_KIND, SUBSYSTEM, heat } from './labels'

type Graph = components['schemas']['MechanicsGraphView']
type Link = components['schemas']['SubsystemLink']
type Mechanic = components['schemas']['MechanicRecord']

const ITEM = navItem('interconnections')
const HEAT = [
  'bg-background',
  'bg-primary/10',
  'bg-primary/25',
  'bg-primary/50',
] as const
const CARRIER_PAGE = 24
const LINK_PAGE = 20
const MECHANIC_PAGE = 30
const MECHANIC_KEY_PAGE = 8

function SubsystemTag({ value }: { value: string }) {
  const spec = named(SUBSYSTEM, value)
  const Icon = spec.icon
  return (
    <Badge size='sm' variant={badgeVariant(spec.tone)}>
      <Icon aria-hidden='true' />
      {spec.label}
    </Badge>
  )
}

function RowHead({ value }: { value: string }) {
  const spec = named(SUBSYSTEM, value)
  const Icon = spec.icon
  return (
    <span className='flex items-center gap-1 whitespace-nowrap'>
      <Icon aria-hidden='true' className='size-icon-sm text-muted-foreground' />
      <Muted as='span' variant='caption'>
        {spec.label}
      </Muted>
    </span>
  )
}

function Carriers({ carriers }: { carriers: readonly string[] }) {
  const more = useShowMore(carriers, CARRIER_PAGE)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {more.visible.map((carrier) => (
          <Badge key={carrier} size='sm' variant='outline'>
            {carrier}
          </Badge>
        ))}
      </div>
      <ShowMore state={more} noun={['carrier', 'carriers']} />
    </div>
  )
}

export function SubsystemMatrix({
  graph,
  chosen,
  onPick,
}: {
  graph: Graph
  chosen: Link | null
  onPick: (link: Link) => void
}) {
  const keys = graph.subsystems.map((item) => item.key)
  const cells = new Map(
    graph.links.map((link) => [`${link.source}>${link.target}`, link])
  )
  const most = Math.max(
    1,
    ...graph.links
      .filter((link) => link.source !== link.target)
      .map((link) => link.edges)
  )
  return (
    <div
      data-surface='SubsystemMatrix'
      className='min-w-0 overflow-x-auto rounded-lg border'
    >
      <table className='border-collapse'>
        <caption className='sr-only'>Which subsystem feeds which</caption>
        <thead>
          <tr>
            <th
              scope='col'
              className='sticky left-0 bg-background p-1 text-left'
            >
              <Muted variant='caption'>From ↓</Muted>
            </th>
            {keys.map((key) => {
              const spec = named(SUBSYSTEM, key)
              const Icon = spec.icon
              return (
                <th key={key} scope='col' className='p-1' title={spec.label}>
                  <Icon
                    aria-label={spec.label}
                    className='mx-auto size-icon-sm text-muted-foreground'
                  />
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {keys.map((source) => (
            <tr key={source}>
              <th
                scope='row'
                className='sticky left-0 bg-background p-1 text-left'
                title={named(SUBSYSTEM, source).label}
              >
                <RowHead value={source} />
              </th>
              {keys.map((target) => {
                const link = cells.get(`${source}>${target}`)
                const level =
                  link && source !== target ? heat(link.edges, most) : 0
                const active =
                  chosen !== null &&
                  link !== undefined &&
                  chosen.source === link.source &&
                  chosen.target === link.target
                return (
                  <td key={target} className='p-0.5'>
                    <Button
                      variant='outline'
                      size='icon-sm'
                      disabled={!link}
                      disabledReason={link ? undefined : 'Nothing flows here.'}
                      aria-label={`${named(SUBSYSTEM, source).label} to ${named(SUBSYSTEM, target).label}: ${plural(link ? link.carriers.length : 0, 'carrier', 'carriers')}`}
                      aria-pressed={active}
                      onClick={() => link && onPick(link)}
                      className={cn(
                        'tabular-nums',
                        HEAT[level],
                        active && 'border-primary',
                        source === target && link && 'bg-muted'
                      )}
                    >
                      {link ? link.carriers.length : ''}
                    </Button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MechanicKeys({
  keys,
  titles,
  onMechanic,
}: {
  keys: readonly string[]
  titles: Map<string, string>
  onMechanic: (key: string) => void
}) {
  const more = useShowMore(keys, MECHANIC_KEY_PAGE)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {more.visible.map((key) =>
          titles.has(key) ? (
            <Button
              key={key}
              size='sm'
              variant='outline'
              onClick={() => onMechanic(key)}
            >
              {titles.get(key)}
            </Button>
          ) : (
            <Badge key={key} size='sm' variant='secondary'>
              {key.replaceAll('_', ' ')}
            </Badge>
          )
        )}
      </div>
      <ShowMore state={more} noun={['mechanic', 'mechanics']} />
    </div>
  )
}

function LinkDetail({
  link,
  titles,
  onMechanic,
}: {
  link: Link
  titles: Map<string, string>
  onMechanic: (key: string) => void
}) {
  return (
    <div
      data-surface='SubsystemLink'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <SubsystemTag value={link.source} />
        <Text as='span'>feeds</Text>
        <SubsystemTag value={link.target} />
        {link.kinds.map((kind) => {
          const spec = named(EDGE_KIND, kind)
          return (
            <Badge key={kind} size='sm' variant={badgeVariant(spec.tone)}>
              {spec.label}
            </Badge>
          )
        })}
      </div>
      <Label variant='overline'>{`Carried by ${plural(link.carriers.length, 'value', 'values')}`}</Label>
      <Carriers carriers={link.carriers} />
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        {(['writers', 'readers'] as const).map((side) => (
          <div key={side} className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>
              {`${side === 'writers' ? 'Written by' : 'Read by'} (${link[side].length})`}
            </Label>
            <MechanicKeys
              keys={link[side]}
              titles={titles}
              onMechanic={onMechanic}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function MechanicDetail({
  mechanic,
  onMechanic,
}: {
  mechanic: Mechanic
  onMechanic: (key: string) => void
}) {
  const detail = useQuery({
    queryKey: ['mechanics', 'links', mechanic.key] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/mechanics/{key}/links', {
          params: { path: { key: mechanic.key } },
        })
      ),
  })
  const links = detail.data?.links ?? []
  const more = useShowMore(links, LINK_PAGE)
  return (
    <div
      data-surface='MechanicLinks'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={named(SUBSYSTEM, mechanic.subsystem).icon}
          tone={named(SUBSYSTEM, mechanic.subsystem).tone ?? 'gold'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {mechanic.title}
          </Text>
          <Muted
            variant='caption'
            truncate
          >{`Spec ${mechanic.spec_item} · steps ${mechanic.phases.join(', ') || 'none'} · shown in ${mechanic.surfaces.map((surface) => surface.replace(/-/g, ' ')).join(', ') || 'no view'}`}</Muted>
        </div>
        <SubsystemTag value={mechanic.subsystem} />
      </div>
      {detail.data && links.length === 0 && (
        <Muted>It neither feeds nor reads another mechanic.</Muted>
      )}
      <ul className='flex min-w-0 flex-col gap-1.5'>
        {more.visible.map((link) => {
          const direction = named(DIRECTION, link.direction)
          const kind = named(EDGE_KIND, link.kind)
          const Icon = direction.icon
          return (
            <li
              key={`${link.direction}-${link.other}-${link.kind}`}
              className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border p-2'
            >
              <Icon
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
              <Text as='span' weight='medium'>
                {direction.label}
              </Text>
              {link.other_title ? (
                <Button
                  size='sm'
                  variant='link'
                  onClick={() => onMechanic(link.other)}
                >
                  {link.other_title}
                </Button>
              ) : (
                <Text as='span'>
                  {link.other.replaceAll('_', ' ') || 'the world'}
                </Text>
              )}
              {link.other_subsystem && (
                <SubsystemTag value={link.other_subsystem} />
              )}
              <Badge size='sm' variant={badgeVariant(kind.tone)}>
                {kind.label}
              </Badge>
              <Muted variant='caption' className='min-w-0 flex-1' truncate>
                {link.carriers.join(', ')}
              </Muted>
            </li>
          )
        })}
      </ul>
      <ShowMore state={more} noun={['link', 'links']} />
    </div>
  )
}

const GHOST_TILES = ['subsystems', 'mechanics', 'links', 'carriers']

export function InterconnectionExplorer() {
  const graph = useQuery({
    queryKey: ['mechanics', 'graph'] as const,
    queryFn: () => unwrap(api.GET('/api/mechanics/graph')),
  })
  const [chosen, setChosen] = useState<Link | null>(null)
  const [mechanicKey, setMechanicKey] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const data = graph.data
  const titles = useMemo(
    () =>
      new Map((data?.mechanics ?? []).map((item) => [item.key, item.title])),
    [data]
  )
  const found = (data?.mechanics ?? []).filter((item) =>
    `${item.title} ${item.key} ${item.subsystem} ${item.spec_item}`
      .toLowerCase()
      .includes(search.toLowerCase())
  )
  const page = useShowMore(found, MECHANIC_PAGE)
  const mechanic =
    data?.mechanics.find((item) => item.key === mechanicKey) ?? null
  const crossLinks = (data?.links ?? []).filter(
    (link) => link.source !== link.target
  )
  const modifierLinks = crossLinks.filter((link) =>
    link.kinds.includes('modifier')
  ).length
  return (
    <div
      data-surface='InterconnectionExplorer'
      className='@container/explorer flex min-w-0 flex-col gap-6'
    >
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      {!data ? (
        <div
          aria-busy='true'
          aria-label='Reading the registry'
          className='flex min-w-0 flex-col gap-6'
        >
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/explorer:grid-cols-2 @3xl/explorer:grid-cols-4'>
            {GHOST_TILES.map((key) => (
              <Skeleton key={key} className='h-32 rounded-xl' />
            ))}
          </div>
          <Skeleton className='h-control-lg w-1/3' />
          <Skeleton className='h-96 rounded-xl' />
        </div>
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/explorer:grid-cols-2 @3xl/explorer:grid-cols-4'>
            <KpiTile
              label='Subsystems'
              value={data.subsystems.length}
              icon={Boxes}
            />
            <KpiTile
              label='Mechanics'
              value={data.mechanics.length}
              icon={Network}
              tone='verdigris'
            />
            <KpiTile
              label='Cross-subsystem links'
              value={crossLinks.length}
              icon={Waypoints}
              tone='info'
            />
            <KpiTile
              label='Links carried by modifiers'
              value={modifierLinks}
              icon={Atom}
              tone='gold'
            />
          </div>
          <Section
            id='section-matrix'
            title='Who feeds whom'
            description='Each cell counts the values one subsystem writes and another reads. Pick a cell to see them.'
            icon={Waypoints}
          >
            <div className='flex min-w-0 flex-col gap-3'>
              <SubsystemMatrix
                graph={data}
                chosen={chosen}
                onPick={setChosen}
              />
              {chosen && (
                <LinkDetail
                  link={chosen}
                  titles={titles}
                  onMechanic={setMechanicKey}
                />
              )}
            </div>
          </Section>
          <Section
            id='section-mechanic-list'
            title='Mechanics'
            description='Every registered mechanic; pick one to see what it feeds and what it reads.'
            icon={Network}
          >
            <div className='flex min-w-0 flex-col gap-3'>
              <div className='flex min-w-0 items-center gap-2'>
                <Search
                  aria-hidden='true'
                  className='size-icon-sm text-muted-foreground'
                />
                <Input
                  aria-label='Find a mechanic'
                  placeholder='Find a mechanic'
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
              {mechanic && (
                <MechanicDetail
                  mechanic={mechanic}
                  onMechanic={setMechanicKey}
                />
              )}
              <ul className='grid min-w-0 grid-cols-1 gap-2 @2xl/explorer:grid-cols-2 @5xl/explorer:grid-cols-3'>
                {page.visible.map((item) => {
                  const spec = named(SUBSYSTEM, item.subsystem)
                  return (
                    <li key={item.key}>
                      <ChoiceCard
                        spec={{
                          label: item.title,
                          icon: spec.icon,
                          tone: spec.tone,
                        }}
                        hint={`${spec.label} · ${item.spec_item}`}
                        selected={mechanicKey === item.key}
                        count={item.couplings.length}
                        onSelect={() => setMechanicKey(item.key)}
                      />
                    </li>
                  )
                })}
              </ul>
              <ShowMore state={page} noun={['mechanic', 'mechanics']} />
            </div>
          </Section>
        </>
      )}
    </div>
  )
}
