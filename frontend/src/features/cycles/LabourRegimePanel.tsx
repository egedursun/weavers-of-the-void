import { useState } from 'react'
import {
  Coins,
  HandCoins,
  Package,
  ScrollText,
  ShoppingBag,
  Unlock,
  UserRoundCheck,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type CyclesView, useCycleAction } from './api'
import { PATHS, REGIMES, YES_NO } from './labels'
import { clamp, MANY, SPAN, useRow, useStep } from './model'
import { StepButton } from './parts'

type Indenture = CyclesView['indentures'][number]
type Market = NonNullable<CyclesView['market']>
type Freeing = CyclesView['manumissions'][number]

function standingLabel(standing: number): string {
  return standing >= SPAN ? 'equals of the freeborn' : `standing ${standing}`
}

const NOT_COMMUNITY = 'Bonds and freedoms are kept by a town or a people'
const NOT_TOWN = 'Only a settlement holds a market'

function IndentureCard({
  row,
  blocked,
}: {
  row: Indenture
  blocked: string | null
}) {
  const action = useRow(
    'indenture:edit',
    'indenture:delete',
    { indenture_id: row.id },
    blocked
  )
  const releasing = useStep(
    'indenture:release',
    { indenture_id: row.id },
    blocked,
    'They go free'
  )
  const regime = REGIMES[row.regime]
  return (
    <Held
      icon={regime.icon}
      tone={regime.tone}
      title={`${row.count} bound in ${regime.label.toLowerCase()}`}
      caption={
        row.regime === 'indenture'
          ? `${plural(row.term_epochs, 'epoch', 'epochs')} left · since epoch ${row.since_epoch}`
          : `Until the debt is paid · since epoch ${row.since_epoch}`
      }
      removeLabel='Strike the bond'
      editTitle='Set the bond'
      note='The bound work off their debt, slower the more they are exploited; a greedy employer can make the debt unpayable. Newcomers sign contracts for their keep, and the further their ways from their hosts the harder the terms. Bondage makes the poor miserable, keeps them from leaving and readies them to rise.'
      fields={[
        {
          key: 'employer_node_id',
          label: 'Employer',
          kind: 'node',
          types: ['faction', 'settlement', 'mortal', 'house', 'polity'],
        },
        { key: 'regime', label: 'Regime', kind: 'pick', table: table(REGIMES) },
        { key: 'count', label: 'Bound', kind: 'number', min: 0 },
        { key: 'term_epochs', label: 'Epochs left', kind: 'number', min: 0 },
        { key: 'debt', label: 'Debt', kind: 'number', min: 0 },
        {
          key: 'exploitation',
          label: 'Exploitation',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'origin_entity_id',
          label: 'Newcomers of',
          kind: 'node',
          types: ['people'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Exploitation'
        value={row.exploitation}
        max={SPAN}
        tone='destructive'
        icon={HandCoins}
      />
      <Facts
        items={[
          [
            'Employer',
            <Ref key='employer' node={row.employer} empty='the town itself' />,
          ],
          ['Debt', row.debt],
          [
            'Bound by',
            row.origin ? (
              <Ref key='origin' node={row.origin} empty='debt' />
            ) : (
              'debt'
            ),
          ],
        ]}
      />
      <StepButton
        icon={Unlock}
        label='Release them'
        busy={releasing.busy}
        onClick={releasing.run}
      />
    </Held>
  )
}

function IndentureForge({
  communityId,
  isCommunity,
  blocked,
}: {
  communityId: number
  isCommunity: boolean
  blocked: string | null
}) {
  const [regime, setRegime] = useState<keyof typeof REGIMES>('indenture')
  const [count, setCount] = useState('20')
  const [debt, setDebt] = useState('100')
  const [exploitation, setExploitation] = useState('30')
  const [employer, setEmployer] = useState<number | null>(null)
  const [origin, setOrigin] = useState<number | null>(null)
  const binding = useCycleAction(
    'indenture:create',
    (_: void) => ({
      community_id: communityId,
      regime,
      count: clamp(count, MANY),
      debt: clamp(debt, MANY),
      exploitation: clamp(exploitation),
      employer_id: employer,
      origin_id: origin,
    }),
    'They are bound'
  )
  const busy = why(isCommunity ? blocked : NOT_COMMUNITY, binding.isPending)
  return (
    <ForgeCard
      icon={ScrollText}
      tone='warning'
      title='Bind labourers'
      note='For a term, or until a debt is paid; name a people to bind its newcomers by contract.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => binding.mutate()}
        >
          <ScrollText />
          Bind them
        </Button>
      }
    >
      <MindPicker
        label='Regime'
        value={regime}
        table={table(REGIMES)}
        blocked={busy}
        onPick={(value) => setRegime(value as keyof typeof REGIMES)}
      />
      <NumberField
        label='How many'
        value={count}
        min={0}
        blocked={busy}
        onChange={setCount}
      />
      <NumberField
        label='Debt'
        value={debt}
        min={0}
        blocked={busy}
        onChange={setDebt}
      />
      <NumberField
        label='Exploitation'
        value={exploitation}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setExploitation}
      />
      <NodePicker
        label='Employer'
        value={employer}
        onChange={setEmployer}
        blocked={busy}
        types={['faction', 'settlement', 'mortal', 'house', 'polity']}
      />
      <NodePicker
        label='Newcomers of'
        value={origin}
        onChange={setOrigin}
        blocked={busy}
        types={['people']}
      />
    </ForgeCard>
  )
}

function MarketCard({
  townId,
  row,
  blocked,
}: {
  townId: number
  row: Market
  blocked: string | null
}) {
  const action = useRow(
    'slave_market:edit',
    'slave_market:delete',
    { town_id: townId },
    blocked
  )
  return (
    <Held
      icon={ShoppingBag}
      tone={row.open ? 'danger' : 'muted'}
      title={row.open ? 'A market in bound folk' : 'A closed market'}
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Close the market'
      editTitle='Set the market'
      note='Prices follow skill, age, origin and looks; dear captives make raiding pay, and raids feed the market.'
      fields={[
        {
          key: 'price',
          label: 'Price of a bound adult',
          kind: 'number',
          min: 0,
        },
        { key: 'stock', label: 'Offered', kind: 'number', min: 0 },
        { key: 'sold', label: 'Sold', kind: 'number', min: 0 },
        { key: 'open', label: 'Open', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Chip icon={Coins}>{row.open ? 'Trading' : 'Closed by law'}</Chip>}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
          <KpiTile label='Price' value={row.price} icon={Coins} tone='gold' />
          <KpiTile
            label='Offered'
            value={row.stock}
            icon={Package}
            tone='warning'
          />
          <KpiTile
            label='Sold'
            value={row.sold}
            icon={HandCoins}
            tone='danger'
          />
        </div>
      </div>
    </Held>
  )
}

function MarketForge({
  townId,
  isTown,
  blocked,
}: {
  townId: number
  isTown: boolean
  blocked: string | null
}) {
  const [price, setPrice] = useState('20')
  const setting = useCycleAction(
    'slave_market:set',
    (_: void) => ({ town_id: townId, price: clamp(price, MANY), open: true }),
    'The market is set'
  )
  const busy = why(isTown ? blocked : NOT_TOWN, setting.isPending)
  return (
    <ForgeCard
      icon={ShoppingBag}
      tone='danger'
      title='Open a market in bound folk'
      note='It sells the bound adults of this town to the richest lawful buyer.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <ShoppingBag />
          Open it
        </Button>
      }
    >
      <NumberField
        label='Price'
        value={price}
        min={0}
        blocked={busy}
        onChange={setPrice}
      />
    </ForgeCard>
  )
}

function FreeingRow({
  row,
  blocked,
}: {
  row: Freeing
  blocked: string | null
}) {
  const action = useRow(
    'manumission:edit',
    'manumission:delete',
    { manumission_id: row.id },
    blocked
  )
  const path = PATHS[row.path]
  return (
    <Held
      icon={path.icon}
      tone={path.tone}
      title={`${row.count} freed, ${path.label.toLowerCase()}`}
      caption={`Epoch ${row.epoch} · ${standingLabel(row.standing)}`}
      removeLabel='Strike from the record'
      editTitle='Set the freeing'
      note='Those freed by purchase or service rise as craftsfolk. The freed start below the freeborn: their low standing sours their satisfaction and keeps them from office and the priesthood until it rises, slower where hierarchy is prized. Freed captives stay a community of their own origin in the town. Risings feed the abolition movement.'
      fields={[
        { key: 'count', label: 'Freed', kind: 'number', min: 0 },
        {
          key: 'path',
          label: 'Way to freedom',
          kind: 'pick',
          table: table(PATHS),
        },
        {
          key: 'standing',
          label: 'Standing among the free',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'origin_entity_id',
          label: 'Folk of',
          kind: 'node',
          types: ['people'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Standing among the free'
        value={row.standing}
        max={SPAN}
        tone='success'
        icon={UserRoundCheck}
      />
      <Facts
        items={[
          ['Folk of', <Ref key='origin' node={row.origin} empty='this town' />],
        ]}
      />
    </Held>
  )
}

function FreeForge({
  communityId,
  isCommunity,
  blocked,
}: {
  communityId: number
  isCommunity: boolean
  blocked: string | null
}) {
  const [share, setShare] = useState('50')
  const [path, setPath] = useState<keyof typeof PATHS>('law')
  const freeing = useCycleAction(
    'manumission:free',
    (_: void) => ({ community_id: communityId, share_pct: clamp(share), path }),
    'They go free'
  )
  const busy = why(isCommunity ? blocked : NOT_COMMUNITY, freeing.isPending)
  return (
    <ForgeCard
      icon={Unlock}
      tone='success'
      title='Free the bound'
      note='Free a share of the bound here by the way you choose.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => freeing.mutate()}
        >
          <Unlock />
          Free them
        </Button>
      }
    >
      <NumberField
        label='Share (%)'
        value={share}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setShare}
      />
      <MindPicker
        label='Way to freedom'
        value={path}
        table={table(PATHS)}
        blocked={busy}
        onPick={(value) => setPath(value as keyof typeof PATHS)}
      />
    </ForgeCard>
  )
}

export function LabourRegimePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: CyclesView
  blocked: string | null
}) {
  const isTown = kind === 'settlement'
  const isCommunity = isTown || kind === 'people'
  return (
    <div
      data-surface='LabourRegimePanel'
      className='flex min-w-0 flex-col gap-4'
    >
      <Listed
        title='Bonds of labour'
        items={data.indentures}
        empty='No one here is bound in labour.'
        noun={['bond', 'bonds']}
        itemKey={(item) => item.id}
      >
        {(item) => <IndentureCard row={item} blocked={blocked} />}
      </Listed>
      <IndentureForge
        communityId={nodeId}
        isCommunity={isCommunity}
        blocked={blocked}
      />
      {data.market ? (
        <MarketCard townId={nodeId} row={data.market} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isTown ? 'No market in bound folk stands here.' : NOT_TOWN}
        </Muted>
      )}
      <MarketForge townId={nodeId} isTown={isTown} blocked={blocked} />
      <Listed
        title='Freedoms granted'
        items={data.manumissions}
        empty='No one has been freed here yet.'
        noun={['freeing', 'freeings']}
        itemKey={(item) => item.id}
      >
        {(item) => <FreeingRow row={item} blocked={blocked} />}
      </Listed>
      <FreeForge
        communityId={nodeId}
        isCommunity={isCommunity}
        blocked={blocked}
      />
    </div>
  )
}
