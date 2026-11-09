import { useState } from 'react'
import { Layers, Orbit, Plus, Star, Trash2, Workflow } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  LoadingBlock,
  Medallion,
  PagedList,
  Section,
} from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Label, Muted, PageTitle } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { NumberField } from '@/features/entity/wilds/parts'
import { BeingCard } from './BeingsPanel'
import { EventsPanel } from './EventsPanel'
import { GalaxyMap } from './GalaxyMap'
import { RiftsPanel } from './RiftsPanel'
import {
  type ClusterRecord,
  type CosmographyCatalog,
  type DimensionRecord,
  type GalaxyRecord,
  catalogLabel,
  catalogTable,
  useCosmography,
  useCosmographyAction,
  useCosmographyCatalog,
} from './api'
import { CAUSALITIES, ELEMENTS, GALAXY_AGES, NUCLEI, ZONES } from './labels'
import { type Ladder, ladderOf, nameTable } from './ladder'
import { Facts, Meter, NodeLink, RecordEditor, RecordRow } from './parts'

const DISCOVERY = {
  known: 'Known',
  legend: 'A legend',
  unknown: 'Unknown',
  forgotten: 'Forgotten',
}

function useLadder() {
  const view = useCosmography()
  const catalog = useCosmographyCatalog()
  return {
    view,
    catalog: catalog.data,
    ladder: view.data ? ladderOf(view.data) : null,
  }
}

function Missing({ icon: Icon, title }: { icon: typeof Orbit; title: string }) {
  return (
    <EmptyState
      icon={Icon}
      title={title}
      description='This link does not point to a part of the heavens that exists now.'
    />
  )
}

function Hero({
  icon: Icon,
  tone,
  eyebrow,
  name,
  description,
}: {
  icon: typeof Orbit
  tone: 'gold' | 'info' | 'verdigris'
  eyebrow: string
  name: string
  description: string | null
}) {
  return (
    <header className='flex min-w-0 items-start gap-3'>
      <Medallion icon={Icon} tone={tone} />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label variant='overline'>{eyebrow}</Label>
        <PageTitle truncate={2}>{name}</PageTitle>
        {description && <Muted>{description}</Muted>}
      </div>
    </header>
  )
}

function DeleteButton({
  label,
  onDelete,
  busy,
}: {
  label: string
  onDelete: () => void
  busy: string | null
}) {
  return (
    <Button
      size='sm'
      variant='destructive'
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onDelete}
    >
      <Trash2 />
      {label}
    </Button>
  )
}

function StructuresSection({
  galaxy,
  ladder,
  catalog,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const structures = ladder.data.structures.filter(
    (row) => row.galaxy_id === galaxy.id
  )
  const [kind, setKind] = useState('')
  const [radius, setRadius] = useState('60')
  const create = useCosmographyAction<void>(
    'galactic_structure:create',
    () => ({
      galaxy_id: galaxy.id,
      kind,
      name: '',
      radius: Number(radius) || 60,
    }),
    'A structure took shape'
  )
  return (
    <Section
      title='Structures'
      description='Arms, nebulae, clusters of stars and stranger works inside the galaxy.'
      icon={Star}
      tone='gold'
    >
      {structures.length === 0 ? (
        <EmptyState
          icon={Star}
          size='compact'
          title='No structure yet'
          description='Shape one below.'
        />
      ) : (
        <PagedList
          items={structures}
          initial={6}
          noun={['structure', 'structures']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => (
            <StructureRow
              structureId={row.id}
              ladder={ladder}
              catalog={catalog}
            />
          )}
        </PagedList>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed p-3 sm:grid-cols-3'>
        <MindPicker
          label='Kind'
          value={kind}
          table={catalogTable(catalog?.structure_kinds)}
          blocked={create.isPending ? 'Shaping' : null}
          onPick={setKind}
        />
        <NumberField
          label='Radius'
          value={radius}
          min={1}
          disabled={create.isPending}
          onChange={setRadius}
        />
        <Button
          size='sm'
          disabled={create.isPending || kind === ''}
          disabledReason={
            create.isPending
              ? 'Shaping'
              : kind === ''
                ? 'Choose its kind first'
                : undefined
          }
          onClick={() => create.mutate()}
        >
          <Plus />
          Shape it
        </Button>
      </div>
    </Section>
  )
}

function StructureRow({
  structureId,
  ladder,
  catalog,
}: {
  structureId: number
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const row = ladder.data.structures.find((item) => item.id === structureId)
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('galactic_structure:edit', (vars) => ({
    structure_id: structureId,
    ...vars,
  }))
  const remove = useCosmographyAction<void>(
    'galactic_structure:delete',
    () => ({ structure_id: structureId }),
    'The structure is unmade'
  )
  if (!row) return null
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <RecordRow
      icon={Star}
      tone={row.ended_epoch === null ? 'gold' : 'muted'}
      title={row.name}
      caption={`${catalogLabel(catalog?.structure_kinds, row.kind)} · radius ${Math.round(row.radius)}`}
      aside={
        <DeleteButton
          label='Unmake'
          busy={busy}
          onDelete={() => remove.mutate()}
        />
      }
    >
      <Meter label='Intensity' value={row.intensity} tone='warning' />
      <RecordEditor
        title='Reshape this structure'
        note='Its place, size and strength; the stars inside it follow.'
        fields={[
          {
            key: 'intensity',
            label: 'Intensity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'radius', label: 'Radius', kind: 'decimal', min: 1 },
          { key: 'x', label: 'Position across', kind: 'decimal' },
          { key: 'y', label: 'Position down', kind: 'decimal' },
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: catalogTable(catalog?.structure_kinds),
          },
        ]}
        locked={row.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
      <Muted variant='caption'>{`In ${ladder.names.get(row.galaxy_id) ?? 'its galaxy'} since epoch ${row.created_epoch}`}</Muted>
    </RecordRow>
  )
}

function GalaxyEditor({
  galaxy,
  ladder,
  catalog,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('galaxy:edit', (vars) => ({ galaxy_id: galaxy.id, ...vars }))
  const remove = useCosmographyAction<void>(
    'galaxy:delete',
    () => ({ galaxy_id: galaxy.id }),
    'The galaxy is unmade'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <Section
      id='section-galaxy'
      title='Shape the galaxy'
      icon={Orbit}
      tone='gold'
      actions={
        <DeleteButton
          label='Unmake the galaxy'
          busy={busy}
          onDelete={() => remove.mutate()}
        />
      }
    >
      <div data-surface='GalaxyPage' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Meter
            label='Star formation'
            value={galaxy.star_formation}
            tone='success'
          />
          <Meter
            label='Metallicity'
            value={galaxy.metallicity}
            tone='warning'
          />
          <Meter label='Leak' value={galaxy.leak} tone='destructive' />
          <Meter
            label='Merge progress'
            value={galaxy.merge_progress}
            tone='info'
          />
        </div>
        <Facts
          items={[
            ['Type', catalogLabel(catalog?.galaxy_types, galaxy.galaxy_type)],
            ['Nucleus', NUCLEI[galaxy.nucleus].label],
            ['Age', GALAXY_AGES[galaxy.age_stage]],
            ['Arms', galaxy.arm_count],
            ['Radius', Math.round(galaxy.radius)],
            [
              'Cluster',
              <NodeLink
                key='cluster'
                kind='cluster'
                id={galaxy.cluster_id}
                name={ladder.names.get(galaxy.cluster_id ?? 0)}
              />,
            ],
            [
              'Merging with',
              <NodeLink
                key='merge'
                kind='galaxy'
                id={galaxy.merging_with_galaxy_id}
                name={ladder.names.get(galaxy.merging_with_galaxy_id ?? 0)}
              />,
            ],
            [
              'Patron',
              <NodeLink
                key='patron'
                kind='son'
                id={galaxy.patron_son_id}
                name={
                  galaxy.patron_son_id ? `Son #${galaxy.patron_son_id}` : 'None'
                }
              />,
            ],
            ['Known', DISCOVERY[galaxy.discovery]],
          ]}
        />
        <RecordEditor
          title='Reshape the galaxy'
          note='Every value you set is held against the engine until you let the world decide again.'
          fields={[
            {
              key: 'galaxy_type',
              label: 'Type',
              kind: 'pick',
              table: catalogTable(catalog?.galaxy_types),
            },
            {
              key: 'star_formation',
              label: 'Star formation',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'metallicity',
              label: 'Metallicity',
              kind: 'number',
              min: 0,
              max: 100,
            },
            { key: 'leak', label: 'Leak', kind: 'number', min: 0, max: 100 },
            { key: 'arm_count', label: 'Arms', kind: 'number', min: 0 },
            { key: 'radius', label: 'Radius', kind: 'decimal', min: 1 },
            { key: 'x', label: 'Place in cluster across', kind: 'decimal' },
            { key: 'y', label: 'Place in cluster down', kind: 'decimal' },
            {
              key: 'nucleus',
              label: 'Nucleus',
              kind: 'pick',
              table: Object.fromEntries(
                Object.entries(NUCLEI).map(([key, value]) => [key, value.label])
              ),
            },
            {
              key: 'age_stage',
              label: 'Age',
              kind: 'pick',
              table: GALAXY_AGES,
            },
            {
              key: 'cluster_id',
              label: 'Cluster',
              kind: 'pick',
              table: nameTable(ladder.data.clusters),
            },
            {
              key: 'dimension_id',
              label: 'Dimension',
              kind: 'pick',
              table: nameTable(ladder.data.dimensions),
            },
            {
              key: 'merging_with_galaxy_id',
              label: 'Merging with',
              kind: 'pick',
              table: nameTable(
                ladder.data.galaxies.filter((row) => row.id !== galaxy.id)
              ),
            },
            {
              key: 'merge_progress',
              label: 'Merge progress',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'discovery',
              label: 'Known',
              kind: 'pick',
              table: DISCOVERY,
            },
          ]}
          locked={galaxy.locked}
          busy={busy}
          onSave={(values) => edit.mutate({ values, release: [] })}
          onRelease={(release) => edit.mutate({ values: {}, release })}
        />
      </div>
    </Section>
  )
}

export function GalaxyView({ galaxyId }: { galaxyId: number }) {
  const { view, catalog, ladder } = useLadder()
  if (view.isPending) return <LoadingBlock label='Reading the galaxy' />
  if (view.isError)
    return (
      <Alert variant='destructive'>
        <Orbit />
        <AlertTitle>The galaxy could not be read</AlertTitle>
        <AlertDescription>{view.error.message}</AlertDescription>
      </Alert>
    )
  const galaxy = ladder?.data.galaxies.find((row) => row.id === galaxyId)
  if (!ladder || !galaxy) return <Missing icon={Orbit} title='No such galaxy' />
  const stars = ladder.data.stars.filter((row) => row.galaxy_id === galaxy.id)
  const beings = ladder.data.beings.filter((row) => row.galaxy_id === galaxy.id)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Hero
        icon={Orbit}
        tone='gold'
        eyebrow={`Galaxy · ${catalogLabel(catalog?.galaxy_types, galaxy.galaxy_type)}`}
        name={galaxy.name}
        description={galaxy.description ?? null}
      />
      <GalaxyMap
        galaxy={galaxy}
        structures={ladder.data.structures.filter(
          (row) => row.galaxy_id === galaxy.id
        )}
        stars={stars.map((row) => ({
          id: row.id,
          name: row.name,
          x: row.x,
          y: row.y,
        }))}
      />
      <GalaxyEditor galaxy={galaxy} ladder={ladder} catalog={catalog} />
      <Section title='Stars of the galaxy' icon={Star} tone='gold'>
        {stars.length === 0 ? (
          <EmptyState
            icon={Star}
            size='compact'
            title='No star burns here yet'
            description='Nurseries bear stars over the epochs, or hang one with a son.'
          />
        ) : (
          <PagedList
            items={stars}
            initial={8}
            noun={['star', 'stars']}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
            itemKey={(row) => row.id}
          >
            {(row) => (
              <li className='flex min-w-0 items-center gap-2 rounded-lg border p-2'>
                <Medallion
                  icon={ZONES[row.galactic_zone ?? 'outer_disc'].icon}
                  tone={ZONES[row.galactic_zone ?? 'outer_disc'].tone}
                  size='sm'
                />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <EntityLink kind='star' id={String(row.id)}>
                    {row.name}
                  </EntityLink>
                  <Muted as='span' variant='caption'>
                    {ZONES[row.galactic_zone ?? 'outer_disc'].label}
                  </Muted>
                </span>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      <StructuresSection galaxy={galaxy} ladder={ladder} catalog={catalog} />
      {beings.length > 0 && (
        <Section title='Beings that roam it' icon={Orbit} tone='warning'>
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
        </Section>
      )}
      <EventsPanel ladder={ladder} catalog={catalog} galaxyId={galaxy.id} />
      <ThingSections nodeId={galaxy.id} />
    </div>
  )
}

function ClusterEditor({
  cluster,
  ladder,
  catalog,
}: {
  cluster: ClusterRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('cluster:edit', (vars) => ({ cluster_id: cluster.id, ...vars }))
  const remove = useCosmographyAction<void>(
    'cluster:delete',
    () => ({ cluster_id: cluster.id }),
    'The cluster scatters'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <Section
      id='section-cluster'
      title='Shape the cluster'
      icon={Workflow}
      tone='verdigris'
      actions={
        <DeleteButton
          label='Scatter the cluster'
          busy={busy}
          onDelete={() => remove.mutate()}
        />
      }
    >
      <div data-surface='ClusterPage' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Meter
            label='Heat of the medium'
            value={cluster.medium_heat}
            tone='warning'
          />
          <Meter label='Drift' value={cluster.expansion} tone='info' />
        </div>
        <RecordEditor
          title='Reshape the cluster'
          note='Values you set are held.'
          fields={[
            {
              key: 'cluster_kind',
              label: 'Kind',
              kind: 'pick',
              table: catalogTable(catalog?.cluster_kinds),
            },
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
  )
}

export function ClusterView({ clusterId }: { clusterId: number }) {
  const { view, catalog, ladder } = useLadder()
  if (view.isPending) return <LoadingBlock label='Reading the cluster' />
  const cluster = ladder?.data.clusters.find((row) => row.id === clusterId)
  if (!ladder || !cluster)
    return <Missing icon={Workflow} title='No such cluster' />
  const galaxies = ladder.galaxiesIn(cluster.id)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Hero
        icon={Workflow}
        tone='verdigris'
        eyebrow={`Cluster · ${catalogLabel(catalog?.cluster_kinds, cluster.cluster_kind)}`}
        name={cluster.name}
        description={cluster.description ?? null}
      />
      <ClusterEditor cluster={cluster} ladder={ladder} catalog={catalog} />
      <Section title='Galaxies of the cluster' icon={Orbit} tone='gold'>
        {galaxies.length === 0 ? (
          <EmptyState
            icon={Orbit}
            size='compact'
            title='No galaxy here yet'
            description='Set one in the Heavens, or move one here.'
          />
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            {galaxies.map((row) => (
              <li
                key={row.id}
                className='flex min-w-0 items-center gap-2 rounded-lg border p-2'
              >
                <Medallion icon={Orbit} tone='gold' size='sm' />
                <EntityLink kind='galaxy' id={String(row.id)}>
                  {row.name}
                </EntityLink>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <ThingSections nodeId={cluster.id} />
    </div>
  )
}

function DimensionEditor({
  dimension,
  ladder,
  catalog,
}: {
  dimension: DimensionRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('dimension:edit', (vars) => ({ dimension_id: dimension.id, ...vars }))
  const remove = useCosmographyAction<void>(
    'dimension:delete',
    () => ({ dimension_id: dimension.id }),
    'The dimension is unmade'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <Section
      id='section-dimension'
      title='Shape the dimension'
      icon={Layers}
      tone='info'
      actions={
        <DeleteButton
          label='Unmake the dimension'
          busy={busy}
          onDelete={() => remove.mutate()}
        />
      }
    >
      <div data-surface='DimensionPage' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Meter label='Veil' value={dimension.veil} tone='info' />
          <Meter
            label='Stability'
            value={dimension.stability}
            tone='verdigris'
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
              catalogLabel(catalog?.dimension_kinds, dimension.dimension_kind),
            ],
            [
              'Element',
              dimension.element ? ELEMENTS[dimension.element] : 'None',
            ],
            ['Time', `${dimension.time_factor} times the prime`],
            ['Sanity drain', dimension.sanity_drain],
            ['Causality', CAUSALITIES[dimension.causality]],
            [
              'Lies within',
              <NodeLink
                key='parent'
                kind='dimension'
                id={dimension.parent_dimension_id}
                name={ladder.names.get(dimension.parent_dimension_id ?? 0)}
              />,
            ],
            [
              'Ruler',
              dimension.ruler_node_id ? `#${dimension.ruler_node_id}` : 'None',
            ],
            ['Known', DISCOVERY[dimension.discovery]],
          ]}
        />
        <RecordEditor
          title='Reshape the dimension'
          note='Veil, stability, time, magic and every other value you set are held.'
          fields={[
            {
              key: 'dimension_kind',
              label: 'Kind',
              kind: 'pick',
              table: catalogTable(catalog?.dimension_kinds),
            },
            { key: 'element', label: 'Element', kind: 'pick', table: ELEMENTS },
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
            { key: 'magic', label: 'Magic', kind: 'number', min: 0, max: 100 },
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
              key: 'causality',
              label: 'Causality',
              kind: 'pick',
              table: CAUSALITIES,
            },
            {
              key: 'parent_dimension_id',
              label: 'Lies within',
              kind: 'pick',
              table: nameTable(
                ladder.data.dimensions.filter((row) => row.id !== dimension.id)
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
  )
}

export function DimensionView({ dimensionId }: { dimensionId: number }) {
  const { view, catalog, ladder } = useLadder()
  if (view.isPending) return <LoadingBlock label='Reading the dimension' />
  const dimension = ladder?.data.dimensions.find(
    (row) => row.id === dimensionId
  )
  if (!ladder || !dimension)
    return <Missing icon={Layers} title='No such dimension' />
  const worlds = ladder.data.placements.filter(
    (row) => row.dimension_id === dimension.id
  )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Hero
        icon={Layers}
        tone='info'
        eyebrow={`Dimension · ${catalogLabel(catalog?.dimension_kinds, dimension.dimension_kind)}`}
        name={dimension.name}
        description={dimension.description ?? null}
      />
      <DimensionEditor
        dimension={dimension}
        ladder={ladder}
        catalog={catalog}
      />
      <Section title='Worlds in this dimension' icon={Orbit} tone='gold'>
        {worlds.length === 0 ? (
          <EmptyState
            icon={Orbit}
            size='compact'
            title='No world lies here'
            description='Move a world or its galaxy into this dimension to give it one.'
          />
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            {worlds.map((row) => (
              <li
                key={row.world_id}
                className='flex min-w-0 items-center gap-2 rounded-lg border p-2'
              >
                <EntityLink kind='world' id={String(row.world_id)}>
                  {ladder.data.world_names[String(row.world_id)] ??
                    `World #${row.world_id}`}
                </EntityLink>
                <Muted
                  as='span'
                  variant='caption'
                >{`time ×${row.pull.time.toFixed(2)}`}</Muted>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <RiftsPanel ladder={ladder} dimensionId={dimension.id} />
      <EventsPanel
        ladder={ladder}
        catalog={catalog}
        dimensionId={dimension.id}
      />
      <ThingSections nodeId={dimension.id} />
    </div>
  )
}

function pageId(id: string | undefined): number | null {
  const value = Number(id)
  return Number.isInteger(value) && value > 0 ? value : null
}

export function GalaxyPage({ id }: DrawerPageProps) {
  const value = pageId(id)
  return value === null ? (
    <Missing icon={Orbit} title='No such galaxy' />
  ) : (
    <GalaxyView galaxyId={value} />
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

export function DimensionPage({ id }: DrawerPageProps) {
  const value = pageId(id)
  return value === null ? (
    <Missing icon={Layers} title='No such dimension' />
  ) : (
    <DimensionView dimensionId={value} />
  )
}
