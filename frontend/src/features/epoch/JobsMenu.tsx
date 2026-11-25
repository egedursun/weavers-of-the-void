import { Link } from '@tanstack/react-router'
import { ArrowRight, ListChecks, LoaderCircle, X } from 'lucide-react'
import { toast } from 'sonner'
import { formatDuration, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import {
  JOB_KIND_LABEL,
  JOB_STATUS_LABEL,
  type JobStatus,
  TERMINAL_JOB_STATUSES,
  isJobKind,
  isJobStatus,
} from '@/constants/jobs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { EmptyState, Medallion } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { JobItems } from './JobItems'
import { type Job, useCancelJob, useRecentJobs } from './api'
import { JOB_KIND_ICON, JOB_STATUS_TONE } from './jobVisuals'
import { useNow } from './useNow'

const PERCENT = 100
const MS_PER_SECOND = 1000

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

const BAR_TONE = {
  queued: 'muted',
  running: 'default',
  succeeded: 'success',
  failed: 'destructive',
  cancelled: 'muted',
  interrupted: 'warning',
} as const

function statusOf(job: Job): JobStatus {
  return isJobStatus(job.status) ? job.status : 'queued'
}

function isActive(job: Job): boolean {
  return !TERMINAL_JOB_STATUSES.has(statusOf(job))
}

function seconds(from: string, to: number): number {
  return Math.max(0, (to - new Date(from).getTime()) / MS_PER_SECOND)
}

function timing(job: Job, now: number): string {
  const status = statusOf(job)
  if (status === 'queued')
    return `Waiting ${formatDuration(seconds(job.created_at, now))}`
  if (!job.started_at) return JOB_STATUS_LABEL[status]
  if (!job.finished_at)
    return `Running ${formatDuration(seconds(job.started_at, now))}`
  const took = formatDuration(
    seconds(job.started_at, new Date(job.finished_at).getTime())
  )
  const ago = formatDuration(seconds(job.finished_at, now))
  return `Took ${took} · ${ago} ago`
}

function CancelButton({ job }: { job: Job }) {
  const cancel = useCancelJob()
  return (
    <Button
      act={cancel}
      variant='ghost'
      size='icon-sm'
      aria-label='Cancel this job'
      disabled={cancel.isPending}
      disabledReason='Cancelling'
      onClick={() =>
        cancel.mutate(job.id, {
          onSuccess: () => toast.success('Cancellation requested'),
          onError: (error) => toast.error(error.message),
        })
      }
    >
      <X />
    </Button>
  )
}

function JobCard({ job, now }: { job: Job; now: number }) {
  const status = statusOf(job)
  const active = isActive(job)
  const kindLabel = isJobKind(job.kind) ? JOB_KIND_LABEL[job.kind] : job.kind
  const title = job.label
    ? job.label.charAt(0).toUpperCase() + job.label.slice(1)
    : kindLabel
  const icon = isJobKind(job.kind) ? JOB_KIND_ICON[job.kind] : ListChecks
  const indeterminate =
    status === 'queued' || (status === 'running' && job.progress <= 0)
  return (
    <div
      data-job-card={status}
      className={cn(
        'flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        active ? 'border-primary/30 bg-primary/5' : 'bg-card'
      )}
    >
      <Medallion icon={icon} tone={JOB_STATUS_TONE[status]} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center gap-2'>
          <Text as='span' weight='semibold' truncate className='flex-1'>
            {title}
          </Text>
          {active && !indeterminate && (
            <Stat value={job.progress} format='percent' />
          )}
          <Badge size='sm' variant={STATUS_BADGE[status]}>
            {JOB_STATUS_LABEL[status]}
          </Badge>
        </div>
        {active && (
          <Progress
            size='sm'
            value={job.progress * PERCENT}
            indeterminate={indeterminate}
            tone={BAR_TONE[status]}
            aria-label={title}
          />
        )}
        {job.stage && !job.error && (
          <Muted variant='caption' truncate={2}>
            {job.stage}
          </Muted>
        )}
        {job.error && (
          <Text variant='caption' tone='destructive' truncate={3}>
            {job.error}
          </Text>
        )}
        <Muted variant='caption' truncate>
          {job.label ? `${kindLabel} · ${timing(job, now)}` : timing(job, now)}
        </Muted>
        <JobItems items={job.items} />
      </div>
      {active && <CancelButton job={job} />}
    </div>
  )
}

function JobGroup({
  label,
  jobs,
  now,
}: {
  label: string
  jobs: Job[]
  now: number
}) {
  if (jobs.length === 0) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`${label} · ${jobs.length}`}</Label>
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} now={now} />
      ))}
    </div>
  )
}

export function JobsMenu() {
  const jobs = useRecentJobs()
  const list = jobs.data ?? []
  const active = list.filter(isActive)
  const finished = list.filter((job) => !isActive(job))
  const running = active.filter((job) => statusOf(job) === 'running').length
  const failed = finished.filter((job) => statusOf(job) === 'failed').length
  const now = useNow(active.length > 0)
  const label =
    active.length > 0
      ? `${plural(active.length, 'job', 'jobs')} in progress`
      : 'Jobs'
  return (
    <Popover>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              variant='ghost'
              size={active.length > 0 ? 'sm' : 'icon'}
              aria-label={label}
              data-jobs-menu
              className={cn(active.length > 0 && 'text-primary')}
            >
              {active.length > 0 ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <ListChecks />
              )}
              {active.length > 0 && (
                <Badge size='sm' variant='solid'>
                  {active.length}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent>{label}</TooltipContent>
      </Tooltip>
      <PopoverContent
        align='end'
        className='flex max-h-144 w-96 flex-col gap-0 p-0'
      >
        <div className='flex min-w-0 items-center gap-3 border-b p-4'>
          <Medallion icon={ListChecks} />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Text as='span' weight='semibold'>
              Jobs
            </Text>
            <Muted as='span' variant='caption' truncate>
              {list.length === 0
                ? 'Nothing has run yet'
                : [
                    `${running} running`,
                    `${active.length - running} queued`,
                    `${failed} failed`,
                  ].join(' · ')}
            </Muted>
          </div>
        </div>
        <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain p-4'>
          {jobs.isError && <Text tone='destructive'>{jobs.error.message}</Text>}
          {list.length === 0 ? (
            <EmptyState
              size='compact'
              icon={ListChecks}
              title='No jobs yet'
              description='Epochs, genesis, deepening and images show their progress here.'
            />
          ) : (
            <>
              <JobGroup label='In progress' jobs={active} now={now} />
              <JobGroup label='Recent' jobs={finished} now={now} />
            </>
          )}
        </div>
        <div className='border-t p-2'>
          <Button
            variant='ghost'
            size='sm'
            asChild
            className='w-full justify-between'
          >
            <Link to='/settings/maintenance'>
              Job history and maintenance
              <ArrowRight />
            </Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
