import { useState } from 'react'
import { Gavel, Landmark, Plus, Scale } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type BelongingNodeView, useBelongingAction } from './api'
import { FUGITIVES, SANCTUARY_KINDS, STATES } from './labels'
import {
  HOST_TYPES,
  MANY,
  MORTAL_TYPES,
  PURSUER_TYPES,
  SPAN,
  useBelongingRow,
  useBelongingStep,
} from './model'

type View = BelongingNodeView
type Refuge = View['sanctuaries'][number]
type Law = NonNullable<View['sanctuary_law']>

function RefugeCard({ row, blocked }: { row: Refuge; blocked: string | null }) {
  const action = useBelongingRow(
    'sanctuary:edit',
    'sanctuary:delete',
    { record_id: row.id },
    blocked
  )
  const kind = SANCTUARY_KINDS[row.kind]
  const state = STATES[row.state]
  return (
    <Held
      icon={kind.icon}
      tone={state.tone}
      title={`${row.fugitive.name} in ${row.host.name}`}
      caption={`${kind.label} · ${FUGITIVES[row.fugitive_kind].label.toLowerCase()} · ${state.label.toLowerCase()} · fee ${row.fee} · since epoch ${row.granted_epoch}`}
      removeLabel='End the sanctuary'
      editTitle='Set the sanctuary'
      note='While sheltered, no one may seize or punish the fugitive, who pays its host each epoch. The pursuer may wait, bargain a price with the host, surround the refuge until the fugitive gives up, or break in at the cost of infamy and the wrath of the god of the place.'
      fields={[
        {
          key: 'host_entity_id',
          label: 'Host',
          kind: 'node',
          types: HOST_TYPES,
        },
        {
          key: 'kind',
          label: 'Kind of refuge',
          kind: 'pick',
          table: table(SANCTUARY_KINDS),
        },
        {
          key: 'fugitive_kind',
          label: 'Fled as',
          kind: 'pick',
          table: table(FUGITIVES),
        },
        {
          key: 'pursuer_entity_id',
          label: 'Pursuer',
          kind: 'node',
          types: PURSUER_TYPES,
        },
        { key: 'state', label: 'State', kind: 'pick', table: table(STATES) },
        {
          key: 'fee',
          label: 'Fee each epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'siege_epochs',
          label: 'Epochs besieged',
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
        <Badge size='sm' variant='secondary'>
          {state.label}
        </Badge>
      }
    >
      <Facts
        items={[
          [
            'Fugitive',
            <Ref key='fugitive' node={row.fugitive} empty='no one' />,
          ],
          ['Host', <Ref key='host' node={row.host} empty='no one' />],
          ['Pursuer', <Ref key='pursuer' node={row.pursuer} empty='no one' />],
        ]}
      />
      <Meter
        label={`Besieged (${plural(row.siege_epochs, 'epoch', 'epochs')})`}
        value={row.siege_epochs}
        max={Math.max(3, row.siege_epochs)}
        tone={row.state === 'besieged' ? 'warning' : 'info'}
        icon={Landmark}
      />
    </Held>
  )
}

function LawCard({
  row,
  polityId,
  blocked,
}: {
  row: Law
  polityId: number
  blocked: string | null
}) {
  const action = useBelongingRow(
    'sanctuary_law:edit',
    'sanctuary_law:delete',
    { polity_id: polityId },
    blocked
  )
  return (
    <Held
      icon={Scale}
      tone={row.restricted ? 'warning' : 'success'}
      title={
        row.restricted
          ? 'Temples may not shelter fugitives'
          : 'Temples may shelter fugitives'
      }
      caption={`The realm takes ${row.fee_pct}% of sanctuary fees`}
      removeLabel='Strike the law'
      editTitle='Set the law of sanctuary'
      note='A realm may forbid its temples to shelter fugitives, and may take a share of the fees its hosts are paid.'
      fields={[
        {
          key: 'restricted',
          label: 'Temples forbidden to shelter',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'fee_pct',
          label: 'Share of fees (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function SanctuaryPanel({
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
  const realm = kind === 'polity'
  const hosting = (HOST_TYPES as readonly string[]).includes(kind ?? '')
  const [fugitive, setFugitive] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [host, setHost] = useState<number | null>(hosting ? nodeId : null)
  const [pursuer, setPursuer] = useState<number | null>(null)
  const [refuge, setRefuge] = useState('temple')
  const [fled, setFled] = useState('outlaw')
  const [share, setShare] = useState('0')
  const sheltering = useBelongingAction(
    'sanctuary:create',
    (_: void) => ({
      fugitive_entity_id: fugitive ?? 0,
      host_entity_id: host ?? 0,
      kind: refuge as Refuge['kind'],
      fugitive_kind: fled as Refuge['fugitive_kind'],
      pursuer_entity_id: pursuer,
    }),
    'The fugitive is sheltered'
  )
  const lawing = useBelongingAction(
    'sanctuary_law:set',
    (_: void) => ({
      polity_id: nodeId,
      restricted: true,
      fee_pct: Math.max(0, Math.min(SPAN, Number(share) || 0)),
    }),
    'The law of sanctuary is set'
  )
  const reading = useBelongingStep(
    'sanctuary:run',
    blocked,
    'Every sanctuary is read'
  )
  const shelterBusy = why(
    blocked ??
      (fugitive === null
        ? 'Choose the fugitive'
        : host === null
          ? 'Choose the host'
          : fugitive === host
            ? 'A fugitive cannot shelter with itself'
            : null),
    sheltering.isPending
  )
  const lawBusy = why(
    blocked ??
      (!realm
        ? 'Only a realm makes a law of sanctuary'
        : data.sanctuary_law
          ? 'The realm has its law already; adjust it above'
          : null),
    lawing.isPending
  )
  return (
    <div data-surface='SanctuaryPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-sanctuary'
        title='Sanctuaries and their sieges'
        legend={[
          { text: 'Fee', variant: 'success' },
          { text: 'Epochs besieged', variant: 'warning' },
        ]}
        rows={data.sanctuaries.map((row) => ({
          key: String(row.id),
          caption: `${row.fugitive.name} in ${row.host.name}: ${STATES[row.state].label.toLowerCase()}`,
          segments: [
            { value: row.fee, fill: 'fill-success' },
            { value: row.siege_epochs, fill: 'fill-warning' },
          ],
        }))}
        noun={['sanctuary', 'sanctuaries']}
        empty='No one shelters here, and no one this pursues is sheltered.'
      />
      <Listed
        title='Sanctuaries'
        items={data.sanctuaries}
        empty='No one shelters here, and no one this pursues is sheltered.'
        noun={['sanctuary', 'sanctuaries']}
        itemKey={(item) => item.id}
      >
        {(item) => <RefugeCard row={item} blocked={blocked} />}
      </Listed>
      {data.sanctuary_law && (
        <LawCard row={data.sanctuary_law} polityId={nodeId} blocked={blocked} />
      )}
      <ForgeCard
        icon={Landmark}
        tone='gold'
        title='Shelter a fugitive'
        note='A temple, a welcoming town or a foreign realm takes in someone who is hunted.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Landmark}
              label='Read sanctuaries now'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              act={sheltering}
              size='sm'
              disabled={shelterBusy !== null}
              disabledReason={shelterBusy ?? undefined}
              onClick={() => sheltering.mutate()}
            >
              <Plus />
              Shelter them
            </Button>
          </div>
        }
      >
        <NodePicker
          label='Fugitive'
          value={fugitive}
          onChange={setFugitive}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <NodePicker
          label='Host'
          value={host}
          onChange={setHost}
          blocked={blocked}
          types={HOST_TYPES}
        />
        <MindPicker
          label='Kind of refuge'
          value={refuge}
          table={table(SANCTUARY_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRefuge}
        />
        <MindPicker
          label='Fled as'
          value={fled}
          table={table(FUGITIVES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setFled}
        />
        <NodePicker
          label='Pursuer'
          value={pursuer}
          onChange={setPursuer}
          blocked={blocked}
          types={PURSUER_TYPES}
        />
      </ForgeCard>
      <ForgeCard
        icon={Gavel}
        tone='warning'
        title='Forbid temple sanctuary in this realm'
        note='The realm forbids its temples to shelter fugitives and takes a share of the fees its other hosts are paid.'
        columns={2}
        action={
          <Button
            act={lawing}
            size='sm'
            disabled={lawBusy !== null}
            disabledReason={lawBusy ?? undefined}
            onClick={() => lawing.mutate()}
          >
            <Plus />
            Make the law
          </Button>
        }
      >
        <NumberField
          label='Share of fees (%)'
          value={share}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setShare}
        />
      </ForgeCard>
    </div>
  )
}
