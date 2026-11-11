import { type ReactNode } from 'react'
import { ExternalLink } from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Paged } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Muted, Text } from '@/components/typography'
import {
  type ClusterRecord,
  type CosmographyCatalog,
  type GalaxyRecord,
  catalogLabel,
} from './api'
import { type ScaleKind } from './heavensSearch'
import { type Ladder } from './ladder'
import { GalaxyThumb } from './visual/GalaxyThumb'
import { ClusterThumb, DimensionSigil } from './visual/ScaleThumbs'
import { sigilOf } from './visual/sigil'

type Selection = { kind: ScaleKind; id: number } | null

type Member =
  | { kind: 'cluster'; row: ClusterRecord }
  | { kind: 'galaxy'; row: GalaxyRecord }

function Members({
  clusters,
  galaxies,
  ladder,
  catalog,
  selection,
  onSelect,
}: {
  clusters: ClusterRecord[]
  galaxies: GalaxyRecord[]
  ladder: Ladder
  catalog: CosmographyCatalog
  selection: Selection
  onSelect: (kind: ScaleKind, id: number) => void
}) {
  const members: Member[] = [
    ...clusters.map((row) => ({ kind: 'cluster' as const, row })),
    ...galaxies.map((row) => ({ kind: 'galaxy' as const, row })),
  ]
  if (members.length === 0) return null
  return (
    <ul className='flex min-w-0 flex-col gap-1.5 border-l pl-4'>
      <Paged items={members} as='li' noun={['member', 'members']}>
        {(member) =>
          member.kind === 'cluster' ? (
            <ClusterRow
              key={`cluster-${member.row.id}`}
              cluster={member.row}
              ladder={ladder}
              catalog={catalog}
              selection={selection}
              onSelect={onSelect}
            />
          ) : (
            <GalaxyRow
              key={`galaxy-${member.row.id}`}
              galaxy={member.row}
              ladder={ladder}
              catalog={catalog}
              selection={selection}
              onSelect={onSelect}
            />
          )
        }
      </Paged>
    </ul>
  )
}

function Row({
  kind,
  id,
  name,
  detail,
  emblem,
  selection,
  onSelect,
  children,
}: {
  kind: ScaleKind
  id: number
  name: string
  detail: string
  emblem: ReactNode
  selection: Selection
  onSelect: (kind: ScaleKind, id: number) => void
  children?: ReactNode
}) {
  const drawers = useDrawerStack()
  const chosen = selection?.kind === kind && selection.id === id
  return (
    <li className='flex min-w-0 flex-col gap-1.5'>
      <div
        className={cn(
          'flex min-w-0 items-center gap-2 rounded-lg border p-1.5 transition-colors',
          chosen
            ? 'border-primary bg-primary/10'
            : 'bg-background hover:bg-muted/40'
        )}
      >
        <div className='min-w-0 flex-1'>
          <Button
            variant='ghost'
            size='tile'
            aria-pressed={chosen}
            onClick={() => onSelect(kind, id)}
          >
            {emblem}
            <span className='flex min-w-0 flex-1 flex-col'>
              <Text as='span' weight='semibold' truncate>
                {name}
              </Text>
              <Muted as='span' variant='caption' truncate>
                {detail}
              </Muted>
            </span>
          </Button>
        </div>
        <Button
          variant='ghost'
          size='sm'
          aria-label={`Open the page of ${name}`}
          onClick={() => drawers.open({ kind, id: String(id) })}
        >
          <ExternalLink />
        </Button>
      </div>
      {children}
    </li>
  )
}

function GalaxyRow({
  galaxy,
  ladder,
  catalog,
  selection,
  onSelect,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  selection: Selection
  onSelect: (kind: ScaleKind, id: number) => void
}) {
  const stars = ladder.starsIn(galaxy.id).length
  return (
    <Row
      kind='galaxy'
      id={galaxy.id}
      name={galaxy.name}
      detail={`${catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)} · ${plural(stars, 'star')}`}
      emblem={
        <GalaxyThumb
          galaxy={galaxy}
          shape={catalog.shape}
          label={galaxy.name}
          points={900}
          className='size-portrait-md shrink-0 rounded-md'
        />
      }
      selection={selection}
      onSelect={onSelect}
    />
  )
}

function ClusterRow({
  cluster,
  ladder,
  catalog,
  selection,
  onSelect,
}: {
  cluster: ClusterRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  selection: Selection
  onSelect: (kind: ScaleKind, id: number) => void
}) {
  const galaxies = ladder.galaxiesIn(cluster.id)
  const children = ladder.childClusters(cluster.id)
  return (
    <Row
      kind='cluster'
      id={cluster.id}
      name={cluster.name}
      detail={`${catalogLabel(catalog.cluster_kinds, cluster.cluster_kind)} · ${plural(galaxies.length, 'galaxy', 'galaxies')}`}
      emblem={
        <ClusterThumb
          cluster={{
            id: cluster.id,
            kind: cluster.cluster_kind,
            galaxies: galaxies.length,
            heat: cluster.medium_heat,
          }}
          label={cluster.name}
          className='size-portrait-md shrink-0 rounded-md'
        />
      }
      selection={selection}
      onSelect={onSelect}
    >
      <Members
        clusters={children}
        galaxies={galaxies}
        ladder={ladder}
        catalog={catalog}
        selection={selection}
        onSelect={onSelect}
      />
    </Row>
  )
}

export function ScaleNavigator({
  ladder,
  catalog,
  selection,
  onSelect,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  selection: Selection
  onSelect: (kind: ScaleKind, id: number) => void
}) {
  return (
    <ul
      aria-label='The scale of the cosmos'
      className='flex min-w-0 flex-col gap-1.5'
    >
      {ladder.data.dimensions.map((dimension) => {
        return (
          <Row
            key={dimension.id}
            kind='dimension'
            id={dimension.id}
            name={dimension.name}
            detail={`${catalogLabel(catalog.dimension_kinds, dimension.dimension_kind)} · time ×${dimension.time_factor}`}
            emblem={
              <DimensionSigil
                dimension={sigilOf(dimension)}
                label={dimension.name}
                className='size-portrait-md shrink-0 rounded-md'
              />
            }
            selection={selection}
            onSelect={onSelect}
          >
            <Members
              clusters={ladder.clustersIn(dimension.id)}
              galaxies={ladder.looseGalaxies(dimension.id)}
              ladder={ladder}
              catalog={catalog}
              selection={selection}
              onSelect={onSelect}
            />
          </Row>
        )
      })}
    </ul>
  )
}
