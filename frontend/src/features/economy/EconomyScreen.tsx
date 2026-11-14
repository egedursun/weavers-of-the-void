import { useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  CalendarClock,
  CalendarRange,
  Coins,
  Flag,
  Gem,
  Globe,
  Landmark,
  PencilRuler,
  Percent,
  Route,
  Store,
  Swords,
  Mountain,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
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
  EmptyState,
  EntityLink,
  IconStat,
  KpiTile,
  Medallion,
  PageHeader,
  PagedList,
  LoadingBlock,
} from '@/components/domain'
import { Label, Muted, Stat } from '@/components/typography'
import { useCosmos, useWorldState } from '@/features/entity/api/queries'
import { HoardControl } from '@/features/entity/economy/HoardControl'
import { PriceBoard } from '@/features/entity/economy/RouteAndMarket'
import { FoundRouteDialog } from '@/features/entity/economy/RouteControls'
import {
  useCurrencies,
  useDebtsLedger,
  useMarkets,
  useTradeRoutes,
} from '@/features/entity/economy/api'
import {
  MODE,
  ROUTE_STATUS,
  ROUTE_STATUSES,
  type TradeRouteStatus,
} from '@/features/entity/economy/labels'
import {
  DANGERS,
  DANGER_KEYS,
  seasonTone,
} from '@/features/entity/economy/routeLabels'
import { MindPicker } from '@/features/entity/mind/parts'
import { MaterialsBrowser } from './MaterialsTab'
import { CurrencyCards, DebtsLedger, Parties } from './MoneyTab'
import { WorkshopDesigns } from './WorkshopDesigns'
import { ECONOMY_TABS, type EconomyTab, economyWorldId } from './economyTabs'

type TradeRoute = components['schemas']['TradeRouteView']

const ITEM = navItem('economy')
const PERCENT = 100
const HALF = 50
const ALL = 'all'
const PAGE = 12

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
  if (!routes) return <LoadingBlock label='Loading the routes' />
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
  if (!markets.data) return <LoadingBlock label='Loading the markets' />
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
          {`${plural(markets.data.length, 'market', 'markets')} in this world`}
        </Badge>
      </div>
      <HoardControl
        key={`hoard-${id}`}
        communityId={Number(id)}
        worldId={worldId}
      />
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
          <TabsTrigger value='workshops'>
            <PencilRuler />
            Workshops
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
              <LoadingBlock label='Loading the markets' />
            ) : (
              <MarketsList key={worldId} worldId={worldId} />
            ))}
        </TabsContent>
        <TabsContent value='materials'>
          {tab === 'materials' &&
            (worldId === null ? (
              <LoadingBlock label='Loading the materials' />
            ) : (
              <MaterialsBrowser key={worldId} worldId={worldId} />
            ))}
        </TabsContent>
        <TabsContent value='workshops'>
          {tab === 'workshops' &&
            (worldId === null ? (
              <LoadingBlock label='Loading the designs' />
            ) : (
              <WorkshopDesigns key={worldId} worldId={worldId} />
            ))}
        </TabsContent>
        <TabsContent value='currencies'>
          {tab === 'currencies' && <CurrencyCards worldId={worldId} />}
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
