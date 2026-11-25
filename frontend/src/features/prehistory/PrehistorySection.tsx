import { useState } from 'react'
import {
  CircleStop,
  Gauge,
  Hourglass,
  Play,
  Sprout,
  Timer,
  Trash2,
} from 'lucide-react'
import { worldTypeValues } from '@/api/generated/schema'
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
import { wordOf } from '@/features/entity/affairs/labels'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { NumberField } from '@/features/wars/military/parts'
import {
  type PrehistoryHappeningView,
  type PrehistoryNodeView,
  useNodePrehistory,
  usePrehistoryAction,
} from './api'
import {
  PREHISTORY_ICON,
  PREHISTORY_KINDS,
  PREHISTORY_SOURCES,
  PREHISTORY_STATES,
} from './labels'

const HAPPENINGS_SHOWN = 8
const YES_NO = { true: 'Yes', false: 'No' }
const OPEN_STATES = new Set(['planned', 'aborted'])

function recordFields(view: PrehistoryNodeView): readonly Field[] {
  return [
    {
      key: 'kind',
      label: 'Kind of past',
      kind: 'pick',
      table: table(PREHISTORY_KINDS),
    },
    {
      key: 'state',
      label: 'Run state',
      kind: 'pick',
      table: table(PREHISTORY_STATES),
    },
    {
      key: 'epochs',
      label: 'Epochs of past',
      kind: 'number',
      min: 0,
      max: view.epochs_max,
    },
    {
      key: 'resolution',
      label: 'Rounds between coarse steps',
      kind: 'number',
      min: 1,
      max: view.resolution_max,
    },
  ]
}

const HAPPENING_FIELDS: readonly Field[] = [
  {
    key: 'round',
    label: 'Round of the past',
    kind: 'number',
    min: 0,
    max: 1000,
  },
  { key: 'magnitude', label: 'Magnitude', kind: 'number', min: 0, max: 100 },
  {
    key: 'mirrored',
    label: 'Mirrored from the twin',
    kind: 'pick',
    table: YES_NO,
  },
]

function Happening({
  happening,
  blocked,
}: {
  happening: PrehistoryHappeningView
  blocked: string | null
}) {
  const source = PREHISTORY_SOURCES[happening.source]
  const editing = usePrehistoryAction(
    'prehistory_event:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ event_id: happening.id, ...vars }),
    'The happening keeps its new values'
  )
  const removing = usePrehistoryAction(
    'prehistory_event:remove',
    (_: void) => ({ event_id: happening.id }),
    'The happening is struck out'
  )
  return (
    <RecordRow
      icon={source.icon}
      tone={source.tone}
      title={
        happening.text ??
        happening.subject?.name ??
        'A happening with no line left'
      }
      caption={`Round ${happening.round} of the past, magnitude ${happening.magnitude}, ${source.label.toLowerCase()}`}
      aside={<Chip icon={Gauge}>Magnitude {happening.magnitude}</Chip>}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={happening.subject} empty='no single subject' />
        <Ref node={happening.source_world} empty='its own world' />
        {happening.mirrored && <Chip icon={source.icon}>Mirrored</Chip>}
      </div>
      <RecordEditor
        title='Set this happening'
        note='Values you set are held against the engine until you release them.'
        fields={HAPPENING_FIELDS}
        locked={happening.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike it out of the past'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Controls({
  view,
  blocked,
}: {
  view: PrehistoryNodeView
  blocked: string | null
}) {
  const worldId = view.world?.id ?? null
  const [epochs, setEpochs] = useState(
    String(view.epochs || view.default_epochs || 10)
  )
  const [resolution, setResolution] = useState(
    String(view.resolution || view.default_resolution)
  )
  const plan = () => ({
    world_id: worldId ?? 0,
    epochs: Math.max(1, Number(epochs) || 1),
    resolution: Math.max(1, Number(resolution) || 1),
  })
  const configuring = usePrehistoryAction(
    'prehistory:configure',
    (_: void) => plan(),
    'The prehistory is planned'
  )
  const seeding = usePrehistoryAction(
    'prehistory:seed',
    (_: void) => plan(),
    'The prehistory begins to run'
  )
  const running = usePrehistoryAction(
    'prehistory:run',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The prehistory begins to run'
  )
  const aborting = usePrehistoryAction(
    'prehistory:abort',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The prehistory stops'
  )
  const removing = usePrehistoryAction(
    'prehistory:remove',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The record of the prehistory is struck out'
  )
  const noWorld = worldId === null ? 'This thing stands on no world' : null
  const settled =
    view.state !== null && !OPEN_STATES.has(view.state)
      ? 'A prehistory that ran keeps its length; strike out its record first'
      : null
  const planBlocked = blocked ?? noWorld ?? settled
  const seedBlocked =
    planBlocked ??
    (view.lore_free
      ? null
      : 'Its story has begun; only a world still empty of lore takes a seeded past')
  const runBlocked =
    blocked ??
    noWorld ??
    (view.state === null || !OPEN_STATES.has(view.state)
      ? 'Plan a prehistory before running it'
      : null)
  const abortBlocked =
    blocked ?? (view.state === 'running' ? null : 'Nothing is running')
  const removeBlocked =
    blocked ??
    (view.state === null
      ? 'There is no record to strike out'
      : view.state === 'running'
        ? 'Stop the run first'
        : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ForgeCard
        icon={PREHISTORY_ICON}
        tone='info'
        title='Plan the past of this world'
        note={`Every other world is held while it runs; its records carry the epoch the world was born in. Seeding a world still empty of lore costs ${view.seed_cost} essence.`}
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={why(planBlocked, configuring.isPending) !== null}
              disabledReason={
                why(planBlocked, configuring.isPending) ?? undefined
              }
              onClick={() => configuring.mutate()}
            >
              <PREHISTORY_ICON />
              Plan it
            </Button>
            <Button
              size='sm'
              variant='secondary'
              disabled={why(seedBlocked, seeding.isPending) !== null}
              disabledReason={why(seedBlocked, seeding.isPending) ?? undefined}
              onClick={() => seeding.mutate()}
            >
              <Sprout />
              Seed and run it
            </Button>
          </div>
        }
      >
        <NumberField
          label='Epochs of past'
          value={epochs}
          min={1}
          max={view.epochs_max}
          onChange={setEpochs}
        />
        <NumberField
          label='Rounds between coarse steps'
          value={resolution}
          min={1}
          max={view.resolution_max}
          onChange={setResolution}
        />
      </ForgeCard>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Play}
          label='Run the planned past'
          busy={why(runBlocked, running.isPending)}
          onClick={() => running.mutate()}
        />
        <StepButton
          icon={CircleStop}
          label='Stop the run'
          busy={why(abortBlocked, aborting.isPending)}
          onClick={() => aborting.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike out the record'
          busy={why(removeBlocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </div>
  )
}

export function PrehistorySection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodePrehistory(nodeId)
  const view = query.data
  const page = useShowMore(
    view?.happenings ?? [],
    HAPPENINGS_SHOWN,
    HAPPENINGS_SHOWN * 2
  )
  const blocked = readOnlyReason ?? view?.absent_reason ?? null
  const editing = usePrehistoryAction(
    'prehistory:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ world_id: view?.world?.id ?? 0, ...vars }),
    'The prehistory keeps its new values'
  )
  return (
    <Section
      id='section-prehistory'
      title='Prehistory: the past its world lived before it joined the cosmos'
      description='The run of epochs its world lived before play, or the past it borrowed from its source, dreamt or mirrored, with the happenings Fate and the chronicler tell as its past. Things on no world show none; the Creator and stars stand on no world.'
      icon={PREHISTORY_ICON}
      tone='info'
    >
      <div
        data-surface='PrehistorySection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the past of its world' />
        ) : query.isError ? (
          <EmptyState
            icon={PREHISTORY_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='World'
                value={
                  query.data.world
                    ? query.data.world_type
                      ? `${query.data.world.name}, ${wordOf(worldTypeValues, query.data.world_type)}`
                      : query.data.world.name
                    : `${query.data.node.name} stands on no world`
                }
                icon={PREHISTORY_ICON}
                tone='muted'
              />
              <KpiTile
                label='Kind of past its world takes'
                value={
                  query.data.kind_of_world
                    ? PREHISTORY_KINDS[query.data.kind_of_world].label
                    : 'none'
                }
                icon={Hourglass}
                tone='info'
              />
              <KpiTile
                label='Run state'
                value={
                  query.data.state
                    ? PREHISTORY_STATES[query.data.state].label
                    : 'No prehistory'
                }
                icon={Play}
                tone={
                  query.data.state
                    ? PREHISTORY_STATES[query.data.state].tone
                    : 'muted'
                }
              />
              <KpiTile
                label='Epochs run'
                value={`${query.data.rounds_done} of ${query.data.epochs}`}
                icon={Timer}
                tone='gold'
              />
              <KpiTile
                label='Seconds spent, slow rounds'
                value={`${query.data.seconds} s, ${query.data.slow_rounds}`}
                icon={Gauge}
                tone={query.data.slow_rounds ? 'warning' : 'muted'}
              />
              <KpiTile
                label='Born in epoch'
                value={
                  query.data.birth_epoch === null
                    ? 'not run'
                    : String(query.data.birth_epoch)
                }
                icon={Sprout}
                tone='muted'
              />
            </div>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              {query.data.kind && (
                <Chip icon={PREHISTORY_KINDS[query.data.kind].icon}>
                  Ran as {PREHISTORY_KINDS[query.data.kind].label.toLowerCase()}
                </Chip>
              )}
              {query.data.source && (
                <Chip icon={PREHISTORY_SOURCES[query.data.source].icon}>
                  {PREHISTORY_SOURCES[query.data.source].label}
                </Chip>
              )}
              <Chip icon={Timer}>
                {query.data.resolution === 1
                  ? 'Coarse steps every round'
                  : `Coarse steps every ${query.data.resolution} rounds`}
              </Chip>
              <Ref node={query.data.source_world} empty='no source world' />
            </div>
            <Bars
              chart='chart-prehistory'
              title='The legendary age, round by round'
              legend={[{ text: 'Magnitude', variant: 'warning' }]}
              rows={page.visible.map((happening) => ({
                key: String(happening.id),
                caption: `Round ${happening.round}: ${happening.text ?? happening.subject?.name ?? 'a happening'}`,
                segments: [
                  { value: happening.magnitude, fill: 'fill-warning' },
                ],
              }))}
              max={100}
              noun={['happening', 'happenings']}
              empty='No happenings are kept for its past.'
            />
            {query.data.happenings.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
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
              </div>
            ) : (
              <EmptyState
                icon={PREHISTORY_ICON}
                size='inline'
                title='No past is kept here'
                description={
                  query.data.absent_reason ??
                  'Its world has no prehistory yet; plan one below.'
                }
              />
            )}
            <RecordEditor
              title='Set the record of this prehistory'
              note={
                query.data.state
                  ? 'Values you set are held against the engine until you release them.'
                  : 'There is no record to set until a prehistory is planned.'
              }
              fields={recordFields(query.data)}
              locked={query.data.locked}
              busy={why(
                blocked ??
                  (query.data.state ? null : 'Plan a prehistory first'),
                editing.isPending
              )}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <Controls view={query.data} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
