import { useState } from 'react'
import {
  ArrowLeftRight,
  Factory,
  Link,
  PiggyBank,
  Plane,
  Plus,
  Shovel,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { COMMODITY } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type OrdersNodeView, useOrdersAction } from './api'
import { HOARD_STATES, SAVING_FORMS, SIGHTS } from './labels'
import { MANY, SPAN, clamp, useOrdersRow } from './model'

type View = OrdersNodeView
const YES_NO = { true: 'Yes', false: 'No' }
const PLACE_TYPES = ['settlement', 'region', 'place', 'structure'] as const
const HOLDER_TYPES = [
  'mortal',
  'faction',
  'settlement',
  'polity',
  'people',
] as const
const MERCHANT_TYPES = ['faction'] as const
const TOWN_TYPES = ['settlement'] as const
const SIGHT_TYPES = ['structure', 'settlement', 'place', 'region'] as const
const GOODS = table(COMMODITY)

function SavingCard({
  row,
  blocked,
}: {
  row: View['savings'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'saving:edit',
    'saving:delete',
    { household_id: row.household_id },
    blocked
  )
  const form = SAVING_FORMS[row.form]
  return (
    <Held
      icon={form.icon}
      tone={form.tone}
      title={row.household}
      caption={`Saves ${row.share_pct}% as ${form.label.toLowerCase()}; ${row.saved} put by; epoch ${row.updated_epoch}`}
      removeLabel='Strike the saving'
      editTitle='Set the saving'
      note='Patient heads save more; insecure towns bury what they save, towns with a bank bank it, and the rest invest it.'
      fields={[
        {
          key: 'share_pct',
          label: 'Share saved',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'form',
          label: 'Kept as',
          kind: 'pick',
          table: table(SAVING_FORMS),
        },
        { key: 'saved', label: 'Put by', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Share saved (${row.share_pct} of ${SPAN})`}
        value={row.share_pct}
        tone='success'
        icon={form.icon}
      />
    </Held>
  )
}

function HoardCard({
  row,
  blocked,
}: {
  row: View['hoards'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'hoard:edit',
    'hoard:delete',
    { record_id: row.id },
    blocked
  )
  const state = HOARD_STATES[row.state]
  return (
    <Held
      icon={state.icon}
      tone={state.tone}
      title={`${row.amount} coin, ${state.label.toLowerCase()}`}
      caption={
        <>
          In <Ref node={row.place} />, buried by{' '}
          <Ref node={row.holder} empty='no one known' /> in epoch{' '}
          {row.hidden_epoch}
          {row.found_by ? (
            <>
              ; found by <Ref node={row.found_by} /> in epoch {row.found_epoch}
            </>
          ) : null}
        </>
      }
      removeLabel='Strike the hoard'
      editTitle='Set the hoard'
      note='A hoard is lost when the one who buried it dies, and found later by those who dig there.'
      fields={[
        {
          key: 'holder_node_id',
          label: 'Buried by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'place_entity_id',
          label: 'Buried in',
          kind: 'node',
          types: PLACE_TYPES,
        },
        { key: 'amount', label: 'Coin', kind: 'number', min: 0, max: MANY },
        {
          key: 'state',
          label: 'State',
          kind: 'pick',
          table: table(HOARD_STATES),
        },
        {
          key: 'found_by_node_id',
          label: 'Found by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'hidden_epoch',
          label: 'Buried in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'found_epoch',
          label: 'Found in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function SavingPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const households = Object.fromEntries(
    data.households.map((row) => [String(row.id), row.name])
  )
  const [household, setHousehold] = useState(
    data.households[0] ? String(data.households[0].id) : ''
  )
  const [share, setShare] = useState('10')
  const [form, setForm] = useState('hoard')
  const [place, setPlace] = useState<number | null>(data.node.id)
  const [amount, setAmount] = useState('20')
  const saving = useOrdersAction(
    'saving:set',
    (_: void) => ({
      household_id: Number(household),
      share_pct: clamp(share, SPAN),
      form: form as View['savings'][number]['form'],
      saved: 0,
    }),
    'The household saves so'
  )
  const burying = useOrdersAction(
    'hoard:create',
    (_: void) => ({
      place_id: place ?? 0,
      amount: clamp(amount, MANY),
      state: 'hidden' as const,
    }),
    'The hoard is buried'
  )
  const saveBusy = why(
    blocked ?? (household === '' ? 'No household lives here to save' : null),
    saving.isPending
  )
  const buryBusy = why(
    blocked ?? (place === null ? 'Choose where it is buried first' : null),
    burying.isPending
  )
  return (
    <div data-surface='SavingPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-savings'
        title='What each household has put by'
        legend={[{ text: 'Put by', variant: 'success' }]}
        rows={data.savings.map((row) => ({
          key: String(row.household_id),
          caption: `${row.household}: ${row.saved} as ${SAVING_FORMS[row.form].label.toLowerCase()}`,
          segments: [{ value: row.saved, fill: 'fill-success' }],
        }))}
        max={Math.max(1, ...data.savings.map((row) => row.saved))}
        noun={['household', 'households']}
        empty='No household here saves yet; households begin to save from what they earn beyond their costs.'
      />
      <Listed
        title='Savings'
        items={data.savings}
        empty='No household here saves yet.'
        noun={['household', 'households']}
        itemKey={(item) => item.household_id}
      >
        {(item) => <SavingCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={PiggyBank}
        tone='success'
        title='Set how a household saves'
        note='The household puts this share of its surplus by in the form chosen.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={saveBusy !== null}
            disabledReason={saveBusy ?? undefined}
            onClick={() => saving.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Household'
          value={household}
          table={households}
          placeholder='Choose'
          blocked={blocked}
          onPick={setHousehold}
        />
        <NumberField
          label='Share saved'
          value={share}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setShare}
        />
        <MindPicker
          label='Kept as'
          value={form}
          table={table(SAVING_FORMS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setForm}
        />
      </ForgeCard>
      <Listed
        title='Hoards'
        items={data.hoards}
        empty='No hoard is known here.'
        noun={['hoard', 'hoards']}
        itemKey={(item) => item.id}
      >
        {(item) => <HoardCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Shovel}
        tone='warning'
        title='Bury a hoard'
        note='A hidden hoard waits for its owner, or for diggers once its owner is gone.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={buryBusy !== null}
            disabledReason={buryBusy ?? undefined}
            onClick={() => burying.mutate()}
          >
            <Plus />
            Bury it
          </Button>
        }
      >
        <NodePicker
          label='Buried in'
          value={place}
          onChange={setPlace}
          blocked={blocked}
          types={PLACE_TYPES}
        />
        <NumberField
          label='Coin'
          value={amount}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setAmount}
        />
      </ForgeCard>
    </div>
  )
}

function RateCard({
  row,
  blocked,
}: {
  row: View['rates'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'exchange_rate:edit',
    'exchange_rate:delete',
    { record_id: row.id },
    blocked
  )
  return (
    <Held
      icon={ArrowLeftRight}
      tone={row.convertible ? 'gold' : 'danger'}
      title={`${row.base.name} to ${row.quote.name}: ${row.rate}`}
      caption={
        <>
          At <Ref node={row.market} empty='no market' />, spread{' '}
          {row.spread_pct}%, changed by{' '}
          <Ref node={row.changer} empty='no changer' />; {row.volume} exchanged
          this epoch{row.convertible ? '' : '; not convertible'}; epoch{' '}
          {row.updated_epoch}
        </>
      }
      removeLabel='Strike the rate'
      editTitle='Set the rate'
      note='A rate follows the purity, trust, supply and trade balance of each coin; a sharp rise swells debts in foreign coin.'
      fields={[
        { key: 'rate', label: 'Rate', kind: 'number', min: 1, max: MANY },
        {
          key: 'spread_pct',
          label: 'Spread',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'changer_node_id',
          label: 'Changer',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'convertible',
          label: 'Convertible',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'volume',
          label: 'Exchanged this epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function BillCard({
  row,
  blocked,
}: {
  row: View['bills'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'bill_of_exchange:edit',
    'bill_of_exchange:delete',
    { record_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Link}
      tone={row.settled ? 'success' : 'info'}
      title={`${row.amount} coin, ${row.settled ? 'settled' : 'open'}`}
      caption={
        <>
          Drawn by <Ref node={row.drawer} /> for <Ref node={row.payee} />, from{' '}
          <Ref node={row.from_market} /> to <Ref node={row.to_market} /> in
          epoch {row.issued_epoch}
        </>
      }
      removeLabel='Tear it up'
      editTitle='Set the bill'
      note='A bill lets a merchant pay across distance without carrying coin, sparing the road its losses.'
      fields={[
        {
          key: 'drawer_node_id',
          label: 'Drawn by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'payee_node_id',
          label: 'Paid to',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'from_entity_id',
          label: 'From',
          kind: 'node',
          types: TOWN_TYPES,
        },
        { key: 'to_entity_id', label: 'To', kind: 'node', types: TOWN_TYPES },
        { key: 'amount', label: 'Coin', kind: 'number', min: 0, max: MANY },
        { key: 'settled', label: 'Settled', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function ExchangePanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const coins = Object.fromEntries(
    data.coins.map((row) => [String(row.id), row.name])
  )
  const first = data.coins[0] ? String(data.coins[0].id) : ''
  const second = data.coins[1] ? String(data.coins[1].id) : first
  const [base, setBase] = useState(first)
  const [quote, setQuote] = useState(second)
  const [rate, setRate] = useState('100')
  const [spread, setSpread] = useState('4')
  const [drawer, setDrawer] = useState<number | null>(null)
  const [payee, setPayee] = useState<number | null>(null)
  const [from, setFrom] = useState<number | null>(null)
  const [to, setTo] = useState<number | null>(null)
  const [amount, setAmount] = useState('20')
  const setting = useOrdersAction(
    'exchange_rate:create',
    (_: void) => ({
      base_currency_id: Number(base),
      quote_currency_id: Number(quote),
      market_id: data.node.id,
      rate: Math.max(1, clamp(rate, MANY)),
      spread_pct: clamp(spread, SPAN),
      convertible: true,
    }),
    'The rate is set'
  )
  const drawing = useOrdersAction(
    'bill_of_exchange:create',
    (_: void) => ({
      drawer_id: drawer ?? 0,
      payee_id: payee ?? 0,
      from_id: from ?? 0,
      to_id: to ?? 0,
      amount: clamp(amount, MANY),
    }),
    'The bill is drawn'
  )
  const rateBusy = why(
    blocked ??
      (base === '' || base === quote
        ? 'Choose two different coins first'
        : null),
    setting.isPending
  )
  const billBusy = why(
    blocked ??
      ([drawer, payee, from, to].includes(null)
        ? 'Choose who draws it, who is paid and both markets first'
        : null),
    drawing.isPending
  )
  return (
    <div data-surface='ExchangePanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          [
            'Coins known here',
            data.coins.map((row) => row.name).join(', ') || 'None',
          ],
        ]}
      />
      <Bars
        chart='chart-rates'
        title='The spread asked on each exchange'
        legend={[{ text: 'Spread', variant: 'warning' }]}
        rows={data.rates.map((row) => ({
          key: String(row.id),
          caption: `${row.base.name} to ${row.quote.name}: rate ${row.rate}, spread ${row.spread_pct}%`,
          segments: [{ value: row.spread_pct, fill: 'fill-warning' }],
        }))}
        max={SPAN}
        noun={['rate', 'rates']}
        empty='No two coins meet at this market yet.'
      />
      <Listed
        title='Rates'
        items={data.rates}
        empty='No two coins meet at this market yet.'
        noun={['rate', 'rates']}
        itemKey={(item) => item.id}
      >
        {(item) => <RateCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={ArrowLeftRight}
        tone='gold'
        title='Set a rate between two coins'
        note='The rate holds at this market until the coins move it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={rateBusy !== null}
            disabledReason={rateBusy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Coin'
          value={base}
          table={coins}
          placeholder='Choose'
          blocked={blocked}
          onPick={setBase}
        />
        <MindPicker
          label='Against'
          value={quote}
          table={coins}
          placeholder='Choose'
          blocked={blocked}
          onPick={setQuote}
        />
        <NumberField
          label='Rate'
          value={rate}
          min={1}
          max={MANY}
          disabled={blocked !== null}
          onChange={setRate}
        />
        <NumberField
          label='Spread'
          value={spread}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setSpread}
        />
      </ForgeCard>
      <Listed
        title='Bills of exchange'
        items={data.bills}
        empty='No bill of exchange touches this.'
        noun={['bill', 'bills']}
        itemKey={(item) => item.id}
      >
        {(item) => <BillCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Link}
        tone='info'
        title='Draw a bill of exchange'
        note='The drawer pays the payee next epoch, and no coin travels the road between them.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={billBusy !== null}
            disabledReason={billBusy ?? undefined}
            onClick={() => drawing.mutate()}
          >
            <Plus />
            Draw it
          </Button>
        }
      >
        <NodePicker
          label='Drawn by'
          value={drawer}
          onChange={setDrawer}
          blocked={blocked}
          types={HOLDER_TYPES}
        />
        <NodePicker
          label='Paid to'
          value={payee}
          onChange={setPayee}
          blocked={blocked}
          types={HOLDER_TYPES}
        />
        <NodePicker
          label='From market'
          value={from}
          onChange={setFrom}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='To market'
          value={to}
          onChange={setTo}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NumberField
          label='Coin'
          value={amount}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setAmount}
        />
      </ForgeCard>
    </div>
  )
}

function PutOutCard({
  row,
  blocked,
}: {
  row: View['putting_out'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'putting_out:edit',
    'putting_out:delete',
    { record_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Factory}
      tone={row.active ? 'success' : 'muted'}
      title={`${COMMODITY[row.raw].label} into ${COMMODITY[row.product].label.toLowerCase()}`}
      caption={
        <>
          <Ref node={row.merchant} /> puts {row.volume} out to{' '}
          <Ref node={row.village} />
          {row.active ? '' : ', now idle'} since epoch {row.since_epoch}
        </>
      }
      removeLabel='End it'
      editTitle='Set the work put out'
      note='Village households make goods at home from the merchant’s raw goods; the merchant keeps a margin and the village prospers.'
      fields={[
        {
          key: 'town_entity_id',
          label: 'Village',
          kind: 'node',
          types: TOWN_TYPES,
        },
        { key: 'raw', label: 'Raw goods', kind: 'pick', table: GOODS },
        { key: 'product', label: 'Made into', kind: 'pick', table: GOODS },
        {
          key: 'volume',
          label: 'Handed out each epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'active', label: 'Working', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function ChainCard({
  row,
  blocked,
}: {
  row: View['chains'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'chain_holding:edit',
    'chain_holding:delete',
    { holder_id: row.holder.id, town_id: row.town.id, product: row.product },
    blocked
  )
  return (
    <Held
      icon={Link}
      tone='gold'
      title={`${row.share_pct}% of the ${COMMODITY[row.product].label.toLowerCase()} of ${row.town.name}`}
      caption={
        <>
          Held by <Ref node={row.holder} /> since epoch {row.since_epoch}
        </>
      }
      removeLabel='Sell the share'
      editTitle='Set the share'
      note='The holder draws this share of the good’s output home each epoch.'
      fields={[
        { key: 'share_pct', label: 'Share', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Share (${row.share_pct} of ${SPAN})`}
        value={row.share_pct}
        tone='warning'
        icon={Link}
      />
    </Held>
  )
}

export function TradePanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const [merchant, setMerchant] = useState<number | null>(null)
  const [village, setVillage] = useState<number | null>(null)
  const [raw, setRaw] = useState('wool')
  const [product, setProduct] = useState('cloth')
  const [volume, setVolume] = useState('10')
  const [holder, setHolder] = useState<number | null>(null)
  const [town, setTown] = useState<number | null>(null)
  const [good, setGood] = useState('cloth')
  const [share, setShare] = useState('20')
  type Good = View['chains'][number]['product']
  const putting = useOrdersAction(
    'putting_out:create',
    (_: void) => ({
      merchant_id: merchant ?? 0,
      town_id: village ?? 0,
      raw: raw as Good,
      product: product as Good,
      volume: clamp(volume, MANY),
    }),
    'The work is put out'
  )
  const buying = useOrdersAction(
    'chain_holding:set',
    (_: void) => ({
      holder_id: holder ?? 0,
      town_id: town ?? 0,
      product: good as Good,
      share_pct: clamp(share, SPAN),
    }),
    'The share is held'
  )
  const putBusy = why(
    blocked ??
      (merchant === null || village === null
        ? 'Choose the merchant body and the village first'
        : null),
    putting.isPending
  )
  const buyBusy = why(
    blocked ??
      (holder === null || town === null
        ? 'Choose who holds it and where first'
        : null),
    buying.isPending
  )
  return (
    <div data-surface='TradePanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-putting-out'
        title='What each arrangement hands out'
        legend={[{ text: 'Raw goods each epoch', variant: 'success' }]}
        rows={data.putting_out.map((row) => ({
          key: String(row.id),
          caption: `${row.merchant.name} to ${row.village.name}: ${row.volume}`,
          segments: [
            {
              value: row.volume,
              fill: row.active ? 'fill-success' : 'fill-muted',
            },
          ],
        }))}
        max={Math.max(1, ...data.putting_out.map((row) => row.volume))}
        noun={['arrangement', 'arrangements']}
        empty='No work is put out here; merchant bodies put wool and fibre out to villages.'
      />
      <Listed
        title='Work put out'
        items={data.putting_out}
        empty='No work is put out here.'
        noun={['arrangement', 'arrangements']}
        itemKey={(item) => item.id}
      >
        {(item) => <PutOutCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Factory}
        tone='success'
        title='Put work out to a village'
        note='The merchant body hands raw goods to the village each epoch and takes the made goods home.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={putBusy !== null}
            disabledReason={putBusy ?? undefined}
            onClick={() => putting.mutate()}
          >
            <Plus />
            Put it out
          </Button>
        }
      >
        <NodePicker
          label='Merchant body'
          value={merchant}
          onChange={setMerchant}
          blocked={blocked}
          types={MERCHANT_TYPES}
        />
        <NodePicker
          label='Village'
          value={village}
          onChange={setVillage}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='Raw goods'
          value={raw}
          table={GOODS}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRaw}
        />
        <MindPicker
          label='Made into'
          value={product}
          table={GOODS}
          placeholder='Choose'
          blocked={blocked}
          onPick={setProduct}
        />
        <NumberField
          label='Each epoch'
          value={volume}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setVolume}
        />
      </ForgeCard>
      <Listed
        title='Shares in chains'
        items={data.chains}
        empty='No one holds a share of the making here.'
        noun={['share', 'shares']}
        itemKey={(item) => `${item.holder.id}-${item.town.id}-${item.product}`}
      >
        {(item) => <ChainCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Link}
        tone='gold'
        title='Hold a share in a chain'
        note='The holder draws its share of a town’s output of the good home.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={buyBusy !== null}
            disabledReason={buyBusy ?? undefined}
            onClick={() => buying.mutate()}
          >
            <Plus />
            Hold it
          </Button>
        }
      >
        <NodePicker
          label='Holder'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
          types={MERCHANT_TYPES}
        />
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='Good'
          value={good}
          table={GOODS}
          placeholder='Choose'
          blocked={blocked}
          onPick={setGood}
        />
        <NumberField
          label='Share'
          value={share}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setShare}
        />
      </ForgeCard>
    </div>
  )
}

function FlowCard({
  row,
  blocked,
}: {
  row: View['flows'][number]
  blocked: string | null
}) {
  const action = useOrdersRow(
    'tourist_flow:edit',
    'tourist_flow:delete',
    { record_id: row.id },
    blocked
  )
  const sight = SIGHTS[row.sight]
  return (
    <Held
      icon={sight.icon}
      tone={sight.tone}
      title={
        <>
          {row.visitors} from <Ref node={row.origin} /> to{' '}
          <Ref node={row.sight_node} />
        </>
      }
      caption={`${sight.label}; ${row.income} coin spent; epoch ${row.epoch}`}
      removeLabel='Strike the flow'
      editTitle='Set the flow'
      note='Travellers spend in the sight’s town, spread its fame and carry home its ways and its sickness.'
      fields={[
        { key: 'sight', label: 'Sight', kind: 'pick', table: table(SIGHTS) },
        {
          key: 'visitors',
          label: 'Travellers',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'income',
          label: 'Coin spent',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function TravelPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const [origin, setOrigin] = useState<number | null>(null)
  const [sightNode, setSightNode] = useState<number | null>(data.node.id)
  const [sight, setSight] = useState('wonder')
  const [visitors, setVisitors] = useState('20')
  const [income, setIncome] = useState('40')
  const sending = useOrdersAction(
    'tourist_flow:create',
    (_: void) => ({
      origin_id: origin ?? 0,
      sight_id: sightNode ?? 0,
      sight: sight as View['flows'][number]['sight'],
      visitors: clamp(visitors, MANY),
      income: clamp(income, MANY),
    }),
    'The travellers set out'
  )
  const busy = why(
    blocked ??
      (origin === null || sightNode === null
        ? 'Choose where they come from and what they see first'
        : null),
    sending.isPending
  )
  return (
    <div data-surface='TravelPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-tourism'
        title='Travellers in each flow'
        legend={[{ text: 'Travellers', variant: 'secondary' }]}
        rows={data.flows.map((row) => ({
          key: String(row.id),
          caption: `${row.origin.name} to ${row.sight_node.name}: ${row.visitors}`,
          segments: [{ value: row.visitors, fill: 'fill-info' }],
        }))}
        max={Math.max(1, ...data.flows.map((row) => row.visitors))}
        noun={['flow', 'flows']}
        empty='No travellers come or go here; wealthy towns send them to the most famous sights of their world.'
      />
      <Listed
        title='Travellers'
        items={data.flows}
        empty='No travellers come or go here.'
        noun={['flow', 'flows']}
        itemKey={(item) => item.id}
      >
        {(item) => <FlowCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Plane}
        tone='info'
        title='Send travellers to a sight'
        note='They spend their coin in the sight’s town this epoch.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => sending.mutate()}
          >
            <Plus />
            Send them
          </Button>
        }
      >
        <NodePicker
          label='From'
          value={origin}
          onChange={setOrigin}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='To see'
          value={sightNode}
          onChange={setSightNode}
          blocked={blocked}
          types={SIGHT_TYPES}
        />
        <MindPicker
          label='Sight'
          value={sight}
          table={table(SIGHTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSight}
        />
        <NumberField
          label='Travellers'
          value={visitors}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setVisitors}
        />
        <NumberField
          label='Coin spent'
          value={income}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setIncome}
        />
      </ForgeCard>
    </div>
  )
}
