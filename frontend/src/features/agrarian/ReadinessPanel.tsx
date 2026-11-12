import { useState } from 'react'
import {
  Check,
  Coins,
  HandHeart,
  Hammer,
  Shield,
  ShieldCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, MANY, SPAN } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type AgrarianNodeView, useAgrarianAction } from './api'
import { AID_KINDS, CAUSES, PLANS, WORKS } from './labels'
import {
  GIVER_TYPES,
  HOLDER_TYPES,
  useAgrarianRow,
  useAgrarianStep,
} from './model'

type Work = AgrarianNodeView['works'][number]
type Aid = AgrarianNodeView['aid'][number]
type Rebuild = AgrarianNodeView['rebuilds'][number]

const NOT_TOWN = 'Only a settlement raises works, receives aid and rebuilds'
const MOST_LEVEL = 5
const GODS = ['son', 'foreign_god', 'creator'] as const
const NO_TYPES = [] as const
const MORTALS = ['mortal'] as const

function WorkCard({ row, blocked }: { row: Work; blocked: string | null }) {
  const action = useAgrarianRow(
    'preparedness:edit',
    'preparedness:delete',
    { settlement_id: row.settlement.id, kind: row.kind },
    blocked
  )
  const kind = WORKS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label} of ${row.settlement.name}, level ${row.level}`}
      caption={`Raised in epoch ${row.built_epoch} · held ${row.averted} times`}
      removeLabel='Tear it down'
      editTitle='Set the work'
      note='Each level of a fitting work lowers the losses of its disaster: levees and seawalls against floods, seawalls against storms, drills against quakes and eruptions, stockpiles against drought and failed harvests, firebreaks against great fires; watchtowers help a little against all. Works wear down and must be raised again; towns pay from their investment, and a realm can order a town to prepare by mandate.'
      fields={[
        {
          key: 'level',
          label: 'Level',
          kind: 'number',
          min: 0,
          max: MOST_LEVEL,
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'averted',
          label: 'Times it held',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Level'
        value={row.level}
        max={MOST_LEVEL}
        tone='info'
        icon={Shield}
      />
      <Meter
        label='Condition'
        value={row.condition}
        tone='success'
        icon={ShieldCheck}
      />
    </Held>
  )
}

function AidCard({ row, blocked }: { row: Aid; blocked: string | null }) {
  const action = useAgrarianRow(
    'relief:edit',
    'relief:delete',
    { aid_id: row.id },
    blocked
  )
  const kind = AID_KINDS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={row.refused ? 'danger' : kind.tone}
      title={`${row.giver.name} sent ${kind.label.toLowerCase()} to ${row.receiver.name}`}
      caption={`${row.refused ? 'Turned away' : 'Received'} in epoch ${row.epoch}`}
      removeLabel='Strike out the record'
      editTitle='Set the aid'
      note='Aid after a disaster brings grain from the giver’s capital and restores prosperity, heals the land or speeds rebuilding. The stricken owe the giver a favour and a gift in return, and love the giver’s god more. A rival’s aid may be turned away, at a cost to the ruler’s face.'
      fields={[
        {
          key: 'kind',
          label: 'What was sent',
          kind: 'pick',
          table: table(AID_KINDS),
        },
        {
          key: 'amount',
          label: 'Coin it carried',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'god_node_id',
          label: 'God of the giver',
          kind: 'node',
          types: NO_TYPES,
          kinds: GODS,
        },
        { key: 'refused', label: 'Turned away', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Disaster',
            <Ref key='event' node={row.event} empty='sent unasked' />,
          ],
          ['Giver', <Ref key='giver' node={row.giver} />],
          ['Stricken town', <Ref key='receiver' node={row.receiver} />],
          ['God of the giver', <Ref key='god' node={row.god} empty='no god' />],
          ['Coin it carried', String(row.amount)],
        ]}
      />
    </Held>
  )
}

function RebuildCard({
  row,
  blocked,
}: {
  row: Rebuild
  blocked: string | null
}) {
  const action = useAgrarianRow(
    'reconstruction:edit',
    'reconstruction:delete',
    { rebuild_id: row.id },
    blocked
  )
  const finishing = useAgrarianStep(
    'reconstruction:finish',
    { rebuild_id: row.id },
    row.finished_epoch !== null ? 'It is already rebuilt' : blocked,
    'Rebuilt'
  )
  const cause = CAUSES[row.cause]
  const plan = PLANS[row.plan]
  return (
    <Held
      icon={cause.icon}
      tone={plan.tone}
      title={`${row.settlement.name} rebuilding after a ${cause.label.toLowerCase()}`}
      caption={`${plan.label} · begun in epoch ${row.started_epoch}${row.finished_epoch !== null ? ` · finished in epoch ${row.finished_epoch}` : ''}`}
      removeLabel='Abandon the rebuilding'
      editTitle='Set the rebuilding'
      note='A planned rebuilding needs coin and a planner and rises in stone with wider streets on a grid, burning less; a hasty one is quick and keeps the old risks. Elites may seize the burned land and put folk out of their homes.'
      fields={[
        {
          key: 'cause',
          label: 'Ruined by',
          kind: 'pick',
          table: table(CAUSES),
        },
        {
          key: 'plan',
          label: 'How it is rebuilt',
          kind: 'pick',
          table: table(PLANS),
        },
        { key: 'cost', label: 'Cost', kind: 'number', min: 0, max: MANY },
        { key: 'paid', label: 'Paid', kind: 'number', min: 0, max: MANY },
        {
          key: 'progress',
          label: 'Rebuilt (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'planner_entity_id',
          label: 'Planner',
          kind: 'node',
          types: MORTALS,
        },
        {
          key: 'seized_by_node_id',
          label: 'Seized by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'seized',
          label: 'Folk put out of their homes',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <StepButton
          icon={Check}
          label='Finish it now'
          busy={finishing.busy}
          onClick={finishing.run}
        />
      }
    >
      <Meter
        label='Rebuilt'
        value={row.progress}
        tone='success'
        icon={Hammer}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-3'>
          <KpiTile label='Cost' value={row.cost} icon={Coins} tone='gold' />
          <KpiTile label='Paid' value={row.paid} icon={Coins} tone='success' />
          <KpiTile
            label='Folk put out'
            value={row.seized}
            icon={HandHeart}
            tone='danger'
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Planner',
            <Ref key='planner' node={row.planner} empty='no planner' />,
          ],
          [
            'Seized by',
            <Ref key='seizer' node={row.seized_by} empty='no one' />,
          ],
        ]}
      />
    </Held>
  )
}

function ReadinessForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const gate = kind === 'settlement' ? blocked : NOT_TOWN
  const [work, setWork] = useState<keyof typeof WORKS>('levee')
  const [level, setLevel] = useState('1')
  const [giver, setGiver] = useState<number | null>(null)
  const [aid, setAid] = useState<keyof typeof AID_KINDS>('goods')
  const [amount, setAmount] = useState('200')
  const [cause, setCause] = useState<keyof typeof CAUSES>('fire')
  const [plan, setPlan] = useState<keyof typeof PLANS>('planned')
  const building = useAgrarianAction(
    'preparedness:build',
    (_: void) => ({
      settlement_id: nodeId,
      kind: work,
      level: clamp(level, MOST_LEVEL, 1),
    }),
    'The work is raised'
  )
  const sending = useAgrarianAction(
    'relief:send',
    (_: void) => ({
      giver_id: giver ?? 0,
      settlement_id: nodeId,
      kind: aid,
      amount: clamp(amount, MANY),
    }),
    'Aid is sent'
  )
  const rebuilding = useAgrarianAction(
    'reconstruction:begin',
    (_: void) => ({ settlement_id: nodeId, cause, plan }),
    'The rebuilding begins'
  )
  const buildBusy = why(gate, building.isPending)
  const sendBusy = why(
    kind === 'settlement'
      ? giver === null
        ? 'Choose a realm or cult to send it'
        : blocked
      : NOT_TOWN,
    sending.isPending
  )
  const rebuildBusy = why(gate, rebuilding.isPending)
  return (
    <ForgeCard
      icon={Shield}
      tone='info'
      title='Prepare, relieve and rebuild'
      note='Raise a work against disaster, send aid to this town from a realm or cult, or set it rebuilding.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={buildBusy !== null}
            disabledReason={buildBusy ?? undefined}
            onClick={() => building.mutate()}
          >
            <Shield />
            Raise the work
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={sendBusy !== null}
            disabledReason={sendBusy ?? undefined}
            onClick={() => sending.mutate()}
          >
            <HandHeart />
            Send aid
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={rebuildBusy !== null}
            disabledReason={rebuildBusy ?? undefined}
            onClick={() => rebuilding.mutate()}
          >
            <Hammer />
            Begin rebuilding
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Work'
        value={work}
        table={table(WORKS)}
        blocked={gate}
        onPick={(value) => setWork(value as keyof typeof WORKS)}
      />
      <NumberField
        label='Level'
        value={level}
        min={1}
        max={MOST_LEVEL}
        blocked={gate}
        onChange={setLevel}
      />
      <NodePicker
        label='Giver of aid'
        value={giver}
        onChange={setGiver}
        blocked={gate}
        types={GIVER_TYPES}
      />
      <MindPicker
        label='Aid sent'
        value={aid}
        table={table(AID_KINDS)}
        blocked={gate}
        onPick={(value) => setAid(value as keyof typeof AID_KINDS)}
      />
      <NumberField
        label='Coin it carries'
        value={amount}
        min={0}
        max={MANY}
        blocked={gate}
        onChange={setAmount}
      />
      <MindPicker
        label='Ruined by'
        value={cause}
        table={table(CAUSES)}
        blocked={gate}
        onPick={(value) => setCause(value as keyof typeof CAUSES)}
      />
      <MindPicker
        label='How it is rebuilt'
        value={plan}
        table={table(PLANS)}
        blocked={gate}
        onPick={(value) => setPlan(value as keyof typeof PLANS)}
      />
    </ForgeCard>
  )
}

export function ReadinessPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: AgrarianNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='ReadinessPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Works against disaster'
        items={data.works}
        empty='No works against disaster stand here.'
        noun={['work', 'works']}
        itemKey={(item) => item.kind}
      >
        {(item) => <WorkCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Aid'
        items={data.aid}
        empty='No aid was sent or received here.'
        noun={['gift of aid', 'gifts of aid']}
        itemKey={(item) => item.id}
      >
        {(item) => <AidCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Rebuilding'
        items={data.rebuilds}
        empty='Nothing here waits to be rebuilt.'
        noun={['rebuilding', 'rebuildings']}
        itemKey={(item) => item.id}
      >
        {(item) => <RebuildCard row={item} blocked={blocked} />}
      </Listed>
      <ReadinessForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}
