import { useCallback, useState } from 'react'
import { navItem } from '@/config/navigation'
import {
  ArrowDownToLine,
  ArrowDownWideNarrow,
  ArrowUpFromLine,
  ArrowUpNarrowWide,
  CalendarClock,
  ChartArea,
  ChartPie,
  Coins,
  Gauge,
  ListTree,
  Logs,
  Maximize2,
  PhoneCall,
  RefreshCw,
  Repeat,
  RotateCcw,
  ScissorsLineDashed,
  Sigma,
  Timer,
  TriangleAlert,
  Workflow,
} from 'lucide-react'
import { usageBucketValues, usageSortValues } from '@/api/generated/schema'
import { formatCompact, formatDateTime, formatPercent } from '@/lib/format'
import { agree, formatMilliseconds, plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
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
  EmptyState,
  KpiTile,
  MiniStat,
  PageHeader,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
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
  EMPTY_FILTER,
  type UsageBucket,
  type UsageFilter,
  type UsageOrder,
  type UsageReport,
  type UsageSort,
  useUsageCalls,
  useUsageSummary,
} from './api'
import {
  BUCKET_LABEL,
  RANGES,
  type RangeKey,
  SORT_LABEL,
  shareOf,
  totalOf,
} from './usageVisuals'

const ITEM = navItem('usage')
const RETENTION_RULE = 'metrics.keep_epochs'
const HOUR_MS = 3_600_000
const BREAKDOWNS = ['steps', 'models', 'roles'] as const
type Breakdown = (typeof BREAKDOWNS)[number]
const FIRST_PAGE: UsageOrder = { sort: 'time', descending: true, offset: 0 }
const TEXT_SORTS: UsageSort[] = ['model', 'step']

function toggled(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value]
}

function isFiltered(filter: UsageFilter): boolean {
  return (
    filter.search.trim() !== '' ||
    filter.models.length > 0 ||
    filter.roles.length > 0 ||
    filter.steps.length > 0 ||
    filter.kinds.length > 0 ||
    filter.statuses.length > 0 ||
    filter.epochFrom !== null ||
    filter.epochTo !== null ||
    filter.since !== null
  )
}

function Headline({ report }: { report: UsageReport }) {
  const { totals } = report
  const total = totalOf(totals)
  const average = total / Math.max(1, totals.calls)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/usage:grid-cols-2 @4xl/usage:grid-cols-4'>
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
          hint={`${formatPercent(shareOf(totals.input_tokens, total))} of every token, cache reads included`}
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
          label='Calls'
          value={formatCompact(totals.calls)}
          icon={PhoneCall}
          tone='success'
          hint={
            totals.epochs > 0
              ? `Across ${plural(totals.epochs, 'epoch', 'epochs')}`
              : 'None ran inside an epoch'
          }
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/usage:grid-cols-2 @4xl/usage:grid-cols-4'>
        <MiniStat
          icon={Gauge}
          label='Tokens per call'
          value={formatCompact(average)}
          tone='gold'
        />
        <MiniStat
          icon={Maximize2}
          label='Largest call'
          value={formatCompact(totals.largest_call)}
          tone='info'
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
        />
        <MiniStat
          icon={ScissorsLineDashed}
          label='Cut short'
          value={totals.partial}
          tone={totals.partial > 0 ? 'warning' : 'success'}
          hint='Agent runs that stopped before they finished.'
        />
        <MiniStat
          icon={Repeat}
          label='Retried calls'
          value={totals.retried}
          tone={totals.retried > 0 ? 'warning' : 'success'}
          hint='Calls that needed more than one attempt.'
        />
        <MiniStat
          icon={CalendarClock}
          label='Measured span'
          value={
            totals.first_at && totals.last_at
              ? `${formatDateTime(totals.first_at)} – ${formatDateTime(totals.last_at)}`
              : 'No calls'
          }
          tone='muted'
        />
      </div>
    </div>
  )
}

function SummarySkeleton() {
  return (
    <div className='flex min-w-0 flex-col gap-3' aria-busy='true'>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/usage:grid-cols-2 @4xl/usage:grid-cols-4'>
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
  const [filter, setFilterState] = useState<UsageFilter>(EMPTY_FILTER)
  const [range, setRangeState] = useState<RangeKey>('all')
  const [bucket, setBucket] = useState<UsageBucket>('epoch')
  const [order, setOrder] = useState<UsageOrder>(FIRST_PAGE)
  const [breakdown, setBreakdown] = useState<Breakdown>('steps')
  const retention = useRuleValue(RETENTION_RULE)
  const summary = useUsageSummary(filter, bucket)
  const calls = useUsageCalls(filter, order)
  const setFilter = useCallback((next: UsageFilter) => {
    setFilterState(next)
    setOrder((current) => ({ ...current, offset: 0 }))
  }, [])
  const setRange = (next: RangeKey) => {
    const hours = RANGES.find((item) => item.key === next)?.hours ?? null
    setRangeState(next)
    setFilter({
      ...filter,
      since:
        hours === null
          ? null
          : new Date(Date.now() - hours * HOUR_MS).toISOString(),
    })
  }
  const pick = (field: 'models' | 'steps' | 'roles') => (value: string) =>
    setFilter({ ...filter, [field]: toggled(filter[field], value) })
  const sortBy = (sort: UsageSort) =>
    setOrder((current) => ({
      sort,
      descending:
        current.sort === sort
          ? !current.descending
          : !TEXT_SORTS.includes(sort),
      offset: 0,
    }))
  const refreshing = summary.isFetching || calls.isFetching
  const refresh = () => {
    void summary.refetch()
    void calls.refetch()
  }
  const report = summary.data
  const empty = report !== undefined && report.facets.calls === 0
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
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
        }
      />
      <div className='@container/usage flex min-w-0 flex-col gap-6'>
        <Muted>
          {`Token counts of every language model call this server has made, across every world. No prices are shown here, only tokens.${retention !== null ? ` Calls of the last ${plural(retention, 'epoch', 'epochs')} ${agree(retention, 'is', 'are')} kept.` : ''}`}
        </Muted>
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
          <div className='flex min-w-0 flex-wrap items-center gap-3'>
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
            <Headline report={report} />
            <Section
              title='Token trend'
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
                  onValueChange={(next) =>
                    setBucket(
                      usageBucketValues.find((value) => value === next) ??
                        bucket
                    )
                  }
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
                  title='Call kinds and outcomes'
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
                onValueChange={(next) =>
                  setBreakdown(
                    BREAKDOWNS.find((item) => item === next) ?? 'steps'
                  )
                }
                className='flex min-w-0 flex-col gap-3'
              >
                <TabsList
                  aria-label='Break tokens down by'
                  className='w-full md:w-fit'
                >
                  <TabsTrigger value='steps'>{`Steps ${report.steps.length}`}</TabsTrigger>
                  <TabsTrigger value='models'>{`Models ${report.models.length}`}</TabsTrigger>
                  <TabsTrigger value='roles'>{`Roles ${report.roles.length}`}</TabsTrigger>
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
              <div className='flex min-w-0 items-center gap-2'>
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
                    setOrder((current) => ({
                      ...current,
                      descending: !current.descending,
                      offset: 0,
                    }))
                  }
                >
                  {order.descending ? (
                    <ArrowDownWideNarrow />
                  ) : (
                    <ArrowUpNarrowWide />
                  )}
                </Button>
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
              onOffset={(offset) =>
                setOrder((current) => ({ ...current, offset }))
              }
              filtered={isFiltered(filter)}
            />
          </Section>
        )}
      </div>
    </>
  )
}
