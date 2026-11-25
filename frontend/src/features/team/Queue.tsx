import { useEffect, useState } from 'react'
import { Hourglass, RotateCcw, X } from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { useCancelQueued, useQueue, useRetryQueued } from './api'
import { useTeamContext } from './teamContext'
import { QUEUE_SOURCE, QUEUE_STATUS, personTone, spokenField } from './teamLook'
import { onTeamView } from './teamSignals'
import {
  type ConflictChangeView,
  type QueuedActStatus,
  type QueuedActView,
} from './types'

const SHOWN = 6
const NOT_YOURS = 'Only its author or an administrator can change a queued act.'

function mayChange(
  act: QueuedActView,
  me: number | null,
  admin: boolean
): string | null {
  if (admin) return null
  return act.author?.account_id !== undefined &&
    act.author.account_id !== null &&
    act.author.account_id === me
    ? null
    : NOT_YOURS
}

function ConflictLine({ change }: { change: ConflictChangeView }) {
  const team = useTeamContext()
  const who =
    change.by_account_id !== null && change.by_account_id === team?.me
      ? 'You'
      : (change.by ?? 'Someone')
  return (
    <li className='flex min-w-0 items-center gap-2'>
      <AccountAvatar name={who} tone={personTone(change.by ?? who)} size='xs' />
      <Muted as='span' variant='caption' truncate>
        {`${who} changed ${spokenField(change.field ?? change.table)}${change.at ? ` ${formatSince(change.at)}` : ''}`}
      </Muted>
    </li>
  )
}

export function QueuedRow({ act }: { act: QueuedActView }) {
  const team = useTeamContext()
  const cancel = useCancelQueued()
  const retry = useRetryQueued()
  const status = QUEUE_STATUS[act.status]
  const source = QUEUE_SOURCE[act.source]
  const StatusIcon = status.icon
  const author = act.author?.name ?? 'Someone'
  const refusal = mayChange(act, team?.me ?? null, team?.role === 'admin')
  const busy = cancel.isPending || retry.isPending
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg surface-sheen p-3'>
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion icon={source.icon} tone={source.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold' truncate={2}>
            {act.title}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <AccountAvatar name={author} tone={personTone(author)} size='xs' />
            <Muted
              as='span'
              variant='caption'
              title={formatDateTime(act.queued_at)}
            >
              {`${author} · ${formatSince(act.queued_at)} · ${source.label}`}
            </Muted>
          </div>
        </div>
        <Badge variant='outline' size='sm'>
          <StatusIcon />
          {status.label}
        </Badge>
      </div>
      {act.reason && (
        <Text variant='caption' className='italic'>{`“${act.reason}”`}</Text>
      )}
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge variant='outline' size='sm'>
          {`Made in epoch ${act.queued_epoch}`}
        </Badge>
        {act.plan_id !== null && act.plan_ordinal !== null && (
          <Badge variant='outline' size='sm'>
            {`Step ${act.plan_ordinal} of a Divine Will plan`}
          </Badge>
        )}
        {act.presence_session_id !== null && (
          <Badge variant='outline' size='sm'>
            From an audience of Summon to Presence
          </Badge>
        )}
        {act.proposal_id !== null && (
          <Badge variant='info' size='sm'>
            Sent for canon review
          </Badge>
        )}
        {act.applied_at && (
          <Badge
            variant='success'
            size='sm'
            title={formatDateTime(act.applied_at)}
          >
            {`Applied ${formatSince(act.applied_at)}`}
          </Badge>
        )}
      </div>
      {act.result && act.status !== 'queued' && (
        <Muted variant='caption'>{act.result}</Muted>
      )}
      {act.cancelled_by && (
        <Muted variant='caption'>{`Cancelled by ${act.cancelled_by.name}`}</Muted>
      )}
      {act.conflict.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1 rounded-md surface-well p-2'>
          <Label>Changed by others while it waited</Label>
          <ul
            aria-label='Changes by others'
            className='flex min-w-0 flex-col gap-1'
          >
            <Paged items={act.conflict} as='li' noun={['change', 'changes']}>
              {(change, position) => (
                <ConflictLine
                  key={`${change.table}-${position}`}
                  change={change}
                />
              )}
            </Paged>
          </ul>
        </div>
      )}
      {(act.status === 'queued' || act.status === 'failed') && (
        <div className='flex min-w-0 flex-wrap justify-end gap-2'>
          {act.status === 'failed' && (
            <Button
              type='button'
              size='sm'
              variant='outline'
              act={retry}
              disabled={refusal !== null || busy}
              disabledReason={refusal ?? 'Working.'}
              onClick={() =>
                retry.mutate(act, {
                  onSuccess: () =>
                    toast.success(`${act.title} is queued again`),
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              <RotateCcw />
              Try again
            </Button>
          )}
          <Button
            type='button'
            size='sm'
            variant='outline'
            className='text-destructive'
            act={cancel}
            disabled={refusal !== null || busy}
            disabledReason={refusal ?? 'Working.'}
            onClick={() =>
              cancel.mutate(act, {
                onSuccess: () => toast.success(`${act.title} will not run`),
                onError: (error) => toast.error(error.message),
              })
            }
          >
            <X />
            {act.status === 'queued' ? 'Cancel it' : 'Clear it'}
          </Button>
        </div>
      )}
    </li>
  )
}

export function QueueList({ status }: { status: QueuedActStatus | null }) {
  const queue = useQueue(status)
  const page = useShowMore(queue.data?.items ?? [], SHOWN)
  if (queue.isPending) return <LoadingBlock label='Reading the queue' />
  if (queue.isError)
    return (
      <EmptyState
        size='compact'
        icon={Hourglass}
        title='The queue could not be read'
        description={queue.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void queue.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  if (page.total === 0)
    return (
      <EmptyState
        size='compact'
        icon={Hourglass}
        title={
          status === 'queued' ? 'Nothing is waiting' : 'No queued acts yet'
        }
        description='Acts made while an age runs wait here and apply, in order and in their authors’ names, as soon as it ends.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul aria-label='Queued acts' className='flex min-w-0 flex-col gap-2'>
        {page.visible.map((act) => (
          <QueuedRow key={act.id} act={act} />
        ))}
      </ul>
      <ShowMore state={page} noun={['act', 'acts']} />
    </div>
  )
}

export function QueueTray() {
  const team = useTeamContext()
  const [open, setOpen] = useState(false)
  useEffect(
    () =>
      onTeamView((view) => {
        if (view === 'queue') setOpen(true)
      }),
    []
  )
  const waiting = team?.team?.queued ?? 0
  const busy = team?.team?.world_busy ?? false
  if (waiting === 0 && !busy) return null
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type='button'
          variant='ghost'
          size='sm'
          aria-label={`Waiting for the age to end: ${waiting}`}
        >
          <Hourglass className='text-warning' />
          <Text as='span' variant='caption' weight='semibold'>
            {waiting}
          </Text>
        </Button>
      </PopoverTrigger>
      <PopoverContent align='end' className='w-96 max-w-full'>
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-2.5'>
            <Medallion icon={Hourglass} tone='warning' size='sm' />
            <span className='flex min-w-0 flex-col'>
              <Label variant='gilded'>Waiting for the age to end</Label>
              <Muted as='span' variant='caption'>
                {busy
                  ? 'An age is running; these run right after it, in order.'
                  : 'The age has ended; these are being applied.'}
              </Muted>
            </span>
          </div>
          <QueueList status='queued' />
        </div>
      </PopoverContent>
    </Popover>
  )
}
