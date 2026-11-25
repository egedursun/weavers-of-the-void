import { useState } from 'react'
import { CircleStop, FastForward, Gauge, Trash2, Users } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Bars } from '@/features/sacred/parts'
import { NumberField } from '@/features/wars/military/parts'
import {
  type DeepTimeHappeningView,
  type DeepTimeRunView,
  useDeepTime,
  usePrehistoryAction,
} from './api'
import { DEEP_TIME_ICON, DEEP_TIME_STATES } from './labels'

const RUNS_SHOWN = 4
const HAPPENINGS_SHOWN = 6
const RUN_FIELDS: readonly Field[] = [
  {
    key: 'state',
    label: 'Run state',
    kind: 'pick',
    table: table(DEEP_TIME_STATES),
  },
]
const HAPPENING_FIELDS: readonly Field[] = [
  { key: 'magnitude', label: 'Magnitude', kind: 'number', min: 0, max: 100 },
]

function Happening({
  happening,
  blocked,
}: {
  happening: DeepTimeHappeningView
  blocked: string | null
}) {
  const editing = usePrehistoryAction(
    'deep_time_event:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ event_id: happening.id, ...vars }),
    'The happening keeps its new values'
  )
  const removing = usePrehistoryAction(
    'deep_time_event:remove',
    (_: void) => ({ event_id: happening.id }),
    'The happening is struck out'
  )
  return (
    <RecordRow
      icon={Gauge}
      tone='gold'
      title={happening.text ?? 'A happening with no line left'}
      caption={`Epoch ${happening.epoch}, magnitude ${happening.magnitude}`}
      aside={<Chip icon={Gauge}>Magnitude {happening.magnitude}</Chip>}
    >
      <RecordEditor
        act={editing}
        title='Set this happening'
        note='Values you set are held against the engine until you release them.'
        fields={HAPPENING_FIELDS}
        locked={happening.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Strike it out of the digest'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Run({
  run,
  blocked,
}: {
  run: DeepTimeRunView
  blocked: string | null
}) {
  const state = DEEP_TIME_STATES[run.state]
  const page = useShowMore(
    run.happenings,
    HAPPENINGS_SHOWN,
    HAPPENINGS_SHOWN * 2
  )
  const editing = usePrehistoryAction(
    'deep_time:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ run_id: run.id, ...vars }),
    'The fast-forward keeps its new values'
  )
  const stopping = usePrehistoryAction(
    'deep_time:stop',
    (_: void) => ({ run_id: run.id }),
    'The fast-forward stops'
  )
  const removing = usePrehistoryAction(
    'deep_time:remove',
    (_: void) => ({ run_id: run.id }),
    'The record of the fast-forward is struck out'
  )
  return (
    <RecordRow
      icon={state.icon}
      tone={state.tone}
      title={`From epoch ${run.from_epoch} to epoch ${run.to_epoch}`}
      caption={`${state.label}: ${run.ran} of ${plural(run.epochs, 'epoch')} run`}
      aside={
        <Chip icon={Users}>Sons ruled by their aims: {run.sons_simulated}</Chip>
      }
    >
      <Bars
        chart='chart-deep-time'
        title='Its strongest happenings'
        legend={[{ text: 'Magnitude', variant: 'warning' }]}
        rows={page.visible.map((happening) => ({
          key: String(happening.id),
          caption: `Epoch ${happening.epoch}: ${happening.text ?? 'a happening'}`,
          segments: [{ value: happening.magnitude, fill: 'fill-warning' }],
        }))}
        max={100}
        noun={['happening', 'happenings']}
        empty='No happenings are kept for this run.'
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        {page.visible.map((happening) => (
          <Happening
            key={happening.id}
            happening={happening}
            blocked={blocked}
          />
        ))}
      </ul>
      <ShowMore state={page} />
      <RecordEditor
        act={editing}
        title='Set this fast-forward'
        note='Values you set are held against the engine until you release them.'
        fields={RUN_FIELDS}
        locked={run.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={stopping}
          icon={CircleStop}
          label='Stop it'
          busy={why(
            blocked ?? (run.state === 'running' ? null : 'It is not running'),
            stopping.isPending
          )}
          onClick={() => stopping.mutate()}
        />
        <StepButton
          act={removing}
          icon={Trash2}
          label='Strike out its record'
          busy={why(
            blocked ?? (run.state === 'running' ? 'Stop it first' : null),
            removing.isPending
          )}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

export function DeepTimePanel({
  readOnlyReason = null,
}: {
  readOnlyReason?: string | null
}) {
  const query = useDeepTime()
  const [epochs, setEpochs] = useState('10')
  const page = useShowMore(query.data?.runs ?? [], RUNS_SHOWN, RUNS_SHOWN * 2)
  const running = usePrehistoryAction(
    'deep_time:run',
    (_: void) => ({ epochs: Math.max(1, Number(epochs) || 1) }),
    'Deep time begins to run'
  )
  const busy = query.data?.runs.some((run) => run.state === 'running')
    ? 'A fast-forward is already running'
    : null
  const runBlocked = readOnlyReason ?? busy
  return (
    <Section
      id='section-deep-time'
      title='Deep time: fast-forward the cosmos'
      description='Run the whole cosmos forward for a number of epochs with no language model: the sons act by their aims and standing, and a digest of the strongest happenings is kept.'
      icon={DEEP_TIME_ICON}
      tone='gold'
    >
      <div data-surface='DeepTimePanel' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the runs of deep time' />
        ) : query.isError ? (
          <EmptyState
            icon={DEEP_TIME_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Runs kept'
                value={String(query.data.runs.length)}
                icon={DEEP_TIME_ICON}
                tone='gold'
              />
              <KpiTile
                label='Most epochs in one run'
                value={String(query.data.max_epochs)}
                icon={FastForward}
                tone='info'
              />
              <KpiTile
                label='Essence for each epoch'
                value={String(query.data.cost_per_epoch)}
                icon={Gauge}
                tone='muted'
              />
            </div>
            <ForgeCard
              icon={DEEP_TIME_ICON}
              tone='gold'
              title='Fast-forward deep time'
              note={`Costs ${query.data.cost_per_epoch} essence for each epoch; an epoch running or another run blocks it.`}
              columns={2}
              action={
                <Button
                  act={running}
                  size='sm'
                  disabled={why(runBlocked, running.isPending) !== null}
                  disabledReason={
                    why(runBlocked, running.isPending) ?? undefined
                  }
                  onClick={() => running.mutate()}
                >
                  <FastForward />
                  Run it forward
                </Button>
              }
            >
              <NumberField
                label='Epochs to run'
                value={epochs}
                min={1}
                max={query.data.max_epochs}
                onChange={setEpochs}
              />
            </ForgeCard>
            {query.data.runs.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((run) => (
                    <Run key={run.id} run={run} blocked={readOnlyReason} />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={DEEP_TIME_ICON}
                size='inline'
                title='Deep time has not been run'
                description='Run it forward above to see what the cosmos does without a hand on it.'
              />
            )}
          </>
        )}
      </div>
    </Section>
  )
}
