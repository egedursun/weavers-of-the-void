import { useState } from 'react'
import { ArrowRight, Plus, Scale } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { COMMODITY } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type OrdersNodeView, useOrdersAction } from './api'
import {
  ALLOCATION,
  CHANGES,
  COMPENSATION,
  DISTRIBUTION,
  LABOUR,
  OWNERSHIP,
  STAGES,
} from './labels'
import { MANY, SPAN, clamp, useOrdersRow } from './model'

type View = OrdersNodeView
type Order = View['orders'][number]
type Axes = {
  [K in 'ownership' | 'allocation' | 'labour' | 'distribution']?:
    Order[K] | null
}
const SECTORS = { none: 'The whole realm', ...table(COMMODITY) }

function axesLine(axes: Axes): string {
  return [
    axes.ownership
      ? `owned by ${OWNERSHIP[axes.ownership].label.toLowerCase()}`
      : null,
    axes.allocation
      ? `allotted by ${ALLOCATION[axes.allocation].label.toLowerCase()}`
      : null,
    axes.labour ? `${LABOUR[axes.labour].label.toLowerCase()} labour` : null,
    axes.distribution
      ? `shared ${DISTRIBUTION[axes.distribution].label.toLowerCase()}`
      : null,
  ]
    .filter(Boolean)
    .join(', ')
}

function OrderCard({
  row,
  kinds,
  blocked,
}: {
  row: Order
  kinds: Record<string, string>
  blocked: string | null
}) {
  const action = useOrdersRow(
    'economic_order:edit',
    'economic_order:delete',
    { record_id: row.id },
    blocked
  )
  const allocation = ALLOCATION[row.allocation]
  return (
    <Held
      icon={allocation.icon}
      tone={allocation.tone}
      title={`${row.sector ? COMMODITY[row.sector].label : 'The whole realm'}${row.kind_id !== null && row.kind_name ? `: ${row.kind_name}` : ''}`}
      caption={`${axesLine(row)}; since epoch ${row.since_epoch}`}
      removeLabel='Strike the order'
      editTitle='Set the order'
      note='Redistribution, dues and sharing move food to and from the centre; command needs planning; distribution favours some classes.'
      fields={[
        { key: 'sector', label: 'Good', kind: 'pick', table: SECTORS },
        {
          key: 'ownership',
          label: 'Ownership',
          kind: 'pick',
          table: table(OWNERSHIP),
        },
        {
          key: 'allocation',
          label: 'Allocation',
          kind: 'pick',
          table: table(ALLOCATION),
        },
        { key: 'labour', label: 'Labour', kind: 'pick', table: table(LABOUR) },
        {
          key: 'distribution',
          label: 'Distribution',
          kind: 'pick',
          table: table(DISTRIBUTION),
        },
        {
          key: 'planning_capacity',
          label: 'Planning capacity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'kind_id',
          label: 'Named order',
          kind: 'pick',
          table: { none: 'None', ...kinds },
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Planning capacity (${row.planning_capacity} of ${SPAN})`}
        value={row.planning_capacity}
        tone='info'
        icon={Scale}
      />
    </Held>
  )
}

function KindCard({
  row,
  blocked,
}: {
  row: View['kinds'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'economic_order_kind:edit',
    'economic_order_kind:delete',
    { record_id: row.id },
    blocked
  )
  const allocation = ALLOCATION[row.allocation]
  return (
    <Held
      icon={allocation.icon}
      tone={allocation.tone}
      title={row.name}
      caption={`${axesLine(row)}${row.built_in ? '; one of the orders every world knows' : ''}`}
      removeLabel='Strike the named order'
      editTitle='Set the named order'
      note='A realm whose order matches these four axes holds this named order.'
      fields={[
        { key: 'name', label: 'Name of the order', kind: 'text' },
        {
          key: 'ownership',
          label: 'Ownership',
          kind: 'pick',
          table: table(OWNERSHIP),
        },
        {
          key: 'allocation',
          label: 'Allocation',
          kind: 'pick',
          table: table(ALLOCATION),
        },
        { key: 'labour', label: 'Labour', kind: 'pick', table: table(LABOUR) },
        {
          key: 'distribution',
          label: 'Distribution',
          kind: 'pick',
          table: table(DISTRIBUTION),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function ChangeCard({
  row,
  blocked,
}: {
  row: View['transitions'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'order_transition:edit',
    'order_transition:delete',
    { record_id: row.id },
    blocked
  )
  const advancing = useOrdersAction(
    'order_transition:advance',
    (_: void) => ({ record_id: row.id }),
    'The change moves on'
  )
  const kind = CHANGES[row.kind]
  const stage = STAGES[row.stage]
  const open = row.stage === 'proclaimed' || row.stage === 'transferring'
  const advanceBusy = why(
    blocked ?? (open ? null : 'This change of order has ended'),
    advancing.isPending
  )
  return (
    <Held
      icon={kind.icon}
      tone={stage.tone}
      title={`${kind.label}: ${stage.label.toLowerCase()}`}
      caption={`${COMPENSATION[row.compensation].label}; ${row.transferred} ${row.transferred === 1 ? 'holding' : 'holdings'} moved; from ${axesLine(row.from_axes) || 'no order'} to ${axesLine(row.to_axes) || 'no order'}; epoch ${row.started_epoch}${row.ended_epoch !== null ? ` to ${row.ended_epoch}` : ''}${row.sector ? `; for ${COMMODITY[row.sector].label}` : ''}`}
      removeLabel='Call it off'
      editTitle='Set the change'
      note='Holdings move in stages; losers resist unless they are paid and may flee; too much resistance breaks the change.'
      fields={[
        { key: 'kind', label: 'Change', kind: 'pick', table: table(CHANGES) },
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        {
          key: 'compensation',
          label: 'Compensation',
          kind: 'pick',
          table: table(COMPENSATION),
        },
        {
          key: 'resistance',
          label: 'Resistance',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'transferred',
          label: 'Holdings moved',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'ended_epoch',
          label: 'Ended in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Button
          size='sm'
          variant='outline'
          disabled={advanceBusy !== null}
          disabledReason={advanceBusy ?? undefined}
          onClick={() => advancing.mutate()}
        >
          <ArrowRight />
          Push it on
        </Button>
      }
    >
      <Meter
        label={`Resistance (${row.resistance} of ${SPAN})`}
        value={row.resistance}
        tone='warning'
        icon={kind.icon}
      />
    </Held>
  )
}

export function OrderPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const realm = data.realm
  const kinds = Object.fromEntries(
    data.kinds.map((row) => [String(row.id), row.name])
  )
  const [sector, setSector] = useState('none')
  const [ownership, setOwnership] = useState('household')
  const [allocation, setAllocation] = useState('market')
  const [labour, setLabour] = useState('free')
  const [distribution, setDistribution] = useState('by_holding')
  const [planning, setPlanning] = useState('30')
  const [name, setName] = useState('')
  const [change, setChange] = useState('land_reform')
  const [paid, setPaid] = useState('none')
  const axes = {
    ownership: ownership as Order['ownership'],
    allocation: allocation as Order['allocation'],
    labour: labour as Order['labour'],
    distribution: distribution as Order['distribution'],
  }
  const chosenSector =
    sector === 'none' ? null : (sector as NonNullable<Order['sector']>)
  const setting = useOrdersAction(
    'economic_order:create',
    (_: void) => ({
      polity_id: realm?.id ?? 0,
      sector: chosenSector,
      planning_capacity: clamp(planning, SPAN),
      ...axes,
    }),
    'The order is set'
  )
  const naming = useOrdersAction(
    'economic_order_kind:create',
    (_: void) => ({ name: name.trim(), ...axes }),
    'The order is named'
  )
  const proclaiming = useOrdersAction(
    'order_transition:create',
    (_: void) => ({
      polity_id: realm?.id ?? 0,
      sector: chosenSector,
      kind: change as View['transitions'][number]['kind'],
      compensation: paid as View['transitions'][number]['compensation'],
    }),
    'The change of order is proclaimed'
  )
  const noRealm =
    realm === null
      ? 'This thing answers to no realm that holds an economic order'
      : null
  const setBusy = why(blocked ?? noRealm, setting.isPending)
  const nameBusy = why(
    blocked ?? (name.trim() === '' ? 'Give the order a name first' : null),
    naming.isPending
  )
  const changeBusy = why(blocked ?? noRealm, proclaiming.isPending)
  const axisPickers = (
    <>
      <MindPicker
        label='Ownership'
        value={ownership}
        table={table(OWNERSHIP)}
        placeholder='Choose'
        blocked={blocked}
        onPick={setOwnership}
      />
      <MindPicker
        label='Allocation'
        value={allocation}
        table={table(ALLOCATION)}
        placeholder='Choose'
        blocked={blocked}
        onPick={setAllocation}
      />
      <MindPicker
        label='Labour'
        value={labour}
        table={table(LABOUR)}
        placeholder='Choose'
        blocked={blocked}
        onPick={setLabour}
      />
      <MindPicker
        label='Distribution'
        value={distribution}
        table={table(DISTRIBUTION)}
        placeholder='Choose'
        blocked={blocked}
        onPick={setDistribution}
      />
    </>
  )
  return (
    <div data-surface='OrderPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={realm} empty='no realm' />],
          ['Orders', String(data.orders.length)],
          [
            'Changes in course',
            String(
              data.transitions.filter(
                (row) =>
                  row.stage === 'proclaimed' || row.stage === 'transferring'
              ).length
            ),
          ],
        ]}
      />
      <Bars
        chart='chart-economic-order'
        title='How well each order is planned'
        legend={[{ text: 'Planning capacity', variant: 'secondary' }]}
        rows={data.orders.map((row) => ({
          key: String(row.id),
          caption: `${row.sector ? COMMODITY[row.sector].label : 'The whole realm'}: ${ALLOCATION[row.allocation].label}, planning ${row.planning_capacity}`,
          segments: [{ value: row.planning_capacity, fill: 'fill-info' }],
        }))}
        max={SPAN}
        noun={['order', 'orders']}
        empty='This realm holds no economic order yet; each realm reads its order from its laws, stores and associations.'
      />
      <Listed
        title='Economic orders'
        items={data.orders}
        empty='No economic order is held here yet.'
        noun={['order', 'orders']}
        itemKey={(item) => item.id}
      >
        {(item) => <OrderCard row={item} kinds={kinds} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Scale}
        tone='gold'
        title='Set an economic order'
        note={`${realm ? realm.name : 'The realm'} holds this order for the whole realm or for one good.`}
        columns={2}
        action={
          <Button
            size='sm'
            disabled={setBusy !== null}
            disabledReason={setBusy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Good'
          value={sector}
          table={SECTORS}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSector}
        />
        {axisPickers}
        <NumberField
          label='Planning capacity'
          value={planning}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setPlanning}
        />
      </ForgeCard>
      <Listed
        title='Changes of order'
        items={data.transitions}
        empty='No change of order has been proclaimed here.'
        noun={['change', 'changes']}
        itemKey={(item) => item.id}
      >
        {(item) => <ChangeCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={CHANGES.land_reform.icon}
        tone='warning'
        title='Proclaim a change of order'
        note='Holdings move to their new hands in stages, with or without pay to those who lose them.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={changeBusy !== null}
            disabledReason={changeBusy ?? undefined}
            onClick={() => proclaiming.mutate()}
          >
            <Plus />
            Proclaim it
          </Button>
        }
      >
        <MindPicker
          label='Change'
          value={change}
          table={table(CHANGES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setChange}
        />
        <MindPicker
          label='Compensation'
          value={paid}
          table={table(COMPENSATION)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPaid}
        />
      </ForgeCard>
      <Listed
        title='Named orders'
        items={data.kinds}
        empty='No order has a name yet.'
        noun={['named order', 'named orders']}
        itemKey={(item) => item.id}
      >
        {(item) => <KindCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Scale}
        tone='info'
        title='Name an order'
        note='Any combination of the four axes may be named; realms that hold it are known by that name.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={nameBusy !== null}
            disabledReason={nameBusy ?? undefined}
            onClick={() => naming.mutate()}
          >
            <Plus />
            Name it
          </Button>
        }
      >
        <TextField
          label='Name of the order'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        {axisPickers}
      </ForgeCard>
    </div>
  )
}
