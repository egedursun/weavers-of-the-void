import { useState } from 'react'
import { Lock, Plus, Trash2, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
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
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { NumberField, RefLink, Tag } from '../realm/parts'
import {
  type Backer,
  type Crisis,
  type CrisisDemand,
  type CrisisSide,
  type CrisisState,
  type Regard,
  type Sphere,
  type Statecraft,
  type Subject,
  type SubjectKind,
  useStatecraft,
} from '../statecraft/api'
import {
  CAPACITY_ICON,
  CRISIS_ICON,
  CRISIS_STATES,
  DEMANDS,
  SIDES,
  SPHERE_ICON,
  STANDINGS,
  STATECRAFT_ICON,
  SUBJECT_ICON,
  SUBJECT_KINDS,
  THREAT_ICON,
  TRUST_ICON,
  labelTable,
  spec,
} from '../statecraft/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const REALMS = ['polity']
const ENDINGS: Record<
  Exclude<components['schemas']['CrisisState'], 'escalating'>,
  string
> = {
  backed_down: 'The demander backs down',
  conceded: 'The target concedes',
  war: 'It comes to war',
}
type Ctx = { view: Statecraft; blocked: string | null; hold: boolean }
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

function RegardRow({
  row,
  ctx,
  threshold,
}: {
  row: Regard
  ctx: Ctx
  threshold: number
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/regard:remove', {
          body: { holder_id: row.holder.id, subject_id: row.subject.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const fearful = row.threat >= threshold
  return (
    <ItemRow
      icon={fearful ? THREAT_ICON : TRUST_ICON}
      tone={fearful ? 'danger' : row.trust >= SPAN / 2 ? 'success' : 'muted'}
      title={
        <>
          <Ref node={row.holder} />
          {' toward '}
          <Ref node={row.subject} />
        </>
      }
      meta={`Threat ${row.threat}, trust ${row.trust}`}
      badges={
        <>
          {fearful && (
            <Badge variant='destructive'>Ready for a coalition</Badge>
          )}
          {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Wipe what ${row.holder.name} feels toward ${row.subject.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the regard'
      editor={
        <AdjustStats
          id={`regard-${row.holder.id}-${row.subject.id}`}
          inline
          groups={[
            {
              title: 'Regard',
              fields: [
                {
                  key: 'threat',
                  label: 'Threat',
                  value: row.threat,
                  min: 0,
                  max: SPAN,
                },
                {
                  key: 'trust',
                  label: 'Trust',
                  value: row.trust,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/regard:set', {
                body: {
                  holder_id: row.holder.id,
                  subject_id: row.subject.id,
                  [key]: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <StatBar
          label='Threat'
          value={row.threat}
          max={SPAN}
          icon={THREAT_ICON}
          tone={fearful ? 'destructive' : 'warning'}
        />
        <StatBar
          label='Trust'
          value={row.trust}
          max={SPAN}
          icon={TRUST_ICON}
          tone='success'
        />
      </div>
    </ItemRow>
  )
}

function AddRegard({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const [other, setOther] = useState<number | null>(null)
  const [threat, setThreat] = useState('0')
  const [trust, setTrust] = useState('50')
  const set = useGodAction({
    run: (otherId: number) =>
      unwrap(
        api.POST('/api/actions/regard:set', {
          body: {
            holder_id: otherId,
            subject_id: realmId,
            threat: clamp(threat),
            trust: clamp(trust),
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setOther(null)
      return 'Regard set'
    },
  })
  const busy = why(ctx.blocked, set.isPending)
  return (
    <AddBar
      title='Set how another realm regards this one'
      action={
        <Button
          size='sm'
          disabled={busy !== null || other === null}
          disabledReason={
            busy ?? (other === null ? 'Choose a realm.' : undefined)
          }
          onClick={() => other !== null && set.mutate(other)}
        >
          <Plus />
          Set
        </Button>
      }
    >
      <NodePicker
        label='Realm'
        types={REALMS}
        value={other}
        onChange={setOther}
        blocked={busy}
      />
      <NumberField
        label='Threat (0–100)'
        min={0}
        max={SPAN}
        value={threat}
        blocked={busy}
        onChange={setThreat}
      />
      <NumberField
        label='Trust (0–100)'
        min={0}
        max={SPAN}
        value={trust}
        blocked={busy}
        onChange={setTrust}
      />
    </AddBar>
  )
}

function CapacityCard({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const diplomacy = ctx.view.diplomacy
  return (
    <MindCard
      title='Diplomatic capacity'
      icon={CAPACITY_ICON}
      hint='A realm keeps as many relations as its administration, the skill of its chancellor and envoys, and its embassies allow. Relations past that sour with every partner each epoch.'
    >
      {diplomacy ? (
        <>
          <StatBar
            label='Relations kept'
            value={diplomacy.relations}
            max={Math.max(diplomacy.capacity, diplomacy.relations, 1)}
            icon={CAPACITY_ICON}
            tone={diplomacy.strain > 0 ? 'destructive' : 'success'}
          />
          <Muted variant='caption'>
            {diplomacy.strain > 0
              ? `${plural(diplomacy.strain, 'relation', 'relations')} beyond its capacity of ${diplomacy.capacity} are souring.`
              : `Within its capacity of ${diplomacy.capacity}.`}
          </Muted>
          {diplomacy.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      ) : (
        <Muted variant='caption'>
          Its capacity is measured at the next epoch; set it now if you wish.
        </Muted>
      )}
      <AdjustStats
        id={`diplomacy-${realmId}`}
        inline
        groups={[
          {
            title: 'Capacity',
            fields: [
              {
                key: 'capacity',
                label: 'Capacity',
                value: diplomacy?.capacity ?? 0,
                min: 0,
                max: SPAN,
              },
              {
                key: 'relations',
                label: 'Relations',
                value: diplomacy?.relations ?? 0,
                min: 0,
                max: SPAN,
              },
              {
                key: 'strain',
                label: 'Strain',
                value: diplomacy?.strain ?? 0,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/diplomacy:edit', {
              body: { polity_id: realmId, [key]: value, hold: ctx.hold },
            })
          )
        }
      />
    </MindCard>
  )
}

function BackerRow({
  crisis,
  item,
  ctx,
}: {
  crisis: Crisis
  item: Backer
  ctx: Ctx
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/backer:remove', {
          body: { crisis_id: crisis.id, backer_id: item.backer.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const side = spec(SIDES, item.side)
  return (
    <ItemRow
      icon={side.icon}
      tone={side.tone}
      title={<Ref node={item.backer} />}
      meta={`${side.label}${item.promised > 0 ? `, promised a share of ${item.promised}` : ''}`}
      badges={
        <>
          {item.swing && <Badge variant='secondary'>Swing party</Badge>}
          {item.locked && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Withdraw ${item.backer.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`the backing of ${item.backer.name}`}
      editor={
        <AdjustStats
          id={`backer-${crisis.id}-${item.backer.id}`}
          inline
          groups={[
            {
              title: 'Backing',
              fields: [
                {
                  key: 'promised',
                  label: 'Promised share',
                  value: item.promised,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/backer:set', {
                body: {
                  crisis_id: crisis.id,
                  backer_id: item.backer.id,
                  side: item.side,
                  promised: value,
                  swing: item.swing,
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

function CrisisEditor({ row, ctx }: { row: Crisis; ctx: Ctx }) {
  const [subject, setSubject] = useState<number | null>(row.subject?.id ?? null)
  const [backer, setBacker] = useState<number | null>(null)
  const [side, setSide] = useState('')
  const [promised, setPromised] = useState('0')
  const edit = useGodAction({
    run: (subjectId: number) =>
      unwrap(
        api.POST('/api/actions/crisis:edit', {
          body: { crisis_id: row.id, subject_id: subjectId, hold: ctx.hold },
        })
      ),
  })
  const back = useGodAction({
    run: (backerId: number) =>
      unwrap(
        api.POST('/api/actions/backer:set', {
          body: {
            crisis_id: row.id,
            backer_id: backerId,
            side: side as CrisisSide,
            promised: clamp(promised),
            swing: false,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setBacker(null)
      setSide('')
      return 'Backer set'
    },
  })
  const busy = why(ctx.blocked, edit.isPending, back.isPending)
  const missing =
    backer === null ? 'Choose a realm.' : !side ? 'Choose a side.' : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <AdjustStats
        id={`crisis-${row.id}`}
        inline
        groups={[
          {
            title: 'Crisis',
            fields: [
              {
                key: 'escalation',
                label: 'Step',
                value: row.escalation,
                min: 0,
                max: 20,
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
            api.POST('/api/actions/crisis:edit', {
              body: { crisis_id: row.id, [key]: value, hold: ctx.hold },
            })
          )
        }
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
        <NodePicker
          label='What is demanded'
          types={['region', 'polity', 'cult', 'settlement', 'people']}
          value={subject}
          onChange={setSubject}
          blocked={busy}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || subject === null}
          disabledReason={
            busy ?? (subject === null ? 'Choose what is demanded.' : undefined)
          }
          onClick={() => subject !== null && edit.mutate(subject)}
        >
          Set the subject
        </Button>
      </div>
      {row.backers.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Backers</Label>
          <Paged items={row.backers} initial={4} noun={['backer', 'backers']}>
            {(item) => (
              <BackerRow
                key={item.backer.id}
                crisis={row}
                item={item}
                ctx={ctx}
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Bring in a backer'
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => backer !== null && back.mutate(backer)}
          >
            <Plus />
            Back
          </Button>
        }
      >
        <NodePicker
          label='Realm'
          types={REALMS}
          value={backer}
          onChange={setBacker}
          blocked={busy}
        />
        <MindPicker
          label='Side'
          value={side}
          table={labelTable(SIDES)}
          blocked={busy}
          onPick={setSide}
        />
        <NumberField
          label='Promised share (0–100)'
          min={0}
          max={SPAN}
          value={promised}
          blocked={busy}
          onChange={setPromised}
        />
      </AddBar>
    </div>
  )
}

function CrisisRow({ row, ctx }: { row: Crisis; ctx: Ctx }) {
  const held = row.locked.length > 0
  const [ending, setEnding] = useState('')
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/crisis:hold', {
          body: { crisis_id: row.id, hold: !held },
        })
      ),
  })
  const resolve = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/crisis:resolve', {
          body: { crisis_id: row.id, state: ending as CrisisState },
        })
      ),
    success: () => 'The crisis is over',
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/crisis:delete', { body: { crisis_id: row.id } })
      ),
  })
  const busy = why(
    ctx.blocked,
    hold.isPending,
    resolve.isPending,
    strike.isPending
  )
  const demand = spec(DEMANDS, row.demand)
  const open = row.state === 'escalating'
  const cannot = !open
    ? 'The crisis is already over.'
    : !ending
      ? 'Choose how it ends.'
      : null
  return (
    <ItemRow
      icon={demand.icon}
      tone={open ? 'warning' : spec(CRISIS_STATES, row.state).tone}
      title={
        <>
          <Ref node={row.demander} />
          {` demands: ${demand.label.toLowerCase()}`}
        </>
      }
      meta={
        <>
          {'Of '}
          <Ref node={row.target} />
          {row.subject && (
            <>
              {', namely '}
              <Ref node={row.subject} />
            </>
          )}
          {row.amount > 0 ? `, ${row.amount} in coin` : ''}
          {`, since epoch ${row.opened_epoch}`}
        </>
      }
      badges={
        <>
          <Tag spec={spec(CRISIS_STATES, row.state)} />
          {held && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={held ? 'Let the crisis run' : 'Freeze the crisis'}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => hold.mutate()}
          >
            {held ? <Unlock /> : <Lock />}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the crisis'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Trash2 />
          </Button>
        </>
      }
      editLabel='the crisis'
      editor={<CrisisEditor row={row} ctx={ctx} />}
    >
      <StatBar
        label={`Escalation (war after ${plural(row.steps, 'step', 'steps')})`}
        value={row.escalation}
        max={row.steps}
        icon={CRISIS_ICON}
        tone={open ? 'warning' : 'muted'}
      />
      <Muted variant='caption'>{`${row.backers.filter((item) => item.side === 'demander').length} back the demand, ${row.backers.filter((item) => item.side === 'target').length} stand by the target.`}</Muted>
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
        <MindPicker
          label='End it'
          value={ending}
          table={ENDINGS}
          blocked={busy ?? (open ? null : 'The crisis is already over.')}
          onPick={setEnding}
        />
        <Button
          size='sm'
          disabled={busy !== null || cannot !== null}
          disabledReason={busy ?? cannot ?? undefined}
          onClick={() => resolve.mutate()}
        >
          End the crisis
        </Button>
      </div>
    </ItemRow>
  )
}

function OpenCrisis({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const [target, setTarget] = useState<number | null>(null)
  const [demand, setDemand] = useState('')
  const [subject, setSubject] = useState<number | null>(null)
  const [amount, setAmount] = useState('0')
  const open = useGodAction({
    run: (targetId: number) =>
      unwrap(
        api.POST('/api/actions/crisis:open', {
          body: {
            demander_id: realmId,
            target_id: targetId,
            demand: demand as CrisisDemand,
            subject_id: subject,
            amount: clamp(amount, 1_000_000),
          },
        })
      ),
    success: () => {
      setTarget(null)
      setDemand('')
      setSubject(null)
      return 'Crisis opened'
    },
  })
  const busy = why(ctx.blocked, open.isPending)
  const missing =
    target === null
      ? 'Choose the realm under demand.'
      : !demand
        ? 'Choose a demand.'
        : null
  return (
    <AddBar
      title='Make a demand of another realm'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => target !== null && open.mutate(target)}
        >
          <Plus />
          Demand
        </Button>
      }
    >
      <NodePicker
        label='Of the realm'
        types={REALMS}
        value={target}
        onChange={setTarget}
        blocked={busy}
      />
      <MindPicker
        label='Demand'
        value={demand}
        table={labelTable(DEMANDS)}
        blocked={busy}
        onPick={setDemand}
      />
      <NodePicker
        label='What is demanded'
        types={['region', 'polity', 'cult', 'settlement', 'people']}
        value={subject}
        onChange={setSubject}
        blocked={busy}
      />
      <NumberField
        label='Amount in coin'
        min={0}
        max={1_000_000}
        value={amount}
        blocked={busy}
        onChange={setAmount}
      />
    </AddBar>
  )
}

function SphereRow({ row, ctx }: { row: Sphere; ctx: Ctx }) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/sphere:remove', {
          body: { power_id: row.power.id, client_id: row.client.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={SPHERE_ICON}
      tone='info'
      title={
        <>
          <Ref node={row.client} />
          {' in the sphere of '}
          <Ref node={row.power} />
        </>
      }
      meta={`Strength ${row.strength}, since epoch ${row.since_epoch}`}
      badges={row.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Free ${row.client.name} from the sphere`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the sphere'
      editor={
        <AdjustStats
          id={`sphere-${row.power.id}-${row.client.id}`}
          inline
          groups={[
            {
              title: 'Sphere',
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
              api.POST('/api/actions/sphere:set', {
                body: {
                  power_id: row.power.id,
                  client_id: row.client.id,
                  strength: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    >
      <StatBar
        label='Hold of the power'
        value={row.strength}
        max={SPAN}
        icon={SPHERE_ICON}
        tone='info'
      />
    </ItemRow>
  )
}

function AddSphere({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const [client, setClient] = useState<number | null>(null)
  const [strength, setStrength] = useState('30')
  const add = useGodAction({
    run: (clientId: number) =>
      unwrap(
        api.POST('/api/actions/sphere:set', {
          body: {
            power_id: realmId,
            client_id: clientId,
            strength: clamp(strength),
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setClient(null)
      return 'Drawn into the sphere'
    },
  })
  const busy = why(ctx.blocked, add.isPending)
  return (
    <AddBar
      title='Draw a realm into this sphere'
      action={
        <Button
          size='sm'
          disabled={busy !== null || client === null}
          disabledReason={
            busy ?? (client === null ? 'Choose a realm.' : undefined)
          }
          onClick={() => client !== null && add.mutate(client)}
        >
          <Plus />
          Draw in
        </Button>
      }
    >
      <NodePicker
        label='Client'
        types={REALMS}
        value={client}
        onChange={setClient}
        blocked={busy}
      />
      <NumberField
        label='Strength (0–100)'
        min={0}
        max={SPAN}
        value={strength}
        blocked={busy}
        onChange={setStrength}
      />
    </AddBar>
  )
}

function SubjectRow({
  row,
  ctx,
  revolt,
}: {
  row: Subject
  ctx: Ctx
  revolt: number
}) {
  const [kind, setKind] = useState<string>(row.kind)
  const edit = useGodAction({
    run: (body: Record<string, unknown>) =>
      unwrap(
        api.POST('/api/actions/vassal:edit', {
          body: { vassal_id: row.vassal.id, ...body },
        })
      ),
  })
  const busy = why(ctx.blocked, edit.isPending)
  const look = spec(SUBJECT_KINDS, row.kind)
  const rights: [string, string, boolean][] = [
    ['private_war', 'Private war', row.private_war],
    ['coinage', 'Coinage', row.coinage],
    ['confirm_succession', 'Overlord confirms heirs', row.confirm_succession],
  ]
  return (
    <ItemRow
      icon={look.icon}
      tone={row.liberty >= revolt ? 'danger' : look.tone}
      title={
        <>
          <Ref node={row.vassal} />
          {` is a ${look.label.toLowerCase()} of `}
          <Ref node={row.overlord} />
        </>
      }
      meta={`Pays ${row.pays_tribute ? `${row.tribute_pct}%` : 'no'} tribute, sends ${row.sends_levies ? `${row.levy_pct}%` : 'no'} levies, since epoch ${row.since_epoch}`}
      badges={
        <>
          <Tag spec={look} />
          {rights
            .filter(([, , on]) => on)
            .map(([key, label]) => (
              <Badge key={key} variant='secondary'>
                {label}
              </Badge>
            ))}
          {row.liberty >= revolt && (
            <Badge variant='destructive'>Ready to rise</Badge>
          )}
          {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      editLabel='the terms'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`subject-${row.vassal.id}`}
            inline
            groups={[
              {
                title: 'Terms',
                fields: [
                  {
                    key: 'tribute_pct',
                    label: 'Tribute (%)',
                    value: row.tribute_pct,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'levy_pct',
                    label: 'Levies (%)',
                    value: row.levy_pct,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'loyalty',
                    label: 'Loyalty',
                    value: row.loyalty,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'liberty',
                    label: 'Wish for liberty',
                    value: row.liberty,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/vassal:edit', {
                  body: { vassal_id: row.vassal.id, [key]: value },
                })
              )
            }
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='Kind of subject'
              value={kind}
              table={labelTable(SUBJECT_KINDS)}
              blocked={busy}
              onPick={setKind}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || kind === row.kind}
              disabledReason={
                busy ?? (kind === row.kind ? 'Choose another kind.' : undefined)
              }
              onClick={() => edit.mutate({ kind: kind as SubjectKind })}
            >
              Set the kind
            </Button>
          </div>
          <PagedList
            items={rights}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-2'
            itemKey={([key]) => key}
          >
            {([key, label, on]) => (
              <Button
                key={key}
                size='sm'
                variant={on ? 'secondary' : 'outline'}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => edit.mutate({ [key]: !on })}
              >
                {on ? `Revoke: ${label}` : `Grant: ${label}`}
              </Button>
            )}
          </PagedList>
        </div>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <StatBar
          label='Loyalty'
          value={row.loyalty}
          max={SPAN}
          tone='success'
        />
        <StatBar
          label={`Wish for liberty (rises at ${revolt})`}
          value={row.liberty}
          max={SPAN}
          tone={row.liberty >= revolt ? 'destructive' : 'warning'}
        />
      </div>
    </ItemRow>
  )
}

export function StatecraftSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useStatecraft(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-statecraft'
        title='Realms abroad'
        icon={STATECRAFT_ICON}
      >
        <EmptyState
          icon={STATECRAFT_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  const realm = view.realm
  return (
    <Section
      id='section-statecraft'
      title='Realms abroad'
      description='Threat and trust between realms, coalitions, crises and their backers, spheres of influence, and subjects with their duties and wish for liberty.'
      icon={STATECRAFT_ICON}
    >
      {!realm ? (
        <EmptyState
          icon={STATECRAFT_ICON}
          title='Not part of a realm'
          description='Threat, crises, spheres and subjects belong to realms. This belongs to none, so its standing among realms is read from the realm it joins.'
        />
      ) : (
        <div className='@container/mind flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
            <KpiTile
              label='Highest threat it stirs'
              value={Math.max(0, ...view.feared.map((row) => row.threat))}
              icon={THREAT_ICON}
              tone='danger'
            />
            <KpiTile
              label='Crises'
              value={
                view.crises.filter((row) => row.state === 'escalating').length
              }
              icon={CRISIS_ICON}
              tone='warning'
            />
            <KpiTile
              label='Spheres'
              value={view.spheres.length}
              icon={SPHERE_ICON}
              tone='info'
            />
            <KpiTile
              label='Subjects'
              value={view.subjects.length}
              icon={SUBJECT_ICON}
              tone='gold'
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <RefLink node={realm} />
            {view.standing && <Tag spec={spec(STANDINGS, view.standing)} />}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
            <MindCard
              title='Threat and trust'
              icon={THREAT_ICON}
              hint={`Conquests, wars without a claim and broken treaties raise threat; kept treaties and summits raise trust. Realms that all feel threat of ${view.coalition_threshold} or more toward one realm band into a coalition against it.`}
            >
              <Label variant='overline'>How others regard it</Label>
              {view.feared.length === 0 ? (
                <Muted variant='caption'>
                  No realm has taken its measure yet.
                </Muted>
              ) : (
                <Paged
                  items={view.feared}
                  initial={3}
                  noun={['realm', 'realms']}
                >
                  {(row) => (
                    <RegardRow
                      key={`${row.holder.id}-${row.subject.id}`}
                      row={row}
                      ctx={ctx}
                      threshold={view.coalition_threshold}
                    />
                  )}
                </Paged>
              )}
              <Label variant='overline'>How it regards others</Label>
              {view.felt.length === 0 ? (
                <Muted variant='caption'>
                  It has taken no other realm's measure yet.
                </Muted>
              ) : (
                <Paged items={view.felt} initial={3} noun={['realm', 'realms']}>
                  {(row) => (
                    <RegardRow
                      key={`${row.holder.id}-${row.subject.id}`}
                      row={row}
                      ctx={ctx}
                      threshold={view.coalition_threshold}
                    />
                  )}
                </Paged>
              )}
              <AddRegard ctx={ctx} realmId={realm.id} />
            </MindCard>
            <CapacityCard ctx={ctx} realmId={realm.id} />
            <MindCard
              title='Crises'
              icon={CRISIS_ICON}
              hint='A demand opens a crisis. Each epoch other realms back a side; the weaker side backs down or concedes, and if neither yields by the last step it becomes war, with every backer in it.'
            >
              {view.crises.length === 0 ? (
                <Muted variant='caption'>No crisis touches this realm.</Muted>
              ) : (
                <Paged
                  items={view.crises}
                  initial={3}
                  noun={['crisis', 'crises']}
                >
                  {(row) => <CrisisRow key={row.id} row={row} ctx={ctx} />}
                </Paged>
              )}
              <OpenCrisis ctx={ctx} realmId={realm.id} />
            </MindCard>
            <MindCard
              title='Spheres of influence'
              icon={SPHERE_ICON}
              hint='Great powers draw weaker neighbours into their spheres, favour them in trade and go to war for them; a client claimed by two powers slips toward the stronger.'
            >
              {view.spheres.length === 0 ? (
                <Muted variant='caption'>
                  It holds no sphere and lies in none.
                </Muted>
              ) : (
                <Paged
                  items={view.spheres}
                  initial={4}
                  noun={['sphere', 'spheres']}
                >
                  {(row) => (
                    <SphereRow
                      key={`${row.power.id}-${row.client.id}`}
                      row={row}
                      ctx={ctx}
                    />
                  )}
                </Paged>
              )}
              <AddSphere ctx={ctx} realmId={realm.id} />
            </MindCard>
            <MindCard
              title='Subjects and overlords'
              icon={SUBJECT_ICON}
              hint='Vassals pay tribute and send levies, tributaries only pay, marches only fight, colonies do both from afar, and personal unions, clients and protectorates owe neither. A subject wishing hard for liberty asks for better terms or rises.'
            >
              {view.subjects.length === 0 ? (
                <Muted variant='caption'>
                  It is no one's subject and holds none.
                </Muted>
              ) : (
                <Paged
                  items={view.subjects}
                  initial={4}
                  noun={['subject', 'subjects']}
                >
                  {(row) => (
                    <SubjectRow
                      key={row.vassal.id}
                      row={row}
                      ctx={ctx}
                      revolt={view.liberty_revolt}
                    />
                  )}
                </Paged>
              )}
            </MindCard>
          </div>
          <ControlPanel
            title='Hold what you set'
            note='Threat, trust, capacity, crisis steps, backers and spheres you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
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
