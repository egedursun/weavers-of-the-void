import { useState } from 'react'
import { Brain, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type FolkwaysNodeView, useFolkwaysAction } from './api'
import { BIASES, DECISIONS } from './labels'
import { MIDDLE, SPAN, useFolkwaysRow, useFolkwaysStep } from './model'

type Bias = FolkwaysNodeView['biases'][number]

const DECIDERS = ['mortal', 'son', 'foreign_god']
const NOT_A_DECIDER =
  'Only those who decide carry biases: mortals and gods; places, peoples, worlds and stars decide nothing'

function BiasCard({
  nodeId,
  row,
  blocked,
}: {
  nodeId: number
  row: Bias
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'bias_weight:edit',
    'bias_weight:delete',
    { holder_id: nodeId, bias: row.bias },
    blocked
  )
  const spec = BIASES[row.bias]
  const decision = row.last_decision ? DECISIONS[row.last_decision] : null
  const lean =
    row.weight > MIDDLE ? 'strong' : row.weight < MIDDLE ? 'faint' : 'level'
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`Weight ${row.weight} of ${SPAN}, ${lean}`}
      removeLabel='Strike the bias'
      editTitle='Set the bias'
      note='A bias is read each epoch from character and stress and drifts toward it unless you hold it. Above the middle it pushes the decisions it touches; below it, it pulls them back. Strategy and tactics dampen it.'
      fields={[
        { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={decision ? <Tag item={decision} /> : undefined}
    >
      <Meter
        label={`Weight (${row.weight} of ${SPAN})`}
        value={row.weight}
        tone={row.weight > MIDDLE ? 'warning' : 'info'}
        icon={spec.icon}
      />
      <Facts
        items={[
          [
            'Last decision it swayed',
            decision
              ? `${decision.label} in epoch ${row.last_epoch ?? 0}, by ${row.last_shift > 0 ? '+' : ''}${row.last_shift}%`
              : 'none yet',
          ],
        ]}
      />
    </Held>
  )
}

export function BiasPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: FolkwaysNodeView
  blocked: string | null
}) {
  const decider = kind !== null && DECIDERS.includes(kind)
  const [bias, setBias] = useState<string>('overconfidence')
  const [weight, setWeight] = useState('70')
  const setting = useFolkwaysAction(
    'bias_weight:set',
    (_: void) => ({
      holder_id: nodeId,
      bias: bias as Bias['bias'],
      weight: Number(weight || '0'),
    }),
    'The bias is set'
  )
  const reading = useFolkwaysStep(
    'bias:read',
    { holder_id: nodeId },
    blocked ?? (decider ? null : NOT_A_DECIDER),
    'Its biases are read'
  )
  const setBusy = why(
    blocked ?? (decider ? null : NOT_A_DECIDER),
    setting.isPending
  )
  return (
    <div data-surface='BiasPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-biases'
        title='How it leans'
        legend={[
          { text: 'Strong', variant: 'warning' },
          { text: 'Faint', variant: 'secondary' },
        ]}
        rows={data.biases.map((row) => ({
          key: row.bias,
          caption: `${BIASES[row.bias].label}: ${row.weight}`,
          segments: [
            {
              value: row.weight,
              fill: row.weight > MIDDLE ? 'fill-warning' : 'fill-info',
            },
          ],
        }))}
        max={SPAN}
        noun={['bias', 'biases']}
        empty='No biases are read for this thing.'
      />
      <Listed
        title='Biases'
        items={data.biases}
        empty='No biases are read for this thing.'
        noun={['bias', 'biases']}
        itemKey={(item) => item.bias}
      >
        {(item) => <BiasCard nodeId={nodeId} row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Brain}
        tone='info'
        title='Sway how it decides'
        note='Set a bias by hand, or read every bias from its character now. Biases lean war, peace, surrender, schemes, belief, conversion, migration and the goals of gods.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Brain}
              label='Read its biases'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              size='sm'
              disabled={setBusy !== null}
              disabledReason={setBusy ?? undefined}
              onClick={() => setting.mutate()}
            >
              <Plus />
              Set the bias
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Bias'
          value={bias}
          table={table(BIASES)}
          placeholder='Choose a bias'
          blocked={blocked}
          onPick={setBias}
        />
        <NumberField
          label='Weight'
          value={weight}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setWeight}
        />
      </ForgeCard>
    </div>
  )
}
