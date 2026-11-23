import { useQuery } from '@tanstack/react-query'
import { ArrowDownToLine, Hammer, Layers, Pickaxe } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  MiniStat,
  PagedList,
  Section,
  ShowMore,
  StatBar,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { GRADE, ROCK, STRATUM } from './geologyLabels'
import { plain } from './labels'

type Layer = components['schemas']['RockLayerView']
type Stratum = components['schemas']['DepthStratumView']

const PERCENT = 100
const VEINS_SHOWN = 6

function LayerRow({ layer }: { layer: Layer }) {
  const rock = ROCK[layer.rock]
  const grade = GRADE[layer.grade]
  const veins = useShowMore(Object.entries(layer.veins), VEINS_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Medallion icon={rock.icon} tone={rock.tone} size='sm' />
        <Text as='span' weight='medium' truncate>
          {rock.label}
        </Text>
        <Muted variant='caption'>{`Layer ${layer.depth_order + 1}, from depth ${layer.top}, ${layer.thickness} deep`}</Muted>
        <Badge variant='secondary'>{grade.label}</Badge>
        {layer.reached_epoch !== null && layer.reached_epoch !== undefined ? (
          <Badge variant='info'>{`Reached in epoch ${layer.reached_epoch}`}</Badge>
        ) : (
          <Badge variant='default'>Not reached</Badge>
        )}
        {layer.locked.length > 0 ? <Badge variant='warning'>Held</Badge> : null}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
        <StatBar label='Hardness' value={layer.hardness} max={PERCENT} framed />
        <StatBar
          label='Holds water'
          value={layer.porosity}
          max={PERCENT}
          framed
        />
        <StatBar
          label='Dissolves'
          value={layer.solubility}
          max={PERCENT}
          framed
        />
        <StatBar
          label='Carves'
          value={layer.workability}
          max={PERCENT}
          framed
        />
      </div>
      {veins.total > 0 ? (
        <div className='flex min-w-0 flex-col gap-1'>
          <div className='flex min-w-0 flex-wrap gap-1' aria-label='Veins'>
            {veins.visible.map(([material, richness]) => (
              <Badge key={material} variant='secondary'>
                {`${plain({}, material)} ${richness}%`}
              </Badge>
            ))}
          </div>
          <ShowMore state={veins} />
        </div>
      ) : (
        <Muted variant='caption'>No vein runs through this layer.</Muted>
      )}
    </div>
  )
}

function StratumCard({ stratum }: { stratum: Stratum }) {
  const spec = STRATUM[stratum.stratum]
  const reached =
    stratum.reached_epoch !== null && stratum.reached_epoch !== undefined
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={spec.icon}
          tone={reached ? spec.tone : 'muted'}
          size='sm'
        />
        <Text as='span' weight='medium' truncate>
          {spec.label}
        </Text>
        <Muted variant='caption'>{`At depth ${stratum.depth}`}</Muted>
      </div>
      <Muted variant='caption'>{spec.hint}</Muted>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Badge variant={reached ? 'info' : 'default'}>
          {reached
            ? `Reached in epoch ${stratum.reached_epoch}`
            : 'Not reached'}
        </Badge>
        {stratum.breached_epoch !== null &&
        stratum.breached_epoch !== undefined ? (
          <Badge variant='destructive'>{`Breached in epoch ${stratum.breached_epoch}`}</Badge>
        ) : null}
        {stratum.tapped_epoch !== null && stratum.tapped_epoch !== undefined ? (
          <Badge variant='warning'>{`Tapped in epoch ${stratum.tapped_epoch}`}</Badge>
        ) : null}
        {stratum.locked.length > 0 ? (
          <Badge variant='warning'>Held</Badge>
        ) : null}
      </div>
      {stratum.volume > 0 || stratum.pressure > 0 ? (
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <StatBar label='Volume' value={stratum.volume} max={1000} framed />
          <StatBar
            label='Pressure'
            value={stratum.pressure}
            max={PERCENT}
            framed
          />
        </div>
      ) : null}
    </div>
  )
}

export function BeneathSection({ regionId }: { regionId: number }) {
  const view = useQuery({
    queryKey: [...loreKeys.entity(regionId), 'environment', 'beneath'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/beneath', {
          params: { path: { region_id: regionId } },
        })
      ),
    retry: false,
  })
  const data = view.data
  return (
    <Section
      id='section-beneath'
      title='Beneath'
      description='The rock this land is made of, layer by layer, and the depths below it. Edit any layer or depth in Every record.'
      icon={Layers}
    >
      {view.isLoading ? (
        <LoadingBlock label='Reading the rock' />
      ) : !data ? (
        <EmptyState
          icon={Layers}
          title='Not surveyed yet'
          description='The next epoch lays the ground of this land.'
        />
      ) : (
        <div className='@container/deep flex min-w-0 flex-col gap-3'>
          <div className='grid min-w-0 grid-cols-1 gap-2 @md/deep:grid-cols-3'>
            <MiniStat
              icon={Pickaxe}
              label='Dug to depth'
              value={data.mined_depth}
            />
            <MiniStat
              icon={Hammer}
              label='Quarry stone'
              value={GRADE[data.quarry_grade].label}
              tone={GRADE[data.quarry_grade].tone}
            />
            <MiniStat
              icon={ArrowDownToLine}
              label='Carved dwellings'
              value={
                data.carvable ? 'The rock can be carved' : 'Too hard to carve'
              }
            />
          </div>
          {data.layers.length === 0 ? (
            <EmptyState
              icon={Layers}
              title='No rock column'
              description='This land holds no ground to dig, or its column is not laid yet.'
            />
          ) : (
            <PagedList
              items={data.layers}
              initial={6}
              noun={['layer', 'layers']}
              className='flex min-w-0 flex-col gap-2'
              itemKey={(layer) => layer.id}
            >
              {(layer) => <LayerRow layer={layer} />}
            </PagedList>
          )}
          {data.strata.length === 0 ? (
            <Muted variant='caption'>
              Nothing lies below the rock of this land.
            </Muted>
          ) : (
            <PagedList
              items={data.strata}
              initial={6}
              noun={['depth', 'depths']}
              className='grid min-w-0 grid-cols-1 gap-2 @md/deep:grid-cols-2'
              itemKey={(stratum) => stratum.id}
            >
              {(stratum) => <StratumCard stratum={stratum} />}
            </PagedList>
          )}
        </div>
      )}
    </Section>
  )
}
