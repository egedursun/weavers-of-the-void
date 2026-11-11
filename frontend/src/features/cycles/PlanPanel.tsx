import { useState } from 'react'
import { ChevronsRight, Eye, EyeOff, Route, Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type PlanView, useCycleAction } from './api'
import { PLAN_KINDS, PLAN_STATUSES } from './labels'
import { clamp, MANY, SPAN, useRow, useStep } from './model'
import { StepButton } from './parts'

const TARGET_TYPES = [
  'region',
  'settlement',
  'people',
  'house',
  'polity',
] as const

export function PlanCard({
  row,
  blocked,
}: {
  row: PlanView
  blocked: string | null
}) {
  const action = useRow(
    'plan:edit',
    'plan:delete',
    { plan_id: row.id },
    blocked
  )
  const forward = useCycleAction(
    'plan:advance',
    (steps: number) => ({ plan_id: row.id, steps }),
    'The plan moves'
  )
  const exposing = useStep(
    'plan:expose',
    { plan_id: row.id },
    blocked,
    'The plan is laid bare'
  )
  const kind = PLAN_KINDS[row.kind]
  const status = PLAN_STATUSES[row.status]
  const busy = why(action.busy, forward.isPending)
  const moving = row.status === 'active' ? busy : 'The plan no longer moves'
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={row.name}
      caption={`${kind.label} · ${status.label} · begun in epoch ${row.started_epoch}${row.finished_epoch !== null ? `, ended in epoch ${row.finished_epoch}` : ''}`}
      removeLabel='Strike the plan'
      editTitle='Set the plan'
      note='Each epoch the holder pays a step and the plan moves on; the less secret it is the likelier it comes to light, and rivals then set it back. It passes to the next ruler or leader when its carrier dies.'
      fields={[
        { key: 'name', label: 'Called', kind: 'text' },
        { key: 'kind', label: 'Aim', kind: 'pick', table: table(PLAN_KINDS) },
        {
          key: 'target_node_id',
          label: 'Aimed at',
          kind: 'node',
          types: TARGET_TYPES,
        },
        {
          key: 'carrier_node_id',
          label: 'Carried by',
          kind: 'node',
          types: ['mortal', 'faction', 'cult'],
          kinds: ['son', 'foreign_god'],
        },
        { key: 'steps', label: 'Steps in all', kind: 'number', min: 1 },
        { key: 'progress', label: 'Steps taken', kind: 'number', min: 0 },
        { key: 'step_cost', label: 'Coin per step', kind: 'number', min: 0 },
        { key: 'secrecy', label: 'Secrecy', kind: 'number', min: 0, max: SPAN },
        {
          key: 'exposed',
          label: 'Come to light',
          kind: 'pick',
          table: { true: 'Yes', false: 'No' },
        },
        {
          key: 'status',
          label: 'Standing',
          kind: 'pick',
          table: table(PLAN_STATUSES),
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={status.icon}>{status.label}</Chip>
          <Chip icon={row.exposed ? Eye : EyeOff}>
            {row.exposed ? 'Come to light' : `Secrecy ${row.secrecy}`}
          </Chip>
        </>
      }
    >
      <Meter
        label={`${row.progress} of ${row.steps} steps`}
        value={row.progress}
        max={Math.max(1, row.steps)}
        tone='info'
        icon={Route}
      />
      <Facts
        items={[
          ['Held by', <Ref key='holder' node={row.holder} />],
          [
            'Begun by',
            <Ref key='author' node={row.author} empty='its holder' />,
          ],
          [
            'Carried by',
            <Ref key='carrier' node={row.carrier} empty='its holder' />,
          ],
          [
            'Aimed at',
            <Ref key='target' node={row.target} empty='nothing named' />,
          ],
          ['Coin per step', row.step_cost],
        ]}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={ChevronsRight}
          label='A step forward'
          busy={moving}
          onClick={() => forward.mutate(1)}
        />
        <StepButton
          icon={Undo2}
          label='A step back'
          busy={
            moving === null && row.progress === 0
              ? 'No step has been taken'
              : moving
          }
          onClick={() => forward.mutate(-1)}
        />
        <StepButton
          icon={Eye}
          label='Lay it bare'
          busy={row.exposed ? 'It has already come to light' : exposing.busy}
          onClick={exposing.run}
        />
      </div>
    </Held>
  )
}

function PlanForge({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [kind, setKind] = useState<keyof typeof PLAN_KINDS>('wonder')
  const [name, setName] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const [steps, setSteps] = useState('10')
  const [cost, setCost] = useState('10')
  const [secrecy, setSecrecy] = useState('50')
  const creating = useCycleAction(
    'plan:create',
    (_: void) => ({
      holder_id: holderId,
      kind,
      name: name.trim(),
      target_id: target,
      steps: clamp(steps, 10_000, 1),
      step_cost: clamp(cost, MANY),
      secrecy: clamp(secrecy),
    }),
    'The plan is set in motion'
  )
  const busy = why(
    blocked ?? (name.trim() === '' ? 'Name the plan first' : null),
    creating.isPending
  )
  return (
    <ForgeCard
      icon={Route}
      tone='gold'
      title='Set a long plan in motion'
      note='A plan outlives its author: remake a land, breed a line, turn a world to a faith or save for a wonder.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => creating.mutate()}
        >
          <Route />
          Begin it
        </Button>
      }
    >
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`plan-name-${holderId}`}>Called</FieldLabel>
        <Input
          id={`plan-name-${holderId}`}
          value={name}
          disabled={blocked !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <MindPicker
        label='Aim'
        value={kind}
        table={table(PLAN_KINDS)}
        blocked={blocked}
        onPick={(value) => setKind(value as keyof typeof PLAN_KINDS)}
      />
      <NodePicker
        label='Aimed at'
        value={target}
        onChange={setTarget}
        blocked={blocked}
        types={TARGET_TYPES}
      />
      <NumberField
        label='Steps'
        value={steps}
        min={1}
        blocked={blocked}
        onChange={setSteps}
      />
      <NumberField
        label='Coin per step'
        value={cost}
        min={0}
        blocked={blocked}
        onChange={setCost}
      />
      <NumberField
        label='Secrecy'
        value={secrecy}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setSecrecy}
      />
    </ForgeCard>
  )
}

export function PlanPanel({
  nodeId,
  plans,
  blocked,
}: {
  nodeId: number
  plans: PlanView[]
  blocked: string | null
}) {
  return (
    <div data-surface='PlanPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Long plans'
        items={plans}
        empty='No long plan is held, carried or aimed here.'
        noun={['plan', 'plans']}
        itemKey={(item) => item.id}
      >
        {(item) => <PlanCard row={item} blocked={blocked} />}
      </Listed>
      <PlanForge holderId={nodeId} blocked={blocked} />
    </div>
  )
}
