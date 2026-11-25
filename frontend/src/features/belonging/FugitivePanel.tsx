import { useState } from 'react'
import { Footprints, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { type BelongingNodeView, useBelongingAction } from './api'
import { FUGITIVES } from './labels'
import { MANY, MORTAL_TYPES, PURSUER_TYPES, useBelongingRow } from './model'

type View = BelongingNodeView
type Flight = View['fugitives'][number]

function standing(row: Flight): string {
  if (row.caught_epoch !== null) return `taken in epoch ${row.caught_epoch}`
  if (row.freed_epoch !== null) return `free since epoch ${row.freed_epoch}`
  return 'at large'
}

function FlightCard({ row, blocked }: { row: Flight; blocked: string | null }) {
  const action = useBelongingRow(
    'fugitive:edit',
    'fugitive:delete',
    { record_id: row.id },
    blocked
  )
  const kind = FUGITIVES[row.kind]
  const open = row.caught_epoch === null && row.freed_epoch === null
  return (
    <Held
      icon={kind.icon}
      tone={open ? 'warning' : 'muted'}
      title={`${row.mortal.name}, ${kind.label.toLowerCase()}`}
      caption={`Fled in epoch ${row.fled_epoch} · ${standing(row)}`}
      removeLabel='End the flight'
      editTitle='Set the flight'
      note='A fugitive is hunted by its pursuer each epoch until it is taken, finds sanctuary or goes free; a runaway who stays out the term in a city whose charter frees it is free.'
      fields={[
        {
          key: 'kind',
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
        {
          key: 'caught_epoch',
          label: 'Taken in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'freed_epoch',
          label: 'Free since epoch',
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
        <Badge size='sm' variant={open ? 'warning' : 'secondary'}>
          {standing(row)}
        </Badge>
      }
    >
      <Facts
        items={[
          ['Fugitive', <Ref key='mortal' node={row.mortal} empty='no one' />],
          ['Pursuer', <Ref key='pursuer' node={row.pursuer} empty='no one' />],
        ]}
      />
    </Held>
  )
}

export function FugitivePanel({
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
  const [mortal, setMortal] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [pursuer, setPursuer] = useState<number | null>(
    kind === 'polity' ? nodeId : null
  )
  const [fled, setFled] = useState('runaway')
  const fleeing = useBelongingAction(
    'fugitive:create',
    (_: void) => ({
      mortal_entity_id: mortal ?? 0,
      kind: fled as Flight['kind'],
      pursuer_entity_id: pursuer,
    }),
    'The mortal flees'
  )
  const busy = why(
    blocked ?? (mortal === null ? 'Choose who flees' : null),
    fleeing.isPending
  )
  return (
    <div data-surface='FugitivePanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Fugitives'
        items={data.fugitives}
        empty='No one here flees, and this hunts no one.'
        noun={['fugitive', 'fugitives']}
        itemKey={(item) => item.id}
      >
        {(item) => <FlightCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Footprints}
        tone='warning'
        title='Set a mortal to flight'
        note='Outlaws, the accused, defectors, runaways from bondage, deserters and those fleeing persecution are hunted until they are taken, sheltered or freed.'
        columns={2}
        action={
          <Button
            act={fleeing}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => fleeing.mutate()}
          >
            <Plus />
            Set them to flight
          </Button>
        }
      >
        <NodePicker
          label='Who flees'
          value={mortal}
          onChange={setMortal}
          blocked={blocked}
          types={MORTAL_TYPES}
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
    </div>
  )
}
