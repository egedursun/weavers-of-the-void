import { useNavigate } from '@tanstack/react-router'
import {
  Eye,
  Globe2,
  Hourglass,
  Layers,
  Orbit,
  Rocket,
  Shield,
  Sparkles,
  Star,
  Workflow,
  X,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { MiniStat } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, Text } from '@/components/typography'
import { type CosmographyCatalog, catalogLabel } from './api'
import { type ScaleKind } from './heavensSearch'
import { GALAXY_AGES, NUCLEI } from './labels'
import { type Ladder } from './ladder'
import { Chip } from './parts'
import { GalaxyThumb } from './visual/GalaxyThumb'
import { ClusterThumb, DimensionThumb } from './visual/ScaleThumbs'
import { stateOf } from './visual/dimensionState'

type Props = {
  ladder: Ladder
  catalog: CosmographyCatalog
  kind: ScaleKind
  id: number
  onClear: () => void
}

function Frame({
  emblem,
  overline,
  name,
  chips,
  stats,
  actions,
  onClear,
}: {
  emblem: React.ReactNode
  overline: string
  name: string
  chips: React.ReactNode
  stats: React.ReactNode
  actions: React.ReactNode
  onClear: () => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card/95 p-3 text-card-foreground shadow-lg backdrop-blur'>
      <div className='flex min-w-0 items-start gap-3'>
        {emblem}
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Label variant='overline'>{overline}</Label>
          <Text weight='semibold' truncate>
            {name}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1'>{chips}</div>
        </div>
        <Button
          variant='ghost'
          size='sm'
          aria-label='Clear the selection'
          onClick={onClear}
        >
          <X />
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>{stats}</div>
      <div className='flex min-w-0 flex-wrap gap-2'>{actions}</div>
    </div>
  )
}

export function SelectedScale({ ladder, catalog, kind, id, onClear }: Props) {
  const drawers = useDrawerStack()
  const navigate = useNavigate()
  const open = (
    <Button size='sm' onClick={() => drawers.open({ kind, id: String(id) })}>
      <Eye />
      Open its page
    </Button>
  )
  if (kind === 'galaxy') {
    const galaxy = ladder.data.galaxies.find((row) => row.id === id)
    if (!galaxy) return null
    const stars = ladder.starsIn(galaxy.id).length
    const worlds = ladder.placementsIn(galaxy.id).length
    const nucleus = NUCLEI[galaxy.nucleus]
    return (
      <Frame
        emblem={
          <GalaxyThumb
            galaxy={galaxy}
            shape={catalog.shape}
            label={galaxy.name}
            points={2400}
            className='size-portrait-xl shrink-0'
          />
        }
        overline={`Galaxy · ${catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}`}
        name={galaxy.name}
        chips={
          <>
            <Chip icon={nucleus.icon}>{nucleus.label}</Chip>
            <Chip>{GALAXY_AGES[galaxy.age_stage]}</Chip>
          </>
        }
        stats={
          <>
            <MiniStat icon={Star} tone='gold' label='Stars' value={stars} />
            <MiniStat icon={Globe2} tone='info' label='Worlds' value={worlds} />
            <MiniStat
              icon={Sparkles}
              tone='success'
              label='Star formation'
              value={`${galaxy.star_formation}%`}
            />
            <MiniStat
              icon={Eye}
              tone='danger'
              label='Leak'
              value={`${galaxy.leak}%`}
            />
          </>
        }
        actions={
          <>
            {open}
            <Button
              size='sm'
              variant='outline'
              onClick={() =>
                void navigate({ to: '/cosmos', search: { galaxy: galaxy.id } })
              }
            >
              <Rocket />
              Enter it in the Cosmos
            </Button>
          </>
        }
        onClear={onClear}
      />
    )
  }
  if (kind === 'cluster') {
    const cluster = ladder.data.clusters.find((row) => row.id === id)
    if (!cluster) return null
    const galaxies = ladder.galaxiesIn(cluster.id)
    return (
      <Frame
        emblem={
          <ClusterThumb
            cluster={{
              id: cluster.id,
              kind: cluster.cluster_kind,
              galaxies: galaxies.length,
              heat: cluster.medium_heat,
            }}
            label={cluster.name}
            className='size-portrait-xl shrink-0'
          />
        }
        overline={`Cluster · ${catalogLabel(catalog.cluster_kinds, cluster.cluster_kind)}`}
        name={cluster.name}
        chips={
          <Chip
            icon={Orbit}
          >{`${plural(galaxies.length, 'galaxy', 'galaxies')}`}</Chip>
        }
        stats={
          <>
            <MiniStat
              icon={Workflow}
              tone='verdigris'
              label='Inner clusters'
              value={ladder.childClusters(cluster.id).length}
            />
            <MiniStat
              icon={Sparkles}
              tone='warning'
              label='Medium heat'
              value={`${cluster.medium_heat}%`}
            />
          </>
        }
        actions={open}
        onClear={onClear}
      />
    )
  }
  const dimension = ladder.data.dimensions.find((row) => row.id === id)
  if (!dimension) return null
  return (
    <Frame
      emblem={
        <DimensionThumb
          dimension={stateOf(dimension)}
          label={dimension.name}
          className='size-portrait-xl shrink-0'
        />
      }
      overline={`Dimension · ${catalogLabel(catalog.dimension_kinds, dimension.dimension_kind)}`}
      name={dimension.name}
      chips={
        <>
          <Chip icon={Hourglass}>{`Time ×${dimension.time_factor}`}</Chip>
          <Chip icon={Layers}>{`Veil ${dimension.veil}`}</Chip>
        </>
      }
      stats={
        <>
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
            icon={Eye}
            tone='danger'
            label='Hostility'
            value={`${dimension.hostility}%`}
          />
          <MiniStat
            icon={Globe2}
            tone='info'
            label='Worlds'
            value={
              ladder.data.placements.filter(
                (row) => row.dimension_id === dimension.id
              ).length
            }
          />
        </>
      }
      actions={
        <>
          {open}
          <Muted variant='caption'>
            Rifts and beings of this dimension are in the tabs below.
          </Muted>
        </>
      }
      onClear={onClear}
    />
  )
}
