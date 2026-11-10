import { useState } from 'react'
import { Plus, Trash2, Vote, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  Paged,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { AssemblyCard } from '../affairs/AssemblyCard'
import { CourtCard } from '../affairs/CourtCard'
import {
  type Affairs,
  type Approval,
  type CommodityKind,
  type CouncilTask,
  type CouncilTaskView,
  type Demand,
  type DistrictKind,
  type Election,
  type Mandate,
  type MandateKind,
  type MandateState,
  type NobleWant,
  type Seat,
  type Tax,
  useAffairs,
} from '../affairs/api'
import {
  AFFAIRS_ICON,
  APPROVAL_ICON,
  CLASSES,
  COMMODITIES,
  CORRUPTION_ICON,
  DEMAND_ICON,
  DISTRICTS,
  ELECTION_ICON,
  MANDATE_ICON,
  MANDATE_KINDS,
  MANDATE_STATES,
  TASKS,
  TAX_ICON,
  TAX_KINDS,
  WANTS,
  labelTable,
  spec,
} from '../affairs/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { OFFICES, named, sentence } from '../realm/labels'
import { NumberField, RefLink, Tag } from '../realm/parts'

const SPAN = 100
const WORKING = 'Working on it.'
type Ctx = { view: Affairs; blocked: string | null; hold: boolean }
type NodeRef = { id: number; kind: string; name: string }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function clamp(value: string, high = SPAN): number {
  return Math.max(0, Math.min(high, Math.round(Number(value) || 0)))
}

function Ref({
  node,
  empty = 'none',
}: {
  node: NodeRef | null | undefined
  empty?: string
}) {
  if (!node) return <span>{empty}</span>
  return <RefLink node={node} />
}

function TaskRow({ row, ctx }: { row: CouncilTaskView; ctx: Ctx }) {
  const [task, setTask] = useState<string>(row.task ?? '')
  const [target, setTarget] = useState<number | null>(row.target?.id ?? null)
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/council:task', {
          body: {
            office_id: row.office_id,
            task: task as CouncilTask,
            target_id: target,
            hold: ctx.hold,
          },
        })
      ),
  })
  const busy = why(ctx.blocked, set.isPending)
  const office = named(OFFICES, row.office)
  const look = row.task ? spec(TASKS, row.task) : null
  return (
    <ItemRow
      icon={office.icon}
      tone={row.diligence < 30 ? 'danger' : office.tone}
      title={
        <>
          {`${office.label}: `}
          <Ref node={row.holder} empty='vacant' />
        </>
      }
      meta={
        look
          ? `${look.label}${row.target ? ` toward ${row.target.name}` : ''}, diligence ${row.diligence}`
          : 'No council task'
      }
      badges={
        <>
          {look && <Tag spec={look} />}
          {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      editLabel={`the task of the ${office.label.toLowerCase()}`}
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`office-${row.office_id}`}
            inline
            groups={[
              {
                title: 'Diligence',
                fields: [
                  {
                    key: 'diligence',
                    label: 'Diligence',
                    value: row.diligence,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/council:task', {
                  body: {
                    office_id: row.office_id,
                    diligence: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='Task'
              value={task}
              table={labelTable(TASKS)}
              blocked={busy}
              onPick={setTask}
            />
            <NodePicker
              label='Aimed at'
              types={['polity', 'settlement', 'people']}
              value={target}
              onChange={setTarget}
              blocked={busy}
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null || !task}
            disabledReason={busy ?? (!task ? 'Choose a task.' : undefined)}
            onClick={() => set.mutate()}
          >
            Set the task
          </Button>
        </div>
      }
    >
      <StatBar
        label='Diligence'
        value={row.diligence}
        max={SPAN}
        tone={row.diligence < 30 ? 'destructive' : 'success'}
      />
    </ItemRow>
  )
}

function ElectionRow({ row, ctx }: { row: Election; ctx: Ctx }) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/election:delete', {
          body: { election_id: row.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={ELECTION_ICON}
      tone='info'
      title={`The election of epoch ${row.epoch}`}
      meta={
        <>
          {`Turnout ${row.turnout}%, ${row.seats} seats; carried by `}
          <Ref node={row.winner} empty='no one' />
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the election'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
    >
      {row.results.length === 0 ? (
        <Muted variant='caption'>No votes were cast.</Muted>
      ) : (
        <Paged items={row.results} initial={4} noun={['result', 'results']}>
          {({ holder, share }) => (
            <StatBar
              key={holder.id}
              label={holder.name}
              value={share}
              max={SPAN}
              tone='info'
            />
          )}
        </Paged>
      )}
    </ItemRow>
  )
}

function SeatRow({ row, ctx }: { row: Seat; ctx: Ctx }) {
  const realmId = ctx.view.realm?.id ?? 0
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/seat:remove', {
          body: { polity_id: realmId, holder_id: row.holder.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={Vote}
      tone='info'
      title={<Ref node={row.holder} />}
      meta={`${row.seats} seats, ${row.votes}% of the vote, since epoch ${row.since_epoch}`}
      badges={row.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Empty the seats of ${row.holder.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`the seats of ${row.holder.name}`}
      editor={
        <AdjustStats
          id={`seat-${row.holder.id}`}
          inline
          groups={[
            {
              title: 'Seats',
              fields: [
                {
                  key: 'seats',
                  label: 'Seats',
                  value: row.seats,
                  min: 0,
                  max: 200,
                },
                {
                  key: 'votes',
                  label: 'Share of the vote',
                  value: row.votes,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/seat:set', {
                body: {
                  polity_id: realmId,
                  holder_id: row.holder.id,
                  seats: key === 'seats' ? value : row.seats,
                  votes: key === 'votes' ? value : row.votes,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function AddSeat({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const [holder, setHolder] = useState<number | null>(null)
  const [seats, setSeats] = useState('1')
  const add = useGodAction({
    run: (holderId: number) =>
      unwrap(
        api.POST('/api/actions/seat:set', {
          body: {
            polity_id: realmId,
            holder_id: holderId,
            seats: clamp(seats, 200),
            votes: 0,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setHolder(null)
      return 'Seated'
    },
  })
  const busy = why(ctx.blocked, add.isPending)
  return (
    <AddBar
      title='Seat a voice in the council'
      action={
        <Button
          size='sm'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose who sits.' : undefined)
          }
          onClick={() => holder !== null && add.mutate(holder)}
        >
          <Plus />
          Seat
        </Button>
      }
    >
      <NodePicker
        label='Holder'
        types={['faction', 'mortal']}
        value={holder}
        onChange={setHolder}
        blocked={busy}
      />
      <NumberField
        label='Seats (0–200)'
        min={0}
        max={200}
        value={seats}
        blocked={busy}
        onChange={setSeats}
      />
    </AddBar>
  )
}

function ElectionsCard({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const call = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/election:call', { body: { polity_id: realmId } })
      ),
    success: () => 'The polls have closed',
  })
  const busy = why(ctx.blocked, call.isPending)
  return (
    <MindCard
      title='Elections and the council'
      icon={ELECTION_ICON}
      hint='Realms that decide by assembly or crown by election go to the polls. The franchise decides which classes vote; estates draw their class, parties those who back their cause, and factions buy votes. Seats weigh on every law, and the winner’s leader becomes chancellor.'
    >
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => call.mutate()}
      >
        <ELECTION_ICON />
        Call an election now
      </Button>
      <Label variant='overline'>Seats</Label>
      {ctx.view.seats.length === 0 ? (
        <Muted variant='caption'>No one sits in an elected council.</Muted>
      ) : (
        <Paged
          items={ctx.view.seats}
          initial={4}
          noun={['seat holder', 'seat holders']}
        >
          {(row) => <SeatRow key={row.holder.id} row={row} ctx={ctx} />}
        </Paged>
      )}
      <AddSeat ctx={ctx} realmId={realmId} />
      <Label variant='overline'>Past elections</Label>
      {ctx.view.elections.length === 0 ? (
        <Muted variant='caption'>The realm has held no election.</Muted>
      ) : (
        <Paged
          items={ctx.view.elections}
          initial={2}
          noun={['election', 'elections']}
        >
          {(row) => <ElectionRow key={row.id} row={row} ctx={ctx} />}
        </Paged>
      )}
    </MindCard>
  )
}

function TaxRow({ row, ctx, cap }: { row: Tax; ctx: Ctx; cap: number }) {
  const realmId = ctx.view.realm?.id ?? 0
  const farm = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tax:set', {
          body: {
            polity_id: realmId,
            kind: row.kind,
            farmed: !row.farmed,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tax:remove', {
          body: { polity_id: realmId, kind: row.kind },
        })
      ),
  })
  const busy = why(ctx.blocked, farm.isPending, strike.isPending)
  const look = spec(TAX_KINDS, row.kind)
  return (
    <ItemRow
      icon={look.icon}
      tone={row.farmed ? 'warning' : look.tone}
      title={look.label}
      meta={`Rate ${row.rate} of ${cap}, collected at ${row.efficiency}% efficiency, bringing ${row.take}`}
      badges={
        <>
          {row.farmed && <Badge variant='secondary'>Farmed out</Badge>}
          {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Return the ${look.label.toLowerCase()} to custom`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Trash2 />
        </Button>
      }
      editLabel={`the ${look.label.toLowerCase()}`}
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`tax-${row.kind}`}
            inline
            groups={[
              {
                title: 'Tax',
                fields: [
                  {
                    key: 'rate',
                    label: 'Rate',
                    value: row.rate,
                    min: 0,
                    max: cap,
                  },
                  {
                    key: 'efficiency',
                    label: 'Efficiency',
                    value: row.efficiency,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/tax:set', {
                  body: {
                    polity_id: realmId,
                    kind: row.kind,
                    [key]: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => farm.mutate()}
          >
            {row.farmed ? 'Take it back from the tax farmers' : 'Farm it out'}
          </Button>
        </div>
      }
    >
      <StatBar
        label='Rate'
        value={row.rate}
        max={cap}
        icon={TAX_ICON}
        tone='warning'
      />
    </ItemRow>
  )
}

function TreasuryCard({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const corruption = ctx.view.corruption ?? 0
  return (
    <MindCard
      title='Corruption and taxes'
      icon={CORRUPTION_ICON}
      hint='Corruption grows from overreach, unjust laws, greedy officers and farmed-out taxes; it skims taxes, erodes the laws and sours the people. Each kind of tax falls on its own classes, and farming one out brings more coin at a cost in corruption and unrest.'
    >
      <StatBar
        label='Corruption'
        value={corruption}
        max={SPAN}
        icon={CORRUPTION_ICON}
        tone={corruption >= SPAN / 2 ? 'destructive' : 'warning'}
      />
      {ctx.view.corruption_held && <Badge variant='outline'>Held</Badge>}
      <AdjustStats
        id={`corruption-${realmId}`}
        inline
        groups={[
          {
            title: 'Corruption',
            fields: [
              {
                key: 'corruption',
                label: 'Corruption',
                value: corruption,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ value }) =>
          unwrap(
            api.POST('/api/actions/corruption:set', {
              body: { polity_id: realmId, corruption: value, hold: ctx.hold },
            })
          )
        }
      />
      <Label variant='overline'>Taxes</Label>
      {ctx.view.taxes.length === 0 ? (
        <Muted variant='caption'>
          The realm sets its taxes at the next epoch.
        </Muted>
      ) : (
        <Paged items={ctx.view.taxes} initial={5} noun={['tax', 'taxes']}>
          {(row) => (
            <TaxRow key={row.kind} row={row} ctx={ctx} cap={ctx.view.tax_cap} />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function MandateRow({ row, ctx }: { row: Mandate; ctx: Ctx }) {
  const [state, setState] = useState<string>(row.state)
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mandate:edit', {
          body: {
            mandate_id: row.id,
            state: state as MandateState,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mandate:delete', {
          body: { mandate_id: row.id },
        })
      ),
  })
  const busy = why(ctx.blocked, edit.isPending, strike.isPending)
  const look = spec(MANDATE_KINDS, row.kind)
  const what = row.commodity
    ? sentence(row.commodity)
    : row.district
      ? sentence(row.district)
      : null
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={
        <>
          {`${look.label} in `}
          <Ref node={row.settlement} empty='the whole realm' />
        </>
      }
      meta={`${what ? `${what}${row.amount ? `, ${row.amount}` : ''}; ` : ''}issued in epoch ${row.issued_epoch}, due by epoch ${row.until_epoch}`}
      badges={
        <>
          <Tag spec={spec(MANDATE_STATES, row.state)} />
          {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Withdraw the mandate'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Trash2 />
        </Button>
      }
      editLabel='the mandate'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`mandate-${row.id}`}
            inline
            groups={[
              {
                title: 'Mandate',
                fields: [
                  {
                    key: 'until_epoch',
                    label: 'Due by epoch',
                    value: row.until_epoch,
                    min: 0,
                    max: 100_000,
                  },
                  {
                    key: 'amount',
                    label: 'Amount',
                    value: row.amount,
                    min: 0,
                    max: 1_000_000,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/mandate:edit', {
                  body: { mandate_id: row.id, [key]: value, hold: ctx.hold },
                })
              )
            }
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='State'
              value={state}
              table={labelTable(MANDATE_STATES)}
              blocked={busy}
              onPick={setState}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || state === row.state}
              disabledReason={
                busy ??
                (state === row.state ? 'Choose another state.' : undefined)
              }
              onClick={() => edit.mutate()}
            >
              Set the state
            </Button>
          </div>
        </div>
      }
    />
  )
}

function IssueMandate({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const [kind, setKind] = useState('')
  const [settlement, setSettlement] = useState<number | null>(null)
  const [commodity, setCommodity] = useState('')
  const [district, setDistrict] = useState('')
  const [amount, setAmount] = useState('0')
  const issue = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mandate:issue', {
          body: {
            polity_id: realmId,
            kind: kind as MandateKind,
            settlement_id: settlement,
            commodity: commodity ? (commodity as CommodityKind) : null,
            district: district ? (district as DistrictKind) : null,
            amount: clamp(amount, 1_000_000),
          },
        })
      ),
    success: () => {
      setKind('')
      return 'Mandate issued'
    },
  })
  const busy = why(ctx.blocked, issue.isPending)
  const missing = !kind
    ? 'Choose a mandate.'
    : kind === 'export_ban' && !commodity
      ? 'Choose the good to ban.'
      : kind === 'build' && !district
        ? 'Choose the quarter to build.'
        : null
  return (
    <AddBar
      title='Issue a mandate'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => issue.mutate()}
        >
          <Plus />
          Issue
        </Button>
      }
    >
      <MindPicker
        label='Mandate'
        value={kind}
        table={labelTable(MANDATE_KINDS)}
        blocked={busy}
        onPick={setKind}
      />
      <NodePicker
        label='Laid on'
        types={['settlement']}
        value={settlement}
        onChange={setSettlement}
        blocked={busy}
      />
      <MindPicker
        label='Good'
        value={commodity}
        table={COMMODITIES}
        blocked={busy}
        onPick={setCommodity}
      />
      <MindPicker
        label='Quarter'
        value={district}
        table={DISTRICTS}
        blocked={busy}
        onPick={setDistrict}
      />
      <NumberField
        label='Amount'
        min={0}
        max={1_000_000}
        value={amount}
        blocked={busy}
        onChange={setAmount}
      />
    </AddBar>
  )
}

function DemandRow({ row, ctx }: { row: Demand; ctx: Ctx }) {
  const toggle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/demand:set', {
          body: {
            mortal_id: row.noble.id,
            want: row.want,
            met: !row.met,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/demand:remove', {
          body: { mortal_id: row.noble.id, want: row.want },
        })
      ),
  })
  const busy = why(ctx.blocked, toggle.isPending, strike.isPending)
  const look = spec(WANTS, row.want)
  return (
    <ItemRow
      icon={look.icon}
      tone={row.met ? 'success' : 'warning'}
      title={look.label}
      meta={row.met ? 'Met' : `Unmet since epoch ${row.since_epoch}`}
      badges={row.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => toggle.mutate()}
          >
            {row.met ? 'Mark unmet' : 'Grant it'}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Forget the demand'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        </>
      }
    />
  )
}

function AddDemand({ ctx, nobleId }: { ctx: Ctx; nobleId: number }) {
  const [want, setWant] = useState('')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/demand:set', {
          body: {
            mortal_id: nobleId,
            want: want as NobleWant,
            met: false,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setWant('')
      return 'Demand set'
    },
  })
  const busy = why(ctx.blocked, add.isPending)
  return (
    <AddBar
      title='Give this mortal a demand'
      action={
        <Button
          size='sm'
          disabled={busy !== null || !want}
          disabledReason={busy ?? (!want ? 'Choose a demand.' : undefined)}
          onClick={() => add.mutate()}
        >
          <Plus />
          Demand
        </Button>
      }
    >
      <MindPicker
        label='Demand'
        value={want}
        table={labelTable(WANTS)}
        blocked={busy}
        onPick={setWant}
      />
    </AddBar>
  )
}

function ApprovalRow({ row, ctx }: { row: Approval; ctx: Ctx }) {
  const realmId = ctx.view.realm?.id ?? 0
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/approval:remove', {
          body: { polity_id: realmId, social_class: row.social_class },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const parts = Object.entries(row.parts).filter(([, value]) => value !== 0)
  return (
    <ItemRow
      icon={APPROVAL_ICON}
      tone={
        row.approval > 0 ? 'success' : row.approval < 0 ? 'danger' : 'muted'
      }
      title={CLASSES[row.social_class] ?? sentence(row.social_class)}
      meta={`Approval ${row.approval > 0 ? '+' : ''}${row.approval}`}
      badges={
        row.locked.length > 0 ? (
          <Badge variant='outline'>Held</Badge>
        ) : undefined
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Weigh this approval anew'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the approval'
      editor={
        <AdjustStats
          id={`approval-${row.social_class}`}
          inline
          groups={[
            {
              title: 'Approval',
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
              api.POST('/api/actions/approval:set', {
                body: {
                  polity_id: realmId,
                  social_class: row.social_class,
                  approval: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    >
      {parts.length === 0 ? (
        <Muted variant='caption'>No policy touches this class.</Muted>
      ) : (
        <PagedList
          items={parts}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap items-center gap-1.5'
          itemKey={([key]) => key}
        >
          {([key, value]) => (
            <Badge key={key} variant={value > 0 ? 'secondary' : 'outline'}>
              {`${sentence(key.split(':')[1] ?? key)} ${value > 0 ? '+' : ''}${value}`}
            </Badge>
          )}
        </PagedList>
      )}
    </ItemRow>
  )
}

export function AffairsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useAffairs(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-affairs'
        title='Affairs of the realm'
        icon={AFFAIRS_ICON}
      >
        <EmptyState
          icon={AFFAIRS_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  const realm = view.realm
  const isMortal = view.is_mortal
  const empty =
    !realm &&
    !isMortal &&
    !view.is_assembly &&
    view.mandates.length === 0 &&
    view.resolutions.length === 0
  return (
    <Section
      id='section-affairs'
      title='Affairs of the realm'
      description='Council tasks, elections and seats, corruption and taxes, mandates and nobles’ demands, and how each class approves of the realm’s policies.'
      icon={AFFAIRS_ICON}
    >
      {empty ? (
        <EmptyState
          icon={AFFAIRS_ICON}
          title='Outside the affairs of any realm'
          description='Councils, taxes and mandates belong to realms, and demands to mortals. This is neither, nor belongs to a realm.'
        />
      ) : (
        <div className='@container/mind flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
            <KpiTile
              label='Corruption'
              value={view.corruption ?? 0}
              icon={CORRUPTION_ICON}
              tone='danger'
            />
            <KpiTile
              label='Taxes this epoch'
              value={view.taxes.reduce((sum, row) => sum + row.take, 0)}
              icon={TAX_ICON}
              tone='gold'
            />
            <KpiTile
              label='Mandates in force'
              value={
                view.mandates.filter((row) => row.state === 'active').length
              }
              icon={MANDATE_ICON}
              tone='info'
            />
            <KpiTile
              label='Council seats'
              value={view.seats.reduce((sum, row) => sum + row.seats, 0)}
              icon={ELECTION_ICON}
              tone='verdigris'
            />
          </div>
          {realm && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <RefLink node={realm} />
            </div>
          )}
          <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
            {realm && (
              <MindCard
                title='Council tasks'
                icon={AFFAIRS_ICON}
                hint='Each officer works a task each epoch. The work scales with their skill and their regard for the ruler; a spymaster who scorns the ruler sells their secrets abroad.'
              >
                {view.council.length === 0 ? (
                  <Muted variant='caption'>The realm has no offices yet.</Muted>
                ) : (
                  <Paged
                    items={view.council}
                    initial={4}
                    noun={['office', 'offices']}
                  >
                    {(row) => (
                      <TaskRow key={row.office_id} row={row} ctx={ctx} />
                    )}
                  </Paged>
                )}
              </MindCard>
            )}
            {realm && <ElectionsCard ctx={ctx} realmId={realm.id} />}
            {realm && <TreasuryCard ctx={ctx} realmId={realm.id} />}
            {realm && <CourtCard ctx={ctx} realmId={realm.id} />}
            {(view.is_assembly || view.resolutions.length > 0) && (
              <AssemblyCard ctx={ctx} />
            )}
            <MindCard
              title='Mandates'
              icon={MANDATE_ICON}
              hint='Rulers order production, ban exports, order building, send famine relief from the state granaries and impose curfews. An unmet mandate costs the ruler legitimacy, and harsh ones weigh on the people.'
            >
              {view.mandates.length === 0 ? (
                <Muted variant='caption'>
                  No mandate has been issued here.
                </Muted>
              ) : (
                <Paged
                  items={view.mandates}
                  initial={3}
                  noun={['mandate', 'mandates']}
                >
                  {(row) => <MandateRow key={row.id} row={row} ctx={ctx} />}
                </Paged>
              )}
              {realm && <IssueMandate ctx={ctx} realmId={realm.id} />}
            </MindCard>
            {isMortal && (
              <MindCard
                title='Demands'
                icon={DEMAND_ICON}
                hint='Nobles want a fine dwelling, fine goods, an office or honour. A demand left unmet sours them toward their ruler each epoch.'
              >
                {view.demands.length === 0 ? (
                  <Muted variant='caption'>This mortal makes no demands.</Muted>
                ) : (
                  <Paged
                    items={view.demands}
                    initial={4}
                    noun={['demand', 'demands']}
                  >
                    {(row) => <DemandRow key={row.want} row={row} ctx={ctx} />}
                  </Paged>
                )}
                <AddDemand ctx={ctx} nobleId={nodeId} />
              </MindCard>
            )}
            {realm && (
              <MindCard
                title='Approval of the realm’s policies'
                icon={APPROVAL_ICON}
                hint='Every law and mandate moves the approval of each class; approval nudges each class’s satisfaction and its estate’s loyalty.'
              >
                {view.approvals.length === 0 ? (
                  <Muted variant='caption'>
                    Approval is weighed at the next epoch.
                  </Muted>
                ) : (
                  <Paged
                    items={view.approvals}
                    initial={5}
                    noun={['class', 'classes']}
                  >
                    {(row) => (
                      <ApprovalRow key={row.social_class} row={row} ctx={ctx} />
                    )}
                  </Paged>
                )}
              </MindCard>
            )}
          </div>
          <ControlPanel
            title='Hold what you set'
            note='Tasks, seats, corruption, taxes, mandates, demands and approval you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
            hold={hold}
            onHold={setHold}
          >
            {null}
          </ControlPanel>
        </div>
      )}
    </Section>
  )
}
