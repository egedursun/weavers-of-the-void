import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { cn } from '@/lib/utils'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  ActionButton,
  type ConfirmSpec,
} from '@/features/pantheon/ActionButton'
import { JobOutcome } from './JobOutcome'

type JobRunRowProps = {
  id: string
  title: string
  description: string
  note?: string
  badges?: ReactNode
  control?: ReactNode
  label: string
  icon: LucideIcon
  cost?: number
  rule?: string
  blocked: string | null
  pending: boolean
  error: string | null
  jobId: string | null
  spent?: number
  confirm?: ConfirmSpec
  onRun: () => void
  onDismiss: () => void
}

export function JobRunRow({
  id,
  title,
  description,
  note,
  badges,
  control,
  label,
  icon,
  cost,
  rule,
  blocked,
  pending,
  error,
  jobId,
  spent,
  confirm,
  onRun,
  onDismiss,
  act,
}: JobRunRowProps & { act?: ActProp }) {
  return (
    <li
      data-job-row={id}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        blocked === null ? 'bg-card' : 'bg-muted/30'
      )}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2'>
        <Medallion
          icon={icon}
          tone={blocked === null ? 'gold' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text weight='medium' truncate={2}>
              {title}
            </Text>
            {badges}
          </div>
          <Muted variant='caption'>{description}</Muted>
          {note && <Muted variant='caption'>{note}</Muted>}
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {control}
          <ActionButton
            act={act}
            label={label}
            icon={icon}
            size='sm'
            cost={cost}
            rule={rule}
            blocked={blocked}
            pending={pending}
            confirm={confirm}
            onRun={onRun}
          />
        </div>
      </div>
      {error && (
        <Text variant='caption' tone='destructive'>
          {error}
        </Text>
      )}
      {jobId && (
        <JobOutcome
          jobId={jobId}
          title={title}
          spent={spent}
          onDismiss={onDismiss}
        />
      )}
    </li>
  )
}
