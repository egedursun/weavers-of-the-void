import { useState } from 'react'
import { Drama, Laugh, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type BelongingNodeView, useBelongingAction } from './api'
import { SOURCES } from './labels'
import {
  MORTAL_TYPES,
  REALM_TYPES,
  SPAN,
  WORK_TYPES,
  useBelongingRow,
  useBelongingStep,
} from './model'

type View = BelongingNodeView
type Satire = View['satires'][number]

function SatireCard({ row, blocked }: { row: Satire; blocked: string | null }) {
  const action = useBelongingRow(
    'satire:edit',
    'satire:delete',
    { record_id: row.id },
    blocked
  )
  const source = SOURCES[row.source]
  const verdict = !row.judged
    ? 'not yet judged'
    : row.tolerated
      ? 'tolerated'
      : row.punished
        ? 'punished'
        : 'not tolerated'
  return (
    <Held
      icon={source.icon}
      tone={row.punished ? 'danger' : row.tolerated ? 'success' : source.tone}
      title={`${row.satirist?.name ?? source.label} mocks ${row.target.name}`}
      caption={`${source.label} · bite ${row.bite} · ${verdict} · epoch ${row.epoch}`}
      removeLabel='Forget the satire'
      editTitle='Set the satire'
      note='Where the court tolerates mockery, a satire costs the ruler standing, lowers the approval of the realm’s folk and lets anger out before it becomes a riot. Where it does not, the satirist may be imprisoned and the realm’s folk hold the punishment against it. A jester mocks by licence and is never punished.'
      fields={[
        {
          key: 'satirist_entity_id',
          label: 'Satirist',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'target_entity_id',
          label: 'Mocked',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'polity_entity_id',
          label: 'Realm',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'work_entity_id',
          label: 'Work',
          kind: 'node',
          types: WORK_TYPES,
        },
        {
          key: 'source',
          label: 'Told by',
          kind: 'pick',
          table: table(SOURCES),
        },
        { key: 'bite', label: 'Bite', kind: 'number', min: 0, max: SPAN },
        { key: 'tolerated', label: 'Tolerated', kind: 'pick', table: YES_NO },
        { key: 'punished', label: 'Punished', kind: 'pick', table: YES_NO },
        { key: 'judged', label: 'Judged', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Badge
          size='sm'
          variant={
            row.punished
              ? 'destructive'
              : row.tolerated
                ? 'success'
                : 'secondary'
          }
        >
          {verdict}
        </Badge>
      }
    >
      <Facts
        items={[
          [
            'Satirist',
            <Ref key='satirist' node={row.satirist} empty='no one named' />,
          ],
          ['Realm', <Ref key='realm' node={row.polity} empty='no realm' />],
          ['Work', <Ref key='work' node={row.work} empty='no work' />],
        ]}
      />
      <Meter
        label={`Bite (${row.bite} of ${SPAN})`}
        value={row.bite}
        tone='warning'
        icon={Laugh}
      />
    </Held>
  )
}

export function SatirePanel({
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
  const [target, setTarget] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [satirist, setSatirist] = useState<number | null>(null)
  const [bite, setBite] = useState('20')
  const realmId = kind === 'polity' ? nodeId : (data.realm?.id ?? null)
  const telling = useBelongingAction(
    'satire:create',
    (_: void) => ({
      satirist_entity_id: satirist,
      target_entity_id: target ?? 0,
      polity_entity_id: realmId,
      bite: Math.max(0, Math.min(SPAN, Number(bite) || 0)),
    }),
    'The satire is told'
  )
  const reading = useBelongingStep(
    'satire:run',
    blocked,
    'Every jest and satire is read'
  )
  const tellBusy = why(
    blocked ?? (target === null ? 'Choose whom the satire mocks' : null),
    telling.isPending
  )
  return (
    <div data-surface='SatirePanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          [
            'Court jester',
            <Ref key='jester' node={data.jester} empty='no jester at court' />,
          ],
        ]}
      />
      <Bars
        chart='chart-satire'
        title='Satires and their bite'
        legend={[
          { text: 'Tolerated', variant: 'success' },
          { text: 'Punished', variant: 'destructive' },
        ]}
        rows={data.satires.map((row) => ({
          key: String(row.id),
          caption: `${row.satirist?.name ?? SOURCES[row.source].label} on ${row.target.name}: bite ${row.bite}`,
          segments: [
            {
              value: row.bite,
              fill: row.punished ? 'fill-destructive' : 'fill-success',
            },
          ],
        }))}
        max={SPAN}
        noun={['satire', 'satires']}
        empty='No one has been mocked here.'
      />
      <Listed
        title='Satires'
        items={data.satires}
        empty='No one has been mocked here.'
        noun={['satire', 'satires']}
        itemKey={(item) => item.id}
      >
        {(item) => <SatireCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Drama}
        tone='gold'
        title='Tell a satire'
        note='Someone mocks a ruler or another in public; the court of the realm judges whether to tolerate it.'
        columns={3}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Laugh}
              label='Read satires now'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              act={telling}
              size='sm'
              disabled={tellBusy !== null}
              disabledReason={tellBusy ?? undefined}
              onClick={() => telling.mutate()}
            >
              <Plus />
              Tell it
            </Button>
          </div>
        }
      >
        <NodePicker
          label='Mocked'
          value={target}
          onChange={setTarget}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <NodePicker
          label='Satirist'
          value={satirist}
          onChange={setSatirist}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <NumberField
          label='Bite (0 to 100)'
          value={bite}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setBite}
        />
      </ForgeCard>
    </div>
  )
}
