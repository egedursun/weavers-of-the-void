import { useQuery } from '@tanstack/react-query'
import { ArrowDownToLine, Hammer, Layers, Lock, Pickaxe } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'
import { DEEP_WORLD } from './deepFamily'
import {
  GRADE,
  PASSAGE_KIND,
  PASSAGE_ORIGIN,
  PASSAGE_STATE,
  ROCK,
  STRATUM,
} from './geologyLabels'
import { TERRAIN, plain } from './labels'

type Layer = components['schemas']['RockLayerView']
type Stratum = components['schemas']['DepthStratumView']
type Passage = components['schemas']['DeepPassageView']

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

function HoldButton({
  action,
  id,
  held,
  noun,
}: {
  action: 'deep_cell:hold' | 'deep_passage:hold'
  id: number
  held: boolean
  noun: string
}) {
  const { reason } = useGodGate()
  const table =
    action === 'deep_cell:hold' ? 'region_underground' : 'deep_passages'
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST(`/api/actions/${action}`, {
          body: { table, key: { id }, values: {}, hold: true, release: [] },
        })
      ),
    success: `The ${noun} is held as it is`,
  })
  const blocked =
    reason() ??
    (held ? `This ${noun} is already held` : hold.isPending ? 'Working…' : null)
  return (
    <Button
      size='sm'
      variant='outline'
      className='self-start'
      disabled={blocked !== null}
      disabledReason={blocked ?? undefined}
      onClick={() => hold.mutate()}
      aria-label={`Hold this ${noun}`}
    >
      <Lock />
      Hold
    </Button>
  )
}

function PassageCard({ passage }: { passage: Passage }) {
  const kind = PASSAGE_KIND[passage.kind]
  const state = PASSAGE_STATE[passage.state]
  const origin = PASSAGE_ORIGIN[passage.origin]
  const near = passage.near_stratum
    ? STRATUM[passage.near_stratum].label
    : 'The surface'
  const far = passage.far_stratum
    ? STRATUM[passage.far_stratum].label
    : 'the surface'
  const showProgress =
    passage.state === 'digging' || passage.state === 'collapsed'
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={kind.icon} tone={state.tone} size='sm' />
        <Text as='span' weight='medium' truncate>
          {kind.label}
        </Text>
        <Badge variant={passage.state === 'open' ? 'info' : 'warning'}>
          {state.label}
        </Badge>
      </div>
      <Muted variant='caption'>
        {`${near} to ${far}${passage.far_region ? ` beneath ${passage.far_region.name}` : ''}`}
      </Muted>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Badge>{origin.label}</Badge>
        {passage.place ? (
          <Badge>{`Comes out at ${passage.place.name}`}</Badge>
        ) : null}
        {passage.digger ? (
          <Badge>{`Dug by ${passage.digger.name}`}</Badge>
        ) : null}
        {passage.locked.length > 0 ? (
          <Badge variant='warning'>Held</Badge>
        ) : null}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <StatBar label='Width' value={passage.width} max={PERCENT} framed />
        {showProgress ? (
          <StatBar
            label='Progress'
            value={passage.progress}
            max={PERCENT}
            framed
          />
        ) : null}
      </div>
      <HoldButton
        action='deep_passage:hold'
        id={passage.id}
        held={passage.locked.length > 0}
        noun='passage'
      />
    </div>
  )
}

function StratumCard({ stratum }: { stratum: Stratum }) {
  const spec = STRATUM[stratum.stratum]
  const fault = stratum.stratum === 'fault_zone'
  const ripe = fault && stratum.pressure >= PERCENT
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
      {stratum.name ? <Text as='span'>{stratum.name}</Text> : null}
      <Muted variant='caption'>{spec.hint}</Muted>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Badge>
          {TERRAIN[stratum.terrain]?.label ?? plain({}, stratum.terrain)}
        </Badge>
        <Badge variant={stratum.dwellable ? 'info' : 'default'}>
          {stratum.dwellable ? 'Can be dwelt in' : 'No one can dwell here'}
        </Badge>
        {stratum.holder ? (
          <Badge variant='info'>{`Held by ${stratum.holder.name}`}</Badge>
        ) : null}
        {stratum.realm ? (
          <Badge>{`The realm of ${stratum.realm.name}`}</Badge>
        ) : null}
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
        {ripe ? <Badge variant='destructive'>Ready to give way</Badge> : null}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <StatBar label='Extent' value={stratum.extent} max={PERCENT} framed />
        <StatBar label='Light' value={stratum.light} max={PERCENT} framed />
        {stratum.volume > 0 || stratum.pressure > 0 || fault ? (
          <>
            <StatBar label='Volume' value={stratum.volume} max={1000} framed />
            <StatBar
              label={fault ? 'Fault stress' : 'Pressure'}
              value={stratum.pressure}
              max={PERCENT}
              framed
            />
          </>
        ) : null}
      </div>
      {stratum.dwellers.length > 0 ? (
        <Muted variant='caption'>{`Dwelling here: ${stratum.dwellers.map((dweller) => dweller.name).join(', ')}`}</Muted>
      ) : null}
      <HoldButton
        action='deep_cell:hold'
        id={stratum.id}
        held={stratum.locked.length > 0}
        noun='cell'
      />
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
              className={
                data.strata.length > 1
                  ? 'grid min-w-0 grid-cols-1 gap-2 @md/deep:grid-cols-2'
                  : 'grid min-w-0 grid-cols-1 gap-2'
              }
              itemKey={(stratum) => stratum.id}
            >
              {(stratum) => <StratumCard stratum={stratum} />}
            </PagedList>
          )}
          {data.passages.length === 0 ? (
            <Muted variant='caption'>
              No passage leads from this land into the deep.
            </Muted>
          ) : (
            <PagedList
              items={data.passages}
              initial={6}
              noun={['passage', 'passages']}
              className={
                data.passages.length > 1
                  ? 'grid min-w-0 grid-cols-1 gap-2 @md/deep:grid-cols-2'
                  : 'grid min-w-0 grid-cols-1 gap-2'
              }
              itemKey={(passage) => passage.id}
            >
              {(passage) => <PassageCard passage={passage} />}
            </PagedList>
          )}
          <RecordRowsSection nodeId={regionId} family={DEEP_WORLD} />
        </div>
      )}
    </Section>
  )
}
