import {
  CalendarDays,
  Flame,
  Globe2,
  Layers,
  Orbit,
  Ruler,
  Star,
  Workflow,
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
import { Label, Stat } from '@/components/typography'
import { CelestialDepthSection } from '@/features/celestial/CelestialDepthSection'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import {
  type ClusterRecord,
  type CosmographyCatalog,
  type GalaxyRecord,
  catalogLabel,
  catalogTable,
  useCosmographyAction,
} from '../api'
import { CreateGalaxyStudio } from '../create/CreateStudio'
import { GALAXY_AGES, NUCLEI } from '../labels'
import { type Ladder, nameTable } from '../ladder'
import { Chip, Facts, Meter, RecordEditor } from '../parts'
import { GalaxyThumb } from '../visual/GalaxyThumb'
import { ClusterThumb } from '../visual/ScaleThumbs'
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

export function GalaxyCard({
  galaxy,
  ladder,
  catalog,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
}) {
  const stars = ladder.data.stars.filter(
    (row) => row.galaxy_id === galaxy.id
  ).length
  const worlds = ladder.data.placements.filter(
    (row) => row.galaxy_id === galaxy.id
  ).length
  const nucleus = NUCLEI[galaxy.nucleus]
  return (
    <li className='flex min-w-0 flex-col overflow-hidden rounded-xl border bg-card'>
      <GalaxyThumb
        galaxy={galaxy}
        shape={catalog.shape}
        label={galaxy.name}
        points={2600}
        className='aspect-video w-full rounded-none'
      />
      <div className='flex min-w-0 flex-col gap-2 p-3'>
        <EntityLink kind='galaxy' id={String(galaxy.id)}>
          {galaxy.name}
        </EntityLink>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip>{catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}</Chip>
          <Chip icon={nucleus.icon}>{nucleus.label}</Chip>
          <Chip>{GALAXY_AGES[galaxy.age_stage]}</Chip>
          <Chip icon={Star}>{`${plural(stars, 'star')}`}</Chip>
          <Chip icon={Globe2}>{`${plural(worlds, 'world')}`}</Chip>
        </div>
      </div>
    </li>
  )
}

function ClusterHero({
  cluster,
  ladder,
  catalog,
  cover,
}: {
  cluster: ClusterRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  cover: string | null
}) {
  const dimensionId = ladder.dimensionOfCluster(cluster)
  return (
    <WikiHero
      nodeId={cluster.id}
      name={cluster.name}
      overline={`Cluster · ${catalogLabel(catalog.cluster_kinds, cluster.cluster_kind)}`}
      description={cluster.description}
      cover={cover}
      emblem={
        <ClusterThumb
          cluster={{
            id: cluster.id,
            kind: cluster.cluster_kind,
            galaxies: ladder.galaxiesIn(cluster.id).length,
            heat: cluster.medium_heat,
          }}
          label={cluster.name}
          className='size-portrait-xl shrink-0'
        />
      }
      badges={
        <>
          {cluster.parent_cluster_id !== null && (
            <Badge size='sm' variant='outline'>
              <Workflow />
              <EntityLink kind='cluster' id={String(cluster.parent_cluster_id)}>
                {ladder.names.get(cluster.parent_cluster_id) ??
                  'Its supercluster'}
              </EntityLink>
            </Badge>
          )}
          {dimensionId !== null && (
            <Badge size='sm' variant='outline'>
              <Layers />
              <EntityLink kind='dimension' id={String(dimensionId)}>
                {ladder.names.get(dimensionId) ?? 'Its dimension'}
              </EntityLink>
            </Badge>
          )}
          <Badge size='sm' variant='outline'>
            <CalendarDays />
            {`Since epoch ${cluster.created_epoch}`}
          </Badge>
          {cluster.locked.length > 0 && (
            <Badge
              size='sm'
              variant='warning'
            >{`${cluster.locked.length} values held`}</Badge>
          )}
        </>
      }
      meter={
        <div className='flex max-w-sm min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 items-center justify-between gap-2'>
            <Label>Heat of the medium</Label>
            <Stat value={cluster.medium_heat} unit={`/ ${PERCENT}`} />
          </div>
          <Progress
            size='sm'
            value={cluster.medium_heat}
            tone='warning'
            aria-label='Heat of the medium'
          />
        </div>
      }
    />
  )
}

export function ClusterView({ clusterId }: { clusterId: number }) {
  const { view, catalog, wiki, ladder } = useScaleData(clusterId)
  const edit = useCosmographyAction<Edit>(
    'cluster:edit',
    (vars) => ({ cluster_id: clusterId, ...vars }),
    'The cluster is reshaped'
  )
  if (view.isPending || !catalog) return <WikiLoading />
  if (view.isError)
    return (
      <WikiError
        icon={Workflow}
        title='The cluster could not be read'
        message={view.error.message}
      />
    )
  const cluster = ladder?.data.clusters.find((row) => row.id === clusterId)
  if (!ladder || !cluster)
    return <Missing icon={Workflow} title='No such cluster' />
  const galaxies = ladder.galaxiesIn(cluster.id)
  const children = ladder.childClusters(cluster.id)
  const stars = ladder.data.stars.filter((row) =>
    galaxies.some((galaxy) => galaxy.id === row.galaxy_id)
  ).length
  const busy = edit.isPending ? 'Working' : null
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <ClusterHero
        cluster={cluster}
        ladder={ladder}
        catalog={catalog}
        cover={wiki?.cover ?? null}
      />
      <Section title='At a glance' icon={Workflow} tone='verdigris'>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
          <MiniStat
            icon={Orbit}
            tone='gold'
            label='Galaxies'
            value={galaxies.length}
          />
          <MiniStat
            icon={Workflow}
            tone='verdigris'
            label='Clusters inside'
            value={children.length}
          />
          <MiniStat icon={Star} tone='gold' label='Stars' value={stars} />
          <MiniStat
            icon={Ruler}
            tone='muted'
            label='Radius'
            value={Math.round(cluster.radius)}
          />
          <MiniStat
            icon={Flame}
            tone='warning'
            label='Medium heat'
            value={`${cluster.medium_heat}%`}
          />
          <MiniStat
            icon={Orbit}
            tone='info'
            label='Drift'
            value={`${cluster.expansion}%`}
          />
        </div>
      </Section>
      <Section
        title='Galaxies of the cluster'
        description='Open one to see its map, its stars and its structures.'
        icon={Orbit}
        tone='gold'
      >
        <div className='flex min-w-0 flex-col gap-3'>
          {galaxies.length === 0 ? (
            <EmptyState
              icon={Orbit}
              size='inline'
              title='No galaxy gathers here yet'
              description='Set one in the cluster below.'
            />
          ) : (
            <PagedList
              items={galaxies}
              initial={6}
              noun={['galaxy', 'galaxies']}
              className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'
              itemKey={(row) => row.id}
            >
              {(row) => (
                <GalaxyCard galaxy={row} ladder={ladder} catalog={catalog} />
              )}
            </PagedList>
          )}
          <CreateGalaxyStudio
            ladder={ladder}
            catalog={catalog}
            clusterId={cluster.id}
          />
        </div>
      </Section>
      {children.length > 0 && (
        <Section title='Clusters inside it' icon={Workflow} tone='verdigris'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            {children.map((row) => (
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
                  <Chip>
                    {catalogLabel(catalog.cluster_kinds, row.cluster_kind)}
                  </Chip>
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <Section
        id='section-cluster'
        title='Shape the cluster'
        description='Every value you set is held against the engine until you release it.'
        icon={Workflow}
        tone='verdigris'
        surface='card'
      >
        <div data-surface='ClusterPage' className='flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Meter
              label='Heat of the medium'
              value={cluster.medium_heat}
              tone='warning'
            />
            <Meter label='Drift' value={cluster.expansion} tone='info' />
          </div>
          <Facts
            items={[
              [
                'Kind',
                catalogLabel(catalog.cluster_kinds, cluster.cluster_kind),
              ],
              ['Place', `${Math.round(cluster.x)}, ${Math.round(cluster.y)}`],
              ['Known', DISCOVERY[cluster.discovery]],
            ]}
          />
          <RecordEditor
            title='Form and account'
            note='Its name, kind and account.'
            fields={[
              { key: 'name', label: 'Name', kind: 'text' },
              {
                key: 'cluster_kind',
                label: 'Kind',
                kind: 'pick',
                table: catalogTable(catalog.cluster_kinds),
              },
              {
                key: 'description',
                label: 'Account',
                kind: 'text',
                long: true,
              },
            ]}
            locked={cluster.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
          <RecordEditor
            title='Medium and place'
            note='Heat of the gas between its galaxies, its drift, its size and where it lies.'
            fields={[
              {
                key: 'medium_heat',
                label: 'Heat of the medium',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'expansion',
                label: 'Drift',
                kind: 'number',
                min: 0,
                max: 100,
              },
              { key: 'radius', label: 'Radius', kind: 'decimal', min: 1 },
              { key: 'x', label: 'Place across', kind: 'decimal' },
              { key: 'y', label: 'Place down', kind: 'decimal' },
              {
                key: 'parent_cluster_id',
                label: 'Inside cluster',
                kind: 'pick',
                table: nameTable(
                  ladder.data.clusters.filter((row) => row.id !== cluster.id)
                ),
              },
              {
                key: 'dimension_id',
                label: 'Dimension',
                kind: 'pick',
                table: nameTable(ladder.data.dimensions),
              },
              {
                key: 'discovery',
                label: 'Known',
                kind: 'pick',
                table: DISCOVERY,
              },
            ]}
            locked={cluster.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </div>
      </Section>
      <CelestialDepthSection
        kind='cluster'
        id={cluster.id}
        name={cluster.name}
        depth={wiki?.depth ?? null}
      />
      <WikiRecords
        nodeId={cluster.id}
        name={cluster.name}
        wiki={wiki}
        prompt={cluster.image_prompt}
        action='cluster:edit'
        target={{ cluster_id: cluster.id }}
      />
      <DangerZone
        noun='cluster'
        name={cluster.name}
        consequence='Its galaxies and inner clusters pass to the cluster or dimension that held it.'
        action='cluster:delete'
        target={{ cluster_id: cluster.id }}
      />
      <ThingSections nodeId={cluster.id} />
    </div>
  )
}

export function ClusterPage({ id }: DrawerPageProps) {
  const value = pageId(id)
  return value === null ? (
    <Missing icon={Workflow} title='No such cluster' />
  ) : (
    <ClusterView clusterId={value} />
  )
}
