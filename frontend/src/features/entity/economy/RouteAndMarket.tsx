import { useState } from 'react'
import {
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowUpFromLine,
  CalendarClock,
  CalendarRange,
  CloudSun,
  Check,
  DoorClosed,
  DoorOpen,
  Flag,
  Landmark,
  Lock,
  Map as MapIcon,
  Mountain,
  Package,
  Percent,
  Route,
  ShieldAlert,
  Store,
  Swords,
  TriangleAlert,
  Undo2,
  Utensils,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  IconStat,
  KpiTile,
  type KpiTone,
  Medallion,
  Section,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Muted, Stat, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustPanel,
  FIELD_GRID,
  GoodChip,
  NumberField,
  PartHeader,
} from './EntityEconomy'
import { PriceHolds } from './PriceHolds'
import {
  RouteDangers,
  RouteEditor,
  StrikeRoute,
  TollControls,
  TollDestination,
} from './RouteControls'
import { useMarketPrices, useTradeRoute } from './api'
import {
  COMMODITY,
  GOODS_FAMILY,
  MATERIAL_LABEL,
  MODE,
  ROUTE_STATUS,
  TRADE_LOSS,
} from './labels'
import { seasonTone } from './routeLabels'

type Toll = components['schemas']['TollView']
type Series = components['schemas']['PriceSeries']
type Flow = components['schemas']['RouteFlowView']

const WORKING = 'Working…'
const BASE = 100
const PERCENT = 100
const DEAR = 2
const CHEAP = 2

const SWING_WIDE = 20

function priceTone(price: number): KpiTone {
  if (price > BASE * DEAR) return 'danger'
  if (price > BASE) return 'warning'
  if (price < BASE / CHEAP) return 'success'
  return 'muted'
}

function priceWord(price: number): string {
  if (price > BASE * DEAR) return 'Scarce'
  if (price > BASE) return 'Dear'
  if (price < BASE / CHEAP) return 'Glut'
  return 'Fair'
}

function PriceCard({ series }: { series: Series }) {
  const spec = COMMODITY[series.commodity]
  const last = series.points[series.points.length - 1]
  const tone = priceTone(last.price)
  return (
    <li
      data-commodity={series.commodity}
      className='flex h-full min-w-0 flex-col gap-2.5 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='medium' truncate>
            {spec.label}
          </Text>
          <Muted variant='caption' truncate>
            {`${priceWord(last.price)} · ${GOODS_FAMILY[spec.family].label}`}
          </Muted>
        </div>
        <Stat
          value={last.price}
          unit='/ 100'
          tone={
            tone === 'danger'
              ? 'destructive'
              : tone === 'success'
                ? 'success'
                : tone === 'warning'
                  ? 'warning'
                  : 'default'
          }
        />
      </div>
      {series.points.length > 1 && (
        <LineChart
          bare
          height={48}
          label={`${spec.label} price`}
          series={[
            {
              key: series.commodity,
              label: spec.label,
              color: 'var(--chart-1)',
              points: series.points.map((point) => ({
                x: point.epoch,
                y: point.price,
              })),
            },
          ]}
        />
      )}
      <div className='mt-auto grid min-w-0 grid-cols-2 gap-1.5'>
        <IconStat
          icon={Package}
          label='Held in the market'
          value={`${formatInteger(last.supply)} held`}
          tone='gold'
        />
        <IconStat
          icon={Utensils}
          label='Needed each epoch'
          value={`${formatInteger(last.demand)} needed`}
          tone={last.demand > last.supply ? 'danger' : 'muted'}
        />
        <IconStat
          icon={ArrowDownToLine}
          label='Bought in from other markets'
          value={`${formatInteger(last.imported)} in`}
          tone='info'
        />
        <IconStat
          icon={ArrowUpFromLine}
          label='Sold out to other markets'
          value={`${formatInteger(last.exported)} out`}
          tone='success'
        />
      </div>
      <div data-surface='chart-market-swing' className='min-w-0'>
        <IconStat
          icon={CloudSun}
          label='How far the sampled years swung the price'
          value={`±${formatInteger(last.swing)}% across the years`}
          tone={last.swing >= SWING_WIDE ? 'warning' : 'muted'}
        />
      </div>
    </li>
  )
}

export function PriceBoard({ marketId }: { marketId: number }) {
  const view = useMarketPrices(marketId)
  if (!view.data || view.data.series.length === 0) return null
  const series = [...view.data.series].sort(
    (a, b) =>
      b.points[b.points.length - 1].price - a.points[a.points.length - 1].price
  )
  const last = (row: Series) => row.points[row.points.length - 1].price
  const scarce = series.filter((row) => last(row) > BASE * DEAR).length
  const glut = series.filter((row) => last(row) < BASE / CHEAP).length
  return (
    <Section
      id='section-market'
      title='Market prices'
      description='What each good costs here, epoch by epoch, against what the market holds and needs. 100 is its usual price.'
      icon={Store}
    >
      <div
        data-surface='PriceBoard'
        className='@container/market flex min-w-0 flex-col gap-3'
      >
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge variant='outline'>
            <Store />
            {`${series.length} goods priced`}
          </Badge>
          <Badge variant={scarce > 0 ? 'destructive' : 'outline'}>
            <TriangleAlert />
            {`${scarce} scarce, over twice the usual`}
          </Badge>
          <Badge variant={glut > 0 ? 'success' : 'outline'}>
            <Package />
            {`${glut} in glut, under half`}
          </Badge>
        </div>
        <ul className='grid min-w-0 grid-cols-1 gap-2 @md/market:grid-cols-2 @3xl/market:grid-cols-3'>
          {series.map((row) => (
            <PriceCard key={row.commodity} series={row} />
          ))}
        </ul>
        <PriceHolds marketId={marketId} />
      </div>
    </Section>
  )
}

function TollStop({ toll }: { toll: Toll }) {
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={Landmark} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <EntityLink kind='entity' id={String(toll.region_id)}>
            {toll.region_name}
          </EntityLink>
          <Muted variant='caption'>
            {'Taken by '}
            <EntityLink kind='entity' id={String(toll.controller_id)}>
              {toll.controller_name}
            </EntityLink>
          </Muted>
        </div>
        <IconStat
          icon={Percent}
          label='Toll on every load'
          value={`${toll.rate_pct}% toll`}
          tone='gold'
        />
      </div>
      {(toll.polity_id !== null || toll.set_by_player) && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5 border-t pt-2'>
          <TollDestination toll={toll} />
          {toll.set_by_player && (
            <Badge size='sm' variant='info'>
              <Check />
              Rate held by you
            </Badge>
          )}
        </div>
      )}
    </li>
  )
}

function TollEditor({
  toll,
  busy,
  onSet,
}: {
  toll: Toll
  busy: string | null
  onSet: (rate: number | null) => void
}) {
  const [rate, setRate] = useState(String(toll.rate_pct))
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 rounded-lg border bg-background p-2.5 @md/route:grid-cols-3'>
      <div className='flex min-w-0 flex-col'>
        <Text weight='medium' truncate>
          {toll.region_name}
        </Text>
        <Muted variant='caption' truncate>
          {toll.set_by_player
            ? 'At the rate you hold'
            : `Set by ${toll.controller_name}`}
        </Muted>
      </div>
      <NumberField
        label='Toll %'
        aria={`Toll in ${toll.region_name}`}
        value={rate}
        max={PERCENT}
        onChange={setRate}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => onSet(Math.round(Number(rate) || 0))}
        >
          <Check />
          Hold this toll
        </Button>
        {toll.set_by_player && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => onSet(null)}
          >
            <Undo2 />
            Leave it to its master
          </Button>
        )}
      </div>
    </div>
  )
}

function CargoEpoch({
  epoch,
  flows,
  last,
}: {
  epoch: number
  flows: Flow[]
  last: boolean
}) {
  const carried = flows.reduce((sum, row) => sum + row.volume, 0)
  const lost = flows.reduce((sum, row) => sum + row.lost, 0)
  const tolls = flows.reduce((sum, row) => sum + row.toll_paid, 0)
  return (
    <TimelineItem
      icon={lost > 0 ? ShieldAlert : Package}
      tone={lost > 0 ? 'warning' : 'success'}
      title={`${formatInteger(carried)} carried`}
      timestamp={`Epoch ${epoch}`}
      last={last}
      framed
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {flows.map((row, index) => (
          <GoodChip
            key={`${row.commodity}-${row.material ?? ''}-${index}`}
            kind={row.commodity}
            quantity={row.volume}
            suffix={
              row.material
                ? ` of ${MATERIAL_LABEL[row.material].toLowerCase()}`
                : undefined
            }
          />
        ))}
        {flows
          .filter((row) => row.lost > 0)
          .map((row, index) => {
            const loss = row.loss ? TRADE_LOSS[row.loss] : null
            const Icon = loss?.icon ?? TriangleAlert
            return (
              <Badge key={`lost-${index}`} variant='destructive'>
                <Icon />
                {`${formatInteger(row.lost)} lost to ${loss?.label ?? 'the road'}`}
              </Badge>
            )
          })}
        {tolls > 0 && (
          <Badge variant='info'>
            <Percent />
            {`${formatInteger(tolls)} paid in tolls`}
          </Badge>
        )}
      </div>
    </TimelineItem>
  )
}

export function TradeRouteSection({
  routeId,
  readOnlyReason,
}: {
  routeId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const view = useTradeRoute(routeId)
  const open = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_route:open', {
          body: { route_id: routeId },
        })
      ),
  })
  const close = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_route:close', {
          body: { route_id: routeId },
        })
      ),
  })
  const toll = useGodAction({
    run: ({ region, rate }: { region: number; rate: number | null }) =>
      unwrap(
        api.POST('/api/actions/trade_route:toll', {
          body: { route_id: routeId, region_id: region, rate },
        })
      ),
  })
  const busy =
    readOnlyReason ??
    reason() ??
    (open.isPending || close.isPending || toll.isPending ? WORKING : null)
  const route = view.data
  const epochs = route
    ? [...new Set(route.flows.map((row) => row.epoch))].sort((a, b) => b - a)
    : []
  return (
    <Section
      id='section-trade-route'
      title='The route'
      description='Where it runs, what it carries, who takes a toll and for which treasury, and what it lost to bandits, beasts, weather and the sea.'
      icon={Route}
    >
      {view.isPending && <Muted>Loading the route…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The route could not be read'
          description={view.error.message}
        />
      )}
      {route && (
        <div
          data-surface='TradeRouteSection'
          className='@container/route flex min-w-0 flex-col gap-5'
        >
          <RouteBanner route={route} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/route:grid-cols-2 @3xl/route:grid-cols-4'>
            <KpiTile
              label='Carried last epoch'
              value={formatInteger(route.volume)}
              icon={Package}
              tone='gold'
              meter={{
                value: route.volume,
                max: Math.max(route.capacity, 1),
                label: 'Carried against capacity',
              }}
              hint={`Of ${formatInteger(route.capacity)} it can bear`}
            />
            <KpiTile
              label='Danger'
              value={route.danger}
              icon={Swords}
              tone={route.danger > BASE / 2 ? 'danger' : 'warning'}
              meter={{ value: route.danger, max: BASE, label: 'Danger' }}
              hint={`Bandits ${route.dangers.bandits}, beasts ${route.dangers.beasts}, weather ${route.dangers.weather}, sea ${route.dangers.sea}`}
            />
            <KpiTile
              label='Renown'
              value={route.renown}
              icon={Flag}
              tone='info'
              meter={{ value: route.renown, max: BASE, label: 'Renown' }}
              hint='Draws more merchants each epoch'
            />
            <KpiTile
              label='Carried culture'
              value={route.culture}
              icon={ArrowLeftRight}
              tone='verdigris'
              meter={{ value: route.culture, max: BASE, label: 'Culture' }}
              hint='Words, gods and customs that travel with it'
            />
          </div>
          <RouteDangers route={route} />
          <div className='flex min-w-0 flex-col gap-3'>
            <PartHeader
              icon={Landmark}
              title='Tolls on the way'
              note={
                route.tolls.length === 0
                  ? 'No one takes a toll on this road.'
                  : `${route.tolls.reduce((sum, row) => sum + row.rate_pct, 0)}% taken in all across ${route.tolls.length} ${route.tolls.length === 1 ? 'land' : 'lands'}`
              }
            />
            {route.tolls.length > 0 && (
              <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/route:grid-cols-2'>
                {route.tolls.map((item) => (
                  <TollStop key={item.region_id} toll={item} />
                ))}
              </ul>
            )}
          </div>
          <div className='flex min-w-0 flex-col gap-3'>
            <PartHeader
              icon={Package}
              title='Cargo by epoch'
              note='What merchants carried each epoch and what the road took from them.'
            />
            {epochs.length === 0 ? (
              <EmptyState
                icon={Package}
                title='No cargo yet'
                description='Loads appear once merchants travel it.'
              />
            ) : (
              <Timeline label='Cargo by epoch'>
                {epochs.map((epoch, index) => (
                  <CargoEpoch
                    key={epoch}
                    epoch={epoch}
                    flows={route.flows.filter((row) => row.epoch === epoch)}
                    last={index === epochs.length - 1}
                  />
                ))}
              </Timeline>
            )}
          </div>
          <AdjustPanel
            label='Adjust the route'
            title='Command the route'
            note='Close it or open it, set and hold any value the world reads (way of travel, master, blockade, every danger, the worst season, capacity), raise or forbid tolls, or strike it from the world. Every change goes into the ledger.'
          >
            <RouteEditor
              key={`${route.route_id}-${route.locked.join('.')}`}
              route={route}
              busy={busy}
            />
            <div className='flex min-w-0 flex-wrap gap-2'>
              {route.status === 'closed' || route.status === 'decayed' ? (
                <Button
                  size='sm'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => open.mutate(undefined)}
                >
                  <DoorOpen />
                  Open the route
                </Button>
              ) : (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => close.mutate(undefined)}
                >
                  <DoorClosed />
                  Close the route
                </Button>
              )}
            </div>
            {route.tolls.length > 0 && (
              <div className={FIELD_GRID}>
                {route.tolls.map((item) => (
                  <TollEditor
                    key={`${item.region_id}-${item.rate_pct}`}
                    toll={item}
                    busy={busy}
                    onSet={(rate) =>
                      toll.mutate({ region: item.region_id, rate })
                    }
                  />
                ))}
              </div>
            )}
            <TollControls route={route} busy={busy} />
            <div className='flex min-w-0 flex-wrap gap-2 border-t pt-3'>
              <StrikeRoute route={route} busy={busy} />
            </div>
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

type RouteView = components['schemas']['TradeRouteView']

export function RouteBanner({ route }: { route: RouteView }) {
  const names = useNames()
  const status = ROUTE_STATUS[route.status]
  const mode = MODE[route.mode]
  const named = (id: number, fallback: string) =>
    names.data?.find((row) => row.kind === 'entity' && row.id === id)?.name ??
    fallback
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={mode.icon} tone={status.tone} />
        <div className='flex min-w-0 flex-1 basis-56 flex-col gap-0.5'>
          <Text
            weight='semibold'
            className='flex min-w-0 flex-wrap items-center gap-x-2'
          >
            <EntityLink kind='entity' id={String(route.first_id)}>
              {route.first_name}
            </EntityLink>
            <ArrowLeftRight
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-muted-foreground'
            />
            <EntityLink kind='entity' id={String(route.second_id)}>
              {route.second_name}
            </EntityLink>
          </Text>
          <Muted variant='caption'>
            {`${mode.label}, ${route.length} ${route.length === 1 ? 'land' : 'lands'} long`}
          </Muted>
        </div>
        <Badge variant={status.variant}>
          <status.icon />
          {status.label}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <IconStat
          icon={MapIcon}
          label='Lands it crosses'
          value={`${route.length} ${route.length === 1 ? 'land' : 'lands'}`}
          tone='info'
        />
        <IconStat
          icon={CalendarClock}
          label='Founded in epoch'
          value={`Founded ${route.founded_epoch}`}
          tone='muted'
        />
        {route.last_traffic_epoch !== null && (
          <IconStat
            icon={Package}
            label='Last traffic in epoch'
            value={`Last trade ${route.last_traffic_epoch}`}
            tone='gold'
          />
        )}
        {route.controller_id !== null && (
          <Badge variant='outline'>
            <Flag />
            {'Kept by '}
            <EntityLink kind='entity' id={String(route.controller_id)}>
              {named(route.controller_id, 'its master')}
            </EntityLink>
          </Badge>
        )}
        {route.blockaded_by_id !== null && (
          <Badge variant='destructive'>
            <ShieldAlert />
            {'Blockaded by '}
            <EntityLink kind='entity' id={String(route.blockaded_by_id)}>
              {named(route.blockaded_by_id, 'an enemy')}
            </EntityLink>
          </Badge>
        )}
        {route.closed_by_player && (
          <Badge variant='warning'>
            <DoorClosed />
            Closed by your hand
          </Badge>
        )}
        {route.closed_by_son_id !== null && (
          <Badge variant='warning'>
            <DoorClosed />
            {`Closed by ${route.closed_by_son_name || 'a son'}`}
          </Badge>
        )}
        <IconStat
          icon={CalendarRange}
          label='Share of cargo still moving in the worst season'
          value={`${route.season_pct}% in the worst season`}
          tone={seasonTone(route.season_pct)}
        />
        {route.chokepoint && (
          <Badge variant='warning'>
            <Mountain />
            Chokepoint
          </Badge>
        )}
        {route.locked.length > 0 && (
          <Badge variant='default'>
            <Lock />
            {`${route.locked.length} held by you`}
          </Badge>
        )}
      </div>
    </div>
  )
}
