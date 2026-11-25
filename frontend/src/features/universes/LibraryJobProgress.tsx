import { CircleAlert, CircleCheck, LoaderCircle } from 'lucide-react'
import { formatPercent } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Muted, Text } from '@/components/typography'
import { type LibraryJob } from './types'
import { JOB_STAGE_LABEL, JOB_STATUS_LABEL } from './universeLook'

const PERCENT = 100
const NOTES_SHOWN = 4

export function LibraryJobProgress({
  job,
  title,
}: {
  job: LibraryJob
  title: string
}) {
  const failed = job.status === 'failed' || job.status === 'cancelled'
  const done = job.status === 'done'
  const ratio = done ? 1 : Math.min(1, Math.max(0, job.progress))
  return (
    <div
      data-domain='library-job'
      data-status={job.status}
      role='status'
      aria-live='polite'
      className='flex min-w-0 flex-col gap-2 rounded-md surface-well p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Text as='span' weight='semibold' truncate>
          {title}
        </Text>
        <Badge
          variant={failed ? 'destructive' : done ? 'success' : 'default'}
          size='sm'
        >
          {failed ? (
            <CircleAlert aria-hidden='true' />
          ) : done ? (
            <CircleCheck aria-hidden='true' />
          ) : (
            <LoaderCircle
              aria-hidden='true'
              className='animate-spin motion-reduce:animate-none'
            />
          )}
          {JOB_STATUS_LABEL[job.status]}
        </Badge>
      </div>
      <Progress
        size='sm'
        tone={failed ? 'destructive' : done ? 'success' : 'default'}
        value={ratio * PERCENT}
        aria-label={`${title}: ${formatPercent(ratio)}`}
      />
      {job.notes.length > 0 && (
        <ul
          aria-label='Notes from the work'
          className='flex min-w-0 flex-col gap-0.5'
        >
          {job.notes.slice(-NOTES_SHOWN).map((note) => (
            <li key={note}>
              <Muted variant='caption'>{note}</Muted>
            </li>
          ))}
        </ul>
      )}
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted variant='caption'>
          {failed
            ? job.error || 'The work stopped without saying why.'
            : done || job.status === 'waiting'
              ? JOB_STATUS_LABEL[job.status]
              : JOB_STAGE_LABEL[job.stage]}
        </Muted>
        <Muted variant='caption'>{formatPercent(ratio)}</Muted>
      </div>
    </div>
  )
}
