import { type ReactNode } from 'react'
import { ChartNoAxesColumn } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from 'recharts'
import { llmCallKindValues, llmCallStatusValues } from '@/api/generated/schema'
import { formatCompact, formatInteger, formatPercent } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { Progress } from '@/components/ui/progress'
import { EmptyState, Medallion } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import {
  type UsageBucket,
  type UsagePoint,
  type UsageReport,
  type UsageShare,
} from './api'
import {
  INPUT_COLOR,
  type Look,
  KIND_LOOK,
  OUTPUT_COLOR,
  STATUS_LOOK,
  seriesColor,
  shareOf,
  totalOf,
} from './usageVisuals'

const PERCENT = 100
const BARS_SHOWN = 8
const DONUT_SLICES = 5
const AXIS_WIDTH = 48
const STEP_AXIS_WIDTH = 132
const OTHER_SLICE = 'Every other model'

const TOKEN_CONFIG = {
  input: { label: 'Tokens in', color: INPUT_COLOR },
  output: { label: 'Tokens out', color: OUTPUT_COLOR },
} satisfies ChartConfig

const dayFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
})
const hourFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
})

function pointLabel(point: UsagePoint, bucket: UsageBucket): string {
  if (bucket === 'epoch' || point.start === null)
    return point.epoch === null ? 'Outside epochs' : `Epoch ${point.epoch}`
  const start = new Date(point.start)
  return bucket === 'hour' ? hourFormat.format(start) : dayFormat.format(start)
}

function NoData({ children }: { children: ReactNode }) {
  return (
    <EmptyState
      size='compact'
      icon={ChartNoAxesColumn}
      title='Nothing to draw'
      description={String(children)}
    />
  )
}

export function TokenTimeline({
  timeline,
  bucket,
}: {
  timeline: UsagePoint[]
  bucket: UsageBucket
}) {
  if (timeline.length === 0)
    return (
      <NoData>
        {bucket === 'epoch'
          ? 'No matching call ran inside an epoch. Try the hourly or daily view.'
          : 'No matching call was measured in this range.'}
      </NoData>
    )
  const rows = timeline.map((point) => ({
    label: pointLabel(point, bucket),
    input: point.input_tokens,
    output: point.output_tokens,
    calls: point.calls,
    errors: point.errors,
  }))
  const peak = rows.reduce(
    (best, row) =>
      row.input + row.output > best.input + best.output ? row : best,
    rows[0]
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ChartContainer
        config={TOKEN_CONFIG}
        role='img'
        aria-label={`Tokens in and out ${bucket === 'epoch' ? 'per epoch' : bucket === 'hour' ? 'per hour' : 'per day'}`}
        className='aspect-auto h-72 w-full'
      >
        <AreaChart data={rows} accessibilityLayer>
          <defs>
            <linearGradient id='usage-in' x1='0' y1='0' x2='0' y2='1'>
              <stop
                offset='0'
                stopColor='var(--color-input)'
                stopOpacity={0.5}
              />
              <stop
                offset='1'
                stopColor='var(--color-input)'
                stopOpacity={0.04}
              />
            </linearGradient>
            <linearGradient id='usage-out' x1='0' y1='0' x2='0' y2='1'>
              <stop
                offset='0'
                stopColor='var(--color-output)'
                stopOpacity={0.55}
              />
              <stop
                offset='1'
                stopColor='var(--color-output)'
                stopOpacity={0.06}
              />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray='2 5' />
          <XAxis
            dataKey='label'
            tickLine={false}
            axisLine={false}
            minTickGap={24}
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
          <Area
            dataKey='input'
            type='monotone'
            stackId='tokens'
            stroke='var(--color-input)'
            strokeWidth={2}
            fill='url(#usage-in)'
          />
          <Area
            dataKey='output'
            type='monotone'
            stackId='tokens'
            stroke='var(--color-output)'
            strokeWidth={2}
            fill='url(#usage-out)'
          />
        </AreaChart>
      </ChartContainer>
      <Muted variant='caption'>
        {`Busiest: ${peak.label} with ${formatCompact(peak.input + peak.output)} ${agree(peak.input + peak.output, 'token')} over ${plural(peak.calls, 'call', 'calls')}${peak.errors > 0 ? `, ${plural(peak.errors, 'failure', 'failures')}` : ''}.`}
      </Muted>
    </div>
  )
}

export function ModelDonut({
  models,
  onPick,
}: {
  models: UsageShare[]
  onPick: (model: string) => void
}) {
  const whole = models.reduce((sum, model) => sum + totalOf(model), 0)
  if (whole === 0) return <NoData>No matching call used any tokens.</NoData>
  const head = models.slice(0, DONUT_SLICES)
  const rest = models.slice(DONUT_SLICES)
  const shown = [
    ...head.map((model, position) => ({
      name: model.name,
      total: totalOf(model),
      calls: model.calls,
      color: seriesColor(position),
      pickable: true,
    })),
    ...(rest.length > 0
      ? [
          {
            name: OTHER_SLICE,
            total: rest.reduce((sum, model) => sum + totalOf(model), 0),
            calls: rest.reduce((sum, model) => sum + model.calls, 0),
            color: 'var(--muted-foreground)',
            pickable: false,
          },
        ]
      : []),
  ]
  const config = Object.fromEntries(
    shown.map((slice) => [
      slice.name,
      { label: slice.name, color: slice.color },
    ])
  ) satisfies ChartConfig
  return (
    <div className='grid min-w-0 grid-cols-1 items-center gap-4 @6xl/usage:grid-cols-2'>
      <div className='relative min-w-0'>
        <ChartContainer
          config={config}
          role='img'
          aria-label='Share of tokens by model'
          className='aspect-square w-full max-w-64 justify-self-center'
        >
          <PieChart accessibilityLayer>
            <ChartTooltip
              content={
                <ChartTooltipContent hideLabel valueFormatter={formatInteger} />
              }
            />
            <Pie
              data={shown}
              dataKey='total'
              nameKey='name'
              innerRadius='62%'
              outerRadius='92%'
              paddingAngle={2}
              strokeWidth={0}
            >
              {shown.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className='pointer-events-none absolute inset-0 flex flex-col items-center justify-center'>
          <Stat
            value={formatCompact(whole)}
            size='kpi'
            className='text-gilded font-display'
          />
          <Label>{agree(whole, 'token')}</Label>
        </div>
      </div>
      <ul
        className='flex min-w-0 flex-col gap-1.5'
        aria-label='Models by tokens'
      >
        {shown.map((slice) => (
          <li key={slice.name} className='flex min-w-0 flex-col gap-1'>
            <div className='flex min-w-0 items-center justify-between gap-2'>
              {slice.pickable ? (
                <Button
                  variant='link'
                  size='sm'
                  aria-label={`Filter to model ${slice.name}`}
                  onClick={() => onPick(slice.name)}
                >
                  <svg
                    aria-hidden='true'
                    viewBox='0 0 8 8'
                    className='size-icon-xs'
                  >
                    <circle cx='4' cy='4' r='4' fill={slice.color} />
                  </svg>
                  {slice.name}
                </Button>
              ) : (
                <Text as='span' variant='caption' tone='muted'>
                  {`${slice.name} (${rest.length})`}
                </Text>
              )}
              <Stat value={formatPercent(shareOf(slice.total, whole))} />
            </div>
            <Muted variant='caption'>
              {`${formatCompact(slice.total)} ${agree(slice.total, 'token')} · ${plural(slice.calls, 'call', 'calls')}`}
            </Muted>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function StepBars({
  steps,
  onPick,
}: {
  steps: UsageShare[]
  onPick: (step: string) => void
}) {
  const rows = steps.slice(0, BARS_SHOWN).map((step) => ({
    label: step.name,
    input: step.input_tokens,
    output: step.output_tokens,
  }))
  if (rows.length === 0)
    return <NoData>No matching step used any tokens.</NoData>
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ChartContainer
        config={TOKEN_CONFIG}
        role='img'
        aria-label='Tokens by step'
        className='aspect-auto h-72 w-full'
      >
        <BarChart data={rows} layout='vertical' accessibilityLayer>
          <CartesianGrid horizontal={false} strokeDasharray='2 5' />
          <XAxis
            type='number'
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => formatCompact(value)}
          />
          <YAxis
            type='category'
            dataKey='label'
            tickLine={false}
            axisLine={false}
            width={STEP_AXIS_WIDTH}
          />
          <ChartTooltip
            content={<ChartTooltipContent valueFormatter={formatInteger} />}
          />
          <Bar
            dataKey='input'
            stackId='tokens'
            fill='var(--color-input)'
            cursor='pointer'
            onClick={(_, index) => onPick(rows[index].label)}
          />
          <Bar
            dataKey='output'
            stackId='tokens'
            fill='var(--color-output)'
            radius={[0, 4, 4, 0]}
            cursor='pointer'
            onClick={(_, index) => onPick(rows[index].label)}
          />
        </BarChart>
      </ChartContainer>
      <Muted variant='caption'>
        {steps.length > BARS_SHOWN
          ? `The ${BARS_SHOWN} heaviest of ${plural(steps.length, 'step', 'steps')}. Click a bar to filter by it; the table below lists them all.`
          : 'Click a bar to filter by its step.'}
      </Muted>
    </div>
  )
}

function SplitRow({
  look,
  calls,
  tokens,
  whole,
}: {
  look: Look
  calls: number
  tokens: number
  whole: number
}) {
  const share = shareOf(tokens, whole)
  return (
    <li className='flex min-w-0 items-center gap-3'>
      <Medallion icon={look.icon} tone={look.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <div className='flex min-w-0 items-baseline justify-between gap-2'>
          <Text as='span' weight='medium' truncate>
            {look.label}
          </Text>
          <Stat value={formatPercent(share)} />
        </div>
        <Progress
          size='sm'
          value={share * PERCENT}
          aria-label={`${look.label}: share of tokens`}
        />
        <Muted variant='caption'>
          {`${formatCompact(tokens)} ${agree(tokens, 'token')} · ${plural(calls, 'call', 'calls')}`}
        </Muted>
      </div>
    </li>
  )
}

export function OutcomeSplit({ report }: { report: UsageReport }) {
  const whole = totalOf(report.totals)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-4 @md/usage:grid-cols-2'>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='gilded'>Call kinds</Label>
        <ul className='flex min-w-0 flex-col gap-3'>
          {llmCallKindValues.map((kind) => {
            const item = report.kinds.find((entry) => entry.kind === kind)
            return (
              <SplitRow
                key={kind}
                look={KIND_LOOK[kind]}
                calls={item?.calls ?? 0}
                tokens={item ? totalOf(item) : 0}
                whole={whole}
              />
            )
          })}
        </ul>
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='gilded'>Outcomes</Label>
        <ul className='flex min-w-0 flex-col gap-3'>
          {llmCallStatusValues.map((status) => {
            const item = report.statuses.find(
              (entry) => entry.status === status
            )
            return (
              <SplitRow
                key={status}
                look={STATUS_LOOK[status]}
                calls={item?.calls ?? 0}
                tokens={item ? totalOf(item) : 0}
                whole={whole}
              />
            )
          })}
        </ul>
      </div>
    </div>
  )
}
