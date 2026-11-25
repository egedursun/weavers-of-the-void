import { useState } from 'react'
import { Handshake, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type NatureNodeView, useNatureAction } from './api'
import { BOND_HINTS, BONDS } from './labels'
import { KIND_TYPES, SPAN, useNatureRow } from './model'

type View = NatureNodeView
type Bond = View['bonds'][number]

function BondCard({ row, blocked }: { row: Bond; blocked: string | null }) {
  const action = useNatureRow(
    'species_relation:edit',
    'species_relation:delete',
    { record_id: row.id },
    blocked
  )
  const bond = BONDS[row.kind]
  return (
    <Held
      icon={bond.icon}
      tone={bond.tone}
      title={`${row.first.name} and ${row.second.name}`}
      caption={`${bond.label} · strength ${row.strength} · since epoch ${row.since_epoch} · ${BOND_HINTS[row.kind].toLowerCase()}`}
      removeLabel='Break the bond'
      editTitle='Set the bond'
      note='Mutualists give each other room where they share a land; the beneficiary of commensalism gains room; a parasite drains its host and takes the livestock of towns where the host is a herd; a mimic is spared by hunters where its model lives.'
      fields={[
        {
          key: 'first_species_id',
          label: 'First kind',
          kind: 'node',
          types: KIND_TYPES,
        },
        {
          key: 'second_species_id',
          label: 'Second kind',
          kind: 'node',
          types: KIND_TYPES,
        },
        { key: 'kind', label: 'Bond', kind: 'pick', table: table(BONDS) },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['First kind', <Ref key='first' node={row.first} empty='no kind' />],
          [
            'Second kind',
            <Ref key='second' node={row.second} empty='no kind' />,
          ],
        ]}
      />
      <Meter
        label={`Strength (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='success'
        icon={bond.icon}
      />
    </Held>
  )
}

export function BondsPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const own = data.kind_profile !== null
  const [first, setFirst] = useState<number | null>(own ? data.node.id : null)
  const [second, setSecond] = useState<number | null>(null)
  const [bond, setBond] = useState('mutualism')
  const [strength, setStrength] = useState('40')
  const binding = useNatureAction(
    'species_relation:create',
    (_: void) => ({
      first_species_id: first ?? 0,
      second_species_id: second ?? 0,
      kind: bond as Bond['kind'],
      strength: Math.max(0, Math.min(SPAN, Number(strength) || 0)),
    }),
    'The two kinds are bound'
  )
  const bindBusy = why(
    blocked ??
      (first === null
        ? 'Choose the first kind'
        : second === null
          ? 'Choose the second kind'
          : first === second
            ? 'A kind cannot be bound to itself'
            : null),
    binding.isPending
  )
  return (
    <div data-surface='BondsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-kind-bonds'
        title='Bonds between kinds and their strength'
        legend={[{ text: 'Strength', variant: 'success' }]}
        rows={data.bonds.map((row) => ({
          key: String(row.id),
          caption: `${row.first.name} and ${row.second.name}: ${BONDS[row.kind].label.toLowerCase()}`,
          segments: [{ value: row.strength, fill: 'fill-success' }],
        }))}
        max={SPAN}
        noun={['bond', 'bonds']}
        empty='No bond between kinds touches this.'
      />
      <Listed
        title='Bonds between kinds'
        items={data.bonds}
        empty='No bond between kinds touches this.'
        noun={['bond', 'bonds']}
        itemKey={(item) => item.id}
      >
        {(item) => <BondCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Handshake}
        tone='success'
        title='Bind two kinds'
        note={BOND_HINTS[bond as Bond['kind']]}
        columns={2}
        action={
          <Button
            act={binding}
            size='sm'
            disabled={bindBusy !== null}
            disabledReason={bindBusy ?? undefined}
            onClick={() => binding.mutate()}
          >
            <Plus />
            Bind them
          </Button>
        }
      >
        <NodePicker
          label='First kind'
          value={first}
          onChange={setFirst}
          blocked={blocked}
          types={KIND_TYPES}
        />
        <NodePicker
          label='Second kind'
          value={second}
          onChange={setSecond}
          blocked={blocked}
          types={KIND_TYPES}
        />
        <MindPicker
          label='Bond'
          value={bond}
          table={table(BONDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setBond}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setStrength}
        />
      </ForgeCard>
    </div>
  )
}
