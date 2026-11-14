import { useState } from 'react'
import { Eye, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type NatureNodeView, useNatureAction } from './api'
import { SENSES } from './labels'
import { SPAN, useNatureRow } from './model'

type View = NatureNodeView
type Sense = View['senses'][number]

function SenseCard({
  row,
  holderId,
  blocked,
}: {
  row: Sense
  holderId: number
  blocked: string | null
}) {
  const action = useNatureRow(
    'sense:edit',
    'sense:delete',
    { holder_id: holderId, sense: row.sense },
    blocked
  )
  const sense = SENSES[row.sense]
  return (
    <Held
      icon={sense.icon}
      tone={sense.tone}
      title={sense.label}
      caption={`Acuity ${row.acuity} of ${SPAN}`}
      removeLabel='Take the sense away'
      editTitle='Set the sense'
      note='Smell, hearing and spirit sight find agents among the folk; night vision, echolocation and heat sense strengthen an army at night; hearing, smell and vibration blunt ambushes; smell, sight, heat and vibration track game; a sense of direction and sight spare ships at sea; spirit sight uncovers the spies of gods.'
      fields={[
        { key: 'acuity', label: 'Acuity', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Acuity (${row.acuity} of ${SPAN})`}
        value={row.acuity}
        tone='info'
        icon={sense.icon}
      />
    </Held>
  )
}

export function SensesPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const holder = data.sense_holder
  const [sense, setSense] = useState('sight')
  const [acuity, setAcuity] = useState('60')
  const giving = useNatureAction(
    'sense:set',
    (_: void) => ({
      holder_id: holder?.id ?? 0,
      sense: sense as Sense['sense'],
      acuity: Math.max(0, Math.min(SPAN, Number(acuity) || 0)),
    }),
    'The sense is given'
  )
  const giveBusy = why(
    blocked ??
      (holder === null
        ? 'This thing has no kind or people whose senses it shares'
        : null),
    giving.isPending
  )
  return (
    <div data-surface='SensesPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          [
            'Senses of',
            <Ref key='holder' node={holder} empty='no kind or people' />,
          ],
        ]}
      />
      <Bars
        chart='chart-senses'
        title='How keen each sense is'
        legend={[{ text: 'Acuity', variant: 'success' }]}
        rows={data.senses.map((row) => ({
          key: row.sense,
          caption: `${SENSES[row.sense].label}: ${row.acuity}`,
          segments: [{ value: row.acuity, fill: 'fill-success' }],
        }))}
        max={SPAN}
        noun={['sense', 'senses']}
        empty='No sense has been read for this yet; the living nature step reads them, or give one below.'
      />
      <Listed
        title='Senses'
        items={data.senses}
        empty='No sense has been read for this yet.'
        noun={['sense', 'senses']}
        itemKey={(item) => item.sense}
      >
        {(item) => (
          <SenseCard row={item} holderId={holder?.id ?? 0} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Eye}
        tone='info'
        title='Give a sense'
        note={`${holder ? holder.name : 'The kind or people'} gains a sense, or has one set to this acuity.`}
        columns={2}
        action={
          <Button
            size='sm'
            disabled={giveBusy !== null}
            disabledReason={giveBusy ?? undefined}
            onClick={() => giving.mutate()}
          >
            <Plus />
            Give it
          </Button>
        }
      >
        <MindPicker
          label='Sense'
          value={sense}
          table={table(SENSES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSense}
        />
        <NumberField
          label='Acuity'
          value={acuity}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setAcuity}
        />
      </ForgeCard>
    </div>
  )
}
