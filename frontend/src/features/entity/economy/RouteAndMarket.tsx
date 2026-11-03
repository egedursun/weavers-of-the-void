import { useState } from 'react'
import {
  DoorClosed,
  DoorOpen,
  Route,
  Scale,
  Store,
  TriangleAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  Medallion,
  Section,
  StatBar,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useMarketPrices, useTradeRoute } from './api'
import { COMMODITY, MODE, ROUTE_STATUS } from './labels'

type Toll = components['schemas']['TollView']

const WORKING = 'Working…'
const BASE = 100

export function PriceBoard({ marketId }: { marketId: number }) {
  const view = useMarketPrices(marketId)
  if (!view.data || view.data.series.length === 0) return null
  return (
    <Section
      id='section-market'
      title='Market prices'
      description='What each good costs here, epoch by epoch, against what the market holds and needs. 100 is its usual price.'
      icon={Store}
    >
      <ul
        data-surface='PriceBoard'
        className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'
      >
        {view.data.series.map((series) => {
          const spec = COMMODITY[series.commodity]
          const last = series.points[series.points.length - 1]
          return (
            <li
              key={series.commodity}
              className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
            >
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion
                  icon={spec.icon}
                  tone={
                    last.price > BASE * 2
                      ? 'danger'
                      : last.price < BASE / 2
                        ? 'success'
                        : 'muted'
                  }
                  size='sm'
                />
                <Text className='min-w-0 flex-1' truncate>
                  {spec.label}
                </Text>
                <Stat value={last.price} />
              </div>
              <Muted variant='caption'>{`Holds ${formatInteger(last.supply)}, needs ${formatInteger(last.demand)}; bought in ${formatInteger(last.imported)}, sold out ${formatInteger(last.exported)}`}</Muted>
              {series.points.length > 1 && (
                <LineChart
                  bare
                  height={56}
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
            </li>
          )
        })}
      </ul>
    </Section>
  )
}

function ModeIcon({ mode }: { mode: components['schemas']['TradeMode'] }) {
  const Icon = MODE[mode].icon
  return <Icon />
}

function TollRow({
  routeId,
  toll,
  busy,
  onSet,
}: {
  routeId: number
  toll: Toll
  busy: string | null
  onSet: (rate: number | null) => void
}) {
  const [rate, setRate] = useState(String(toll.rate_pct))
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-lg border bg-muted/30 p-2'>
      <div className='flex min-w-0 flex-1 flex-col'>
        <EntityLink kind='entity' id={String(toll.region_id)}>
          {toll.region_name}
        </EntityLink>
        <Muted variant='caption'>
          {'Taken by '}
          <EntityLink kind='entity' id={String(toll.controller_id)}>
            {toll.controller_name}
          </EntityLink>
          {toll.set_by_player ? ' at the rate you set' : ''}
        </Muted>
      </div>
      <div className='flex w-24 flex-col gap-1'>
        <Label>Toll %</Label>
        <Input
          type='number'
          min={0}
          max={100}
          value={rate}
          aria-label={`Toll in ${toll.region_name}`}
          onChange={(event) => setRate(event.target.value)}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => onSet(Math.round(Number(rate) || 0))}
        data-route={routeId}
      >
        <Scale />
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
          Leave it to its master
        </Button>
      )}
    </li>
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
  return (
    <Section
      id='section-trade-route'
      title='The route'
      description='Where it runs, what it carries, who takes a toll on the way and what it lost to bandits and the sea.'
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
          className='flex min-w-0 flex-col gap-5'
        >
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge variant={ROUTE_STATUS[route.status].variant}>
              {ROUTE_STATUS[route.status].label}
            </Badge>
            <Badge variant='outline'>
              <ModeIcon mode={route.mode} />
              {`${MODE[route.mode].label}, ${route.length} regions long`}
            </Badge>
            <Text>
              <EntityLink kind='entity' id={String(route.first_id)}>
                {route.first_name}
              </EntityLink>
              {' ⇄ '}
              <EntityLink kind='entity' id={String(route.second_id)}>
                {route.second_name}
              </EntityLink>
            </Text>
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            <StatBar
              label='Carried last epoch'
              value={route.volume}
              max={Math.max(route.capacity, 1)}
            />
            <StatBar
              label='Danger'
              value={route.danger}
              max={BASE}
              tone={route.danger > BASE / 2 ? 'destructive' : 'default'}
            />
            <StatBar label='Renown' value={route.renown} max={BASE} />
            <StatBar label='Carried culture' value={route.culture} max={BASE} />
          </div>
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
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Tolls on the way</Label>
              <ul className='flex min-w-0 flex-col gap-2'>
                {route.tolls.map((item) => (
                  <TollRow
                    key={item.region_id}
                    routeId={routeId}
                    toll={item}
                    busy={busy}
                    onSet={(rate) =>
                      toll.mutate({ region: item.region_id, rate })
                    }
                  />
                ))}
              </ul>
            </div>
          )}
          {route.flows.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Cargo by epoch</Label>
              <ul className='flex min-w-0 flex-col gap-1'>
                {[...route.flows].reverse().map((flow, index) => (
                  <li
                    key={`${flow.epoch}-${flow.commodity}-${index}`}
                    className='flex min-w-0 flex-wrap items-center gap-2'
                  >
                    <Badge
                      size='sm'
                      variant='outline'
                    >{`Epoch ${flow.epoch}`}</Badge>
                    <Text>{`${formatInteger(flow.volume)} ${COMMODITY[flow.commodity].label.toLowerCase()}${flow.material ? ` of ${flow.material.replace('_', ' ')}` : ''}`}</Text>
                    {flow.lost > 0 && (
                      <Badge
                        size='sm'
                        variant='destructive'
                      >{`${formatInteger(flow.lost)} lost to ${flow.loss ?? 'the road'}`}</Badge>
                    )}
                    {flow.toll_paid > 0 && (
                      <Badge
                        size='sm'
                        variant='info'
                      >{`${formatInteger(flow.toll_paid)} in tolls`}</Badge>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}
