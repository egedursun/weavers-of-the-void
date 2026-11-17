import { Fragment, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronDown,
  ChevronRight,
  ListX,
  RotateCcw,
} from 'lucide-react'
import { formatCompact, formatInteger, formatPercent } from '@/lib/format'
import { formatMilliseconds } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
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
  EmptyState,
  KeyValueList,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Muted, Stat, Text } from '@/components/typography'
import {
  type UsageCall,
  type UsageCallPage,
  type UsageShare,
  type UsageSort,
} from './api'
import {
  KIND_LOOK,
  SORT_LABEL,
  STATUS_BADGE,
  STATUS_LOOK,
  shareOf,
  totalOf,
} from './usageVisuals'

const PERCENT = 100
const BREAKDOWN_SHOWN = 10
const LOG_COLUMNS = 11
const SKELETON_ROWS = 6

const timeFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  second: '2-digit',
})

type Direction = { descending: boolean }

function SortHead<K extends string>({
  label,
  column,
  sort,
  descending,
  onSort,
  end = false,
}: {
  label: string
  column: K
  sort: K
  descending: boolean
  onSort: (column: K) => void
  end?: boolean
}) {
  const active = sort === column
  const Icon = !active ? ArrowUpDown : descending ? ArrowDown : ArrowUp
  return (
    <TableHead
      aria-sort={active ? (descending ? 'descending' : 'ascending') : 'none'}
      className={end ? 'text-end' : undefined}
    >
      <Button
        variant='ghost'
        size='sm'
        aria-label={`Sort by ${label.toLowerCase()}`}
        onClick={() => onSort(column)}
      >
        {label}
        <Icon />
      </Button>
    </TableHead>
  )
}

type BreakdownSort =
  | 'name'
  | 'calls'
  | 'input'
  | 'output'
  | 'total'
  | 'average'
  | 'errors'
  | 'time'

const BREAKDOWN_VALUE: Record<
  Exclude<BreakdownSort, 'name'>,
  (share: UsageShare) => number
> = {
  calls: (share) => share.calls,
  input: (share) => share.input_tokens,
  output: (share) => share.output_tokens,
  total: totalOf,
  average: (share) => totalOf(share) / Math.max(1, share.calls),
  errors: (share) => share.errors,
  time: (share) => share.milliseconds,
}

function sortShares(
  shares: UsageShare[],
  sort: BreakdownSort,
  { descending }: Direction
): UsageShare[] {
  const sign = descending ? -1 : 1
  return [...shares].sort((left, right) => {
    const order =
      sort === 'name'
        ? left.name.localeCompare(right.name)
        : BREAKDOWN_VALUE[sort](left) - BREAKDOWN_VALUE[sort](right)
    return order === 0 ? left.name.localeCompare(right.name) : order * sign
  })
}

export function BreakdownTable({
  shares,
  noun,
  onPick,
  picked,
}: {
  shares: UsageShare[]
  noun: [string, string]
  onPick: (name: string) => void
  picked: string[]
}) {
  const [sort, setSort] = useState<BreakdownSort>('total')
  const [descending, setDescending] = useState(true)
  const sorted = useMemo(
    () => sortShares(shares, sort, { descending }),
    [shares, sort, descending]
  )
  const page = useShowMore(sorted, BREAKDOWN_SHOWN)
  const whole = shares.reduce((sum, share) => sum + totalOf(share), 0)
  const choose = (column: BreakdownSort) => {
    setDescending(column === sort ? !descending : column !== 'name')
    setSort(column)
  }
  if (shares.length === 0)
    return (
      <EmptyState
        size='compact'
        icon={ListX}
        title={`No ${noun[1]} match`}
        description='Loosen the filters to see this breakdown.'
      />
    )
  const head = (label: string, column: BreakdownSort, end = true) => (
    <SortHead
      label={label}
      column={column}
      sort={sort}
      descending={descending}
      onSort={choose}
      end={end}
    />
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Table>
        <TableHeader>
          <TableRow>
            {head(
              noun[0].charAt(0).toUpperCase() + noun[0].slice(1),
              'name',
              false
            )}
            {head('Calls', 'calls')}
            {head('Tokens in', 'input')}
            {head('Tokens out', 'output')}
            {head('Total', 'total')}
            <TableHead className='min-w-32'>Share</TableHead>
            {head('Per call', 'average')}
            {head('Failures', 'errors')}
            {head('Time', 'time')}
          </TableRow>
        </TableHeader>
        <TableBody>
          {page.visible.map((share) => {
            const portion = shareOf(totalOf(share), whole)
            const active = picked.includes(share.name)
            return (
              <TableRow
                key={share.name}
                data-state={active ? 'selected' : undefined}
              >
                <TableCell className='min-w-48'>
                  <Button
                    variant='link'
                    size='sm'
                    aria-pressed={active}
                    aria-label={`${active ? 'Remove the filter on' : 'Filter by'} ${noun[0]} ${share.name}`}
                    onClick={() => onPick(share.name)}
                  >
                    <Text as='span' truncate>
                      {share.name}
                    </Text>
                  </Button>
                </TableCell>
                <TableCell className='text-end'>
                  <Stat value={formatInteger(share.calls)} />
                </TableCell>
                <TableCell className='text-end'>
                  {formatInteger(share.input_tokens)}
                </TableCell>
                <TableCell className='text-end'>
                  {formatInteger(share.output_tokens)}
                </TableCell>
                <TableCell className='text-end'>
                  <Stat value={formatInteger(totalOf(share))} />
                </TableCell>
                <TableCell>
                  <div className='flex min-w-0 items-center gap-2'>
                    <Progress
                      size='sm'
                      className='w-16'
                      value={portion * PERCENT}
                      aria-label={`${share.name}: share of tokens`}
                    />
                    <Muted as='span' variant='caption'>
                      {formatPercent(portion)}
                    </Muted>
                  </div>
                </TableCell>
                <TableCell className='text-end'>
                  {formatCompact(totalOf(share) / Math.max(1, share.calls))}
                </TableCell>
                <TableCell className='text-end'>
                  <Stat
                    value={share.errors}
                    tone={share.errors > 0 ? 'destructive' : 'inherit'}
                  />
                </TableCell>
                <TableCell className='text-end'>
                  {formatMilliseconds(share.milliseconds)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      <ShowMore state={page} noun={noun} />
    </div>
  )
}

function CallDetail({ call }: { call: UsageCall }) {
  return (
    <KeyValueList
      items={[
        { label: 'Call', value: `Call ${formatInteger(call.id)}` },
        { label: 'Role', value: call.role ?? 'No role' },
        { label: 'Attempts', value: formatInteger(call.attempts) },
        {
          label: 'Agent turns',
          value:
            call.turns === null ? 'Single answer' : formatInteger(call.turns),
        },
        {
          label: 'Actions taken',
          value:
            call.actions === null
              ? 'None recorded'
              : formatInteger(call.actions),
        },
        {
          label: 'Tokens per second',
          value:
            call.duration_ms > 0
              ? formatCompact(call.output_tokens / (call.duration_ms / 1000))
              : 'Not measured',
        },
        { label: 'Error', value: call.error ?? 'No error' },
      ]}
    />
  )
}

function CallRow({ call }: { call: UsageCall }) {
  const [open, setOpen] = useState(false)
  const kind = KIND_LOOK[call.kind]
  const status = STATUS_LOOK[call.status]
  return (
    <Fragment>
      <TableRow data-state={open ? 'selected' : undefined}>
        <TableCell>
          <Button
            variant='ghost'
            size='icon-sm'
            aria-expanded={open}
            aria-label={`${open ? 'Hide' : 'Show'} details of call ${call.id}`}
            onClick={() => setOpen(!open)}
          >
            {open ? <ChevronDown /> : <ChevronRight />}
          </Button>
        </TableCell>
        <TableCell className='whitespace-nowrap'>
          <Muted as='span' variant='caption'>
            {timeFormat.format(new Date(call.created_at))}
          </Muted>
        </TableCell>
        <TableCell className='text-end'>
          {call.epoch === null ? (
            <Muted as='span' variant='caption'>
              Outside
            </Muted>
          ) : (
            formatInteger(call.epoch)
          )}
        </TableCell>
        <TableCell className='max-w-0 min-w-44'>
          <Text as='span' weight='medium' truncate>
            {call.job}
          </Text>
        </TableCell>
        <TableCell>
          <Badge size='sm' variant='outline'>
            {call.model}
          </Badge>
        </TableCell>
        <TableCell>
          <Badge size='sm' variant='secondary'>
            <kind.icon />
            {kind.label}
          </Badge>
        </TableCell>
        <TableCell>
          <Badge size='sm' variant={STATUS_BADGE[call.status]}>
            <status.icon />
            {status.label}
          </Badge>
        </TableCell>
        <TableCell className='text-end'>
          {formatInteger(call.input_tokens)}
        </TableCell>
        <TableCell className='text-end'>
          {formatInteger(call.output_tokens)}
        </TableCell>
        <TableCell className='text-end'>
          <Stat value={formatInteger(totalOf(call))} />
        </TableCell>
        <TableCell className='text-end whitespace-nowrap'>
          {formatMilliseconds(call.duration_ms)}
        </TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={LOG_COLUMNS}>
            <CallDetail call={call} />
          </TableCell>
        </TableRow>
      )}
    </Fragment>
  )
}

type CallLogProps = {
  page: UsageCallPage | undefined
  pending: boolean
  fetching: boolean
  error: Error | null
  onRetry: () => void
  sort: UsageSort
  descending: boolean
  onSort: (sort: UsageSort) => void
  onOffset: (offset: number) => void
  filtered: boolean
}

export function CallLog({
  page,
  pending,
  fetching,
  error,
  onRetry,
  sort,
  descending,
  onSort,
  onOffset,
  filtered,
}: CallLogProps) {
  if (error)
    return (
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Text tone='destructive'>{error.message}</Text>
        <Button variant='outline' size='sm' onClick={onRetry}>
          <RotateCcw />
          Try again
        </Button>
      </div>
    )
  if (pending || !page)
    return (
      <div className='flex min-w-0 flex-col gap-2' aria-busy='true'>
        {Array.from({ length: SKELETON_ROWS }, (_, row) => (
          <Skeleton key={row} className='h-9 w-full' />
        ))}
      </div>
    )
  if (page.total === 0)
    return (
      <EmptyState
        size='compact'
        icon={ListX}
        title={filtered ? 'No call matches' : 'No calls logged yet'}
        description={
          filtered
            ? 'Change the search or clear a filter to see more calls.'
            : 'Every language model call is logged here once an epoch, genesis or deepening runs.'
        }
      />
    )
  const head = (column: UsageSort, end = false) => (
    <SortHead
      label={SORT_LABEL[column]}
      column={column}
      sort={sort}
      descending={descending}
      onSort={onSort}
      end={end}
    />
  )
  return (
    <div className='flex min-w-0 flex-col gap-3' aria-busy={fetching}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>
              <Muted as='span' variant='caption'>
                Details
              </Muted>
            </TableHead>
            {head('time')}
            {head('epoch', true)}
            {head('step')}
            {head('model')}
            <TableHead>Call kind</TableHead>
            <TableHead>Outcome</TableHead>
            {head('input_tokens', true)}
            {head('output_tokens', true)}
            {head('total_tokens', true)}
            {head('duration', true)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {page.items.map((call) => (
            <CallRow key={call.id} call={call} />
          ))}
        </TableBody>
      </Table>
      <PageControls
        offset={page.offset}
        limit={page.limit}
        total={page.total}
        onChange={onOffset}
        label='Call log pages'
        busy={fetching}
      />
    </div>
  )
}
