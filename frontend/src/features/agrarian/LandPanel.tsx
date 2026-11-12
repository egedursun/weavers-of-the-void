import { useState } from 'react'
import { Gauge, Map as MapIcon, Ruler, Store, Wheat } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, MANY, SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type AgrarianNodeView, useAgrarianAction } from './api'
import { NUTRIENTS, RANKS, RINGS } from './labels'
import { bar, TOWN_TYPES, useAgrarianRow } from './model'

type Ring = NonNullable<AgrarianNodeView['ring']>
type Central = NonNullable<AgrarianNodeView['central_place']>
type Nutrient = AgrarianNodeView['nutrients'][number]
type Pressure = NonNullable<AgrarianNodeView['intensity']>

const NOT_LAND = 'Only a land has a ring of use, a soil and farmers'
const NOT_TOWN = 'Only a settlement ranks among central places'

function RingCard({ row, blocked }: { row: Ring; blocked: string | null }) {
  const action = useAgrarianRow(
    'land_ring:edit',
    'land_ring:delete',
    { region_id: row.region.id },
    blocked
  )
  const ring = RINGS[row.ring]
  return (
    <Held
      icon={ring.icon}
      tone={ring.tone}
      title={`${row.region.name}: ${ring.label}`}
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Read the ring anew'
      editTitle='Set the ring of use'
      note='Around each market, land use follows the cost of carrying goods: gardens and dairy beside the town, fuel wood next, grain further out and herds furthest. Rivers, roads and canals bring the market nearer. A wide gap between markets draws settlers to found a new town.'
      fields={[
        {
          key: 'ring',
          label: 'Ring of use',
          kind: 'pick',
          table: table(RINGS),
        },
        {
          key: 'market_entity_id',
          label: 'Nearest market',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'distance',
          label: 'Cost of carrying to market',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'by_water',
          label: 'Carried by water',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'gap',
          label: 'Gap between markets',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Gap between markets'
        value={row.gap}
        tone='warning'
        icon={MapIcon}
      />
      <Facts
        items={[
          [
            'Market',
            <Ref key='market' node={row.market} empty='no market in reach' />,
          ],
          ['Cost of carrying', String(row.distance)],
          ['By water', row.by_water ? 'Yes' : 'No'],
        ]}
      />
    </Held>
  )
}

function CentralCard({
  row,
  blocked,
}: {
  row: Central
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'central_place:edit',
    'central_place:delete',
    { settlement_id: row.settlement.id },
    blocked
  )
  const rank = RANKS[row.rank]
  return (
    <Held
      icon={rank.icon}
      tone={rank.tone}
      title={`${row.settlement.name}: ${rank.label}`}
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Read the rank anew'
      editTitle='Set the central place'
      note='A place serves the goods its buyers within reach can carry: hamlets serve daily needs, markets the goods of every week and cities rare goods. Centrality helps a settlement grow into a larger tier.'
      fields={[
        {
          key: 'rank',
          label: 'Rank of goods',
          kind: 'pick',
          table: table(RANKS),
        },
        {
          key: 'catchment',
          label: 'Buyers within reach',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'served_by_entity_id',
          label: 'Served by',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'centrality',
          label: 'Centrality',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Centrality'
        value={row.centrality}
        tone='legendary'
        icon={Store}
      />
      <Facts
        items={[
          ['Buyers within reach', String(row.catchment)],
          [
            'Served by',
            <Ref key='served' node={row.served_by} empty='no higher place' />,
          ],
        ]}
      />
    </Held>
  )
}

function NutrientCard({
  row,
  regionId,
  blocked,
}: {
  row: Nutrient
  regionId: number
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'soil_nutrient:edit',
    'soil_nutrient:delete',
    { region_id: regionId, nutrient: row.nutrient },
    blocked
  )
  const kind = NUTRIENTS[row.nutrient]
  const trend = row.trend > 0 ? `+${row.trend}` : String(row.trend)
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`${trend} last epoch · read in epoch ${row.updated_epoch}`}
      removeLabel='Reset to the natural soil'
      editTitle='Set the stock'
      note='Crops draw the stocks by their kind, root crops taking more minerals and fodder crops returning the fixed element; rotations return it too, fallow and manure restore it, rivers, floods and ash bring minerals, and forest feeds organic matter. Irrigation without drainage leaves salt. The soil’s fertility follows these stocks.'
      fields={[
        { key: 'stock', label: 'Stock', kind: 'number', min: 0, max: SPAN },
        {
          key: 'trend',
          label: 'Change last epoch',
          kind: 'number',
          min: -SPAN,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={kind.label}
        value={row.stock}
        tone={bar(kind.tone)}
        icon={kind.icon}
      />
    </Held>
  )
}

function PressureCard({
  row,
  regionId,
  blocked,
}: {
  row: Pressure
  regionId: number
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'intensification:edit',
    'intensification:delete',
    { region_id: regionId },
    blocked
  )
  return (
    <Held
      icon={Wheat}
      tone='gold'
      title='Farming under pressure'
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Read the pressure anew'
      editTitle='Set the farming of the land'
      note='When their numbers press on what the land can feed, farmers work it harder, research farming and take up irrigation, terraces and rotations; where land is plenty, they do not.'
      fields={[
        {
          key: 'pressure',
          label: 'People against what the land feeds (%)',
          kind: 'number',
          min: 0,
          max: SPAN * 3,
        },
        {
          key: 'intensity',
          label: 'Labour per land',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'research_boost',
          label: 'Research boost to farming (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-3'>
          <KpiTile
            label='Pressure'
            value={`${row.pressure}%`}
            icon={Gauge}
            tone='warning'
          />
          <KpiTile
            label='Labour per land'
            value={row.intensity}
            icon={Wheat}
            tone='gold'
          />
          <KpiTile
            label='Research boost'
            value={`${row.research_boost}%`}
            icon={Ruler}
            tone='info'
          />
        </div>
      </div>
    </Held>
  )
}

function LandForge({
  nodeId,
  isLand,
  data,
  blocked,
}: {
  nodeId: number
  isLand: boolean
  data: AgrarianNodeView
  blocked: string | null
}) {
  const [ring, setRing] = useState<keyof typeof RINGS>('grain')
  const [market, setMarket] = useState<number | null>(null)
  const [nutrient, setNutrient] = useState<keyof typeof NUTRIENTS>('fixed')
  const [stock, setStock] = useState('50')
  const [intensity, setIntensity] = useState('40')
  const [boost, setBoost] = useState('20')
  const gate = isLand ? blocked : NOT_LAND
  const ringing = useAgrarianAction(
    'land_ring:set',
    (_: void) => ({ region_id: nodeId, ring, market_id: market }),
    'The ring of use is set'
  )
  const feeding = useAgrarianAction(
    'soil_nutrient:set',
    (_: void) => ({ region_id: nodeId, nutrient, stock: clamp(stock) }),
    'The soil is set'
  )
  const pressing = useAgrarianAction(
    'intensification:set',
    (_: void) => ({
      region_id: nodeId,
      intensity: clamp(intensity),
      research_boost: clamp(boost),
    }),
    'The farming is set'
  )
  const ringBusy = why(gate, ringing.isPending)
  const soilBusy = why(gate, feeding.isPending)
  const pressBusy = why(gate, pressing.isPending)
  return (
    <ForgeCard
      icon={MapIcon}
      tone='verdigris'
      title='Shape the land'
      note={
        data.ring
          ? 'Set the land’s ring, one of its soil stocks, or how hard it is farmed.'
          : 'This land has not been read yet; set its ring, soil and farming as you wish.'
      }
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={ringBusy !== null}
            disabledReason={ringBusy ?? undefined}
            onClick={() => ringing.mutate()}
          >
            <MapIcon />
            Set the ring
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={soilBusy !== null}
            disabledReason={soilBusy ?? undefined}
            onClick={() => feeding.mutate()}
          >
            <Wheat />
            Set the soil
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={pressBusy !== null}
            disabledReason={pressBusy ?? undefined}
            onClick={() => pressing.mutate()}
          >
            <Gauge />
            Set the farming
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Ring of use'
        value={ring}
        table={table(RINGS)}
        blocked={gate}
        onPick={(value) => setRing(value as keyof typeof RINGS)}
      />
      <NodePicker
        label='Nearest market'
        value={market}
        onChange={setMarket}
        blocked={gate}
        types={TOWN_TYPES}
      />
      <MindPicker
        label='Soil stock'
        value={nutrient}
        table={table(NUTRIENTS)}
        blocked={gate}
        onPick={(value) => setNutrient(value as keyof typeof NUTRIENTS)}
      />
      <NumberField
        label='Stock'
        value={stock}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setStock}
      />
      <NumberField
        label='Labour per land'
        value={intensity}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setIntensity}
      />
      <NumberField
        label='Research boost (%)'
        value={boost}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setBoost}
      />
    </ForgeCard>
  )
}

function CentralForge({
  nodeId,
  isTown,
  blocked,
}: {
  nodeId: number
  isTown: boolean
  blocked: string | null
}) {
  const [rank, setRank] = useState<keyof typeof RANKS>('weekly')
  const [centrality, setCentrality] = useState('50')
  const gate = isTown ? blocked : NOT_TOWN
  const setting = useAgrarianAction(
    'central_place:set',
    (_: void) => ({
      settlement_id: nodeId,
      rank,
      centrality: clamp(centrality),
    }),
    'The central place is set'
  )
  const busy = why(gate, setting.isPending)
  return (
    <ForgeCard
      icon={Store}
      tone='gold'
      title='Rank this place'
      note='Make the settlement a market of daily, weekly or rare goods.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Store />
          Rank it
        </Button>
      }
    >
      <MindPicker
        label='Rank of goods'
        value={rank}
        table={table(RANKS)}
        blocked={gate}
        onPick={(value) => setRank(value as keyof typeof RANKS)}
      />
      <NumberField
        label='Centrality'
        value={centrality}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setCentrality}
      />
    </ForgeCard>
  )
}

export function LandPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: AgrarianNodeView
  blocked: string | null
}) {
  const isLand = kind === 'region'
  return (
    <div data-surface='LandPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Ring of use'
        items={data.ring ? [data.ring] : []}
        empty='No ring of land use has been read here.'
        noun={['ring', 'rings']}
        itemKey={(item) => item.region.id}
      >
        {(item) => <RingCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Soil'
        items={data.nutrients}
        empty='No soil stocks have been read here.'
        noun={['stock', 'stocks']}
        itemKey={(item) => item.nutrient}
      >
        {(item) => (
          <NutrientCard row={item} regionId={nodeId} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Farming under pressure'
        items={data.intensity ? [data.intensity] : []}
        empty='No pressure on the land has been read here.'
        noun={['reading', 'readings']}
        itemKey={() => nodeId}
      >
        {(item) => (
          <PressureCard row={item} regionId={nodeId} blocked={blocked} />
        )}
      </Listed>
      <LandForge
        nodeId={nodeId}
        isLand={isLand}
        data={data}
        blocked={blocked}
      />
      <Listed
        title='Central place'
        items={data.central_place ? [data.central_place] : []}
        empty='This is not ranked among central places.'
        noun={['place', 'places']}
        itemKey={(item) => item.settlement.id}
      >
        {(item) => <CentralCard row={item} blocked={blocked} />}
      </Listed>
      <CentralForge
        nodeId={nodeId}
        isTown={kind === 'settlement'}
        blocked={blocked}
      />
    </div>
  )
}
