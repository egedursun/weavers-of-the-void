import { type ReactNode, useState } from 'react'
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  ChevronDown,
  CircleDollarSign,
  Gauge,
  Hourglass,
  PhoneCall,
  Timer,
  TriangleAlert,
} from 'lucide-react'
import { formatCompact, formatDecimal } from '@/lib/format'
import { formatDuration, formatMilliseconds, formatUsd } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { EmptyState, MiniStat, PagedList, Section } from '@/components/domain'
import { Muted, Stat, Text } from '@/components/typography'
import { useEpochTiming } from '@/features/epoch/useEpochTiming'
import { type LlmCall, type ModelMetricsView, useModelMetrics } from './api'

const WINDOWS = [5, 10, 25, 50]
const PERCENT = 100
const DEFAULT_WINDOW = 'default'

function Chip({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  const chip = (
    <Badge variant='outline' tabIndex={hint ? 0 : undefined}>
      {`${value} ${label}`}
    </Badge>
  )
  if (!hint) return chip
  return (
    <Tooltip>
      <TooltipTrigger asChild>{chip}</TooltipTrigger>
      <TooltipContent className='max-w-xs'>{hint}</TooltipContent>
    </Tooltip>
  )
}

function Folder({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Collapsible>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='w-fit'>
          <ChevronDown />
          {title}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='pt-2'>{children}</CollapsibleContent>
    </Collapsible>
  )
}

function CallList({
  calls,
  tone,
}: {
  calls: LlmCall[]
  tone: 'warning' | 'destructive'
}) {
  return (
    <ul className='flex min-w-0 flex-col gap-1'>
      {calls.map((call) => (
        <li
          key={call.id}
          className='flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-0.5'
        >
          <Muted as='span' variant='caption'>
            {call.epoch !== null ? `Epoch ${call.epoch}` : 'Outside epochs'}
          </Muted>
          <Text
            as='span'
            variant='caption'
            weight='medium'
            truncate
            className='min-w-0 flex-1'
          >
            {call.role ? `${call.job} · ${call.role}` : call.job}
          </Text>
          <Text as='span' variant='caption' tone={tone}>
            {tone === 'destructive'
              ? (call.error ?? 'Failed')
              : `${formatMilliseconds(call.duration_ms)}${call.cost_usd > 0 ? ` · $${formatDecimal(call.cost_usd, 4)}` : ''}`}
          </Text>
        </li>
      ))}
    </ul>
  )
}

function MetricsBody({ data }: { data: ModelMetricsView }) {
  const { totals } = data
  const busiest = Math.max(1, ...data.epochs.map((epoch) => epoch.calls))
  if (totals.calls === 0)
    return (
      <EmptyState
        size='compact'
        icon={Gauge}
        title='No calls measured yet'
        description='Language model calls appear here once an epoch, genesis or deepening has run.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6'>
        <MiniStat
          icon={PhoneCall}
          label='Calls'
          value={formatCompact(totals.calls)}
          tone='gold'
        />
        <MiniStat
          icon={Timer}
          label='Time spent'
          value={formatMilliseconds(totals.milliseconds)}
          tone='info'
        />
        <MiniStat
          icon={ArrowDownToLine}
          label='Tokens in'
          value={formatCompact(totals.input_tokens)}
          tone='verdigris'
        />
        <MiniStat
          icon={ArrowUpFromLine}
          label='Tokens out'
          value={formatCompact(totals.output_tokens)}
          tone='verdigris'
        />
        <MiniStat
          icon={CircleDollarSign}
          label='API equivalent'
          value={formatUsd(totals.cost)}
          tone='muted'
          hint='What these calls would cost at API prices. The subscription does not charge it separately; it counts against the quota.'
        />
        <MiniStat
          icon={TriangleAlert}
          label='Errors'
          value={data.epochs.reduce((sum, epoch) => sum + epoch.errors, 0)}
          tone={
            data.epochs.some((epoch) => epoch.errors > 0) ? 'danger' : 'success'
          }
        />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Epoch</TableHead>
            <TableHead className='text-end'>Calls</TableHead>
            <TableHead className='text-end'>Time</TableHead>
            <TableHead className='text-end'>Tokens in / out</TableHead>
            <TableHead className='text-end'>Cost</TableHead>
            <TableHead className='text-end'>Errors</TableHead>
            <TableHead className='text-end'>Slow</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.epochs.map((epoch) => (
            <TableRow key={epoch.epoch}>
              <TableCell>{`Epoch ${epoch.epoch}`}</TableCell>
              <TableCell className='text-end'>
                <div className='flex min-w-0 items-center justify-end gap-2'>
                  <Progress
                    size='sm'
                    className='w-16'
                    value={(epoch.calls / busiest) * PERCENT}
                    aria-label={`Calls in epoch ${epoch.epoch}`}
                  />
                  <Stat value={epoch.calls} />
                </div>
              </TableCell>
              <TableCell className='text-end'>
                {formatMilliseconds(epoch.milliseconds)}
              </TableCell>
              <TableCell className='text-end'>
                {`${formatCompact(epoch.input_tokens)} / ${formatCompact(epoch.output_tokens)}`}
              </TableCell>
              <TableCell className='text-end'>
                {formatUsd(epoch.cost)}
              </TableCell>
              <TableCell className='text-end'>
                <Stat
                  value={
                    epoch.retried > 0
                      ? `${epoch.errors} · ${epoch.retried} retried`
                      : epoch.errors
                  }
                  tone={epoch.errors > 0 ? 'destructive' : 'inherit'}
                />
              </TableCell>
              <TableCell className='text-end'>
                <Stat
                  value={epoch.slow}
                  tone={epoch.slow > 0 ? 'warning' : 'inherit'}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <PagedList
        items={data.models}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-2'
        itemKey={(model) => model.model}
      >
        {(model) => (
          <Chip
            key={model.model}
            label={`· ${model.calls} calls · average ${formatMilliseconds(model.average_ms)}`}
            value={model.model}
          />
        )}
      </PagedList>
      <Folder title={`By step (${data.steps.length})`}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Step</TableHead>
              <TableHead className='text-end'>Calls</TableHead>
              <TableHead className='text-end'>Average</TableHead>
              <TableHead className='text-end'>Longest</TableHead>
              <TableHead className='text-end'>Cost</TableHead>
              <TableHead className='text-end'>Errors</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.steps.map((step) => (
              <TableRow key={step.step}>
                <TableCell>{step.step}</TableCell>
                <TableCell className='text-end'>
                  <Stat value={step.calls} />
                </TableCell>
                <TableCell className='text-end'>
                  {formatMilliseconds(step.average_ms)}
                </TableCell>
                <TableCell className='text-end'>
                  {formatMilliseconds(step.longest_ms)}
                </TableCell>
                <TableCell className='text-end'>
                  {formatUsd(step.cost)}
                </TableCell>
                <TableCell className='text-end'>
                  <Stat
                    value={step.errors}
                    tone={step.errors > 0 ? 'destructive' : 'inherit'}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Folder>
      {data.slowest.length > 0 && (
        <Folder title={`Slow calls (${data.slowest.length})`}>
          <CallList calls={data.slowest} tone='warning' />
        </Folder>
      )}
      {data.latest_errors.length > 0 && (
        <Folder title={`Recent errors (${data.latest_errors.length})`}>
          <CallList calls={data.latest_errors} tone='destructive' />
        </Folder>
      )}
      <Muted variant='caption'>
        {`Calls over ${formatMilliseconds(data.slow_threshold_ms)} count as slow.`}
      </Muted>
    </div>
  )
}

function EpochEta() {
  const timing = useEpochTiming(false)
  const running = timing.active && timing.remainingSeconds !== null
  return (
    <MiniStat
      icon={Hourglass}
      label={running ? 'Left in the running epoch' : 'An epoch takes'}
      value={
        running && timing.remainingSeconds !== null
          ? formatDuration(timing.remainingSeconds)
          : timing.averageSeconds !== null
            ? formatDuration(timing.averageSeconds)
            : 'Not measured yet'
      }
      tone={running ? 'gold' : 'info'}
      hint={
        timing.averageSeconds !== null
          ? `Average of ${timing.samples} epochs`
          : undefined
      }
    />
  )
}

export function ModelMetrics() {
  const [windowSize, setWindowSize] = useState<string>(DEFAULT_WINDOW)
  const metrics = useModelMetrics(
    windowSize === DEFAULT_WINDOW ? null : Number(windowSize)
  )
  return (
    <Section
      title='Model metrics'
      description='Every language model call: how many, how long, how many tokens, what it would cost, and what failed.'
      surface='card'
      level={3}
      icon={Gauge}
      tone='info'
      actions={
        <Select value={windowSize} onValueChange={setWindowSize}>
          <SelectTrigger size='sm' aria-label='Epoch window' className='w-40'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={DEFAULT_WINDOW}>Default window</SelectItem>
            {WINDOWS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {`Last ${size} epochs`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
    >
      <EpochEta />
      {metrics.isPending && <Skeleton className='h-48 w-full' />}
      {metrics.isError && (
        <Text tone='destructive'>{metrics.error.message}</Text>
      )}
      {metrics.data && <MetricsBody data={metrics.data} />}
    </Section>
  )
}
