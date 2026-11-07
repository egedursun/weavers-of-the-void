import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EmptyState, KpiTile, Paged, Section } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type Cipher,
  type Correspondence,
  type Dispatch,
  type DispatchContent,
  type DispatchState,
  type Medium,
  type Opinion,
  type OpinionSubject,
  type Signal,
  type SignalKind,
  type SignalState,
  useCorrespondence,
} from '../communication/api'
import {
  CIPHER_ICON,
  CORRESPONDENCE_ICON,
  LETTER_ICON,
  MEDIUMS,
  OPINION_ICON,
  SIGNAL_ICON,
  SIGNAL_ICONS,
  STATE_TONE,
  approvalTone,
} from '../communication/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { RefLink } from '../realm/parts'

const SPAN = 100
const WORKING = 'Working on it.'
const BEINGS = [
  'mortal',
  'settlement',
  'people',
  'polity',
  'house',
  'faction',
  'cult',
]

type Ctx = { view: Correspondence; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function Ref({
  node,
}: {
  node: { id: number; kind: string; name: string } | null
}) {
  if (!node) return <span>someone now gone</span>
  return <RefLink node={node} />
}

function DispatchRow({
  row,
  ctx,
  side,
}: {
  row: Dispatch
  ctx: Ctx
  side: 'sent' | 'received' | 'intercepted'
}) {
  const edit = useGodAction({
    run: (state: DispatchState) =>
      unwrap(
        api.POST('/api/actions/dispatch:edit', {
          body: { message_id: row.id, state, hold: ctx.hold },
        })
      ),
  })
  const flag = useGodAction({
    run: (patch: { forged?: boolean; misread?: boolean }) =>
      unwrap(
        api.POST('/api/actions/dispatch:edit', {
          body: { message_id: row.id, ...patch, hold: ctx.hold },
        })
      ),
  })
  const freeze = useGodAction({
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/dispatch:hold', {
          body: { message_id: row.id, hold },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/dispatch:delete', {
          body: { message_id: row.id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    edit.isPending,
    flag.isPending,
    freeze.isPending,
    strike.isPending
  )
  const look = MEDIUMS[row.medium ?? 'letter'] ?? MEDIUMS.letter
  const frozen = row.held.length > 0
  const other =
    side === 'received' ? row.sender : side === 'sent' ? row.recipient : null
  return (
    <ItemRow
      icon={look.icon}
      tone={STATE_TONE[row.state ?? 'under_way'] ?? look.tone}
      title={
        side === 'intercepted' ? (
          <>
            {`${row.content_label}: `}
            <Ref node={row.sender} />
            {' to '}
            <Ref node={row.recipient} />
          </>
        ) : (
          <>
            {`${row.content_label} ${side === 'sent' ? 'to' : 'from'} `}
            <Ref node={other} />
          </>
        )
      }
      meta={`${row.medium_label}, sent in epoch ${row.sent_epoch}, ${row.state_label.toLowerCase()}${row.arrival_epoch !== null ? ` (due in epoch ${row.arrival_epoch})` : ''}${row.envoy_fate_label ? `; the envoy was ${row.envoy_fate_label.toLowerCase()}` : ''}`}
      badges={
        <>
          {row.enciphered && <Badge variant='outline'>Enciphered</Badge>}
          {row.forged && <Badge variant='destructive'>Forged</Badge>}
          {row.misread && <Badge variant='secondary'>Misread</Badge>}
          {row.intercepted_by && side !== 'intercepted' && (
            <Badge variant='destructive'>Intercepted</Badge>
          )}
          {frozen && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Unmake the message'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the message'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <MindPicker
            label='Where it stands'
            value={row.state ?? 'under_way'}
            table={table(ctx.view.states)}
            blocked={busy}
            onPick={(value) => edit.mutate(value as DispatchState)}
          />
          <AdjustStats
            id={`dispatch-${row.id}`}
            inline
            groups={[
              {
                title: 'Journey',
                fields: [
                  {
                    key: 'arrival_epoch',
                    label: 'Due in epoch',
                    value: row.arrival_epoch ?? row.sent_epoch,
                    min: 0,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/dispatch:edit', {
                  body: {
                    message_id: row.id,
                    arrival_epoch: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <div className='flex min-w-0 flex-wrap justify-end gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => flag.mutate({ forged: !row.forged })}
            >
              {row.forged ? 'Make it genuine' : 'Make it a forgery'}
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => flag.mutate({ misread: !row.misread })}
            >
              {row.misread ? 'Let it be read rightly' : 'Make it misread'}
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => freeze.mutate(!frozen)}
            >
              {frozen ? 'Let it travel' : 'Hold it where it is'}
            </Button>
          </div>
        </div>
      }
    />
  )
}

function LettersCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [recipient, setRecipient] = useState<number | null>(null)
  const [content, setContent] = useState('')
  const [medium, setMedium] = useState('letter')
  const send = useGodAction({
    run: (recipientId: number) =>
      unwrap(
        api.POST('/api/actions/dispatch:send', {
          body: {
            sender_id: view.node_id,
            recipient_id: recipientId,
            content: content as DispatchContent,
            medium: medium as Medium,
            forged: false,
          },
        })
      ),
    success: () => {
      setRecipient(null)
      setContent('')
      return 'Sent'
    },
  })
  const busy = why(ctx.blocked, send.isPending)
  const empty =
    view.sent.length === 0 &&
    view.received.length === 0 &&
    view.intercepted.length === 0
  return (
    <MindCard
      title='Letters, envoys and heralds'
      icon={LETTER_ICON}
      wide
      hint='Messages take time by distance, medium and season; spies may read or seize them, outlaws waylay them, forgers replace them, and between tongues a clause may be misread. Envoys carry them with courtesy, or meet a hostile court.'
    >
      {empty && <Muted variant='caption'>No message has passed here.</Muted>}
      {view.received.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Received</Label>
          <Paged
            items={view.received}
            initial={3}
            noun={['message', 'messages']}
          >
            {(row) => (
              <DispatchRow key={row.id} row={row} ctx={ctx} side='received' />
            )}
          </Paged>
        </div>
      )}
      {view.sent.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Sent</Label>
          <Paged items={view.sent} initial={3} noun={['message', 'messages']}>
            {(row) => (
              <DispatchRow key={row.id} row={row} ctx={ctx} side='sent' />
            )}
          </Paged>
        </div>
      )}
      {view.intercepted.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Intercepted by its spies</Label>
          <Paged
            items={view.intercepted}
            initial={3}
            noun={['message', 'messages']}
          >
            {(row) => (
              <DispatchRow
                key={row.id}
                row={row}
                ctx={ctx}
                side='intercepted'
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Send a message in its name'
        action={
          <Button
            size='sm'
            disabled={busy !== null || recipient === null || !content}
            disabledReason={
              busy ??
              (recipient === null
                ? 'Choose a recipient first.'
                : content
                  ? undefined
                  : 'Choose what it says.')
            }
            onClick={() => recipient !== null && send.mutate(recipient)}
          >
            <Plus />
            Send
          </Button>
        }
      >
        <NodePicker
          label='To'
          types={BEINGS}
          value={recipient}
          onChange={setRecipient}
          blocked={busy}
        />
        <MindPicker
          label='Says'
          value={content}
          table={table(view.contents)}
          blocked={busy}
          onPick={setContent}
        />
        <MindPicker
          label='By'
          value={medium}
          table={table(view.mediums)}
          blocked={busy}
          onPick={setMedium}
        />
      </AddBar>
    </MindCard>
  )
}

function OpinionRow({
  row,
  ctx,
  holding,
}: {
  row: Opinion
  ctx: Ctx
  holding: boolean
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/opinion:delete', {
          body: {
            community_id: row.community?.id ?? 0,
            subject_id: row.subject?.id ?? 0,
          },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={OPINION_ICON}
      tone={approvalTone(row.approval)}
      title={
        holding ? (
          <>
            {`${row.subject_label}: `}
            <Ref node={row.subject} />
          </>
        ) : (
          <>
            {'Thought of by '}
            <Ref node={row.community} />
          </>
        )
      }
      meta={`Approval ${row.approval > 0 ? '+' : ''}${row.approval}, as of epoch ${row.epoch}`}
      badges={
        <>
          {row.censored && (
            <Badge variant='destructive'>Censorship noticed</Badge>
          )}
          {row.held.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Wipe the opinion'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the opinion'
      editor={
        <AdjustStats
          id={`opinion-${row.community?.id}-${row.subject?.id}`}
          inline
          groups={[
            {
              title: 'Opinion',
              fields: [
                {
                  key: 'approval',
                  label: 'Approval',
                  value: row.approval,
                  min: -SPAN,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/opinion:set', {
                body: {
                  community_id: row.community?.id ?? 0,
                  subject_id: row.subject?.id ?? 0,
                  subject: row.subject_kind,
                  approval: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    >
      <Progress
        value={(row.approval + SPAN) / 2}
        size='sm'
        tone={row.approval >= 0 ? 'success' : 'warning'}
        aria-label={`Approval ${row.approval}`}
      />
    </ItemRow>
  )
}

function OpinionCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [subject, setSubject] = useState<number | null>(null)
  const [kind, setKind] = useState('ruler')
  const set = useGodAction({
    run: (subjectId: number) =>
      unwrap(
        api.POST('/api/actions/opinion:set', {
          body: {
            community_id: view.node_id,
            subject_id: subjectId,
            subject: kind as OpinionSubject,
            approval: 0,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setSubject(null)
      return 'Opinion set'
    },
  })
  const busy = why(ctx.blocked, set.isPending)
  const empty = view.opinions.length === 0 && view.regarded.length === 0
  return (
    <MindCard
      title='Public opinion'
      icon={OPINION_ICON}
      hint='What communities think of their ruler, wars, laws, gods and creeds, fed by fortune, renown, rumour, heralds, art, sermons and broadsheets and muted by censorship. Approval of the ruler feeds legitimacy and unrest, of a war its weariness, of a law its enforcement.'
    >
      {empty && (
        <Muted variant='caption'>No opinion is held here or of it.</Muted>
      )}
      {view.opinions.length > 0 && (
        <Paged items={view.opinions} initial={4} noun={['opinion', 'opinions']}>
          {(row) => (
            <OpinionRow
              key={`${row.subject?.id}`}
              row={row}
              ctx={ctx}
              holding
            />
          )}
        </Paged>
      )}
      {view.regarded.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>What others think of it</Label>
          <Paged
            items={view.regarded}
            initial={4}
            noun={['opinion', 'opinions']}
          >
            {(row) => (
              <OpinionRow
                key={`${row.community?.id}`}
                row={row}
                ctx={ctx}
                holding={false}
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Plant an opinion here'
        action={
          <Button
            size='sm'
            disabled={busy !== null || subject === null}
            disabledReason={
              busy ??
              (subject === null ? 'Choose the subject first.' : undefined)
            }
            onClick={() => subject !== null && set.mutate(subject)}
          >
            <Plus />
            Set
          </Button>
        }
      >
        <NodePicker
          label='Of'
          types={[...BEINGS, 'law', 'ideology']}
          value={subject}
          onChange={setSubject}
          blocked={busy}
        />
        <MindPicker
          label='As'
          value={kind}
          table={table(view.subjects)}
          blocked={busy}
          onPick={setKind}
        />
      </AddBar>
    </MindCard>
  )
}

function CipherRowView({
  row,
  ctx,
  own,
}: {
  row: Cipher
  ctx: Ctx
  own: boolean
}) {
  const mend = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cipher:mend', {
          body: { owner_id: row.owner?.id ?? 0 },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cipher:delete', {
          body: { owner_id: row.owner?.id ?? 0 },
        })
      ),
  })
  const busy = why(ctx.blocked, mend.isPending, strike.isPending)
  return (
    <ItemRow
      icon={CIPHER_ICON}
      tone={row.broken_by.length > 0 ? 'danger' : 'verdigris'}
      title={
        own ? (
          `A cipher of strength ${row.strength}`
        ) : (
          <>
            {'The cipher of '}
            <Ref node={row.owner} />
          </>
        )
      }
      meta={`In use since epoch ${row.since_epoch}; ${row.broken_by.length > 0 ? `read by ${row.broken_by.map((node) => node.name).join(', ')}` : 'unbroken'}, after ${row.attempts} attempts`}
      badges={
        <>
          {row.break_known && <Badge variant='secondary'>Break noticed</Badge>}
          {row.held.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        own ? (
          <>
            {row.broken_by.length > 0 && (
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => mend.mutate()}
              >
                Make it new
              </Button>
            )}
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label='Strike the cipher'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => strike.mutate()}
            >
              <X />
            </Button>
          </>
        ) : undefined
      }
      editLabel={own ? 'the cipher' : undefined}
      editor={
        own ? (
          <AdjustStats
            id={`cipher-${row.owner?.id}`}
            inline
            groups={[
              {
                title: 'Cipher',
                fields: [
                  {
                    key: 'strength',
                    label: 'Strength',
                    value: row.strength,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/cipher:set', {
                  body: {
                    owner_id: row.owner?.id ?? 0,
                    strength: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
        ) : undefined
      }
    />
  )
}

function CiphersCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [breaker, setBreaker] = useState<number | null>(null)
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cipher:set', {
          body: { owner_id: view.node_id, strength: 30, hold: ctx.hold },
        })
      ),
  })
  const crack = useGodAction({
    run: (breakerId: number) =>
      unwrap(
        api.POST('/api/actions/cipher:break', {
          body: { owner_id: view.node_id, breaker_id: breakerId, known: false },
        })
      ),
    success: () => {
      setBreaker(null)
      return 'Broken'
    },
  })
  const busy = why(ctx.blocked, give.isPending, crack.isPending)
  return (
    <MindCard
      title='Ciphers'
      icon={CIPHER_ICON}
      hint='Those who know cryptography write in ciphers. Intercepted ciphered messages yield nothing until a codebreaker breaks them over seasons, the more traffic the sooner; a broken cipher is a secret until its owner notices.'
    >
      {view.cipher ? (
        <CipherRowView row={view.cipher} ctx={ctx} own />
      ) : (
        <>
          <Muted variant='caption'>Writes in plain words.</Muted>
          <div className='flex justify-end'>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => give.mutate()}
            >
              <Plus />
              Give it a cipher
            </Button>
          </div>
        </>
      )}
      {view.cipher && (
        <AddBar
          title='Let someone read it'
          action={
            <Button
              size='sm'
              disabled={busy !== null || breaker === null}
              disabledReason={
                busy ??
                (breaker === null ? 'Choose the codebreaker first.' : undefined)
              }
              onClick={() => breaker !== null && crack.mutate(breaker)}
            >
              Break it
            </Button>
          }
        >
          <NodePicker
            label='Codebreaker'
            types={BEINGS}
            value={breaker}
            onChange={setBreaker}
            blocked={busy}
          />
        </AddBar>
      )}
      {view.ciphers_read.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Ciphers it reads</Label>
          <Paged
            items={view.ciphers_read}
            initial={3}
            noun={['cipher', 'ciphers']}
          >
            {(row) => (
              <CipherRowView
                key={row.owner?.id}
                row={row}
                ctx={ctx}
                own={false}
              />
            )}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function SignalRow({ row, ctx }: { row: Signal; ctx: Ctx }) {
  const edit = useGodAction({
    run: (state: SignalState) =>
      unwrap(
        api.POST('/api/actions/signal:edit', {
          body: { link_id: row.id, state, hold: ctx.hold },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/signal:delete', { body: { link_id: row.id } })
      ),
  })
  const busy = why(ctx.blocked, edit.isPending, strike.isPending)
  const look = SIGNAL_ICONS[row.kind] ?? SIGNAL_ICONS.fire_beacon
  return (
    <ItemRow
      icon={look.icon}
      tone={row.state === 'active' ? look.tone : 'muted'}
      title={
        <>
          {`${row.kind_label}: `}
          <Ref node={row.start} />
          {' to '}
          <Ref node={row.end} />
        </>
      }
      meta={`${row.state_label} since epoch ${row.since_epoch}`}
      badges={
        row.held.length > 0 ? <Badge variant='outline'>Held</Badge> : undefined
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Tear down the link'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the link'
      editor={
        <MindPicker
          label='State'
          value={row.state}
          table={table(ctx.view.signal_states)}
          blocked={busy}
          onPick={(value) => edit.mutate(value as SignalState)}
        />
      }
    />
  )
}

function SignalsCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [kind, setKind] = useState('fire_beacon')
  const [start, setStart] = useState<number | null>(null)
  const [end, setEnd] = useState<number | null>(null)
  const build = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/signal:build', {
          body: {
            owner_id: view.node_id,
            kind: kind as SignalKind,
            from_region_id: start ?? 0,
            to_region_id: end ?? 0,
          },
        })
      ),
    success: () => {
      setStart(null)
      setEnd(null)
      return 'Built'
    },
  })
  const busy = why(ctx.blocked, build.isPending)
  return (
    <MindCard
      title='Signal links'
      icon={SIGNAL_ICON}
      hint='Fire beacons, mirror towers, post stations and sending stones cut the time its messages take; an enemy who takes either end captures or burns them.'
    >
      {view.signals.length === 0 ? (
        <Muted variant='caption'>Owns no signal link.</Muted>
      ) : (
        <Paged items={view.signals} initial={4} noun={['link', 'links']}>
          {(row) => <SignalRow key={row.id} row={row} ctx={ctx} />}
        </Paged>
      )}
      <AddBar
        title='Raise a link'
        action={
          <Button
            size='sm'
            disabled={busy !== null || start === null || end === null}
            disabledReason={
              busy ??
              (start === null || end === null
                ? 'Choose both lands.'
                : undefined)
            }
            onClick={() => build.mutate()}
          >
            <Plus />
            Build
          </Button>
        }
      >
        <MindPicker
          label='Kind'
          value={kind}
          table={table(view.signal_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <NodePicker
          label='From'
          types={['region']}
          value={start}
          onChange={setStart}
          blocked={busy}
        />
        <NodePicker
          label='To'
          types={['region']}
          value={end}
          onChange={setEnd}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

export function CorrespondenceSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useCorrespondence(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-correspondence'
        title='Messages and opinion'
        icon={CORRESPONDENCE_ICON}
      >
        <EmptyState
          icon={CORRESPONDENCE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  const underWay = [...view.sent, ...view.received].filter(
    (row) => row.state === 'under_way'
  ).length
  const mean =
    view.regarded.length > 0
      ? Math.round(
          view.regarded.reduce((sum, row) => sum + row.approval, 0) /
            view.regarded.length
        )
      : 0
  return (
    <Section
      id='section-correspondence'
      title='Messages and opinion'
      description='The letters, envoys and heralds it sends and receives, what it intercepts, the opinions it holds and that others hold of it, its cipher and the signal links it keeps.'
      icon={CORRESPONDENCE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
          <KpiTile
            label='Under way'
            value={underWay}
            icon={LETTER_ICON}
            tone='info'
          />
          <KpiTile
            label='Intercepted'
            value={view.intercepted.length}
            icon={CIPHER_ICON}
            tone='danger'
          />
          <KpiTile
            label='Approval of it'
            value={mean}
            icon={OPINION_ICON}
            tone={approvalTone(mean)}
          />
          <KpiTile
            label='Signal links'
            value={view.signals.length}
            icon={SIGNAL_ICON}
            tone='gold'
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          <LettersCard ctx={ctx} />
          <OpinionCard ctx={ctx} />
          <CiphersCard ctx={ctx} />
          <SignalsCard ctx={ctx} />
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Messages, opinions, ciphers and links you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
