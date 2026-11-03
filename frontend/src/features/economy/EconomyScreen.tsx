import { useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  Coins,
  Gem,
  HandCoins,
  Landmark,
  Route,
  Save,
  Scale,
  Store,
  TrendingDown,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  PageHeader,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useCosmos, useWorldState } from '@/features/entity/api/queries'
import { PriceBoard } from '@/features/entity/economy/RouteAndMarket'
import {
  useCurrencies,
  useDebtsLedger,
  useMarkets,
  useTradeRoutes,
  useWorldMaterials,
} from '@/features/entity/economy/api'
import {
  FAMILY_TONE,
  MODE,
  ROUTE_STATUS,
} from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ECONOMY_TABS, type EconomyTab } from './economyTabs'

type Material = components['schemas']['MaterialView']
type Currency = components['schemas']['CurrencyView']

const ITEM = navItem('economy')
const WORKING = 'Working…'
const PROPERTIES = [
  'hardness',
  'toughness',
  'weight',
  'edge',
  'conductivity',
  'sanctity',
  'corruption',
  'rarity',
  'base_value',
  'decay',
] as const

function useBusy(pending: boolean): string | null {
  const { reason } = useGodGate()
  return reason() ?? (pending ? WORKING : null)
}

function MaterialCard({
  worldId,
  material,
}: {
  worldId: number
  material: Material
}) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(PROPERTIES.map((key) => [key, String(material[key])]))
  )
  const [name, setName] = useState(material.label)
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/material:edit', {
          body: {
            world_id: worldId,
            material:
              material.world_material_id === null ? material.kind : null,
            world_material_id: material.world_material_id,
            values: Object.fromEntries(
              Object.entries(values).map(([key, value]) => [
                key,
                Math.min(100, Math.max(0, Math.round(Number(value) || 0))),
              ])
            ),
            name: material.world_material_id !== null ? name : null,
          },
        })
      ),
  })
  const busy = useBusy(edit.isPending)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={Gem} tone={FAMILY_TONE[material.family]} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {material.label}
          </Text>
          <Muted variant='caption'>
            {material.family}
            {material.branch
              ? ` · needs ${material.branch.replace('_', ' ')} ${material.level}`
              : ''}
            {material.gate ? ` and ${material.gate.replace('_', ' ')}` : ''}
          </Muted>
        </div>
        {material.edited && <Badge variant='info'>Edited in this world</Badge>}
        {material.origin !== 'catalog' && (
          <Badge variant='warning'>{`From ${material.origin.replace('_', ' ')}`}</Badge>
        )}
      </div>
      {material.description && <Muted>{material.description}</Muted>}
      {material.deposit_id !== null && (
        <EntityLink kind='entity' id={String(material.deposit_id)}>
          Its deposit
        </EntityLink>
      )}
      {material.world_material_id !== null && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Name</Label>
          <Input
            value={name}
            aria-label={`${material.label} name`}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-5'>
        {PROPERTIES.map((key) => (
          <div key={key} className='flex min-w-0 flex-col gap-1'>
            <Label truncate>{key.replace('_', ' ')}</Label>
            <Input
              type='number'
              min={0}
              max={100}
              value={values[key]}
              aria-label={`${material.label} ${key}`}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  [key]: event.target.value,
                }))
              }
            />
          </div>
        ))}
      </div>
      <Button
        size='sm'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => edit.mutate(undefined)}
      >
        <Save />
        Set these properties
      </Button>
    </li>
  )
}

function MaterialsBrowser({ worldId }: { worldId: number }) {
  const view = useWorldMaterials(worldId)
  if (!view.data) return <Muted>Loading the materials…</Muted>
  return (
    <div
      data-surface='MaterialsBrowser'
      className='flex min-w-0 flex-col gap-4'
    >
      <Muted>
        Every value is the world's physics for that material: edge and hardness
        cut, toughness and hardness protect, weight slows armies and burns them
        in heat, conductivity holds enchantment, sanctity and corruption draw
        gods and outer beings, decay wears things away.
      </Muted>
      <ul className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'>
        {view.data.materials.map((material) => (
          <MaterialCard
            key={`${material.kind ?? ''}-${material.world_material_id ?? ''}`}
            worldId={worldId}
            material={material}
          />
        ))}
      </ul>
    </div>
  )
}

function NumberField({
  label,
  owner,
  value,
  onChange,
}: {
  label: string
  owner: string
  value: string
  onChange: (next: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <Input
        type='number'
        min={0}
        value={value}
        aria-label={`${owner} ${label}`}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function CurrencyCard({ currency }: { currency: Currency }) {
  const [purity, setPurity] = useState(String(currency.purity))
  const [trust, setTrust] = useState(String(currency.trust))
  const [supply, setSupply] = useState(String(currency.supply))
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:edit', {
          body: {
            currency_id: currency.id,
            purity: Number(purity) || 0,
            trust: Number(trust) || 0,
            supply: Number(supply) || 0,
          },
        })
      ),
  })
  const debase = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:debase', {
          body: { currency_id: currency.id },
        })
      ),
  })
  const busy = useBusy(edit.isPending || debase.isPending)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={Coins} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {currency.name}
          </Text>
          <Muted variant='caption'>
            {'Struck by '}
            <EntityLink kind='entity' id={String(currency.issuer_id)}>
              {currency.issuer_name}
            </EntityLink>
            {` in ${currency.metal.replace('_', ' ')}, epoch ${currency.minted_epoch}; used by ${currency.users.length}`}
          </Muted>
        </div>
        {currency.debased_epoch !== null && (
          <Badge variant='destructive'>{`Debased in epoch ${currency.debased_epoch}`}</Badge>
        )}
      </div>
      <StatBar
        label='Purity'
        value={currency.purity}
        max={100}
        tone={currency.purity < 50 ? 'destructive' : 'default'}
      />
      <StatBar
        label='Trust'
        value={currency.trust}
        max={100}
        tone={currency.trust < 50 ? 'destructive' : 'default'}
      />
      <Muted variant='caption'>{`${formatInteger(currency.supply)} coins abroad`}</Muted>
      <div className='grid min-w-0 grid-cols-3 gap-2'>
        <NumberField
          label='Purity'
          owner={currency.name}
          value={purity}
          onChange={setPurity}
        />
        <NumberField
          label='Trust'
          owner={currency.name}
          value={trust}
          onChange={setTrust}
        />
        <NumberField
          label='Coins'
          owner={currency.name}
          value={supply}
          onChange={setSupply}
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => edit.mutate(undefined)}
        >
          <Save />
          Set the coin
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => debase.mutate(undefined)}
        >
          <TrendingDown />
          Debase it
        </Button>
      </div>
    </li>
  )
}

function CurrencyCards() {
  const view = useCurrencies()
  if (!view.data) return <Muted>Loading the coins…</Muted>
  if (view.data.length === 0)
    return (
      <EmptyState
        icon={Coins}
        title='No one strikes coins yet'
        description='Peoples with trade knowledge and coin metal begin to mint.'
      />
    )
  return (
    <ul
      data-surface='CurrencyCards'
      className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'
    >
      {view.data.map((currency) => (
        <CurrencyCard key={currency.id} currency={currency} />
      ))}
    </ul>
  )
}

function DebtsLedger() {
  const view = useDebtsLedger()
  const forgive = useGodAction({
    run: (loan: number) =>
      unwrap(
        api.POST('/api/actions/loan:forgive', { body: { loan_id: loan } })
      ),
  })
  const writeOff = useGodAction({
    run: (bond: number) =>
      unwrap(
        api.POST('/api/actions/market:write_off', { body: { bond_id: bond } })
      ),
  })
  const busy = useBusy(forgive.isPending || writeOff.isPending)
  if (!view.data) return <Muted>Loading the ledger…</Muted>
  return (
    <div data-surface='DebtsLedger' className='flex min-w-0 flex-col gap-4'>
      <Label variant='overline'>Bank loans</Label>
      {view.data.loans.length === 0 ? (
        <Muted>No bank has lent yet.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {view.data.loans.map((loan) => (
            <li
              key={loan.id}
              className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
            >
              <Medallion
                icon={Landmark}
                tone={
                  loan.status === 'defaulted'
                    ? 'danger'
                    : loan.status === 'open'
                      ? 'warning'
                      : 'muted'
                }
                size='sm'
              />
              <Text className='min-w-0 flex-1'>
                <EntityLink kind='entity' id={String(loan.lender_id)}>
                  {loan.lender_name}
                </EntityLink>
                {' lent '}
                <EntityLink kind='entity' id={String(loan.borrower_id)}>
                  {loan.borrower_name}
                </EntityLink>
                {` ${loan.principal} at ${loan.interest_pct}%, due epoch ${loan.due_epoch}; ${loan.owed} still owed`}
              </Text>
              <Badge
                variant={
                  loan.status === 'defaulted' ? 'destructive' : 'outline'
                }
              >
                {loan.status}
              </Badge>
              {loan.status === 'open' && (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => forgive.mutate(loan.id)}
                >
                  <HandCoins />
                  Forgive
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <Label variant='overline'>Debts between peoples</Label>
      {view.data.debts.length === 0 ? (
        <Muted>No one owes anyone.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {view.data.debts.map((debt) => (
            <li
              key={debt.bond_id}
              className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
            >
              <Medallion icon={Scale} tone='warning' size='sm' />
              <Text className='min-w-0 flex-1'>
                <EntityLink kind='entity' id={String(debt.debtor_id)}>
                  {debt.debtor_name}
                </EntityLink>
                {' owes '}
                <EntityLink kind='entity' id={String(debt.creditor_id)}>
                  {debt.creditor_name}
                </EntityLink>
                {` ${debt.amount} ${debt.what}${debt.due_epoch ? `, due epoch ${debt.due_epoch}` : ''}`}
              </Text>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => writeOff.mutate(debt.bond_id)}
              >
                Write it off
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RoutesList({ worldId }: { worldId: number | null }) {
  const view = useTradeRoutes(worldId)
  if (!view.data) return <Muted>Loading the routes…</Muted>
  if (view.data.length === 0)
    return (
      <EmptyState
        icon={Route}
        title='No trade routes yet'
        description='Merchants open a way between markets once goods are dearer at one end.'
      />
    )
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      {view.data.map((route) => {
        const Mode = MODE[route.mode].icon
        return (
          <li
            key={route.route_id}
            className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
          >
            <Mode
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-muted-foreground'
            />
            <EntityLink kind='entity' id={String(route.route_id)}>
              {route.name}
            </EntityLink>
            <Badge size='sm' variant={ROUTE_STATUS[route.status].variant}>
              {ROUTE_STATUS[route.status].label}
            </Badge>
            <Muted variant='caption' className='min-w-0 flex-1'>
              {`${formatInteger(route.volume)} carried of ${formatInteger(route.capacity)}; danger ${route.danger}; tolls ${route.tolls.reduce((sum, toll) => sum + toll.rate_pct, 0)}%`}
            </Muted>
          </li>
        )
      })}
    </ul>
  )
}

function MarketsList({ worldId }: { worldId: number | null }) {
  const markets = useMarkets(worldId)
  const [chosen, setChosen] = useState<string>('')
  const table = Object.fromEntries(
    (markets.data ?? []).map((row) => [String(row.id), row.name])
  )
  const id = chosen || Object.keys(table)[0] || ''
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='max-w-sm'>
        <MindPicker
          label='Market'
          value={id}
          table={table}
          blocked={null}
          placeholder='Choose a market'
          onPick={setChosen}
        />
      </div>
      {id !== '' && <PriceBoard marketId={Number(id)} />}
    </div>
  )
}

function Overview() {
  const routes = useTradeRoutes(null).data ?? []
  const currencies = useCurrencies().data ?? []
  const ledger = useDebtsLedger().data
  const open = routes.filter((route) => route.status === 'open').length
  const blocked = routes.filter((route) => route.status === 'blockaded').length
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
      <KpiTile
        label='Open routes'
        icon={Route}
        tone='success'
        value={open}
        hint='Ways merchants travel now'
      />
      <KpiTile
        label='Blockaded'
        icon={Route}
        tone={blocked > 0 ? 'danger' : 'muted'}
        value={blocked}
        hint='Cut by armies of an enemy'
      />
      <KpiTile
        label='Coins'
        icon={Coins}
        tone='gold'
        value={currencies.length}
        hint='Currencies struck in the cosmos'
      />
      <KpiTile
        label='Open loans'
        icon={Landmark}
        tone='warning'
        value={
          ledger?.loans.filter((loan) => loan.status === 'open').length ?? 0
        }
        hint='War loans not yet repaid'
      />
    </div>
  )
}

export function EconomyScreen() {
  const search = useSearch({ from: '/_app/economy' })
  const tab: EconomyTab = search.ledger ?? 'routes'
  const navigate = useNavigate({ from: '/economy' })
  const state = useWorldState()
  const cosmos = useCosmos()
  const worlds = cosmos.data?.worlds ?? []
  const [world, setWorld] = useState<string>('')
  const worldId = world
    ? Number(world)
    : (state.data?.world?.id ?? worlds[0]?.world.id ?? null)
  const setTab = (next: string) =>
    void navigate({
      search: { ledger: ECONOMY_TABS.find((item) => item === next) },
    })
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon ?? Coins}
      />
      <Overview />
      <div className='max-w-sm'>
        <MindPicker
          label='World'
          value={worldId !== null ? String(worldId) : ''}
          table={Object.fromEntries(
            worlds.map((item) => [String(item.world.id), item.world.name])
          )}
          blocked={null}
          onPick={setWorld}
        />
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList aria-label='Economy sections'>
          <TabsTrigger value='routes'>
            <Route />
            Trade routes
          </TabsTrigger>
          <TabsTrigger value='markets'>
            <Store />
            Markets
          </TabsTrigger>
          <TabsTrigger value='materials'>
            <Gem />
            Materials
          </TabsTrigger>
          <TabsTrigger value='currencies'>
            <Coins />
            Coins
          </TabsTrigger>
          <TabsTrigger value='debts'>
            <Landmark />
            Debts and loans
          </TabsTrigger>
        </TabsList>
        <TabsContent value='routes'>
          {tab === 'routes' && <RoutesList worldId={worldId} />}
        </TabsContent>
        <TabsContent value='markets'>
          {tab === 'markets' && <MarketsList worldId={worldId} />}
        </TabsContent>
        <TabsContent value='materials'>
          {tab === 'materials' && worldId !== null && (
            <MaterialsBrowser worldId={worldId} />
          )}
        </TabsContent>
        <TabsContent value='currencies'>
          {tab === 'currencies' && <CurrencyCards />}
        </TabsContent>
        <TabsContent value='debts'>
          {tab === 'debts' && <DebtsLedger />}
        </TabsContent>
      </Tabs>
    </>
  )
}
