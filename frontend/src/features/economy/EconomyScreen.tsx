import { useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  ArrowRight,
  CalendarClock,
  CalendarRange,
  Coins,
  Flag,
  Gem,
  Globe,
  HandCoins,
  Landmark,
  Percent,
  Route,
  Save,
  Scale,
  Store,
  Swords,
  TrendingDown,
  Users,
  Mountain,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  AttributeTile,
  EmptyState,
  EntityLink,
  IconStat,
  KpiTile,
  Medallion,
  MiniStat,
  PageHeader,
  PagedList,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useCosmos, useWorldState } from '@/features/entity/api/queries'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from '@/features/entity/economy/EntityEconomy'
import { PriceBoard } from '@/features/entity/economy/RouteAndMarket'
import { FoundRouteDialog } from '@/features/entity/economy/RouteControls'
import {
  useCurrencies,
  useDebtsLedger,
  useMarkets,
  useTradeRoutes,
  useWorldMaterials,
} from '@/features/entity/economy/api'
import {
  LOAN_STATUS,
  MATERIAL_FAMILY,
  MATERIAL_LABEL,
  MATERIAL_ORIGIN,
  MATERIAL_PROPERTIES,
  MODE,
  ROUTE_STATUS,
  ROUTE_STATUSES,
  type MaterialFamily,
  type TradeRouteStatus,
  branch,
} from '@/features/entity/economy/labels'
import {
  DANGERS,
  DANGER_KEYS,
  seasonTone,
} from '@/features/entity/economy/routeLabels'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ECONOMY_TABS, type EconomyTab, economyWorldId } from './economyTabs'

type Material = components['schemas']['MaterialView']
type Currency = components['schemas']['CurrencyView']
type TradeRoute = components['schemas']['TradeRouteView']
type Loan = components['schemas']['LoanView']
type Debt = components['schemas']['DebtView']

const ITEM = navItem('economy')
const WORKING = 'Working…'
const PERCENT = 100
const HALF = 50
const ALL = 'all'
const PAGE = 12
const LOW = 50
const MATERIAL_FAMILIES = Object.keys(MATERIAL_FAMILY) as MaterialFamily[]
const PURPOSE: Record<string, string> = {
  war: 'to wage war',
  trade: 'for trade',
  famine: 'against famine',
  building: 'to build',
  ransom: 'to pay a ransom',
  tribute: 'to pay tribute',
}

function useBusy(pending: boolean): string | null {
  const { reason } = useGodGate()
  return reason() ?? (pending ? WORKING : null)
}

function plainWords(value: string): string {
  return value.replaceAll('_', ' ')
}

function MaterialCard({
  worldId,
  material,
}: {
  worldId: number
  material: Material
}) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(
      MATERIAL_PROPERTIES.map(({ key }) => [key, String(material[key])])
    )
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
                Math.min(PERCENT, Math.max(0, Math.round(Number(value) || 0))),
              ])
            ),
            name: material.world_material_id !== null ? name : null,
          },
        })
      ),
  })
  const busy = useBusy(edit.isPending)
  const family = MATERIAL_FAMILY[material.family]
  const origin = MATERIAL_ORIGIN[material.origin]
  const needs = material.branch ? branch(material.branch) : null
  const gate = material.gate ? branch(material.gate) : null
  return (
    <li
      data-material={material.kind ?? material.world_material_id ?? undefined}
      className='@container/card flex h-full min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={family.icon} tone={family.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Text weight='semibold' truncate>
            {material.label}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='outline'>
              <family.icon />
              {family.label}
            </Badge>
            {material.origin !== 'catalog' && (
              <Badge size='sm' variant='warning'>
                <origin.icon />
                {origin.label}
              </Badge>
            )}
            {needs && (
              <Badge size='sm' variant='info'>
                <needs.icon />
                {`Needs ${needs.label.toLowerCase()} ${material.level}`}
              </Badge>
            )}
            {gate && (
              <Badge size='sm' variant='info'>
                <gate.icon />
                {`and ${gate.label.toLowerCase()}`}
              </Badge>
            )}
            {material.edited && (
              <Badge size='sm' variant='default'>
                <Save />
                Edited in this world
              </Badge>
            )}
          </div>
        </div>
      </div>
      {material.description && (
        <Muted variant='caption' truncate={2}>
          {material.description}
        </Muted>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-1.5 @md/card:grid-cols-3 @2xl/card:grid-cols-5'>
        {MATERIAL_PROPERTIES.map((property) => (
          <AttributeTile
            key={property.key}
            icon={property.icon}
            abbr={property.abbr}
            label={property.label}
            value={material[property.key]}
            max={PERCENT}
            hint={property.hint}
            tone={
              property.key === 'corruption' || property.key === 'decay'
                ? 'destructive'
                : property.key === 'sanctity'
                  ? 'verdigris'
                  : 'default'
            }
          />
        ))}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        {material.deposit_id !== null && (
          <EntityLink kind='entity' id={String(material.deposit_id)}>
            Its deposit
          </EntityLink>
        )}
        <AdjustPanel
          label='Adjust the material'
          title={`The physics of ${material.label.toLowerCase()}`}
          note='Every value runs from 0 to 100 and is this world’s law for the material.'
        >
          {material.world_material_id !== null && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label as='label'>Name</Label>
              <Input
                value={name}
                aria-label={`${material.label} name`}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
          )}
          <div
            className={cn(
              FIELD_GRID,
              'grid-cols-2 @md/card:grid-cols-3 @2xl/card:grid-cols-5'
            )}
          >
            {MATERIAL_PROPERTIES.map((property) => (
              <NumberField
                key={property.key}
                label={property.label}
                aria={`${material.label} ${property.key}`}
                value={values[property.key]}
                max={PERCENT}
                onChange={(next) =>
                  setValues((current) => ({
                    ...current,
                    [property.key]: next,
                  }))
                }
              />
            ))}
          </div>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Set these properties
          </Button>
        </AdjustPanel>
      </div>
    </li>
  )
}

function MaterialsBrowser({ worldId }: { worldId: number }) {
  const view = useWorldMaterials(worldId)
  const [family, setFamily] = useState<string>(ALL)
  if (!view.data) return <Muted>Loading the materials…</Muted>
  const materials = view.data.materials
  const shown =
    family === ALL
      ? materials
      : materials.filter((item) => item.family === family)
  return (
    <div
      data-surface='MaterialsBrowser'
      className='flex min-w-0 flex-col gap-4'
    >
      <PartHeader
        icon={Gem}
        title='Materials of this world'
        note='Edge and hardness cut, toughness and hardness protect, weight slows armies and burns them in heat, conductivity holds enchantment, sanctity and corruption draw gods and outer beings, decay wears things away.'
      />
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={family}
        onValueChange={(next) => setFamily(next || ALL)}
        aria-label='Material family'
      >
        <ToggleGroupItem value={ALL}>
          <Gem />
          {`All ${materials.length}`}
        </ToggleGroupItem>
        {MATERIAL_FAMILIES.map((key) => {
          const spec = MATERIAL_FAMILY[key]
          const count = materials.filter((item) => item.family === key).length
          return (
            <ToggleGroupItem key={key} value={key} disabled={count === 0}>
              <spec.icon />
              {`${spec.label} ${count}`}
            </ToggleGroupItem>
          )
        })}
      </ToggleGroup>
      <PagedList
        items={shown}
        initial={PAGE}
        step={PAGE}
        noun={['material', 'materials']}
        className='grid min-w-0 grid-cols-1 gap-3 @4xl/eco:grid-cols-2'
        itemKey={(material) =>
          `${material.kind ?? ''}-${material.world_material_id ?? ''}`
        }
      >
        {(material) => <MaterialCard worldId={worldId} material={material} />}
      </PagedList>
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
  const debased = currency.debased_epoch !== null
  return (
    <li className='@container/coin flex h-full min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Coins} tone={debased ? 'danger' : 'gold'} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold' truncate>
            {currency.name}
          </Text>
          <Muted variant='caption'>
            {'Struck by '}
            <EntityLink kind='entity' id={String(currency.issuer_id)}>
              {currency.issuer_name}
            </EntityLink>
            {` in ${(MATERIAL_LABEL[currency.metal] ?? plainWords(currency.metal)).toLowerCase()}, epoch ${currency.minted_epoch}`}
          </Muted>
        </div>
        {debased ? (
          <Badge variant='destructive'>
            <TrendingDown />
            {`Debased in epoch ${currency.debased_epoch}`}
          </Badge>
        ) : (
          <Badge variant='success'>
            <Coins />
            Sound
          </Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/coin:grid-cols-4'>
        <AttributeTile
          icon={Gem}
          abbr='Purity'
          label='Purity of the metal'
          value={currency.purity}
          max={PERCENT}
          tone={currency.purity < LOW ? 'destructive' : 'default'}
          hint='Debasing thins the metal'
        />
        <AttributeTile
          icon={Scale}
          abbr='Trust'
          label='Trust of those who use it'
          value={currency.trust}
          max={PERCENT}
          tone={currency.trust < LOW ? 'destructive' : 'success'}
          hint='Low trust drives people back to barter'
        />
        <MiniStat
          icon={HandCoins}
          tone='gold'
          label='Coins abroad'
          value={formatInteger(currency.supply)}
        />
        <MiniStat
          icon={Users}
          tone='info'
          label='Peoples using it'
          value={currency.users.length}
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <AdjustPanel
          label='Adjust the coin'
          title={`Strike ${currency.name} anew`}
          note='Set its purity and trust from 0 to 100 and how many coins are abroad, or debase it at a stroke.'
        >
          <div className={cn(FIELD_GRID, 'grid-cols-3')}>
            <NumberField
              label='Purity'
              aria={`${currency.name} Purity`}
              value={purity}
              max={PERCENT}
              onChange={setPurity}
            />
            <NumberField
              label='Trust'
              aria={`${currency.name} Trust`}
              value={trust}
              max={PERCENT}
              onChange={setTrust}
            />
            <NumberField
              label='Coins'
              aria={`${currency.name} Coins`}
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
        </AdjustPanel>
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
      className='grid min-w-0 grid-cols-1 gap-3 @3xl/eco:grid-cols-2'
    >
      {view.data.map((currency) => (
        <CurrencyCard key={currency.id} currency={currency} />
      ))}
    </ul>
  )
}

function Parties({
  from,
  to,
}: {
  from: { id: number; name: string }
  to: { id: number; name: string }
}) {
  return (
    <Text
      weight='medium'
      className='flex min-w-0 flex-wrap items-center gap-x-1.5'
    >
      <EntityLink kind='entity' id={String(from.id)}>
        {from.name}
      </EntityLink>
      <ArrowRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <EntityLink kind='entity' id={String(to.id)}>
        {to.name}
      </EntityLink>
    </Text>
  )
}

function LoanCard({
  loan,
  busy,
  onForgive,
}: {
  loan: Loan
  busy: string | null
  onForgive: () => void
}) {
  const status = LOAN_STATUS[loan.status]
  const total = loan.repaid + loan.owed
  return (
    <li className='flex h-full min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Landmark} tone={status.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Parties
            from={{ id: loan.lender_id, name: loan.lender_name }}
            to={{ id: loan.borrower_id, name: loan.borrower_name }}
          />
          <Muted variant='caption'>
            {`Lent ${PURPOSE[loan.purpose] ?? plainWords(loan.purpose)} in epoch ${loan.issued_epoch}`}
          </Muted>
        </div>
        <Badge variant={status.variant}>
          <status.icon />
          {status.label}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <IconStat
          icon={Coins}
          label='Lent'
          value={`${formatInteger(loan.principal)} lent`}
          tone='gold'
        />
        <IconStat
          icon={Percent}
          label='Interest'
          value={`${loan.interest_pct}% interest`}
          tone='warning'
        />
        <IconStat
          icon={HandCoins}
          label='Still owed'
          value={`${formatInteger(loan.owed)} owed`}
          tone={loan.owed > 0 ? 'danger' : 'success'}
        />
        <IconStat
          icon={CalendarClock}
          label='Due in epoch'
          value={`Due ${loan.due_epoch}`}
          tone='muted'
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label>Repaid</Label>
          <Stat value={loan.repaid} unit={`/ ${formatInteger(total)}`} />
        </div>
        <Progress
          size='sm'
          tone='success'
          value={total > 0 ? (loan.repaid / total) * PERCENT : 0}
          aria-label='Repaid'
        />
      </div>
      {loan.status === 'open' && (
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={onForgive}
        >
          <HandCoins />
          Forgive
        </Button>
      )}
    </li>
  )
}

function DebtCard({
  debt,
  busy,
  onWriteOff,
}: {
  debt: Debt
  busy: string | null
  onWriteOff: () => void
}) {
  return (
    <li className='flex h-full min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={Scale} tone='warning' size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Parties
          from={{ id: debt.debtor_id, name: debt.debtor_name }}
          to={{ id: debt.creditor_id, name: debt.creditor_name }}
        />
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <IconStat
            icon={HandCoins}
            label={`Owed in ${plainWords(debt.what)}`}
            value={`${formatInteger(debt.amount)} ${plainWords(debt.what)}`}
            tone='warning'
          />
          {debt.due_epoch !== null && (
            <IconStat
              icon={CalendarClock}
              label='Due in epoch'
              value={`Due ${debt.due_epoch}`}
              tone='muted'
            />
          )}
        </div>
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={onWriteOff}
      >
        Write it off
      </Button>
    </li>
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
  const { loans, debts } = view.data
  return (
    <div data-surface='DebtsLedger' className='flex min-w-0 flex-col gap-6'>
      <div className='flex min-w-0 flex-col gap-3'>
        <PartHeader
          icon={Landmark}
          title='Bank loans'
          note={`${loans.filter((loan) => loan.status === 'open').length} still owed of ${loans.length} lent`}
        />
        {loans.length === 0 ? (
          <EmptyState
            icon={Landmark}
            title='No bank has lent yet'
            description='Banks lend once a people knows trade and strikes coin.'
          />
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-3 @2xl/eco:grid-cols-2'>
            {loans.map((loan) => (
              <LoanCard
                key={loan.id}
                loan={loan}
                busy={busy}
                onForgive={() => forgive.mutate(loan.id)}
              />
            ))}
          </ul>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-3'>
        <PartHeader
          icon={Scale}
          title='Debts between peoples'
          tone='warning'
          note={`${debts.length} ${debts.length === 1 ? 'debt' : 'debts'} outstanding`}
        />
        {debts.length === 0 ? (
          <EmptyState
            icon={Scale}
            title='No one owes anyone'
            description='Debts arise from trade on credit, tribute and war.'
          />
        ) : (
          <PagedList
            items={debts}
            initial={PAGE}
            step={PAGE}
            noun={['debt', 'debts']}
            className='grid min-w-0 grid-cols-1 gap-2 @2xl/eco:grid-cols-2'
            itemKey={(debt) => debt.bond_id}
          >
            {(debt) => (
              <DebtCard
                debt={debt}
                busy={busy}
                onWriteOff={() => writeOff.mutate(debt.bond_id)}
              />
            )}
          </PagedList>
        )}
      </div>
    </div>
  )
}

function RouteCard({ route }: { route: TradeRoute }) {
  const status = ROUTE_STATUS[route.status]
  const mode = MODE[route.mode]
  const tolls = route.tolls.reduce((sum, toll) => sum + toll.rate_pct, 0)
  const load =
    route.capacity > 0
      ? Math.min(PERCENT, (route.volume / route.capacity) * PERCENT)
      : 0
  return (
    <li
      data-route={route.route_id}
      className='flex h-full min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={mode.icon} tone={status.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <EntityLink kind='entity' id={String(route.route_id)}>
            {route.name}
          </EntityLink>
          <Muted variant='caption' truncate>
            {`${mode.label}, ${route.length} ${route.length === 1 ? 'land' : 'lands'} long`}
          </Muted>
        </div>
        <Badge size='sm' variant={status.variant}>
          <status.icon />
          {status.label}
        </Badge>
      </div>
      <Parties
        from={{ id: route.first_id, name: route.first_name }}
        to={{ id: route.second_id, name: route.second_name }}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label>Carried last epoch</Label>
          <Stat
            value={route.volume}
            unit={`/ ${formatInteger(route.capacity)}`}
          />
        </div>
        <Progress
          size='sm'
          tone={route.status === 'open' ? 'success' : 'muted'}
          value={load}
          aria-label={`${route.name} load`}
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-wrap gap-1.5'>
        <IconStat
          icon={Swords}
          label='Danger on the way'
          value={`${route.danger} danger`}
          tone={route.danger > HALF ? 'danger' : 'warning'}
        />
        {DANGER_KEYS.filter((key) => route.dangers[key] > 0).map((key) => {
          const spec = DANGERS[key]
          return (
            <IconStat
              key={key}
              icon={spec.icon}
              label={spec.hint}
              value={`${spec.label} ${route.dangers[key]}`}
              tone={spec.tone}
            />
          )
        })}
        <IconStat
          icon={CalendarRange}
          label='Share of cargo still moving in the worst season'
          value={`${route.season_pct}% worst season`}
          tone={seasonTone(route.season_pct)}
        />
        <IconStat
          icon={Percent}
          label='Tolls taken in all'
          value={`${tolls}% tolls`}
          tone='gold'
        />
        {route.chokepoint && (
          <IconStat
            icon={Mountain}
            label='Strategic goods pass here and no other way leads between its markets'
            value='Chokepoint'
            tone='warning'
          />
        )}
        <IconStat
          icon={Flag}
          label='Renown'
          value={`${route.renown} renown`}
          tone='info'
        />
        <IconStat
          icon={CalendarClock}
          label='Founded in epoch'
          value={`Since ${route.founded_epoch}`}
          tone='muted'
        />
      </div>
    </li>
  )
}

function RoutesList({ routes }: { routes: TradeRoute[] | undefined }) {
  const [status, setStatus] = useState<string>(ALL)
  if (!routes) return <Muted>Loading the routes…</Muted>
  if (routes.length === 0)
    return (
      <div className='flex min-w-0 flex-col gap-4'>
        <div className='flex min-w-0 justify-end'>
          <FoundRouteDialog />
        </div>
        <EmptyState
          icon={Route}
          title='No trade routes yet'
          description='Merchants open a way between markets once goods are dearer at one end, or lay one out yourself.'
        />
      </div>
    )
  const shown =
    status === ALL ? routes : routes.filter((route) => route.status === status)
  const sorted = [...shown].sort(
    (a, b) =>
      ROUTE_STATUSES.indexOf(a.status) - ROUTE_STATUSES.indexOf(b.status) ||
      b.volume - a.volume
  )
  return (
    <div data-surface='RoutesList' className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <Muted variant='caption'>
          Every route, its dangers by source and its worst season. Open one to
          command it.
        </Muted>
        <FoundRouteDialog />
      </div>
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={status}
        onValueChange={(next) => setStatus(next || ALL)}
        aria-label='Route status'
      >
        <ToggleGroupItem value={ALL}>
          <Route />
          {`All ${routes.length}`}
        </ToggleGroupItem>
        {ROUTE_STATUSES.map((key: TradeRouteStatus) => {
          const spec = ROUTE_STATUS[key]
          const count = routes.filter((route) => route.status === key).length
          if (count === 0) return null
          return (
            <ToggleGroupItem key={key} value={key}>
              <spec.icon />
              {`${spec.label} ${count}`}
            </ToggleGroupItem>
          )
        })}
      </ToggleGroup>
      <PagedList
        items={sorted}
        initial={PAGE}
        step={PAGE}
        noun={['route', 'routes']}
        className='grid min-w-0 grid-cols-1 gap-3 @2xl/eco:grid-cols-2 @6xl/eco:grid-cols-3'
        itemKey={(route) => route.route_id}
      >
        {(route) => <RouteCard route={route} />}
      </PagedList>
    </div>
  )
}

function MarketsList({ worldId }: { worldId: number }) {
  const markets = useMarkets(worldId)
  const [chosen, setChosen] = useState<string>('')
  if (!markets.data) return <Muted>Loading the markets…</Muted>
  if (markets.data.length === 0)
    return (
      <EmptyState
        icon={Store}
        title='No markets in this world yet'
        description='Settlements with a market workshop start to set prices.'
      />
    )
  const table = Object.fromEntries(
    markets.data.map((row) => [String(row.id), row.name])
  )
  const id = chosen in table ? chosen : String(markets.data[0].id)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-end gap-3 rounded-xl border bg-background p-4'>
        <Medallion icon={Store} tone='gold' />
        <div className='flex min-w-0 flex-1 basis-56 flex-col'>
          <MindPicker
            label='Market'
            value={id}
            table={table}
            blocked={null}
            placeholder='Choose a market'
            onPick={setChosen}
          />
        </div>
        <Badge variant='outline'>
          <Store />
          {`${markets.data.length} markets in this world`}
        </Badge>
      </div>
      <PriceBoard key={id} marketId={Number(id)} />
    </div>
  )
}

function Overview({
  routes,
  worldName,
}: {
  routes: TradeRoute[] | undefined
  worldName: string
}) {
  const currencies = useCurrencies().data
  const ledger = useDebtsLedger().data
  const all = routes ?? []
  const open = all.filter((route) => route.status === 'open').length
  const blocked = all.filter((route) => route.status === 'blockaded').length
  const owed = ledger?.loans.filter((loan) => loan.status === 'open') ?? []
  const debased =
    currencies?.filter((coin) => coin.debased_epoch !== null).length ?? 0
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @lg/eco:grid-cols-2 @4xl/eco:grid-cols-4'>
      <KpiTile
        label='Open routes'
        icon={Route}
        tone='success'
        value={routes ? open : '—'}
        meter={{
          value: open,
          max: Math.max(1, all.length),
          label: 'Open routes',
        }}
        hint={`Of ${all.length} in ${worldName}`}
      />
      <KpiTile
        label='Blockaded'
        icon={Swords}
        tone={blocked > 0 ? 'danger' : 'muted'}
        value={routes ? blocked : '—'}
        meter={{
          value: blocked,
          max: Math.max(1, all.length),
          label: 'Blockaded routes',
        }}
        hint='Cut by the armies of an enemy'
      />
      <KpiTile
        label='Coins struck'
        icon={Coins}
        tone='gold'
        value={currencies ? currencies.length : '—'}
        hint={
          debased > 0
            ? `${debased} debased across the cosmos`
            : 'Across the cosmos, all sound'
        }
      />
      <KpiTile
        label='Loans owed'
        icon={Landmark}
        tone='warning'
        value={ledger ? owed.length : '—'}
        hint={`${formatInteger(owed.reduce((sum, loan) => sum + loan.owed, 0))} still owed to the banks`}
      />
    </div>
  )
}

function WorldPicker({
  value,
  worlds,
  onPick,
}: {
  value: number | null
  worlds: { id: number; name: string }[]
  onPick: (value: string) => void
}) {
  return (
    <Select
      value={value === null ? '' : String(value)}
      onValueChange={onPick}
      disabled={worlds.length === 0}
    >
      <SelectTrigger aria-label='World' className='min-w-48'>
        <Globe />
        <SelectValue placeholder='Finding the worlds…' />
      </SelectTrigger>
      <SelectContent>
        {worlds.map((world) => (
          <SelectItem key={world.id} value={String(world.id)}>
            {world.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function EconomyLedger({
  tab,
  onTab,
}: {
  tab: EconomyTab
  onTab: (next: string) => void
}) {
  const state = useWorldState()
  const cosmos = useCosmos()
  const worlds = (cosmos.data?.worlds ?? []).map((item) => ({
    id: item.world.id,
    name: item.world.name,
  }))
  const [world, setWorld] = useState<string>('')
  const worldId = economyWorldId(
    world,
    state.data?.world?.primary_world_id,
    worlds.map((item) => item.id)
  )
  const worldName =
    worlds.find((item) => item.id === worldId)?.name ?? 'this world'
  const routes = useTradeRoutes(worldId, worldId !== null)
  return (
    <div
      data-surface='EconomyLedger'
      className='@container/eco flex min-w-0 flex-col gap-6'
    >
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon ?? Coins}
        actions={
          <WorldPicker value={worldId} worlds={worlds} onPick={setWorld} />
        }
      />
      <Overview routes={routes.data} worldName={worldName} />
      <Tabs value={tab} onValueChange={onTab}>
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
          {tab === 'routes' && (
            <RoutesList routes={worldId === null ? undefined : routes.data} />
          )}
        </TabsContent>
        <TabsContent value='markets'>
          {tab === 'markets' &&
            (worldId === null ? (
              <Muted>Loading the markets…</Muted>
            ) : (
              <MarketsList key={worldId} worldId={worldId} />
            ))}
        </TabsContent>
        <TabsContent value='materials'>
          {tab === 'materials' &&
            (worldId === null ? (
              <Muted>Loading the materials…</Muted>
            ) : (
              <MaterialsBrowser key={worldId} worldId={worldId} />
            ))}
        </TabsContent>
        <TabsContent value='currencies'>
          {tab === 'currencies' && <CurrencyCards />}
        </TabsContent>
        <TabsContent value='debts'>
          {tab === 'debts' && <DebtsLedger />}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export function EconomyScreen() {
  const search = useSearch({ from: '/_app/economy' })
  const tab: EconomyTab = search.ledger ?? 'routes'
  const navigate = useNavigate({ from: '/economy' })
  const setTab = (next: string) =>
    void navigate({
      search: { ledger: ECONOMY_TABS.find((item) => item === next) },
    })
  return <EconomyLedger tab={tab} onTab={setTab} />
}
