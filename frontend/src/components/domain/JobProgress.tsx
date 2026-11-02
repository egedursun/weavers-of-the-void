import { type ReactNode } from 'react'
import { type components } from '@/api/generated/schema'
import {
  JOB_KIND_LABEL,
  JOB_STATUS_LABEL,
  type JobStatus,
  TERMINAL_JOB_STATUSES,
  isJobKind,
  isJobStatus,
} from '@/constants/jobs'
import { Badge } from '@/components/ui/badge'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import { Muted, Stat, Text } from '@/components/typography'

const PERCENT = 100

type Job = Pick<
  components['schemas']['JobResponse'],
  'kind' | 'status' | 'progress' | 'stage' | 'error'
>

const STATUS_BADGE: Record<
  JobStatus,
  'secondary' | 'default' | 'success' | 'destructive' | 'warning' | 'outline'
> = {
  queued: 'outline',
  running: 'default',
  succeeded: 'success',
  failed: 'destructive',
  cancelled: 'secondary',
  interrupted: 'warning',
}

const STATUS_TONE: Record<JobStatus, ProgressTone> = {
  queued: 'muted',
  running: 'default',
  succeeded: 'success',
  failed: 'destructive',
  cancelled: 'muted',
  interrupted: 'warning',
}

type JobProgressProps = {
  job: Job
  title?: string
  action?: ReactNode
}

export function JobProgress({ job, title, action }: JobProgressProps) {
  const status: JobStatus = isJobStatus(job.status) ? job.status : 'queued'
  const heading =
    title ?? (isJobKind(job.kind) ? JOB_KIND_LABEL[job.kind] : job.kind)
  const finished = TERMINAL_JOB_STATUSES.has(status)
  const indeterminate =
    status === 'queued' || (status === 'running' && job.progress <= 0)
  return (
    <div data-domain='job-progress' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Text as='span' weight='medium' truncate className='flex-1'>
          {heading}
        </Text>
        {!indeterminate && <Stat value={job.progress} format='percent' />}
        <Badge size='sm' variant={STATUS_BADGE[status]}>
          {JOB_STATUS_LABEL[status]}
        </Badge>
        {action}
      </div>
      <Progress
        value={job.progress * PERCENT}
        indeterminate={indeterminate && !finished}
        tone={STATUS_TONE[status]}
        aria-label={heading}
      />
      {job.stage && !job.error && (
        <Muted variant='caption' truncate>
          {job.stage}
        </Muted>
      )}
      {job.error && (
        <Text variant='caption' tone='destructive' truncate={2}>
          {job.error}
        </Text>
      )}
    </div>
  )
}
