import { useState } from 'react'
import { Flame, Gavel } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type FolkwaysNodeView, useFolkwaysAction } from './api'
import { OUTCOMES } from './labels'
import { MANY, MORTAL_TYPES, SPAN, TOWN_TYPES, useFolkwaysRow } from './model'

type Accusation = FolkwaysNodeView['accusations'][number]
type Hunt = FolkwaysNodeView['hunts'][number]

function AccusationCard({
  row,
  blocked,
}: {
  row: Accusation
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'accusation:edit',
    'accusation:delete',
    { accusation_id: row.id },
    blocked
  )
  const outcome = OUTCOMES[row.outcome]
  return (
    <Held
      icon={outcome.icon}
      tone={outcome.tone}
      title={`${row.accused.name} accused of witchcraft`}
      caption={`Epoch ${row.opened_epoch}${row.closed_epoch !== null ? ` to epoch ${row.closed_epoch}` : ''} · ${row.guilty_in_truth ? 'truly a caster' : 'no caster in truth'}${row.hunt_id !== null ? ' · in a witch hunt' : row.mishap_id !== null ? ' · after a misfortune' : ''}`}
      removeLabel='Strike the accusation'
      editTitle='Set the accusation'
      note="The accused is chosen by envy, by being an outsider or alone, by old grudges and earlier accusations, and by truly having cast on the victim. The realm's court tries the case; you see whether the charge is true."
      fields={[
        {
          key: 'settlement_entity_id',
          label: 'Town',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'accuser_node_id',
          label: 'Accuser',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'accused_node_id',
          label: 'Accused',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'outcome',
          label: 'Outcome',
          kind: 'pick',
          table: table(OUTCOMES),
        },
        {
          key: 'guilty_in_truth',
          label: 'Truly a caster',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={outcome} />}
    >
      <Facts
        items={[
          ['Town', <Ref key='town' node={row.town} empty='no town' />],
          [
            'Accuser',
            <Ref
              key='accuser'
              node={row.accuser}
              empty='the crowd of a hunt'
            />,
          ],
          [
            'Case',
            row.case_id !== null ? 'before the court' : 'no case opened',
          ],
        ]}
      />
    </Held>
  )
}

function HuntCard({ row, blocked }: { row: Hunt; blocked: string | null }) {
  const action = useFolkwaysRow(
    'witch_hunt:edit',
    'witch_hunt:delete',
    { hunt_id: row.id },
    blocked
  )
  const burning = row.ended_epoch === null
  return (
    <Held
      icon={Flame}
      tone={burning ? 'danger' : 'muted'}
      title={burning ? 'A witch hunt under way' : 'A witch hunt that ended'}
      caption={`From epoch ${row.started_epoch}${row.ended_epoch !== null ? ` to epoch ${row.ended_epoch}` : ''} · ${row.accused} accused · ${row.killed} killed`}
      removeLabel='Strike the hunt'
      editTitle='Set the hunt'
      note="Hunger, insecurity, plague, war or political stress turns a run of accusations into a hunt, fiercer where the town's church has turned to inquisition: each epoch it brings accusations by its fervour, which fades until the hunt ends."
      fields={[
        { key: 'fervour', label: 'Fervour', kind: 'number', min: 0, max: SPAN },
        { key: 'accused', label: 'Accused', kind: 'number', min: 0, max: MANY },
        { key: 'killed', label: 'Killed', kind: 'number', min: 0, max: MANY },
        {
          key: 'ended_epoch',
          label: 'Ended in epoch',
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
        label={`Fervour (${row.fervour} of ${SPAN})`}
        value={row.fervour}
        tone='warning'
        icon={Flame}
      />
    </Held>
  )
}

export function WitchcraftPanel({
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
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [accuser, setAccuser] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [fervour, setFervour] = useState('60')
  const accusing = useFolkwaysAction(
    'accusation:create',
    (_: void) => ({ town_id: town ?? 0, accuser_id: accuser, mishap_id: null }),
    'An accusation is made'
  )
  const hunting = useFolkwaysAction(
    'witch_hunt:create',
    (_: void) => ({ town_id: town ?? 0, fervour: Number(fervour || '0') }),
    'A witch hunt takes hold'
  )
  const burning = data.hunts.some((row) => row.ended_epoch === null)
  const accuseBusy = why(
    blocked ?? (town === null ? 'Choose a town' : null),
    accusing.isPending
  )
  const huntBusy = why(
    blocked ??
      (town === null
        ? 'Choose a town'
        : burning && town === nodeId
          ? 'A witch hunt already burns here'
          : null),
    hunting.isPending
  )
  return (
    <div data-surface='WitchcraftPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-hunts'
        title='Fervour of the witch hunts'
        legend={[
          { text: 'Active', variant: 'destructive' },
          { text: 'Ended', variant: 'secondary' },
        ]}
        rows={data.hunts.map((row) => ({
          key: row.id,
          caption: `From epoch ${row.started_epoch}: ${row.accused} accused, ${row.killed} killed`,
          segments: [
            {
              value: row.fervour,
              fill:
                row.ended_epoch === null ? 'fill-destructive' : 'fill-muted',
            },
          ],
        }))}
        max={SPAN}
        noun={['hunt', 'hunts']}
        empty='No witch hunt has burned here.'
      />
      <Listed
        title='Accusations of witchcraft'
        items={data.accusations}
        empty='No accusation of witchcraft touches this.'
        noun={['accusation', 'accusations']}
        itemKey={(entry) => entry.id}
      >
        {(entry) => <AccusationCard row={entry} blocked={blocked} />}
      </Listed>
      <Listed
        title='Witch hunts'
        items={data.hunts}
        empty='No witch hunt has burned here.'
        noun={['hunt', 'hunts']}
        itemKey={(entry) => entry.id}
      >
        {(entry) => <HuntCard row={entry} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Gavel}
        tone='danger'
        title='Raise an accusation'
        note='Suspicion falls on the town folk by envy, outsiders, loneliness, grudges and true castings; the court tries the case.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={accuseBusy !== null}
            disabledReason={accuseBusy ?? undefined}
            onClick={() => accusing.mutate()}
          >
            <Gavel />
            Accuse
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='Accuser'
          value={accuser}
          onChange={setAccuser}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
      </ForgeCard>
      <ForgeCard
        icon={Flame}
        tone='warning'
        title='Start a witch hunt'
        note='Each epoch it brings accusations by its fervour until it fades.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={huntBusy !== null}
            disabledReason={huntBusy ?? undefined}
            onClick={() => hunting.mutate()}
          >
            <Flame />
            Start the hunt
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NumberField
          label='Fervour'
          value={fervour}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setFervour}
        />
      </ForgeCard>
    </div>
  )
}
