import { useCallback, useMemo, useState } from 'react'
import { useLocation, useNavigate } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  ArrowDownToLine,
  ArrowDownWideNarrow,
  ArrowUpFromLine,
  ArrowUpNarrowWide,
  ChartArea,
  ChartPie,
  Coins,
  Cpu,
  Crown,
  FileDown,
  Flame,
  Gauge,
  ListTree,
  Logs,
  Maximize2,
  PhoneCall,
  RefreshCw,
  Repeat,
  RotateCcw,
  Ruler,
  Sigma,
  Timer,
  Trophy,
  TriangleAlert,
  Workflow,
} from 'lucide-react'
import { usageBucketValues, usageSortValues } from '@/api/generated/schema'
import { formatCompact, formatDateTime, formatPercent } from '@/lib/format'
import { agree, formatMilliseconds, plural } from '@/lib/units'
import { RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  HeroFrame,
  KpiTile,
  Medallion,
  MiniStat,
  PageHeader,
  RarityBadge,
  Section,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useRuleValue } from '@/features/world-rules/api'
import {
  ModelDonut,
  OutcomeSplit,
  StepBars,
  TokenTimeline,
} from './UsageCharts'
import { UsageFilters } from './UsageFilters'
import { BreakdownTable, CallLog } from './UsageTables'
import {
  type UsageBucket,
  type UsageFilter,
  type UsageOrder,
  type UsageReport,
  type UsageSort,
  usageExportUrl,
  useUsageCalls,
  useUsageSummary,
} from './api'
import {
  BREAKDOWNS,
  type UsageSearch,
  filterOf,
  orderOf,
  searchOfFilter,
  validateUsageSearch,
} from './usageSearch'
import {
  BUCKET_LABEL,
  type RangeKey,
  SORT_LABEL,
  pointLabel,
  rankOf,
  shareOf,
  totalOf,
} from './usageVisuals'

const ITEM = navItem('usage')
const RETENTION_RULE = 'metrics.keep_epochs'
const PERCENT = 100
const TEXT_SORTS: UsageSort[] = ['model', 'step']

const clockFormat = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  second: '2-digit',
})

function toggled(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value]
}

function isFiltered(search: UsageSearch): boolean {
  const chosen = Object.values(searchOfFilter(filterOf(search, 0)))
  return (
    chosen.some((value) => value !== undefined) ||
    (search.range ?? 'all') !== 'all'
  )
}

function RankHero({ report }: { report: UsageReport }) {
  const lifetime = report.facets.tokens
  const rank = rankOf(lifetime)
  const missing = rank.next ? rank.next.floor - lifetime : 0
  return (
    <HeroFrame>
      <div className='flex min-w-0 items-center gap-4'>
        <Medallion icon={Trophy} tone='gold' />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Label variant='overline'>Lifetime usage rank</Label>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <RarityBadge rarity={rank.current.rarity} />
            <Stat
              value={formatCompact(lifetime)}
              size='kpi'
              className='text-gilded font-display'
            />
            <Muted as='span'>
              {`${agree(lifetime, 'token')} over ${plural(report.facets.calls, 'call', 'calls')}`}
            </Muted>
          </div>
          <Progress
            size='sm'
            value={rank.progress * PERCENT}
            aria-label={
              rank.next
                ? `Progress to ${RARITY_LABEL[rank.next.rarity]}`
                : 'Highest rank reached'
            }
          />
          <Muted variant='caption'>
            {rank.next
              ? `${formatCompact(missing)} more ${agree(missing, 'token')} to ${RARITY_LABEL[rank.next.rarity]} at ${formatCompact(rank.next.floor)}.`
              : 'The highest rank is reached.'}
          </Muted>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant='outline' tabIndex={0}>
              <Ruler />
              {`Counted with ${report.tokenizer}`}
            </Badge>
          </TooltipTrigger>
          <TooltipContent className='max-w-xs'>
            Every call is counted on this server with the same tokenizer,
            whatever model or provider answered it. The counts are close
            estimates, not the provider&apos;s own figures.
          </TooltipContent>
        </Tooltip>
        <Muted as='span' variant='caption'>
          The rank counts every kept call; the filters below do not change it.
        </Muted>
      </div>
    </HeroFrame>
  )
}

function Headline({
  report,
  bucket,
}: {
  report: UsageReport
  bucket: UsageBucket
}) {
  const { totals, timeline } = report
  const total = totalOf(totals)
  const step = report.steps.at(0)
  const model = report.models.at(0)
  const latest = timeline.at(-1)
  const before = timeline.at(-2)
  const change =
    latest && before && totalOf(before) > 0
      ? totalOf(latest) / totalOf(before) - 1
      : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 @4xl/usage:grid-cols-4'>
        <KpiTile
          label='Total tokens'
          value={formatCompact(total)}
          icon={Sigma}
          tone='gold'
          hint={`${formatCompact(totals.input_tokens)} in and ${formatCompact(totals.output_tokens)} out`}
        />
        <KpiTile
          label='Tokens in'
          value={formatCompact(totals.input_tokens)}
          icon={ArrowDownToLine}
          tone='info'
          meter={{
            value: totals.input_tokens,
            max: total,
            label: 'Share of tokens sent in',
          }}
          hint={`${formatPercent(shareOf(totals.input_tokens, total))} of every token`}
        />
        <KpiTile
          label='Tokens out'
          value={formatCompact(totals.output_tokens)}
          icon={ArrowUpFromLine}
          tone='verdigris'
          meter={{
            value: totals.output_tokens,
            max: total,
            label: 'Share of tokens written out',
          }}
          hint={`${formatPercent(shareOf(totals.output_tokens, total))} of every token`}
        />
        <KpiTile
          label={latest ? `Latest · ${pointLabel(latest, bucket)}` : 'Latest'}
          value={latest ? formatCompact(totalOf(latest)) : '0'}
          icon={Flame}
          tone={change !== null && change > 0 ? 'warning' : 'success'}
          hint={
            change !== null && before
              ? `${formatPercent(Math.abs(change))} ${change >= 0 ? 'more' : 'fewer'} than ${pointLabel(before, bucket)}`
              : 'Nothing earlier to compare with.'
          }
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @4xl/usage:grid-cols-5'>
        <MiniStat
          icon={Crown}
          label='Heaviest step'
          value={step ? step.name : 'None'}
          tone='gold'
          hint={
            step
              ? `${formatCompact(totalOf(step))} ${agree(totalOf(step), 'token')}, ${formatPercent(shareOf(totalOf(step), total))} of the tokens in view`
              : undefined
          }
        />
        <MiniStat
          icon={Cpu}
          label='Busiest model'
          value={model ? model.name : 'None'}
          tone='info'
          hint={
            model
              ? `${formatCompact(totalOf(model))} ${agree(totalOf(model), 'token')} over ${plural(model.calls, 'call', 'calls')}`
              : undefined
          }
        />
        <MiniStat
          icon={PhoneCall}
          label='Calls'
          value={formatCompact(totals.calls)}
          tone='success'
          hint={
            totals.epochs > 0
              ? `Across ${plural(totals.epochs, 'epoch', 'epochs')}`
              : 'None ran inside an epoch'
          }
        />
        <MiniStat
          icon={Gauge}
          label='Median call'
          value={formatCompact(totals.median_call)}
          tone='gold'
          hint={`Half of the calls used fewer tokens. The average is ${formatCompact(total / Math.max(1, totals.calls))}.`}
        />
        <MiniStat
          icon={ChartArea}
          label='95th percentile'
          value={formatCompact(totals.p95_call)}
          tone='info'
          hint='Nineteen calls in twenty used fewer tokens than this.'
        />
        <MiniStat
          icon={Maximize2}
          label='Largest call'
          value={formatCompact(totals.largest_call)}
          tone='warning'
          hint='The most tokens one call used, in and out together.'
        />
        <MiniStat
          icon={Workflow}
          label='Agent turns'
          value={formatCompact(totals.turns)}
          tone='verdigris'
          hint='Model turns taken inside agent runs.'
        />
        <MiniStat
          icon={Timer}
          label='Time spent'
          value={formatMilliseconds(totals.milliseconds)}
          tone='muted'
        />
        <MiniStat
          icon={TriangleAlert}
          label='Failed calls'
          value={totals.errors}
          tone={totals.errors > 0 ? 'danger' : 'success'}
          hint={
            totals.partial > 0
              ? `${plural(totals.partial, 'agent run', 'agent runs')} also stopped before finishing.`
              : 'No agent run stopped before finishing.'
          }
        />
        <MiniStat
          icon={Repeat}
          label='Retried calls'
          value={totals.retried}
          tone={totals.retried > 0 ? 'warning' : 'success'}
          hint='Calls that needed more than one attempt.'
        />
      </div>
      <Muted variant='caption'>
        {totals.first_at && totals.last_at
          ? `Measured from ${formatDateTime(totals.first_at)} to ${formatDateTime(totals.last_at)}.`
          : 'No call in view.'}
      </Muted>
    </div>
  )
}

function SummarySkeleton() {
  return (
    <div className='flex min-w-0 flex-col gap-3' aria-busy='true'>
      <Skeleton className='h-40 w-full' />
      <div className='grid min-w-0 grid-cols-2 gap-3 @4xl/usage:grid-cols-4'>
        <Skeleton className='h-32 w-full' />
        <Skeleton className='h-32 w-full' />
        <Skeleton className='h-32 w-full' />
        <Skeleton className='h-32 w-full' />
      </div>
      <Skeleton className='h-72 w-full' />
    </div>
  )
}

export function UsageScreen() {
  const raw = useLocation({ select: (location) => location.search })
  const search = useMemo(
    () => validateUsageSearch(raw as Record<string, unknown>),
    [raw]
  )
  const navigate = useNavigate()
  const [now, setNow] = useState(() => Date.now())
  const filter = useMemo(() => filterOf(search, now), [search, now])
  const order = useMemo(() => orderOf(search), [search])
  const bucket: UsageBucket = search.bucket ?? 'epoch'
  const range: RangeKey = search.range ?? 'all'
  const breakdown = search.view ?? 'steps'
  const retention = useRuleValue(RETENTION_RULE)
  const summary = useUsageSummary(filter, bucket)
  const calls = useUsageCalls(filter, order)
  const update = useCallback(
    (patch: Partial<UsageSearch>) =>
      void navigate({
        search: (previous: Record<string, unknown>) => {
          const next: Record<string, unknown> = {
            ...previous,
            ...search,
            ...patch,
          }
          for (const key of Object.keys(next))
            if (next[key] === undefined) delete next[key]
          return next
        },
        replace: true,
      } as never),
    [navigate, search]
  )
  const setFilter = useCallback(
    (next: UsageFilter) =>
      update({ ...searchOfFilter(next), offset: undefined }),
    [update]
  )
  const setRange = (next: RangeKey) => {
    setNow(Date.now())
    update({ range: next === 'all' ? undefined : next, offset: undefined })
  }
  const pick = (field: 'models' | 'steps' | 'roles') => (value: string) =>
    setFilter({ ...filter, [field]: toggled(filter[field], value) })
  const setOrder = (next: UsageOrder) =>
    update({
      sort: next.sort === 'time' ? undefined : next.sort,
      asc: next.descending ? undefined : true,
      offset: next.offset || undefined,
    })
  const sortBy = (sort: UsageSort) =>
    setOrder({
      sort,
      descending:
        order.sort === sort ? !order.descending : !TEXT_SORTS.includes(sort),
      offset: 0,
    })
  const refreshing = summary.isFetching || calls.isFetching
  const refresh = () => {
    setNow(Date.now())
    void summary.refetch()
    void calls.refetch()
  }
  const report = summary.data
  const empty = report !== undefined && report.facets.calls === 0
  const updatedAt = Math.max(summary.dataUpdatedAt, calls.dataUpdatedAt)
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          <div className='flex min-w-0 items-center gap-2'>
            {updatedAt > 0 && (
              <Muted as='span' variant='caption' aria-live='polite'>
                {refreshing
                  ? 'Updating'
                  : `Updated ${clockFormat.format(updatedAt)}`}
              </Muted>
            )}
            <Button
              variant='outline'
              size='sm'
              disabled={refreshing}
              disabledReason='Counting the latest calls.'
              onClick={refresh}
            >
              <RefreshCw className={refreshing ? 'animate-spin' : undefined} />
              Refresh
            </Button>
          </div>
        }
      />
      <div className='@container/usage flex min-w-0 flex-col gap-6'>
        <Muted>
          {`Token counts of every language model call this server has made, across every world and provider. No prices, only tokens. The page updates by itself as turns, epochs and jobs finish.${retention !== null ? ` Calls of the last ${plural(retention, 'epoch', 'epochs')} ${agree(retention, 'is', 'are')} kept.` : ''}`}
        </Muted>
        {report && !empty && <RankHero report={report} />}
        <Section
          title='Filters'
          surface='card'
          level={3}
          icon={ListTree}
          tone='info'
        >
          <UsageFilters
            filter={filter}
            onChange={setFilter}
            range={range}
            onRange={setRange}
            facets={report?.facets}
            matching={report?.totals.calls}
          />
        </Section>
        {summary.isError && (
          <div
            role='alert'
            className='flex min-w-0 flex-wrap items-center gap-3'
          >
            <Text tone='destructive'>{summary.error.message}</Text>
            <Button
              variant='outline'
              size='sm'
              onClick={() => void summary.refetch()}
            >
              <RotateCcw />
              Try again
            </Button>
          </div>
        )}
        {summary.isPending && <SummarySkeleton />}
        {empty && (
          <EmptyState
            icon={Coins}
            title='No tokens spent yet'
            description='Every language model call is counted here once an epoch, genesis or deepening runs. Run an epoch and come back.'
          />
        )}
        {report && !empty && (
          <>
            <Headline report={report} bucket={bucket} />
            <Section
              title='Trend'
              description='Tokens in and out, stacked, for every matching call.'
              surface='card'
              level={3}
              icon={ChartArea}
              tone='gold'
              actions={
                <ToggleGroup
                  type='single'
                  variant='outline'
                  size='sm'
                  value={bucket}
                  onValueChange={(next) => {
                    const chosen = usageBucketValues.find(
                      (value) => value === next
                    )
                    if (chosen)
                      update({
                        bucket: chosen === 'epoch' ? undefined : chosen,
                      })
                  }}
                  aria-label='Group tokens over time'
                >
                  {usageBucketValues.map((value) => (
                    <ToggleGroupItem key={value} value={value}>
                      {BUCKET_LABEL[value]}
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
              }
            >
              <TokenTimeline timeline={report.timeline} bucket={bucket} />
            </Section>
            <div className='grid min-w-0 grid-cols-1 items-stretch gap-4 @4xl/usage:grid-cols-2'>
              <Section
                title='By model'
                description='Which models carried the tokens. Pick one to filter by it.'
                surface='card'
                level={3}
                icon={ChartPie}
                tone='verdigris'
              >
                <ModelDonut models={report.models} onPick={pick('models')} />
              </Section>
              <Section
                title='By step'
                description='Which steps of the game asked for the most tokens.'
                surface='card'
                level={3}
                icon={Workflow}
                tone='info'
              >
                <StepBars steps={report.steps} onPick={pick('steps')} />
              </Section>
              <div className='flex min-w-0 flex-col @4xl/usage:col-span-2'>
                <Section
                  title='Outcomes'
                  description='How tokens split between agent runs and structured answers, and how the calls ended.'
                  surface='card'
                  level={3}
                  icon={Gauge}
                  tone='success'
                >
                  <OutcomeSplit report={report} />
                </Section>
              </div>
            </div>
            <Section
              title='Breakdown'
              description='Every step, model and role with its tokens. Sort any column; pick a name to filter by it.'
              surface='card'
              level={3}
              icon={ListTree}
              tone='gold'
            >
              <Tabs
                value={breakdown}
                onValueChange={(next) => {
                  const chosen = BREAKDOWNS.find((item) => item === next)
                  update({ view: chosen === 'steps' ? undefined : chosen })
                }}
                className='flex min-w-0 flex-col gap-3'
              >
                <TabsList
                  aria-label='Break tokens down by'
                  className='w-full md:w-fit'
                >
                  <TabsTrigger value='steps'>
                    {`Steps ${report.steps.length}`}
                  </TabsTrigger>
                  <TabsTrigger value='models'>
                    {`Models ${report.models.length}`}
                  </TabsTrigger>
                  <TabsTrigger value='roles'>
                    {`Roles ${report.roles.length}`}
                  </TabsTrigger>
                </TabsList>
                <TabsContent value='steps'>
                  <BreakdownTable
                    shares={report.steps}
                    noun={['step', 'steps']}
                    onPick={pick('steps')}
                    picked={filter.steps}
                  />
                </TabsContent>
                <TabsContent value='models'>
                  <BreakdownTable
                    shares={report.models}
                    noun={['model', 'models']}
                    onPick={pick('models')}
                    picked={filter.models}
                  />
                </TabsContent>
                <TabsContent value='roles'>
                  <BreakdownTable
                    shares={report.roles}
                    noun={['role', 'roles']}
                    onPick={pick('roles')}
                    picked={filter.roles}
                  />
                </TabsContent>
              </Tabs>
            </Section>
          </>
        )}
        {!empty && (
          <Section
            title='Call log'
            description='Every matching call, one row each. Open a row for its attempts, turns, actions and error.'
            surface='card'
            level={3}
            icon={Logs}
            tone='muted'
            actions={
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Select
                  value={order.sort}
                  onValueChange={(next) =>
                    sortBy(
                      usageSortValues.find((value) => value === next) ?? 'time'
                    )
                  }
                >
                  <SelectTrigger
                    size='sm'
                    aria-label='Sort calls by'
                    className='w-40'
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {usageSortValues.map((value) => (
                      <SelectItem key={value} value={value}>
                        {SORT_LABEL[value]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant='outline'
                  size='icon-sm'
                  aria-label={
                    order.descending ? 'Sort ascending' : 'Sort descending'
                  }
                  onClick={() =>
                    setOrder({
                      ...order,
                      descending: !order.descending,
                      offset: 0,
                    })
                  }
                >
                  {order.descending ? (
                    <ArrowDownWideNarrow />
                  ) : (
                    <ArrowUpNarrowWide />
                  )}
                </Button>
                {(calls.data?.total ?? 0) > 0 ? (
                  <Button variant='outline' size='sm' asChild>
                    <a href={usageExportUrl(filter, order)} download>
                      <FileDown />
                      Export CSV
                    </a>
                  </Button>
                ) : (
                  <Button
                    variant='outline'
                    size='sm'
                    disabled
                    disabledReason='No call matches, so there is nothing to export.'
                  >
                    <FileDown />
                    Export CSV
                  </Button>
                )}
              </div>
            }
          >
            <CallLog
              page={calls.data}
              pending={calls.isPending}
              fetching={calls.isFetching}
              error={calls.error}
              onRetry={() => void calls.refetch()}
              sort={order.sort}
              descending={order.descending}
              onSort={sortBy}
              onOffset={(offset) => setOrder({ ...order, offset })}
              filtered={isFiltered(search)}
            />
          </Section>
        )}
      </div>
    </>
  )
}
