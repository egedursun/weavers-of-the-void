import { useState } from 'react'
import { Fingerprint, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type BelongingNodeView, useBelongingAction } from './api'
import { DRIVERS, LAYERS } from './labels'
import {
  SPAN,
  VALUE_KINDS,
  VALUE_TYPES,
  useBelongingRow,
  useBelongingStep,
} from './model'

type View = BelongingNodeView
type Identity = View['identities'][number]

const HOLDERS = ['mortal', 'settlement', 'people']

function valueName(row: Identity): string {
  return row.value?.name ?? row.value_label ?? 'no single value'
}

function IdentityCard({
  row,
  holderId,
  blocked,
}: {
  row: Identity
  holderId: number
  blocked: string | null
}) {
  const action = useBelongingRow(
    'held_identity:edit',
    'held_identity:delete',
    { holder_id: holderId, layer: row.layer },
    blocked
  )
  const layer = LAYERS[row.layer]
  const driver = DRIVERS[row.driver]
  return (
    <Held
      icon={layer.icon}
      tone={layer.tone}
      title={`${layer.label}: ${valueName(row)}`}
      caption={`Matters ${row.salience} of ${SPAN} · moved by ${driver.label.toLowerCase()} · held at ${row.strength} · read in epoch ${row.updated_epoch}`}
      removeLabel='Let it go'
      editTitle='Set the identity'
      note='The identity that matters most decides whom its holder trusts, how loyal a town stays to its realm and along which line a realm divides. Holy war, hunger, invasion, strikes, preaching and segregation make a layer matter more; marriages across its lines make it matter less.'
      fields={[
        {
          key: 'value_node_id',
          label: 'Held with',
          kind: 'node',
          types: VALUE_TYPES,
          kinds: VALUE_KINDS,
        },
        { key: 'value_label', label: 'Or named as', kind: 'text' },
        {
          key: 'strength',
          label: 'How firmly held',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'salience',
          label: 'How much it matters',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'driver',
          label: 'What moves it',
          kind: 'pick',
          table: table(DRIVERS),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Badge size='sm' variant='secondary'>
          {driver.label}
        </Badge>
      }
    >
      <Facts
        items={[
          [
            'Held with',
            row.value ? (
              <Ref key='value' node={row.value} empty='no single value' />
            ) : (
              valueName(row)
            ),
          ],
        ]}
      />
      <Meter
        label={`Matters (${row.salience} of ${SPAN})`}
        value={row.salience}
        tone={row.salience >= SPAN / 2 ? 'warning' : 'info'}
        icon={layer.icon}
      />
    </Held>
  )
}

export function IdentityPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const [layer, setLayer] = useState('faith')
  const [salience, setSalience] = useState(String(SPAN / 2))
  const holds = HOLDERS.includes(kind ?? '')
  const setting = useBelongingAction(
    'held_identity:set',
    (_: void) => ({
      holder_id: nodeId,
      layer: layer as Identity['layer'],
      salience: Math.max(0, Math.min(SPAN, Number(salience) || 0)),
      driver: 'god' as const,
    }),
    'The identity is set'
  )
  const reading = useBelongingStep(
    'belonging:run',
    blocked,
    'Every identity and peer group is read'
  )
  const setBusy = why(
    blocked ??
      (!holds ? 'Only a mortal, a town or a people holds identities' : null),
    setting.isPending
  )
  const sorted = [...data.identities].sort(
    (left, right) => right.salience - left.salience
  )
  return (
    <div data-surface='IdentityPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={data.realm} empty='no realm' />],
          [
            'Divides along',
            data.fault_layer ? LAYERS[data.fault_layer].label : 'no fault line',
          ],
        ]}
      />
      <Bars
        chart='chart-identities'
        title='How much each identity matters'
        legend={[
          { text: 'Matters', variant: 'warning' },
          { text: 'Held firmly', variant: 'success' },
        ]}
        rows={sorted.map((row) => ({
          key: row.layer,
          caption: `${LAYERS[row.layer].label}: ${valueName(row)}, matters ${row.salience}`,
          segments: [
            { value: row.salience, fill: 'fill-warning' },
            { value: row.strength, fill: 'fill-success' },
          ],
        }))}
        max={SPAN * 2}
        noun={['identity', 'identities']}
        empty='No identity has been read for this yet.'
      />
      <Listed
        title='Identities'
        items={sorted}
        empty='No identity has been read for this yet.'
        noun={['identity', 'identities']}
        itemKey={(item) => item.layer}
      >
        {(item) => (
          <IdentityCard row={item} holderId={nodeId} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Fingerprint}
        tone='gold'
        title='Stir an identity'
        note='Set how much one identity matters to this; the engine moves it from there by what befalls it.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Fingerprint}
              label='Read identities now'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              act={setting}
              size='sm'
              disabled={setBusy !== null}
              disabledReason={setBusy ?? undefined}
              onClick={() => setting.mutate()}
            >
              <Plus />
              Set it
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Identity'
          value={layer}
          table={table(LAYERS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setLayer}
        />
        <NumberField
          label='How much it matters (0 to 100)'
          value={salience}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setSalience}
        />
      </ForgeCard>
    </div>
  )
}
