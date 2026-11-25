import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  CloudDownload,
  DatabaseZap,
  Hourglass,
  type LucideIcon,
  SearchX,
} from 'lucide-react'
import { chunkSourceValues } from '@/api/generated/schema'
import { formatDateTime } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { useWillIndex } from './api'
import { type IndexStatus } from './types'

const PERCENT = 100

const STATUS_LOOK: Record<
  Exclude<IndexStatus, 'ready'>,
  { title: string; icon: LucideIcon; tone: string }
> = {
  fetching: {
    title: 'The Divine Will is fetching what it reads with',
    icon: CloudDownload,
    tone: 'text-info',
  },
  building: {
    title: 'The Divine Will is still reading the world',
    icon: DatabaseZap,
    tone: 'text-info',
  },
  waiting: {
    title: 'The Divine Will reads on once the epoch ends',
    icon: Hourglass,
    tone: 'text-warning',
  },
  unavailable: {
    title: 'Search by meaning is not available',
    icon: SearchX,
    tone: 'text-warning',
  },
}

export function IndexNotice() {
  const index = useWillIndex()
  const [open, setOpen] = useState(false)
  const data = index.data
  if (!data || data.status === 'ready') return null
  const look = STATUS_LOOK[data.status]
  const Icon = look.icon
  return (
    <div
      role='status'
      data-index-status={data.status}
      className='flex min-w-0 flex-col gap-1.5 rounded-md surface-well px-3 py-2'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Icon
          aria-hidden='true'
          className={cn('size-icon-sm shrink-0', look.tone)}
        />
        <Text
          as='span'
          variant='caption'
          weight='medium'
          className='min-w-0 flex-1'
        >
          {look.title}
        </Text>
        <Muted as='span' variant='caption'>
          {`${plural(data.embedded, 'passage')} of ${String(data.passages)} read`}
        </Muted>
      </div>
      <Progress
        size='sm'
        value={
          data.passages > 0 ? (data.embedded / data.passages) * PERCENT : 0
        }
        indeterminate={data.status === 'fetching'}
        aria-label='Reading the world'
      />
      <Muted variant='caption'>
        {[
          data.note,
          data.semantic
            ? 'It already answers; its searches grow sharper as it reads.'
            : 'It answers by searching words until it can search by meaning.',
          data.pending > 0 ? `${plural(data.pending, 'passage')} wait` : '',
        ]
          .filter(Boolean)
          .join(' ')}
      </Muted>
      <Button
        variant='ghost'
        size='sm'
        className='w-fit'
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown /> : <ChevronRight />}
        What it reads
      </Button>
      {open && (
        <div className='flex min-w-0 flex-col gap-1'>
          {data.sources.map((source) => (
            <div
              key={source.source}
              className='flex min-w-0 items-center gap-2'
            >
              <Text
                as='span'
                variant='caption'
                className='min-w-0 flex-1'
                truncate
              >
                {wordOf(chunkSourceValues, source.source)}
              </Text>
              <Muted as='span' variant='caption' className='tabular-nums'>
                {`${String(source.embedded)} / ${String(source.passages)}`}
              </Muted>
            </div>
          ))}
          <Muted variant='caption'>
            {[
              data.model ? `Read with ${data.model}` : '',
              data.built_at
                ? `last finished ${formatDateTime(data.built_at)}`
                : '',
            ]
              .filter(Boolean)
              .join(' · ')}
          </Muted>
        </div>
      )}
    </div>
  )
}
