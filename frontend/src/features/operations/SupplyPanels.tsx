import { useState } from 'react'
import {
  Activity,
  Gauge,
  Package,
  PauseCircle,
  Scissors,
  Truck,
  Warehouse,
  Wrench,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type OperationsNodeView, useOperationsAction } from './api'
import { TRANSPORTS } from './labels'
import {
  MANY,
  OWNER_TYPES,
  REGION_TYPES,
  SPAN,
  STRUCTURE_TYPES,
  share,
  useOpsRow,
} from './model'

type Flow = OperationsNodeView['flows'][number]
type Depot = OperationsNodeView['depots'][number]
type Transport = OperationsNodeView['transport'][number]
type Operation = NonNullable<OperationsNodeView['operation']>

const OWNER_KINDS = new Set<string>(OWNER_TYPES)
const NOT_OWNER =
  'Only a realm, a town, a people, a faction or a house keeps depots and transport'
const NOT_ARMY = 'Only an army goes on the offensive'

function OperationCard({
  row,
  blocked,
}: {
  row: Operation
  blocked: string | null
}) {
  const action = useOpsRow(
    'army_operation:edit',
    'army_operation:delete',
    { army_id: row.army.id },
    blocked
  )
  const fed = share(row.delivered, row.need)
  return (
    <Held
      icon={row.culminated ? PauseCircle : Activity}
      tone={row.culminated ? 'danger' : 'success'}
      title={`The offensive of ${row.army.name}`}
      caption={`Read in epoch ${row.updated_epoch}${row.culminated_epoch !== null ? ` · culminated in epoch ${row.culminated_epoch}` : ''}`}
      removeLabel='Read the offensive anew'
      editTitle='Set the offensive'
      note='An army on the offensive outruns its supply as its line lengthens and its losses mount. When the supply delivered falls short of its need while its organisation is low, the offensive reaches its culmination: a commander skilled in logistics sees it coming and pauses in time, one who does not may press on and see it collapse. Foresight counts the seasons the commander sees ahead.'
      fields={[
        {
          key: 'offensive_seasons',
          label: 'Seasons on the offensive',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'need',
          label: 'Supply needed a season',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'delivered',
          label: 'Supply delivered',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'organisation',
          label: 'Organisation',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'culminated', label: 'Culminated', kind: 'pick', table: YES_NO },
        {
          key: 'pause_seasons',
          label: 'Seasons of pause left',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'foresight',
          label: 'Foresight (seasons)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'standing',
          label: 'Mostly on standing orders',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {row.culminated && (
            <Badge size='sm' variant='destructive'>
              <PauseCircle aria-hidden='true' />
              Culminated
            </Badge>
          )}
          {row.pause_seasons > 0 && (
            <Badge size='sm' variant='warning'>
              Pausing {row.pause_seasons} more seasons
            </Badge>
          )}
          {row.standing && (
            <Badge size='sm' variant='secondary'>
              Mostly on standing orders
            </Badge>
          )}
        </div>
      }
    >
      <Meter
        label={`Supply delivered against need (${fed}%)`}
        value={Math.min(SPAN, fed)}
        tone='success'
        icon={Package}
      />
      <Meter
        label='Organisation'
        value={row.organisation}
        tone='info'
        icon={Gauge}
      />
      <Facts
        items={[
          ['Seasons on the offensive', String(row.offensive_seasons)],
          ['Foresight', `${row.foresight} seasons`],
          ['Supply needed', String(row.need)],
          ['Supply delivered', String(row.delivered)],
        ]}
      />
    </Held>
  )
}

function FlowCard({ row, blocked }: { row: Flow; blocked: string | null }) {
  const action = useOpsRow(
    'supply_flow:edit',
    'supply_flow:delete',
    { flow_id: row.id },
    blocked
  )
  const widest = Math.max(1, row.produced, row.shipped, row.need)
  return (
    <Held
      icon={Truck}
      tone={row.delivered >= row.need ? 'success' : 'warning'}
      title={`Supply to ${row.army.name}`}
      caption={`Epoch ${row.epoch}, season ${row.season + 1}${row.depot_id !== null ? ` · from depot ${row.depot_id}` : ''}`}
      removeLabel='Strike the flow'
      editTitle='Set the flow'
      note='Each season a depot draws food from the realm’s stocks, the train carries what its throughput allows toward the army, and some is lost on every land it crosses and more on a raided line. What arrives is what was drawn, less what was lost on the way and what stays in the depot.'
      fields={[
        {
          key: 'produced',
          label: 'Drawn from stocks',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'shipped', label: 'Sent on', kind: 'number', min: 0, max: MANY },
        {
          key: 'lost',
          label: 'Lost on the way',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'delivered',
          label: 'Delivered',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'need', label: 'Needed', kind: 'number', min: 0, max: MANY },
        {
          key: 'throughput',
          label: 'Throughput',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Drawn from stocks: ${row.produced}`}
        value={row.produced}
        max={widest}
        tone='legendary'
        icon={Warehouse}
      />
      <Meter
        label={`Sent on: ${row.shipped}`}
        value={row.shipped}
        max={widest}
        tone='info'
        icon={Truck}
      />
      <Meter
        label={`Lost on the way: ${row.lost}`}
        value={row.lost}
        max={widest}
        tone='destructive'
        icon={Scissors}
      />
      <Meter
        label={`Delivered: ${row.delivered} of ${row.need} needed`}
        value={row.delivered}
        max={widest}
        tone='success'
        icon={Package}
      />
      <Facts
        items={[
          ['Throughput', String(row.throughput)],
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
        ]}
      />
    </Held>
  )
}

function DepotCard({ row, blocked }: { row: Depot; blocked: string | null }) {
  const action = useOpsRow(
    'depot:edit',
    'depot:delete',
    { depot_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Warehouse}
      tone={row.cut ? 'danger' : row.field ? 'warning' : 'gold'}
      title={`${row.field ? 'Field depot' : 'Depot'} in ${row.region?.name ?? 'no land'}`}
      caption={`Depot ${row.id} · founded in epoch ${row.founded_epoch}`}
      removeLabel='Empty the depot'
      editTitle='Set the depot'
      note='A depot holds supplies for the armies it feeds. Field depots are founded along an advancing line and hold less; an enemy army standing in a depot’s land cuts it off, and a cut depot sends nothing.'
      fields={[
        {
          key: 'region_entity_id',
          label: 'Land',
          kind: 'node',
          types: REGION_TYPES,
        },
        {
          key: 'structure_entity_id',
          label: 'Storehouse',
          kind: 'node',
          types: STRUCTURE_TYPES,
        },
        {
          key: 'supplies',
          label: 'Supplies',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'capacity',
          label: 'Capacity',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'field', label: 'Field depot', kind: 'pick', table: YES_NO },
        { key: 'cut', label: 'Cut off', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        row.cut ? (
          <Badge size='sm' variant='destructive'>
            <Scissors aria-hidden='true' />
            Cut off
          </Badge>
        ) : undefined
      }
    >
      <Meter
        label={`Supplies (${row.supplies} of ${row.capacity})`}
        value={row.supplies}
        max={Math.max(1, row.capacity)}
        tone='legendary'
        icon={Package}
      />
      <Facts
        items={[
          [
            'Storehouse',
            <Ref key='store' node={row.structure} empty='in the open' />,
          ],
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
        ]}
      />
    </Held>
  )
}

function TransportCard({
  row,
  depots,
  blocked,
}: {
  row: Transport
  depots: Depot[]
  blocked: string | null
}) {
  const action = useOpsRow(
    'transport:edit',
    'transport:delete',
    { transport_id: row.id },
    blocked
  )
  const look = TRANSPORTS[row.transport_kind]
  const depot = depots.find((item) => item.id === row.depot_id)
  return (
    <Held
      icon={look.icon}
      tone={look.tone}
      title={`${row.count} ${look.label.toLowerCase()}`}
      caption={`Each carries ${row.capacity}${depot ? ` · based at the depot in ${depot.region?.name ?? 'no land'}` : ''}`}
      removeLabel='Remove from the train'
      editTitle='Set the transport'
      note='Transport sets how much a line carries each season: its count times what each carries, worn down by hauling and mended at peace. Roads raise it, barges carry more along a river and only there, and supply ships only reach an army on the coast.'
      fields={[
        {
          key: 'depot_id',
          label: 'Based at depot',
          kind: 'pick',
          table: Object.fromEntries(
            depots.map((item) => [
              String(item.id),
              `Depot in ${item.region?.name ?? 'no land'}`,
            ])
          ),
        },
        {
          key: 'kind',
          label: 'Carrier',
          kind: 'pick',
          table: table(TRANSPORTS),
        },
        { key: 'count', label: 'Count', kind: 'number', min: 0, max: MANY },
        {
          key: 'capacity',
          label: 'Each carries',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'condition',
          label: 'Condition',
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
        label='Condition'
        value={row.condition}
        tone='verdigris'
        icon={Wrench}
      />
      <Facts
        items={[
          [
            'Carries in all',
            String(
              Math.round((row.count * row.capacity * row.condition) / SPAN)
            ),
          ],
          ['Owner', <Ref key='owner' node={row.owner} empty='no owner' />],
        ]}
      />
    </Held>
  )
}

function SupplyForge({
  nodeId,
  kind,
  depots,
  blocked,
}: {
  nodeId: number
  kind: string | null
  depots: Depot[]
  blocked: string | null
}) {
  const isOwner = OWNER_KINDS.has(kind ?? '')
  const gate = isOwner ? blocked : NOT_OWNER
  const [region, setRegion] = useState<number | null>(null)
  const [field, setField] = useState<'true' | 'false'>('false')
  const [capacity, setCapacity] = useState('600')
  const [supplies, setSupplies] = useState('200')
  const [carrier, setCarrier] = useState<keyof typeof TRANSPORTS>('wagons')
  const [count, setCount] = useState('10')
  const [base, setBase] = useState('')
  const founding = useOperationsAction(
    'depot:create',
    (_: void) => ({
      owner_id: nodeId,
      region_id: region ?? 0,
      field: field === 'true',
      capacity: clamp(capacity, MANY),
      supplies: clamp(supplies, MANY),
    }),
    'The depot is stocked'
  )
  const adding = useOperationsAction(
    'transport:create',
    (_: void) => ({
      owner_id: nodeId,
      kind: carrier,
      count: Math.max(1, clamp(count, MANY)),
      depot_id: base === '' ? null : Number(base),
    }),
    'Transport joins the train'
  )
  const depotBusy = why(
    gate ?? (region === null ? 'Choose the land of the depot' : null),
    founding.isPending
  )
  const trainBusy = why(gate, adding.isPending)
  return (
    <ForgeCard
      icon={Warehouse}
      tone='gold'
      title='Stock a depot or add transport'
      note='Found a depot in a land of your choosing and stock it, or add wagons, pack animals, porters, barges, supply ships or sky barges to the realm’s train.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={depotBusy !== null}
            disabledReason={depotBusy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <Warehouse />
            Stock the depot
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={trainBusy !== null}
            disabledReason={trainBusy ?? undefined}
            onClick={() => adding.mutate()}
          >
            <Truck />
            Add to the train
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Land of the depot'
        value={region}
        onChange={setRegion}
        blocked={gate}
        types={REGION_TYPES}
      />
      <MindPicker
        label='Field depot'
        value={field}
        table={YES_NO}
        blocked={gate}
        onPick={(value) => setField(value as 'true' | 'false')}
      />
      <NumberField
        label='Capacity'
        value={capacity}
        min={0}
        max={MANY}
        blocked={gate}
        onChange={setCapacity}
      />
      <NumberField
        label='Supplies at first'
        value={supplies}
        min={0}
        max={MANY}
        blocked={gate}
        onChange={setSupplies}
      />
      <MindPicker
        label='Carrier'
        value={carrier}
        table={table(TRANSPORTS)}
        blocked={gate}
        onPick={(value) => setCarrier(value as keyof typeof TRANSPORTS)}
      />
      <NumberField
        label='How many'
        value={count}
        min={1}
        max={MANY}
        blocked={gate}
        onChange={setCount}
      />
      <MindPicker
        label='Based at depot'
        value={base}
        table={Object.fromEntries(
          depots.map((item) => [
            String(item.id),
            `Depot in ${item.region?.name ?? 'no land'}`,
          ])
        )}
        blocked={gate}
        placeholder='No base'
        onPick={setBase}
      />
    </ForgeCard>
  )
}

function OperationForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const gate = kind === 'army' ? blocked : NOT_ARMY
  const [culminated, setCulminated] = useState<'true' | 'false'>('false')
  const [pause, setPause] = useState('0')
  const setting = useOperationsAction(
    'army_operation:set',
    (_: void) => ({
      army_id: nodeId,
      culminated: culminated === 'true',
      pause_seasons: clamp(pause, SPAN),
    }),
    'The offensive is set'
  )
  const busy = why(gate, setting.isPending)
  return (
    <ForgeCard
      icon={Activity}
      tone='danger'
      title='Halt or drive the offensive'
      note='Declare the offensive culminated and order a pause of some seasons, or clear it so the army presses on.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <PauseCircle />
          Set the offensive
        </Button>
      }
    >
      <MindPicker
        label='Culminated'
        value={culminated}
        table={YES_NO}
        blocked={gate}
        onPick={(value) => setCulminated(value as 'true' | 'false')}
      />
      <NumberField
        label='Seasons of pause'
        value={pause}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setPause}
      />
    </ForgeCard>
  )
}

export function SupplyPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: OperationsNodeView
  blocked: string | null
}) {
  const produced = data.flows.reduce((sum, item) => sum + item.produced, 0)
  const lost = data.flows.reduce((sum, item) => sum + item.lost, 0)
  const delivered = data.flows.reduce((sum, item) => sum + item.delivered, 0)
  return (
    <div
      data-surface='SupplyPanel'
      data-chart='chart-supply-flow'
      className='flex min-w-0 flex-col gap-4'
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-3'>
          <KpiTile
            label='Drawn from stocks'
            value={produced}
            icon={Warehouse}
            tone='gold'
          />
          <KpiTile
            label='Lost on the way'
            value={lost}
            icon={Scissors}
            tone='danger'
          />
          <KpiTile
            label='Delivered to armies'
            value={delivered}
            icon={Package}
            tone='success'
          />
        </div>
      </div>
      <Listed
        title='The offensive'
        items={data.operation ? [data.operation] : []}
        empty='This army has not yet been read on the offensive.'
        noun={['offensive', 'offensives']}
        itemKey={(item) => item.army.id}
      >
        {(item) => <OperationCard row={item} blocked={blocked} />}
      </Listed>
      <OperationForge nodeId={nodeId} kind={kind} blocked={blocked} />
      <Listed
        title='Supply flows, season by season'
        items={data.flows}
        empty='No supply has flowed here.'
        noun={['flow', 'flows']}
        itemKey={(item) => item.id}
      >
        {(item) => <FlowCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Depots'
        items={data.depots}
        empty='No depot stands here.'
        noun={['depot', 'depots']}
        itemKey={(item) => item.id}
      >
        {(item) => <DepotCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='The train'
        items={data.transport}
        empty='No transport is kept here.'
        noun={['carrier', 'carriers']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <TransportCard row={item} depots={data.depots} blocked={blocked} />
        )}
      </Listed>
      <SupplyForge
        nodeId={nodeId}
        kind={kind}
        depots={data.depots}
        blocked={blocked}
      />
    </div>
  )
}
