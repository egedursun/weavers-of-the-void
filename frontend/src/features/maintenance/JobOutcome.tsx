import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { NotebookPen, X } from 'lucide-react'
import { queryKeys } from '@/api/queryKeys'
import { fetchJob } from '@/api/system'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { JobProgress } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { JobItems } from '@/features/epoch/JobItems'
import { resultCounters, resultLedgerEntry } from './jobResult'

type JobOutcomeProps = {
  jobId: string
  title: string
  spent?: number
  onDismiss: () => void
}

const REFUNDED_STATUSES = new Set(['failed', 'cancelled', 'interrupted'])

export function JobOutcome({
  jobId,
  title,
  spent = 0,
  onDismiss,
}: JobOutcomeProps) {
  const job = useQuery({
    queryKey: queryKeys.jobs.detail(jobId),
    queryFn: () => fetchJob(jobId),
  })
  if (job.isPending) return <Skeleton className='h-control-lg w-full' />
  if (job.isError)
    return (
      <Text variant='caption' tone='destructive'>
        {job.error.message}
      </Text>
    )
  const counters =
    job.data.status === 'succeeded' ? resultCounters(job.data.result) : []
  const ledgerEntry = resultLedgerEntry(job.data.result)
  const refunded = spent > 0 && REFUNDED_STATUSES.has(job.data.status)
  return (
    <div
      data-job-outcome={jobId}
      className='flex min-w-0 flex-col gap-2 rounded-lg border p-3'
    >
      <JobProgress
        job={job.data}
        title={title}
        action={
          <Button
            className='self-start'
            variant='ghost'
            size='icon-sm'
            aria-label='Dismiss progress'
            onClick={onDismiss}
          >
            <X />
          </Button>
        }
      />
      {counters.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {counters.map((counter) => (
            <Badge key={counter.key} size='sm' variant='outline'>
              {`${counter.label} ${formatInteger(counter.value)}`}
            </Badge>
          ))}
        </div>
      )}
      <JobItems items={job.data.items} />
      {job.data.status === 'succeeded' &&
        counters.length === 0 &&
        job.data.items.length === 0 && (
          <Muted variant='caption'>Finished; nothing needed changing.</Muted>
        )}
      {refunded && (
        <Muted variant='caption'>
          {`The work did not finish, so your ${formatInteger(spent)} essence was returned.`}
        </Muted>
      )}
      {ledgerEntry !== null && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button variant='link' size='sm' asChild>
            <Link to='/ledger'>
              <NotebookPen />
              {`Ledger entry ${formatInteger(ledgerEntry)}: undo it there`}
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}
