import { useId, useState } from 'react'
import { BookLock, Check, Lock, Undo2, X } from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  KeyValueList,
  LoadingBlock,
  Medallion,
  ShowMore,
  useShowMore,
  PagedList,
} from '@/components/domain'
import { FieldTile } from '@/components/domain/FieldTile'
import { Label, Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { useNodeIndex } from '@/features/feed/nodes'
import {
  useApproveProposal,
  useProposals,
  useRejectProposal,
  useWithdrawProposal,
} from './api'
import { useTeamContext } from './teamContext'
import {
  CANON_TOUCH,
  PROPOSAL_STATUS,
  personTone,
  spokenField,
} from './teamLook'
import { type CanonProposalView, type ProposalStatus } from './types'

const SHOWN = 5
const NOTE_MAX = 500
const ADMINS_ONLY = 'Only administrators decide canon proposals.'
const AUTHOR_ONLY = 'Only its author can withdraw a proposal.'

function shownValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean')
    return String(value)
  return JSON.stringify(value)
}

function entries(record: Record<string, unknown>) {
  return Object.entries(record).map(([key, value]) => ({
    label: spokenField(key),
    value: shownValue(value),
  }))
}

export function ProposalCard({ proposal }: { proposal: CanonProposalView }) {
  const team = useTeamContext()
  const names = useNodeIndex()
  const noteId = useId()
  const [note, setNote] = useState('')
  const approve = useApproveProposal()
  const reject = useRejectProposal()
  const withdraw = useWithdrawProposal()
  const status = PROPOSAL_STATUS[proposal.status]
  const StatusIcon = status.icon
  const author = proposal.author?.name ?? 'Someone'
  const admin = team?.role === 'admin'
  const mine =
    proposal.author?.account_id !== undefined &&
    proposal.author.account_id !== null &&
    proposal.author.account_id === team?.me
  const pending = proposal.status === 'pending'
  const busy = approve.isPending || reject.isPending || withdraw.isPending
  const decided = (verb: string) => ({
    onSuccess: () => {
      setNote('')
      toast.success(`${proposal.title} ${verb}`)
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const preview = entries(proposal.preview)
  const asked = entries(proposal.payload)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-lg surface-framed p-3'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={BookLock} tone={status.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold' className='font-display'>
            {proposal.title}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <AccountAvatar name={author} tone={personTone(author)} size='xs' />
            <Muted
              as='span'
              variant='caption'
              title={formatDateTime(proposal.proposed_at)}
            >
              {`${author} · epoch ${proposal.proposed_epoch} · ${formatSince(proposal.proposed_at)}`}
            </Muted>
          </div>
        </div>
        <Badge variant='outline' size='sm'>
          <StatusIcon />
          {status.label}
        </Badge>
      </div>
      {proposal.reason && (
        <Text
          variant='caption'
          className='italic'
        >{`“${proposal.reason}”`}</Text>
      )}
      <PagedList
        items={proposal.touches}
        initial={SHOWN}
        noun={['change', 'changes']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(touch) => touch}
      >
        {(touch) => {
          const look = CANON_TOUCH[touch]
          const Icon = look.icon
          return (
            <Badge variant='warning' size='sm'>
              <Icon />
              {look.label}
            </Badge>
          )
        }}
      </PagedList>
      {proposal.held_node_ids.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label>Held things it touches</Label>
          {proposal.held_node_ids.map((nodeId) => (
            <Badge key={nodeId} variant='outline' size='sm'>
              <Lock />
              {names.get(nodeId)?.name ?? 'A held record'}
            </Badge>
          ))}
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>What was asked</Label>
          {asked.length === 0 ? (
            <Muted variant='caption'>No values.</Muted>
          ) : (
            <KeyValueList items={asked} />
          )}
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>What it would change</Label>
          {preview.length === 0 ? (
            <Muted variant='caption'>The rehearsal changed nothing else.</Muted>
          ) : (
            <KeyValueList items={preview} />
          )}
        </div>
      </div>
      {!pending && (proposal.decided_by || proposal.note) && (
        <Muted variant='caption'>
          {`${status.label}${proposal.decided_by ? ` by ${proposal.decided_by.name}` : ''}${proposal.decided_at ? ` ${formatSince(proposal.decided_at)}` : ''}${proposal.note ? `: ${proposal.note}` : ''}`}
        </Muted>
      )}
      {pending && (
        <div className='flex min-w-0 flex-col gap-2'>
          {admin && (
            <FieldTile id={noteId} label='Note to the author (optional)'>
              <Textarea
                id={noteId}
                rows={2}
                maxLength={NOTE_MAX}
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </FieldTile>
          )}
          <div className='flex min-w-0 flex-wrap justify-end gap-2'>
            <Button
              type='button'
              size='sm'
              variant='ghost'
              act={withdraw}
              disabled={!mine || busy}
              disabledReason={mine ? 'Working.' : AUTHOR_ONLY}
              onClick={() =>
                withdraw.mutate(proposal.id, decided('is withdrawn'))
              }
            >
              <Undo2 />
              Withdraw
            </Button>
            <Button
              type='button'
              size='sm'
              variant='destructive'
              act={reject}
              disabled={!admin || busy}
              disabledReason={admin ? 'Working.' : ADMINS_ONLY}
              onClick={() =>
                reject.mutate({ id: proposal.id, note }, decided('is rejected'))
              }
            >
              <X />
              Reject
            </Button>
            <Button
              type='button'
              size='sm'
              act={approve}
              disabled={!admin || busy}
              disabledReason={admin ? 'Working.' : ADMINS_ONLY}
              onClick={() =>
                approve.mutate(
                  { id: proposal.id, note },
                  decided('is approved and runs in its author’s name')
                )
              }
            >
              <Check />
              Approve
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

export function ProposalList({ status }: { status: ProposalStatus | null }) {
  const proposals = useProposals(status)
  const page = useShowMore(proposals.data?.items ?? [], SHOWN)
  if (proposals.isPending) return <LoadingBlock label='Reading the proposals' />
  if (proposals.isError)
    return (
      <EmptyState
        size='compact'
        icon={BookLock}
        title='The proposals could not be read'
        description={proposals.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void proposals.refetch()}
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
        icon={BookLock}
        title={
          status === 'pending' ? 'Nothing waits for review' : 'No proposals yet'
        }
        description='With canon approval on, an Editor’s act that touches locked canon waits here until an administrator approves it.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul aria-label='Canon proposals' className='flex min-w-0 flex-col gap-3'>
        {page.visible.map((proposal) => (
          <ProposalCard key={proposal.id} proposal={proposal} />
        ))}
      </ul>
      <ShowMore state={page} noun={['proposal', 'proposals']} />
    </div>
  )
}
