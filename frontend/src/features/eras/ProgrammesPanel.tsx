import { useState } from 'react'
import { Eye, Hammer, Plus } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type ErasNodeView, useEraAction } from './api'
import { STAGES } from './labels'
import { MANY, SPAN, useProgrammeRow } from './model'

type View = ErasNodeView
type Programme = View['programmes'][number]

function ProgrammeCard({
  row,
  goals,
  blocked,
}: {
  row: Programme
  goals: Record<string, string>
  blocked: string | null
}) {
  const action = useProgrammeRow(row.id, blocked)
  const stage = STAGES[row.stage]
  return (
    <Held
      icon={stage.icon}
      tone={stage.tone}
      title={`${row.polity.name} toward ${row.label.toLowerCase()}`}
      caption={`${stage.label} · ${row.progress}% done · seen ${row.visibility}% abroad · ${plural(row.sabotaged, 'sabotage', 'sabotages')} · begun in epoch ${row.started_epoch}${row.finished_epoch !== null ? ` · ended in epoch ${row.finished_epoch}` : ''}`}
      removeLabel='End the programme'
      editTitle='Set the programme'
      note='Each epoch the programme costs the treasury and gains ground, faster for every scientist, engineer and computer of the realm. Each new stage is heard abroad, and a rival that spies on the realm may set it back. At the end the capital knows the technique.'
      fields={[
        {
          key: 'technique',
          label: 'Technique sought',
          kind: 'pick',
          table: goals,
        },
        {
          key: 'progress',
          label: 'Progress (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        {
          key: 'visibility',
          label: 'Seen abroad (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'sabotaged',
          label: 'Times sabotaged',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'finished_epoch',
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
      extra={
        <Badge size='sm' variant='secondary'>
          {stage.label}
        </Badge>
      }
    >
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={row.polity} empty='no realm' />],
        ]}
      />
      <Meter
        label={`Progress (${row.progress} of ${SPAN})`}
        value={row.progress}
        tone={row.stage === 'abandoned' ? 'warning' : 'success'}
        icon={Hammer}
      />
      <Meter
        label={`Seen abroad (${row.visibility} of ${SPAN})`}
        value={row.visibility}
        tone='info'
        icon={Eye}
      />
    </Held>
  )
}

export function ProgrammesPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const goals = Object.fromEntries(
    data.techniques
      .filter((row) => row.programme)
      .map((row) => [row.technique, row.label])
  )
  const [goal, setGoal] = useState(Object.keys(goals)[0] ?? '')
  const realm = data.realm
  const beginning = useEraAction(
    'tech_programme:create',
    (_: void) => ({
      polity_id: realm?.id ?? 0,
      technique: goal as Programme['technique'],
    }),
    'The realm begins its programme'
  )
  const running = data.programmes.some(
    (row) =>
      row.technique === goal &&
      row.stage !== 'complete' &&
      row.stage !== 'abandoned'
  )
  const beginBusy = why(
    blocked ??
      (realm === null
        ? 'This belongs to no realm, and only a realm runs a programme'
        : !goal
          ? 'Choose the technique'
          : running
            ? 'The realm already runs a programme toward this'
            : null),
    beginning.isPending
  )
  return (
    <div data-surface='ProgrammesPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-tech-programmes'
        title='Programmes and how far they are'
        legend={[
          { text: 'Progress', variant: 'success' },
          { text: 'Seen abroad', variant: 'secondary' },
        ]}
        rows={data.programmes.map((row) => ({
          key: String(row.id),
          caption: `${row.polity.name} toward ${row.label.toLowerCase()}: ${STAGES[row.stage].label.toLowerCase()}`,
          segments: [
            { value: row.progress, fill: 'fill-success' },
            { value: row.visibility, fill: 'fill-info' },
          ],
        }))}
        noun={['programme', 'programmes']}
        empty='No programme runs in this realm.'
      />
      <Listed
        title='Programmes'
        items={data.programmes}
        empty='No programme runs in this realm.'
        noun={['programme', 'programmes']}
        itemKey={(item) => item.id}
      >
        {(item) => <ProgrammeCard row={item} goals={goals} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Hammer}
        tone='gold'
        title='Begin a programme'
        note={`${realm ? realm.name : 'The realm'} plans, builds and tests its way toward a technique too great for research alone.`}
        columns={2}
        action={
          <Button
            size='sm'
            disabled={beginBusy !== null}
            disabledReason={beginBusy ?? undefined}
            onClick={() => beginning.mutate()}
          >
            <Plus />
            Begin it
          </Button>
        }
      >
        <MindPicker
          label='Technique sought'
          value={goal}
          table={goals}
          placeholder='Choose'
          blocked={blocked}
          onPick={setGoal}
        />
      </ForgeCard>
    </div>
  )
}
