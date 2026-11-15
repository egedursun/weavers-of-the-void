import { RotateCcw, Skull } from 'lucide-react'
import { EmptyState, KpiTile, LoadingBlock, Section } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  Facts,
  type Field,
  RecordEditor,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Bars } from '@/features/sacred/parts'
import { useEndsAction, useNodeLifecycle } from './api'
import { LIFE_CAUSES, LIFE_ICON, LIFE_KINDS, LIFE_STATES } from './labels'

const IDLE_MAX = 1000

const FIELDS: readonly Field[] = [
  { key: 'state', label: 'State', kind: 'pick', table: table(LIFE_STATES) },
  { key: 'cause', label: 'Why', kind: 'pick', table: table(LIFE_CAUSES) },
  {
    key: 'idle_epochs',
    label: 'Epochs without anyone or anything holding it',
    kind: 'number',
    min: 0,
    max: IDLE_MAX,
  },
]

export function LifecycleSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeLifecycle(nodeId)
  const absent = query.data?.absent_reason ?? null
  const blocked = readOnlyReason ?? absent
  const editing = useEndsAction(
    'lifecycle:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ holder_id: nodeId, ...vars }),
    'Its life keeps its new state'
  )
  const resetting = useEndsAction(
    'lifecycle:reset',
    (_: void) => ({ holder_id: nodeId }),
    'Its life is read again from the world'
  )
  const destroying = useEndsAction(
    'lifecycle:destroy',
    (_: void) => ({ holder_id: nodeId }),
    'The outer being is destroyed for good'
  )
  const running = useEndsAction(
    'lifecycles:run',
    (_: void) => ({}),
    'Every life is read'
  )
  const data = query.data
  const destroyBlocked =
    blocked ??
    (data?.kind !== 'outer_being'
      ? 'Only an outer being is destroyed for good'
      : data.state === 'destroyed'
        ? 'It is already destroyed'
        : null)
  return (
    <Section
      id='section-lifecycle'
      title='Life and end: whether it lives on, sleeps or is gone'
      description='Whether an ideology, theory or rite is still held, lies dormant in surviving texts, or is lost; whether a disease still has hosts or is eradicated; whether an outer being is present, banished or destroyed. Other kinds of things have no such life, and the controls say so.'
      icon={LIFE_ICON}
      tone='muted'
    >
      <div
        data-surface='LifecycleSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its life' />
        ) : query.isError ? (
          <EmptyState
            icon={LIFE_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {data?.kind && data.state ? (
              <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
                <KpiTile
                  label='State'
                  value={LIFE_STATES[data.state].label}
                  icon={LIFE_STATES[data.state].icon}
                  tone={LIFE_STATES[data.state].tone}
                  hint={LIFE_CAUSES[data.cause ?? 'living'].label}
                />
                <KpiTile
                  label={
                    data.kind === 'disease'
                      ? 'Hosts'
                      : data.kind === 'outer_being'
                        ? 'Breaches and cults'
                        : 'Holders'
                  }
                  value={String(data.holders)}
                  icon={LIFE_KINDS[data.kind].icon}
                  tone={LIFE_KINDS[data.kind].tone}
                />
                <KpiTile
                  label='Surviving texts'
                  value={String(data.texts)}
                  icon={LIFE_ICON}
                  tone='info'
                  hint={`${data.idle_epochs} of ${data.grace_epochs} epochs idle`}
                />
              </div>
            ) : (
              <EmptyState
                icon={LIFE_ICON}
                size='inline'
                title={
                  data?.kind
                    ? 'Its life is read at the next epoch'
                    : 'This has no such life'
                }
                description={absent ?? ''}
              />
            )}
            <Bars
              chart='chart-lifecycle'
              title='What still holds it against how long it may go unheld'
              legend={[
                { text: 'Now', variant: 'warning' },
                { text: 'Grace before it ends', variant: 'outline' },
              ]}
              rows={
                data?.kind
                  ? [
                      {
                        key: 'holders',
                        caption: `Holders: ${data.holders}`,
                        segments: [
                          { value: data.holders, fill: 'fill-success' },
                        ],
                      },
                      {
                        key: 'texts',
                        caption: `Surviving texts: ${data.texts}`,
                        segments: [{ value: data.texts, fill: 'fill-info' }],
                      },
                      {
                        key: 'idle',
                        caption: `Epochs unheld: ${data.idle_epochs} of ${data.grace_epochs}`,
                        segments: [
                          { value: data.idle_epochs, fill: 'fill-warning' },
                        ],
                        mark: data.grace_epochs,
                      },
                    ]
                  : []
              }
              noun={['measure', 'measures']}
              empty='This has no such life to measure.'
            />
            {data?.kind && (
              <Facts
                items={[
                  ['Kind', LIFE_KINDS[data.kind].label],
                  [
                    'In this state since',
                    data.since_epoch === null
                      ? 'not yet read'
                      : `epoch ${data.since_epoch}`,
                  ],
                ]}
              />
            )}
            {data?.locked.includes('state') && (
              <Chip icon={LIFE_ICON} variant='warning'>
                Held against the engine
              </Chip>
            )}
            <RecordEditor
              title='Set its life'
              note='Every value you set is held against the engine and against the sons until you release it.'
              fields={FIELDS}
              locked={data?.locked ?? []}
              busy={why(blocked, editing.isPending)}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                icon={RotateCcw}
                label='Read its life again from the world'
                busy={why(blocked, resetting.isPending)}
                onClick={() => resetting.mutate()}
              />
              <StepButton
                icon={Skull}
                label={`Destroy for good (${data?.destroy_cost ?? 0} essence)`}
                busy={why(destroyBlocked, destroying.isPending)}
                onClick={() => destroying.mutate()}
              />
              <StepButton
                icon={LIFE_ICON}
                label='Read every life now'
                busy={why(readOnlyReason, running.isPending)}
                onClick={() => running.mutate()}
              />
            </div>
          </>
        )}
      </div>
    </Section>
  )
}
