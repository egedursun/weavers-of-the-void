import { useEffect, useState } from 'react'
import {
  Building2,
  CircleSlash,
  Clock,
  type LucideIcon,
  RefreshCw,
  Swords,
  Telescope,
  TrendingUp,
  UsersRound,
} from 'lucide-react'
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { toast } from 'sonner'
import {
  entityStatusValues,
  flowCategoryValues,
  nodeKindValues,
} from '@/api/generated/schema'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import {
  formatCompact,
  formatDateTime,
  formatDecimal,
  formatInteger,
} from '@/lib/format'
import { formatClock, formatDuration, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { OrnateFrame } from '@/components/ui/ornate'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ChangeChip,
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { ShareToggle } from '@/features/team/share'
import { NodeRef } from './NodeRef'
import { useCancelForecast, useForecast } from './api'
import { FORECAST_STATUS_LOOK } from './planLook'
import { argumentSummary } from './toolLook'
import {
  type WillForecast,
  type WillForecastReport,
  type WillScenario,
  type WillTouchedNode,
} from './types'
import { useActionTitle } from './useActionTitle'
import { useNameOf } from './useNameOf'
import { useWill } from './willStore'

const PERCENT = 100
const TICK_MS = 1000
const MS = 1000
const AXIS_WIDTH = 44
const LINES_SHOWN = 6
const NEARLY_DONE = 0.99

type Measure = 'population' | 'prosperity' | 'communities' | 'wars'

const MEASURES: readonly Measure[] = [
  'population',
  'prosperity',
  'communities',
  'wars',
]

const MEASURE_LOOK: Record<
  Measure,
  { label: string; icon: LucideIcon; harmful: boolean }
> = {
  population: { label: 'Population', icon: UsersRound, harmful: false },
  prosperity: { label: 'Prosperity', icon: TrendingUp, harmful: false },
  communities: { label: 'Communities', icon: Building2, harmful: false },
  wars: { label: 'Wars under way', icon: Swords, harmful: true },
}

const SCENARIO_CONFIG = {
  baseline: { label: 'Without your hand', color: 'var(--chart-3)' },
  intervened: { label: 'With your hand', color: 'var(--chart-1)' },
} satisfies ChartConfig

function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const handle = window.setInterval(() => setNow(Date.now()), TICK_MS)
    return () => window.clearInterval(handle)
  }, [active])
  return now
}

function valueOf(scenario: WillScenario, measure: Measure): number {
  if (measure === 'wars') return scenario.wars.ongoing
  return scenario[measure]
}

function startOf(report: WillForecastReport, measure: Measure): number {
  if (measure === 'population') return report.start_population
  if (measure === 'prosperity') return report.start_prosperity
  if (measure === 'communities') return report.start_communities
  return report.start_wars
}

function shown(measure: Measure, value: number): string {
  return measure === 'prosperity'
    ? formatDecimal(value, 1)
    : formatCompact(value)
}

function relative(value: number, start: number): number {
  if (start === 0) return value === 0 ? 0 : PERCENT
  return Math.round(((value - start) / Math.abs(start)) * PERCENT)
}

function statsLine(
  node: WillTouchedNode,
  other: WillTouchedNode | undefined
): string {
  return Object.entries(node.stats)
    .map(([key, value]) => {
      const before = other?.stats[key]
      const change =
        before === undefined || before === value
          ? ''
          : ` (${value > before ? '+' : ''}${formatInteger(value - before)})`
      return `${key.replaceAll('_', ' ')} ${formatInteger(value)}${change}`
    })
    .join(' · ')
}

function NodeFate({
  node,
  baseline,
}: {
  node: WillTouchedNode
  baseline: WillTouchedNode | undefined
}) {
  return (
    <li className='flex min-w-0 flex-col gap-0.5 rounded-md surface-well px-2.5 py-1.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <NodeRef id={node.node_id} name={node.name} />
        {node.kind && (
          <Badge size='sm' variant='outline'>
            {wordOf(nodeKindValues, node.kind)}
          </Badge>
        )}
        <Badge size='sm' variant={node.exists ? 'success' : 'destructive'}>
          {node.exists ? 'Still there' : 'Gone'}
        </Badge>
        {node.status && (
          <Badge size='sm' variant='outline'>
            {wordOf(entityStatusValues, node.status)}
          </Badge>
        )}
        {baseline && baseline.exists !== node.exists && (
          <Badge size='sm' variant='warning'>
            {baseline.exists
              ? 'Lives on without you'
              : 'Exists only by your hand'}
          </Badge>
        )}
      </div>
      {Object.keys(node.stats).length > 0 && (
        <Muted variant='caption'>{statsLine(node, baseline)}</Muted>
      )}
    </li>
  )
}

function Comparison({ report }: { report: WillForecastReport }) {
  const { baseline, intervened } = report
  const rows = MEASURES.map((measure) => ({
    label: MEASURE_LOOK[measure].label,
    baseline: relative(valueOf(baseline, measure), startOf(report, measure)),
    intervened: relative(
      valueOf(intervened, measure),
      startOf(report, measure)
    ),
  }))
  const categories = [
    ...new Set(
      [...baseline.deaths, ...intervened.deaths].map((row) => row.category)
    ),
  ].sort()
  const deathRows = categories.map((category) => ({
    label: wordOf(flowCategoryValues, category),
    baseline:
      baseline.deaths.find((row) => row.category === category)?.deaths ?? 0,
    intervened:
      intervened.deaths.find((row) => row.category === category)?.deaths ?? 0,
  }))
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted variant='caption'>
        {`From epoch ${String(report.start_epoch)} to epoch ${String(report.end_epoch)} · lived in ${formatDuration(report.seconds)} (${formatDuration(baseline.seconds)} without, ${formatDuration(intervened.seconds)} with your hand)`}
      </Muted>
      {report.interventions.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-1'>
          <Paged
            items={report.interventions}
            initial={LINES_SHOWN}
            as='li'
            noun={['act', 'acts']}
          >
            {(act, index) => (
              <li
                key={index}
                className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-md surface-sheen px-2.5 py-1.5'
              >
                <Text
                  as='span'
                  variant='caption'
                  weight='medium'
                  className='min-w-0 flex-1'
                >
                  {act.action_title || act.action_id}
                </Text>
                {act.essence_spent > 0 && (
                  <Badge size='sm' variant='default'>
                    {`${formatInteger(act.essence_spent)} essence`}
                  </Badge>
                )}
                {act.message && (
                  <Muted as='span' variant='caption' className='basis-full'>
                    {act.message}
                  </Muted>
                )}
              </li>
            )}
          </Paged>
        </ul>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 @lg/will:grid-cols-4'>
        {MEASURES.map((measure) => {
          const look = MEASURE_LOOK[measure]
          const Icon = look.icon
          const without = valueOf(baseline, measure)
          const withHand = valueOf(intervened, measure)
          return (
            <div
              key={measure}
              className='flex min-w-0 flex-col gap-1 rounded-md surface-sheen px-2.5 py-2'
            >
              <Label className='flex items-center gap-1'>
                <Icon aria-hidden='true' className='size-icon-xs' />
                {look.label}
              </Label>
              <Text as='span' weight='semibold' className='tabular-nums'>
                {shown(measure, withHand)}
              </Text>
              <Muted as='span' variant='caption'>
                {`${shown(measure, without)} without · ${shown(measure, startOf(report, measure))} now`}
              </Muted>
              <ChangeChip
                value={Math.round(withHand - without)}
                harmful={look.harmful}
              />
            </div>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label>{`Change since epoch ${String(report.start_epoch)}, in percent`}</Label>
        <ChartContainer
          config={SCENARIO_CONFIG}
          role='img'
          aria-label='Change of each measure in both worlds'
          className='aspect-auto h-52 w-full'
        >
          <BarChart data={rows} accessibilityLayer>
            <CartesianGrid vertical={false} strokeDasharray='2 5' />
            <XAxis
              dataKey='label'
              tickLine={false}
              axisLine={false}
              minTickGap={4}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={AXIS_WIDTH}
              tickFormatter={(value: number) => `${String(value)}%`}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  valueFormatter={(value) => `${formatInteger(value)}%`}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar
              dataKey='baseline'
              fill='var(--color-baseline)'
              radius={[3, 3, 0, 0]}
            />
            <Bar
              dataKey='intervened'
              fill='var(--color-intervened)'
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ChartContainer>
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label>Deaths by cause</Label>
        {deathRows.length === 0 ? (
          <Muted variant='caption'>No death was counted in either world.</Muted>
        ) : (
          <ChartContainer
            config={SCENARIO_CONFIG}
            role='img'
            aria-label='Deaths by cause in both worlds'
            className='aspect-auto h-48 w-full'
          >
            <BarChart data={deathRows} accessibilityLayer>
              <CartesianGrid vertical={false} strokeDasharray='2 5' />
              <XAxis
                dataKey='label'
                tickLine={false}
                axisLine={false}
                minTickGap={4}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={AXIS_WIDTH}
                tickFormatter={(value: number) => formatCompact(value)}
              />
              <ChartTooltip
                content={<ChartTooltipContent valueFormatter={formatInteger} />}
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar
                dataKey='baseline'
                fill='var(--color-baseline)'
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey='intervened'
                fill='var(--color-intervened)'
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ChartContainer>
        )}
      </div>
      <Muted variant='caption'>
        {`Wars begun ${String(intervened.wars.begun)} with your hand and ${String(baseline.wars.begun)} without; ended ${String(intervened.wars.ended)} and ${String(baseline.wars.ended)}.`}
      </Muted>
      {intervened.nodes.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>What your hand touched</Label>
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged
              items={intervened.nodes}
              initial={LINES_SHOWN}
              as='li'
              noun={['record', 'records']}
            >
              {(node) => (
                <NodeFate
                  key={node.node_id}
                  node={node}
                  baseline={baseline.nodes.find(
                    (other) => other.node_id === node.node_id
                  )}
                />
              )}
            </Paged>
          </ul>
        </div>
      )}
      <Tabs defaultValue='intervened' className='flex min-w-0 flex-col gap-2'>
        <TabsList aria-label='Chronicle of each world' className='w-full'>
          <TabsTrigger value='intervened'>
            {SCENARIO_CONFIG.intervened.label}
          </TabsTrigger>
          <TabsTrigger value='baseline'>
            {SCENARIO_CONFIG.baseline.label}
          </TabsTrigger>
        </TabsList>
        {(['intervened', 'baseline'] as const).map((side) => {
          const lines =
            side === 'intervened' ? intervened.chronicle : baseline.chronicle
          return (
            <TabsContent key={side} value={side}>
              {lines.length === 0 ? (
                <Muted variant='caption'>
                  This world wrote no chronicle line.
                </Muted>
              ) : (
                <ul className='flex min-w-0 flex-col gap-1'>
                  <Paged
                    items={lines}
                    initial={LINES_SHOWN}
                    as='li'
                    noun={['line', 'lines']}
                  >
                    {(line, index) => (
                      <li
                        key={index}
                        className='flex min-w-0 flex-col rounded-md surface-well px-2.5 py-1.5'
                      >
                        <Label>
                          {line.year === null
                            ? `Epoch ${String(line.epoch)}`
                            : `Epoch ${String(line.epoch)}, year ${String(line.year)}`}
                        </Label>
                        <Text variant='caption'>{line.text}</Text>
                      </li>
                    )}
                  </Paged>
                </ul>
              )}
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}

function Intervention({
  actionId,
  input,
}: {
  actionId: string
  input: Record<string, unknown>
}) {
  const title = useActionTitle(actionId)
  const nameOf = useNameOf()
  return (
    <li className='flex min-w-0 flex-col rounded-md surface-well px-2.5 py-1.5'>
      <Text as='span' variant='caption' weight='medium'>
        {title || actionId}
      </Text>
      <Muted as='span' variant='caption' truncate={2}>
        {argumentSummary(input, nameOf) || 'With no input.'}
      </Muted>
    </li>
  )
}

function ForecastBody({ forecast }: { forecast: WillForecast }) {
  const cancel = useCancelForecast(forecast.id)
  const live = forecast.status === 'queued' || forecast.status === 'running'
  const now = useNow(forecast.status === 'running')
  const look = FORECAST_STATUS_LOOK[forecast.status]
  const StatusIcon = look.icon
  const started = forecast.started_at
    ? new Date(forecast.started_at).getTime()
    : null
  const elapsed = started === null ? 0 : Math.max(0, (now - started) / MS)
  const remaining = Math.max(0, forecast.eta_seconds - elapsed)
  const streamed = useWill((state) => state.foresight[forecast.id] ?? 0)
  const byEpoch = forecast.epochs_done / Math.max(1, forecast.epochs)
  const byClock =
    forecast.eta_seconds > 0
      ? Math.min(NEARLY_DONE, elapsed / forecast.eta_seconds)
      : 0
  const fraction =
    forecast.status === 'done' ? 1 : Math.max(byEpoch, byClock, streamed)
  const block = isReadOnly()
    ? READ_ONLY_MESSAGE
    : cancel.isPending
      ? 'Stopping the forecast.'
      : null
  return (
    <OrnateFrame
      frame='card'
      tone={look.tone}
      role='group'
      aria-label='Forecast of the Divine Will'
      data-domain='will-forecast'
      data-status={forecast.status}
      className='flex min-w-0 flex-col gap-3 p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Telescope} tone={look.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Label variant='overline'>Foresight</Label>
          <Text weight='semibold' className='text-gilded font-display'>
            {`${plural(forecast.epochs, 'epoch')} ahead, on a copy of the world`}
          </Text>
        </div>
        <Badge size='sm' variant={look.badge}>
          <StatusIcon
            className={
              forecast.status === 'running' ? 'animate-spin' : undefined
            }
          />
          {look.label}
        </Badge>
      </div>
      <ShareToggle
        kind='forecast'
        id={forecast.id}
        shared={forecast.owner.shared}
        mine={forecast.owner.mine}
        author={forecast.owner.author_name}
      />
      {forecast.interventions.length > 0 ? (
        <ul className='flex min-w-0 flex-col gap-1'>
          <Paged
            items={forecast.interventions}
            initial={LINES_SHOWN}
            as='li'
            noun={['act', 'acts']}
          >
            {(item, index) => (
              <Intervention
                key={index}
                actionId={item.action_id}
                input={item.input}
              />
            )}
          </Paged>
        </ul>
      ) : (
        <Muted variant='caption'>
          No intervention: both copies live untouched, as a measure of chance.
        </Muted>
      )}
      {live && (
        <div className='flex min-w-0 flex-col gap-2' aria-live='polite'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Clock
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
            <Text as='span' variant='caption' weight='medium'>
              {forecast.status === 'queued'
                ? `Expected to take about ${formatDuration(forecast.eta_seconds)}`
                : `About ${formatClock(remaining)} left`}
            </Text>
            <Muted as='span' variant='caption'>
              {[
                `Epoch ${String(Math.min(forecast.epochs, forecast.epochs_done + 1))} of ${String(forecast.epochs)}`,
                forecast.job_id ? 'a background work of the world' : '',
              ]
                .filter(Boolean)
                .join(' · ')}
            </Muted>
          </div>
          <Progress
            value={fraction * PERCENT}
            indeterminate={forecast.status === 'queued'}
            aria-label={`Forecast progress, ${String(Math.round(fraction * PERCENT))}%`}
          />
          <div className='flex justify-end'>
            <Button
              act={cancel}
              variant='outline'
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() =>
                cancel.mutate(undefined, {
                  onSuccess: () => toast('The forecast is cancelled.'),
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              <CircleSlash />
              Cancel the forecast
            </Button>
          </div>
        </div>
      )}
      {forecast.status === 'done' &&
        (forecast.report ? (
          <Comparison report={forecast.report} />
        ) : (
          <EmptyState
            size='compact'
            icon={Telescope}
            title='No comparison'
            description='The forecast finished without a report.'
          />
        ))}
      {forecast.status === 'failed' && (
        <Text variant='caption' tone='destructive' role='alert'>
          {forecast.error ||
            'The forecast failed; the Divine Will explains why in its answer.'}
        </Text>
      )}
      {forecast.status === 'cancelled' && (
        <Muted variant='caption'>
          This forecast was cancelled before it finished.
        </Muted>
      )}
      {forecast.finished_at && (
        <Muted variant='caption'>
          {`Asked for ${plural(forecast.epochs, 'epoch')}, ${plural(forecast.epochs_done, 'epoch')} lived; finished ${formatDateTime(forecast.finished_at)} after ${formatDuration(Math.max(0, (new Date(forecast.finished_at).getTime() - new Date(forecast.started_at ?? forecast.created_at).getTime()) / MS))}`}
        </Muted>
      )}
    </OrnateFrame>
  )
}

export function ForecastCard({ forecastId }: { forecastId: number }) {
  const query = useForecast(forecastId)
  if (query.isPending) return <LoadingBlock label='Opening the forecast' />
  if (query.isError)
    return (
      <EmptyState
        size='inline'
        icon={Telescope}
        title='The forecast could not be opened'
        description={query.error.message}
        action={
          <Button
            variant='outline'
            size='sm'
            onClick={() => void query.refetch()}
          >
            <RefreshCw />
            Try again
          </Button>
        }
      />
    )
  return <ForecastBody forecast={query.data} />
}
