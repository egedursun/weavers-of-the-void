import { useState } from 'react'
import { Package, Plus, Swords } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { unitIcon } from '@/features/wars/military/labels'
import { type EquipmentModel, type ThingKinds, useLever } from './api'
import { SLOT, familyLabel, sectionLabel } from './labels'
import { useKindStep } from './model'

type Store = ThingKinds['stores'][number]
type Stack = ThingKinds['stacks'][number]
type Carried = Stack['carried'][number]

const LOTS = 1_000_000

function StoreCard({
  row,
  nodeId,
  blocked,
}: {
  row: Store
  nodeId: number
  blocked: string | null
}) {
  const set = useLever(
    'equipment_store:set',
    (count: number) => ({ holder_id: nodeId, model_id: row.model_id, count }),
    'The store is set'
  )
  const remove = useKindStep(
    'equipment_store:delete',
    { holder_id: nodeId, model_id: row.model_id },
    blocked,
    'The store is emptied'
  )
  const slot = SLOT[row.slot]
  return (
    <Held
      icon={slot.icon}
      tone={slot.tone}
      title={`${row.count} × ${row.model_name}`}
      caption={`${slot.label} · ${familyLabel(row.family).toLowerCase()}`}
      removeLabel='Empty the store'
      editTitle='Set the store'
      note='Pieces held ready; armies draw on them at muster and when they rearm, and forges add to them each epoch.'
      fields={[
        {
          key: 'count',
          label: 'Pieces in store',
          kind: 'number',
          min: 0,
          max: LOTS,
        },
      ]}
      locked={row.locked}
      blocked={why(remove.busy, set.isPending)}
      onEdit={(vars) => set.mutate(Number(vars.values.count ?? row.count))}
      onRemove={remove.run}
    />
  )
}

function CarriedCard({
  row,
  stack,
  blocked,
}: {
  row: Carried
  stack: Stack
  blocked: string | null
}) {
  const set = useLever(
    'army_equipment:set',
    (values: { count: number; condition: number }) => ({
      unit_id: stack.unit_id,
      model_id: row.model_id,
      ...values,
    }),
    'The stack carries it so'
  )
  const remove = useKindStep(
    'army_equipment:delete',
    { unit_id: stack.unit_id, model_id: row.model_id },
    blocked,
    'The stack no longer carries it'
  )
  const slot = SLOT[row.slot]
  return (
    <Held
      icon={slot.icon}
      tone={row.condition < 40 ? 'danger' : slot.tone}
      title={`${row.count} × ${row.model_name}`}
      caption={`${slot.label} · condition ${row.condition}`}
      removeLabel='Take it from the stack'
      editTitle='Set what the stack carries'
      note='The pieces a stack carries set its damage, piercing and protection in battle; they wear in every fight and are dropped when the stack falls.'
      fields={[
        {
          key: 'count',
          label: 'Pieces carried',
          kind: 'number',
          min: 0,
          max: LOTS,
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={why(remove.busy, set.isPending)}
      onEdit={(vars) =>
        set.mutate({
          count: Number(vars.values.count ?? row.count),
          condition: Number(vars.values.condition ?? row.condition),
        })
      }
      onRemove={remove.run}
    />
  )
}

function StackKit({
  stack,
  models,
  blocked,
}: {
  stack: Stack
  models: EquipmentModel[]
  blocked: string | null
}) {
  const [model, setModel] = useState('')
  const [count, setCount] = useState(String(stack.count))
  const add = useLever(
    'army_equipment:set',
    (_: void) => ({
      unit_id: stack.unit_id,
      model_id: Number(model),
      count: Number(count),
      condition: SPAN,
    }),
    'The stack carries it'
  )
  const busy = why(blocked, add.isPending)
  const have = new Set(stack.carried.map((item) => item.model_id))
  const table = Object.fromEntries(
    models
      .filter((item) => item.slot !== 'vehicle_weapon' && !have.has(item.id))
      .map((item) => [String(item.id), `${item.name} (${item.family_label})`])
  )
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={unitIcon(stack.kind, Swords)} tone='gold' size='sm' />
        <Label>{`${stack.count} ${stack.design_name ?? sectionLabel(stack.kind).toLowerCase()}`}</Label>
      </div>
      {stack.carried.length === 0 ? (
        <Muted variant='caption'>
          This stack carries nothing of a named model.
        </Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {stack.carried.map((item) => (
            <CarriedCard
              key={item.model_id}
              row={item}
              stack={stack}
              blocked={blocked}
            />
          ))}
        </ul>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <MindPicker
          label='Model'
          value={model}
          table={table}
          blocked={
            Object.keys(table).length
              ? busy
              : 'No other model of this world can be carried'
          }
          onPick={setModel}
        />
        <NumberField
          label='Pieces'
          value={count}
          min={1}
          max={LOTS}
          blocked={busy}
          onChange={setCount}
        />
        <Button
          size='sm'
          disabled={(busy ?? (model ? null : 'Pick a model')) !== null}
          disabledReason={busy ?? (model ? undefined : 'Pick a model')}
          onClick={() => add.mutate()}
        >
          <Plus />
          Arm the stack
        </Button>
      </div>
    </li>
  )
}

export function KitPanel({
  nodeId,
  data,
  models,
  army,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  models: EquipmentModel[]
  army: boolean
  blocked: string | null
}) {
  const [model, setModel] = useState('')
  const [count, setCount] = useState('10')
  const add = useLever(
    'equipment_store:set',
    (_: void) => ({
      holder_id: nodeId,
      model_id: Number(model),
      count: Number(count),
    }),
    'The store is filled'
  )
  const busy = why(blocked, add.isPending)
  const held = new Set(data.stores.map((item) => item.model_id))
  const table = Object.fromEntries(
    models
      .filter((item) => !held.has(item.id))
      .map((item) => [String(item.id), `${item.name} (${item.family_label})`])
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Listed
        title='Stores of equipment'
        items={data.stores}
        empty='It keeps no store of weapons, armour or materiel.'
        noun={['store', 'stores']}
        itemKey={(item) => item.model_id}
      >
        {(item) => <StoreCard row={item} nodeId={nodeId} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Package}
        tone='gold'
        title='Fill a store'
        note='Give it pieces of a model known in its world.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={(busy ?? (model ? null : 'Pick a model')) !== null}
            disabledReason={busy ?? (model ? undefined : 'Pick a model')}
            onClick={() => add.mutate()}
          >
            <Plus />
            Fill it
          </Button>
        }
      >
        <MindPicker
          label='Model'
          value={model}
          table={table}
          blocked={
            Object.keys(table).length
              ? busy
              : 'No other model is known in this world yet'
          }
          onPick={setModel}
        />
        <NumberField
          label='Pieces'
          value={count}
          min={1}
          max={LOTS}
          blocked={busy}
          onChange={setCount}
        />
      </ForgeCard>
      {army && (
        <>
          <Label variant='overline'>{`What its stacks carry (${data.stacks.length})`}</Label>
          <Muted variant='caption'>
            Only an army has stacks that carry equipment into battle; every
            other holder keeps its pieces in store.
          </Muted>
          {data.stacks.length === 0 ? (
            <Muted variant='caption'>
              It has no stacks yet; raise one in its army panel.
            </Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              {data.stacks.map((stack) => (
                <StackKit
                  key={stack.unit_id}
                  stack={stack}
                  models={models}
                  blocked={blocked}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
