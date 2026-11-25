import {
  ArrowRight,
  Ban,
  Check,
  CircleCheck,
  CircleSlash,
  Clock,
  Coins,
  Hourglass,
  type LucideIcon,
  Plus,
  ShieldAlert,
  Skull,
  Sparkles,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { formatDateTime, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { NodeRef } from './NodeRef'
import { UndoButton } from './UndoButton'
import { useDecideConfirmation } from './api'
import { type PreviewChange, parsePreview, tableWords } from './previewModel'
import { argumentSummary } from './toolLook'
import { type ConfirmationReply } from './traceModel'
import {
  type ConfirmationReason,
  type ConfirmationStatus,
  type WillConfirmation,
} from './types'
import { useNameOf } from './useNameOf'

const CHANGES_SHOWN = 6

const REASON_LOOK: Record<
  ConfirmationReason,
  { label: string; icon: LucideIcon; hint: string }
> = {
  destructive: {
    label: 'Destructive',
    icon: Trash2,
    hint: 'It deletes or ends something in the world.',
  },
  costly: {
    label: 'Costly',
    icon: Coins,
    hint: 'It spends a great deal of essence.',
  },
  both: {
    label: 'Destructive and costly',
    icon: ShieldAlert,
    hint: 'It ends something in the world and spends a great deal of essence.',
  },
}

const STATUS_LOOK: Record<
  ConfirmationStatus,
  {
    label: string
    icon: LucideIcon
    variant: 'warning' | 'success' | 'outline' | 'destructive'
  }
> = {
  pending: { label: 'Waits for you', icon: Clock, variant: 'warning' },
  approved: { label: 'Approved', icon: CircleCheck, variant: 'success' },
  declined: { label: 'Declined', icon: CircleSlash, variant: 'destructive' },
  expired: { label: 'Lapsed', icon: Clock, variant: 'outline' },
}

const OPERATION_LOOK: Record<
  string,
  { icon: LucideIcon; tone: string; verb: string }
> = {
  insert: { icon: Plus, tone: 'text-success', verb: 'made' },
  update: { icon: ArrowRight, tone: 'text-muted-foreground', verb: 'changed' },
  delete: { icon: Trash2, tone: 'text-destructive', verb: 'removed' },
}

function ChangeRow({ change }: { change: PreviewChange }) {
  const look = OPERATION_LOOK[change.operation] ?? OPERATION_LOOK.update
  const Icon = look.icon
  const subject = change.nodeName || tableWords(change.table)
  return (
    <li
      data-operation={change.operation}
      className='flex min-w-0 items-start gap-2 rounded-md surface-well px-2.5 py-1.5'
    >
      <Icon
        aria-hidden='true'
        className={cn('size-icon-sm shrink-0', look.tone)}
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' variant='caption' weight='medium'>
          {change.nodeId !== null ? (
            <NodeRef id={change.nodeId} name={subject} />
          ) : (
            subject
          )}
          {change.field ? ` · ${change.field.replaceAll('_', ' ')}` : ''}
        </Text>
        {change.operation === 'update' ? (
          <Muted as='span' variant='caption' className='wrap-anywhere'>
            <span className='line-through'>{change.before || 'nothing'}</span>
            {' → '}
            <span className='text-foreground'>{change.after || 'nothing'}</span>
          </Muted>
        ) : (
          <Muted as='span' variant='caption'>
            {`A record of ${tableWords(change.table)} is ${look.verb}`}
          </Muted>
        )}
      </div>
    </li>
  )
}

function Losses({ preview }: { preview: ReturnType<typeof parsePreview> }) {
  const gone = [
    ...preview.deletedNodes.map((node, index) => ({
      key: `node-${String(index)}`,
      text: node.name || 'A record',
      nodeId: node.nodeId,
      what: 'is deleted',
    })),
    ...preview.deletedRecords.map((row, index) => ({
      key: `row-${String(index)}`,
      text: row.nodeName || tableWords(row.table),
      nodeId: row.nodeId,
      what: `loses a record of ${tableWords(row.table)}`,
    })),
    ...preview.ended.map((row, index) => ({
      key: `end-${String(index)}`,
      text: row.nodeName || tableWords(row.table),
      nodeId: row.nodeId,
      what: 'comes to an end',
    })),
  ]
  if (gone.length === 0) return null
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-md surface-well border-destructive/40 px-3 py-2'>
      <Label className='flex items-center gap-1.5 text-destructive'>
        <Skull aria-hidden='true' className='size-icon-xs' />
        What is lost
      </Label>
      <ul className='flex min-w-0 flex-col gap-0.5'>
        <Paged
          items={gone}
          initial={CHANGES_SHOWN}
          as='li'
          noun={['loss', 'losses']}
        >
          {(item) => (
            <li key={item.key}>
              <Text as='span' variant='caption'>
                {item.nodeId !== null ? (
                  <NodeRef id={item.nodeId} name={item.text} />
                ) : (
                  item.text
                )}
                {` ${item.what}`}
              </Text>
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}

export function ConfirmationCard({
  confirmation,
  reply,
}: {
  confirmation: WillConfirmation
  reply: ConfirmationReply | null
}) {
  const decide = useDecideConfirmation()
  const nameOf = useNameOf()
  const reason = REASON_LOOK[confirmation.reason]
  const ReasonIcon = reason.icon
  const status = STATUS_LOOK[confirmation.status]
  const StatusIcon = status.icon
  const pending = confirmation.status === 'pending'
  const preview = parsePreview(confirmation.preview)
  const title = preview.title || confirmation.action_id
  const block = isReadOnly()
    ? READ_ONLY_MESSAGE
    : decide.isPending
      ? 'Your word is on its way.'
      : null
  const answer = (decision: 'approve' | 'decline') =>
    decide.mutate(
      { id: confirmation.id, decision },
      {
        onSuccess: () =>
          decision === 'approve'
            ? toast.success('Approved. The Divine Will acts.')
            : toast('Declined. The Divine Will is told no.'),
        onError: (error) => toast.error(error.message),
      }
    )
  const inputs = argumentSummary(confirmation.input, nameOf)
  const tallies = preview.tallies
    .map(
      (tally) =>
        `${plural(tally.count, 'record')} ${(OPERATION_LOOK[tally.operation] ?? OPERATION_LOOK.update).verb} in ${tableWords(tally.table)}`
    )
    .join(' · ')
  return (
    <OrnateFrame
      frame='card'
      tone={
        pending ? 'warning' : status.variant === 'success' ? 'success' : 'muted'
      }
      data-domain='will-confirmation'
      data-status={confirmation.status}
      role='group'
      aria-label={`Approval for ${title}`}
      className='flex min-w-0 flex-col gap-3 p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={pending ? TriangleAlert : ReasonIcon}
          tone={pending ? 'warning' : 'muted'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Label variant='overline'>
            {pending ? 'Your word is needed' : 'An act that asked first'}
          </Label>
          <Text weight='semibold' className='text-gilded font-display'>
            {title}
          </Text>
          {inputs && (
            <Muted variant='caption' truncate={2}>
              {inputs}
            </Muted>
          )}
        </div>
        <Badge size='sm' variant={status.variant}>
          <StatusIcon />
          {status.label}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='destructive'>
          <ReasonIcon />
          {reason.label}
        </Badge>
        <Badge size='sm' variant='default'>
          <Sparkles />
          {`${formatInteger(preview.essence)} essence`}
        </Badge>
        {preview.gained > 0 && (
          <Badge size='sm' variant='success'>
            <Sparkles />
            {`${formatInteger(preview.gained)} essence back`}
          </Badge>
        )}
        {preview.cost && (
          <Badge size='sm' variant='outline'>
            {preview.cost}
          </Badge>
        )}
        {preview.job && (
          <Badge size='sm' variant='outline'>
            <Hourglass />
            Runs as a job
          </Badge>
        )}
      </div>
      <Muted variant='caption'>
        {preview.job
          ? `${reason.hint} It runs as a job, so it could not be rehearsed; this is its declared cost.`
          : `${reason.hint} The Divine Will rehearsed it on the world and rolled it back; this is what it would do.`}
      </Muted>
      {preview.message && <Text variant='caption'>{preview.message}</Text>}
      <Losses preview={preview} />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label>
          {preview.changes.length === 1
            ? 'One change in the rehearsal'
            : `${plural(preview.changes.length, 'change')} in the rehearsal`}
        </Label>
        {tallies && <Muted variant='caption'>{tallies}</Muted>}
        {preview.changes.length === 0 ? (
          <Muted variant='caption'>The rehearsal changed no record.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged
              items={preview.changes}
              initial={CHANGES_SHOWN}
              as='li'
              noun={['change', 'changes']}
            >
              {(change, index) => <ChangeRow key={index} change={change} />}
            </Paged>
          </ul>
        )}
      </div>
      {pending ? (
        <div className='flex min-w-0 flex-wrap items-center justify-end gap-2'>
          <Button
            act={decide}
            variant='outline'
            size='sm'
            disabled={block !== null}
            disabledReason={block ?? undefined}
            onClick={() => answer('decline')}
          >
            <Ban />
            Decline
          </Button>
          <Button
            act={decide}
            size='sm'
            disabled={block !== null}
            disabledReason={block ?? undefined}
            onClick={() => answer('approve')}
          >
            <Check />
            Approve
          </Button>
        </div>
      ) : (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Muted variant='caption' className='min-w-0 flex-1'>
            {[
              confirmation.decided_at
                ? `${status.label} ${formatDateTime(confirmation.decided_at)}`
                : `Asked ${formatDateTime(confirmation.created_at)}`,
              reply?.text ?? '',
              reply && reply.essence > 0
                ? `${formatInteger(reply.essence)} essence spent`
                : '',
              reply?.jobId ? 'running as a job' : '',
              reply && !reply.ok ? 'the act was refused' : '',
            ]
              .filter(Boolean)
              .join(' · ')}
          </Muted>
          {confirmation.ledger_entry_id !== null && (
            <UndoButton entryId={confirmation.ledger_entry_id} />
          )}
        </div>
      )}
    </OrnateFrame>
  )
}
