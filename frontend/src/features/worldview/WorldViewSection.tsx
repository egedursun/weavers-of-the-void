import { RotateCcw } from 'lucide-react'
import { worldTypeValues } from '@/api/generated/schema'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  Facts,
  type Field,
  RecordEditor,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { wordOf } from '@/features/entity/affairs/labels'
import { Ref } from '@/features/gatherings/parts'
import { PREHISTORY_KINDS } from '@/features/prehistory/labels'
import { Bars } from '@/features/sacred/parts'
import {
  type WorldNatureView,
  type WorldViewNodeView,
  useNodeWorldView,
  useWorldViewAction,
} from './api'
import {
  FLAGS,
  LIGHTS,
  NEEDS,
  NUMBERS,
  SETTLES,
  SHARES,
  WARS,
  WORLD_VIEW_ICON,
} from './labels'

const SHARE_MAX = 500
const NUMBER_MAX = 100
const YES_NO = { true: 'Yes', false: 'No' }
const ORDINARY = 100

const FIELDS: readonly Field[] = [
  { key: 'light', label: 'Light', kind: 'pick', table: table(LIGHTS) },
  {
    key: 'need',
    label: 'What binds its towns',
    kind: 'pick',
    table: table(NEEDS),
  },
  {
    key: 'settle',
    label: 'How its towns stand',
    kind: 'pick',
    table: table(SETTLES),
  },
  {
    key: 'war',
    label: 'Where its wars are fought',
    kind: 'pick',
    table: table(WARS),
  },
  {
    key: 'prehistory_kind',
    label: 'Kind of past it takes',
    kind: 'pick',
    table: table(PREHISTORY_KINDS),
  },
  ...FLAGS.map((flag): Field => ({
    key: flag.key,
    label: flag.label,
    kind: 'pick',
    table: YES_NO,
  })),
  ...SHARES.map((share): Field => ({
    key: share.key,
    label: `${share.label} (%)`,
    kind: 'number',
    min: 0,
    max: SHARE_MAX,
  })),
  ...NUMBERS.map((number): Field => ({
    key: number.key,
    label: number.label,
    kind: 'number',
    min: 0,
    max: NUMBER_MAX,
  })),
]

function Nature({ nature }: { nature: WorldNatureView }) {
  const light = LIGHTS[nature.light]
  const need = NEEDS[nature.need]
  const settle = SETTLES[nature.settle]
  const war = WARS[nature.war]
  const past = PREHISTORY_KINDS[nature.prehistory_kind]
  return (
    <div className='flex min-w-0 flex-wrap gap-2'>
      <Chip icon={light.icon}>Light: {light.label}</Chip>
      <Chip icon={need.icon}>Towns bound to: {need.label}</Chip>
      <Chip icon={settle.icon}>Towns stand: {settle.label}</Chip>
      <Chip icon={war.icon}>Wars fought: {war.label}</Chip>
      <Chip icon={past.icon}>Past it takes: {past.label}</Chip>
      {FLAGS.map((flag) => (
        <Chip
          key={flag.key}
          icon={flag.icon}
          variant={nature[flag.key] ? 'outline' : 'warning'}
        >
          {flag.label}: {nature[flag.key] ? 'yes' : 'none'}
        </Chip>
      ))}
    </div>
  )
}

function Shares({ data }: { data: WorldViewNodeView }) {
  const nature = data.nature
  const kind = data.kind_nature
  return (
    <Bars
      chart='chart-world-view'
      title='What this world gives and how often it strikes, against an ordinary world'
      legend={[
        { text: 'This world', variant: 'warning' },
        { text: 'Its kind', variant: 'outline' },
      ]}
      rows={
        nature
          ? SHARES.map((share) => ({
              key: share.key,
              caption: `${share.label}: ${nature[share.key]}%${kind ? `, its kind ${kind[share.key]}%` : ''}`,
              segments: [{ value: nature[share.key], fill: 'fill-warning' }],
              mark: kind ? kind[share.key] : ORDINARY,
            }))
          : []
      }
      max={SHARE_MAX}
      noun={['share', 'shares']}
      empty='This thing stands on no world, so no world nature reaches it.'
    />
  )
}

function Numbers({ nature }: { nature: WorldNatureView }) {
  return (
    <Facts
      items={NUMBERS.map((number) => [
        number.label,
        String(nature[number.key]),
      ])}
    />
  )
}

export function WorldViewSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeWorldView(nodeId)
  const worldId = query.data?.world?.id ?? null
  const absent = query.data?.absent_reason ?? null
  const editing = useWorldViewAction(
    'world_view:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({
      world_id: worldId ?? 0,
      ...vars,
    }),
    'The world keeps its new nature'
  )
  const resetting = useWorldViewAction(
    'world_view:reset',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The world returns to the nature of its kind'
  )
  const running = useWorldViewAction(
    'world_views:run',
    (_: void) => ({}),
    'Every world is read'
  )
  const blocked = readOnlyReason ?? absent
  return (
    <Section
      id='section-world-view'
      title='World nature: what its world gives and binds'
      description='The nature of the world this thing stands on: its light, soil and fire, its seasons and nights, what binds its towns, how they stand, where its wars are fought, and how much timber, ore, food and room for life it gives against how often it strikes. Every kind of thing shows the nature of its world; the Creator and stars stand on none, and the controls say so.'
      icon={WORLD_VIEW_ICON}
      tone='info'
    >
      <div
        data-surface='WorldViewSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the nature of its world' />
        ) : query.isError ? (
          <EmptyState
            icon={WORLD_VIEW_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Facts
              items={[
                [
                  'World',
                  <Ref key='world' node={query.data.world} empty='no world' />,
                ],
                [
                  'Kind of world',
                  query.data.world_type
                    ? wordOf(worldTypeValues, query.data.world_type)
                    : 'none',
                ],
                [
                  'Set for this world',
                  query.data.seeded
                    ? `since epoch ${query.data.updated_epoch ?? 0}`
                    : 'not yet: it follows its kind',
                ],
              ]}
            />
            {query.data.nature ? (
              <Nature nature={query.data.nature} />
            ) : (
              <EmptyState
                icon={WORLD_VIEW_ICON}
                size='inline'
                title='No world nature reaches this'
                description={absent ?? ''}
              />
            )}
            <Shares data={query.data} />
            {query.data.nature && <Numbers nature={query.data.nature} />}
            <RecordEditor
              act={editing}
              title='Set the nature of this world'
              note='Every value you set is held against the engine and against the sons until you release it.'
              fields={FIELDS}
              locked={query.data.locked}
              busy={why(blocked, editing.isPending)}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                act={resetting}
                icon={RotateCcw}
                label='Return it to the nature of its kind'
                busy={why(blocked, resetting.isPending)}
                onClick={() => resetting.mutate()}
              />
              <StepButton
                act={running}
                icon={WORLD_VIEW_ICON}
                label='Read every world now'
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
