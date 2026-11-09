import {
  CalendarDays,
  Eye,
  Flame,
  Globe2,
  Hourglass,
  Layers,
  Orbit,
  Shield,
  Sparkles,
  Workflow,
  Zap,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  PagedList,
  Section,
} from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Label, Muted, Stat } from '@/components/typography'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { BeingCard } from '../BeingsPanel'
import { EventsPanel } from '../EventsPanel'
import { RiftsPanel } from '../RiftsPanel'
import {
  type CosmographyCatalog,
  type DimensionRecord,
  catalogLabel,
  catalogTable,
  useCosmographyAction,
} from '../api'
import { CreateClusterStudio, CreateGalaxyStudio } from '../create/CreateStudio'
import { CAUSALITIES, ELEMENTS } from '../labels'
import { type Ladder, nameTable } from '../ladder'
import { Chip, Facts, Meter, NodeLink, RecordEditor } from '../parts'
import { ClusterThumb, DimensionSigil } from '../visual/ScaleThumbs'
import { sigilOf } from '../visual/sigil'
import { GalaxyCard } from './ClusterWiki'
import { pageId, useScaleData } from './data'
import {
  DangerZone,
  Missing,
  WikiError,
  WikiHero,
  WikiLoading,
  WikiRecords,
} from './shared'

type Edit = { values: Record<string, unknown>; release: string[] }

const DISCOVERY = {
  known: 'Known',
  legend: 'A legend',
  unknown: 'Unknown',
  forgotten: 'Forgotten',
}
const PERCENT = 100

function DimensionHero({
  dimension,
  ladder,
  catalog,
  cover,
}: {
  dimension: DimensionRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  cover: string | null
}) {
  return (
    <WikiHero
      nodeId={dimension.id}
      name={dimension.name}
      overline={`Dimension · ${catalogLabel(catalog.dimension_kinds, dimension.dimension_kind)}`}
      description={dimension.description}
      cover={cover}
      emblem={
        <DimensionSigil
          dimension={sigilOf(dimension)}
          label={dimension.name}
          className='size-portrait-xl shrink-0'
        />
      }
      badges={
        <>
          <Badge size='sm' variant='default'>
            <Hourglass />
            {`Time ×${dimension.time_factor}`}
          </Badge>
          <Badge size='sm' variant='outline'>
            {CAUSALITIES[dimension.causality]}
          </Badge>
          {dimension.element && (
            <Badge size='sm' variant='outline'>
              {ELEMENTS[dimension.element]}
            </Badge>
          )}
          {dimension.parent_dimension_id !== null && (
            <Badge size='sm' variant='outline'>
              <Layers />
              <EntityLink
                kind='dimension'
                id={String(dimension.parent_dimension_id)}
              >
                {ladder.names.get(dimension.parent_dimension_id) ??
                  'Its outer dimension'}
              </EntityLink>
            </Badge>
          )}
          <Badge size='sm' variant='outline'>
            <CalendarDays />
            {`Since epoch ${dimension.created_epoch}`}
          </Badge>
          {dimension.locked.length > 0 && (
            <Badge
              size='sm'
              variant='warning'
            >{`${dimension.locked.length} values held`}</Badge>
          )}
        </>
      }
      meter={
        <div className='flex max-w-sm min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 items-center justify-between gap-2'>
            <Label>Veil</Label>
            <Stat value={dimension.veil} unit={`/ ${PERCENT}`} />
          </div>
          <Progress
            size='sm'
            value={dimension.veil}
            tone='info'
            aria-label='Veil'
          />
          <Muted variant='caption'>
            A thin veil lets rifts, beings and leak through.
          </Muted>
        </div>
      }
    />
  )
}

export function DimensionView({ dimensionId }: { dimensionId: number }) {
  const { view, catalog, wiki, ladder } = useScaleData(dimensionId)
  const edit = useCosmographyAction<Edit>(
    'dimension:edit',
    (vars) => ({ dimension_id: dimensionId, ...vars }),
    'The dimension is reshaped'
  )
  if (view.isPending || !catalog) return <WikiLoading />
  if (view.isError)
    return (
      <WikiError
        icon={Layers}
        title='The dimension could not be read'
        message={view.error.message}
      />
    )
  const dimension = ladder?.data.dimensions.find(
    (row) => row.id === dimensionId
  )
  if (!ladder || !dimension)
    return <Missing icon={Layers} title='No such dimension' />
  const clusters = ladder.clustersIn(dimension.id)
  const loose = ladder.looseGalaxies(dimension.id)
  const galaxies = ladder.data.galaxies.filter(
    (row) => ladder.dimensionOfGalaxy(row) === dimension.id
  )
  const worlds = ladder.data.placements.filter(
    (row) => row.dimension_id === dimension.id
  )
  const inner = ladder.data.dimensions.filter(
    (row) => row.parent_dimension_id === dimension.id
  )
  const beings = ladder.data.beings.filter(
    (row) => row.home_dimension_id === dimension.id
  )
  const busy = edit.isPending ? 'Working' : null
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <DimensionHero
        dimension={dimension}
        ladder={ladder}
        catalog={catalog}
        cover={wiki?.cover ?? null}
      />
      <Section title='At a glance' icon={Layers} tone='info'>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
          <MiniStat
            icon={Workflow}
            tone='verdigris'
            label='Clusters'
            value={clusters.length}
          />
          <MiniStat
            icon={Orbit}
            tone='gold'
            label='Galaxies'
            value={galaxies.length}
          />
          <MiniStat
            icon={Globe2}
            tone='info'
            label='Worlds'
            value={worlds.length}
          />
          <MiniStat
            icon={Shield}
            tone='success'
            label='Stability'
            value={`${dimension.stability}%`}
          />
          <MiniStat
            icon={Sparkles}
            tone='verdigris'
            label='Magic'
            value={`${dimension.magic}%`}
          />
          <MiniStat
            icon={Flame}
            tone='danger'
            label='Hostility'
            value={`${dimension.hostility}%`}
          />
          <MiniStat
            icon={Zap}
            tone='warning'
            label='Leak'
            value={`${dimension.leak}%`}
          />
          <MiniStat
            icon={Eye}
            tone='danger'
            label='Sanity drain'
            value={dimension.sanity_drain}
          />
        </div>
      </Section>
      <Section
        title='What it holds'
        description='Its clusters and the galaxies that drift outside any cluster.'
        icon={Workflow}
        tone='verdigris'
      >
        <div className='flex min-w-0 flex-col gap-3'>
          {clusters.length === 0 && loose.length === 0 ? (
            <EmptyState
              icon={Workflow}
              size='compact'
              title='An empty dimension'
              description='Gather a cluster or set a galaxy in it below.'
            />
          ) : (
            <>
              {clusters.length > 0 && (
                <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
                  {clusters.map((row) => (
                    <li
                      key={row.id}
                      className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-2'
                    >
                      <ClusterThumb
                        cluster={{
                          id: row.id,
                          kind: row.cluster_kind,
                          galaxies: ladder.galaxiesIn(row.id).length,
                          heat: row.medium_heat,
                        }}
                        label={row.name}
                        className='size-portrait-lg shrink-0'
                      />
                      <span className='flex min-w-0 flex-col gap-1'>
                        <EntityLink kind='cluster' id={String(row.id)}>
                          {row.name}
                        </EntityLink>
                        <span className='flex min-w-0 flex-wrap gap-1.5'>
                          <Chip>
                            {catalogLabel(
                              catalog.cluster_kinds,
                              row.cluster_kind
                            )}
                          </Chip>
                          <Chip
                            icon={Orbit}
                          >{`${plural(ladder.galaxiesIn(row.id).length, 'galaxy', 'galaxies')}`}</Chip>
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {loose.length > 0 && (
                <PagedList
                  items={loose}
                  initial={4}
                  noun={['galaxy', 'galaxies']}
                  className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'
                  itemKey={(row) => row.id}
                >
                  {(row) => (
                    <GalaxyCard
                      galaxy={row}
                      ladder={ladder}
                      catalog={catalog}
                    />
                  )}
                </PagedList>
              )}
            </>
          )}
          <div className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'>
            <CreateClusterStudio
              ladder={ladder}
              catalog={catalog}
              dimensionId={dimension.id}
            />
            <CreateGalaxyStudio
              ladder={ladder}
              catalog={catalog}
              dimensionId={dimension.id}
            />
          </div>
        </div>
      </Section>
      <Section title='Worlds in this dimension' icon={Globe2} tone='info'>
        {worlds.length === 0 ? (
          <EmptyState
            icon={Globe2}
            size='compact'
            title='No world lies here'
            description='Move a world, its star or its galaxy into this dimension.'
          />
        ) : (
          <PagedList
            items={worlds}
            initial={8}
            noun={['world', 'worlds']}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
            itemKey={(row) => row.world_id}
          >
            {(row) => (
              <li className='flex min-w-0 items-center justify-between gap-2 rounded-xl border bg-background p-3'>
                <EntityLink kind='world' id={String(row.world_id)}>
                  {ladder.data.world_names[String(row.world_id)] ??
                    `World #${row.world_id}`}
                </EntityLink>
                <span className='flex shrink-0 flex-wrap gap-1.5'>
                  <Chip icon={Hourglass}>{`×${row.pull.time.toFixed(2)}`}</Chip>
                  <Chip icon={Sparkles}>{`+${row.pull.magic}`}</Chip>
                </span>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      {inner.length > 0 && (
        <Section title='Dimensions within it' icon={Layers} tone='info'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            {inner.map((row) => (
              <li
                key={row.id}
                className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-2'
              >
                <DimensionSigil
                  dimension={sigilOf(row)}
                  label={row.name}
                  className='size-portrait-lg shrink-0'
                />
                <span className='flex min-w-0 flex-col gap-1'>
                  <EntityLink kind='dimension' id={String(row.id)}>
                    {row.name}
                  </EntityLink>
                  <Chip>
                    {catalogLabel(catalog.dimension_kinds, row.dimension_kind)}
                  </Chip>
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <Section
        id='section-dimension'
        title='Shape the dimension'
        description='Veil, stability, time, magic and every other value you set are held.'
        icon={Layers}
        tone='info'
        surface='card'
      >
        <div
          data-surface='DimensionPage'
          className='flex min-w-0 flex-col gap-4'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Meter label='Veil' value={dimension.veil} tone='info' />
            <Meter
              label='Stability'
              value={dimension.stability}
              tone='success'
            />
            <Meter label='Magic' value={dimension.magic} tone='success' />
            <Meter
              label='Hostility'
              value={dimension.hostility}
              tone='destructive'
            />
            <Meter label='Leak' value={dimension.leak} tone='warning' />
          </div>
          <Facts
            items={[
              [
                'Kind',
                catalogLabel(catalog.dimension_kinds, dimension.dimension_kind),
              ],
              ['Time against the prime', `×${dimension.time_factor}`],
              ['Causality', CAUSALITIES[dimension.causality]],
              [
                'Ruler',
                <NodeLink
                  key='ruler'
                  kind='son'
                  id={dimension.ruler_node_id}
                  name={dimension.ruler_node_id !== null ? null : 'None'}
                />,
              ],
              ['Known', DISCOVERY[dimension.discovery]],
            ]}
          />
          <RecordEditor
            title='Form and account'
            note='Its name, kind, element and account.'
            fields={[
              { key: 'name', label: 'Name', kind: 'text' },
              {
                key: 'dimension_kind',
                label: 'Kind',
                kind: 'pick',
                table: catalogTable(catalog.dimension_kinds),
              },
              {
                key: 'element',
                label: 'Element',
                kind: 'pick',
                table: ELEMENTS,
              },
              {
                key: 'causality',
                label: 'Causality',
                kind: 'pick',
                table: CAUSALITIES,
              },
              {
                key: 'description',
                label: 'Account',
                kind: 'text',
                long: true,
              },
            ]}
            locked={dimension.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
          <RecordEditor
            title='Laws of the dimension'
            note='How thin its veil is, how steady, how fast its time runs and what it does to those inside.'
            fields={[
              { key: 'veil', label: 'Veil', kind: 'number', min: 0, max: 100 },
              {
                key: 'stability',
                label: 'Stability',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'time_factor',
                label: 'Time against the prime',
                kind: 'decimal',
                min: 0.01,
              },
              {
                key: 'magic',
                label: 'Magic',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'hostility',
                label: 'Hostility',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'sanity_drain',
                label: 'Sanity drain',
                kind: 'number',
                min: 0,
              },
              { key: 'leak', label: 'Leak', kind: 'number', min: 0, max: 100 },
              {
                key: 'parent_dimension_id',
                label: 'Lies within',
                kind: 'pick',
                table: nameTable(
                  ladder.data.dimensions.filter(
                    (row) => row.id !== dimension.id
                  )
                ),
              },
              {
                key: 'discovery',
                label: 'Known',
                kind: 'pick',
                table: DISCOVERY,
              },
            ]}
            locked={dimension.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </div>
      </Section>
      <RiftsPanel ladder={ladder} dimensionId={dimension.id} />
      <EventsPanel
        ladder={ladder}
        catalog={catalog}
        dimensionId={dimension.id}
      />
      <Section title='Beings of this dimension' icon={Eye} tone='warning'>
        {beings.length === 0 ? (
          <EmptyState
            icon={Eye}
            size='compact'
            title='No being calls it home'
            description='Call one from the Heavens.'
          />
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {beings.map((row) => (
              <BeingCard
                key={row.entity_id}
                being={row}
                ladder={ladder}
                catalog={catalog}
              />
            ))}
          </ul>
        )}
      </Section>
      <WikiRecords
        nodeId={dimension.id}
        name={dimension.name}
        wiki={wiki}
        prompt={dimension.image_prompt}
        action='dimension:edit'
        target={{ dimension_id: dimension.id }}
      />
      <DangerZone
        noun='dimension'
        name={dimension.name}
        consequence='Its clusters, galaxies, worlds and inner dimensions pass to the dimension that held it.'
        action='dimension:delete'
        target={{ dimension_id: dimension.id }}
      />
      <ThingSections nodeId={dimension.id} />
    </div>
  )
}

export function DimensionPage({ id }: DrawerPageProps) {
  const value = pageId(id)
  return value === null ? (
    <Missing icon={Layers} title='No such dimension' />
  ) : (
    <DimensionView dimensionId={value} />
  )
}
