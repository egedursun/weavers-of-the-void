import { useState } from 'react'
import { CirclePlus, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { FORMS, table } from '@/features/arcana/labels'
import { ELEMENTS } from '@/features/cosmography/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type AspectView,
  type CreatureAttackRecord,
  type HeroQuestView,
  type HorrorEventView,
  type TypedModelsView,
  useTypedModels,
} from './api'
import {
  AIMS,
  ASPECT_ICON,
  ATTACK_EFFECTS,
  ATTACK_ICON,
  DELIVERIES,
  HORROR_EFFECTS,
  HORROR_ICON,
  HORROR_SCOPES,
  HORROR_SENSES,
  HORROR_SOURCES,
  HORROR_TARGETS,
  OBSTACLES,
  QUEST_ICON,
  QUEST_STATES,
  QUEST_TARGETS,
  RANGES,
  REWARDS,
  SCALES,
} from './labels'

const SHOWN = 4
const HOLD =
  'Values you set are held against the engine until you release them.'
const YES_NO = { true: 'Yes', false: 'No' }
const NOT_DIMENSION = 'Only a dimension has aspects'
const ELEMENT_NAMES = Object.fromEntries(
  Object.entries(ELEMENTS).map(([key, label]) => [
    key,
    { label, icon: ASPECT_ICON, tone: 'info' as const },
  ])
)

type Edit = { values: EditValues; release: string[] }

const HORROR_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name given to it', kind: 'text' },
  {
    key: 'target',
    label: 'What it touches',
    kind: 'pick',
    table: table(HORROR_TARGETS),
  },
  {
    key: 'effect',
    label: 'What it does',
    kind: 'pick',
    table: table(HORROR_EFFECTS),
  },
  {
    key: 'scope',
    label: 'How far it reaches',
    kind: 'pick',
    table: table(HORROR_SCOPES),
  },
  {
    key: 'sense',
    label: 'How it is perceived',
    kind: 'pick',
    table: table(HORROR_SENSES),
  },
  {
    key: 'source',
    label: 'Where it comes from',
    kind: 'pick',
    table: table(HORROR_SOURCES),
  },
  {
    key: 'duration',
    label: 'Epochs it lingers',
    kind: 'number',
    min: 1,
    max: 100,
  },
  {
    key: 'sanity_cost',
    label: 'Sanity it costs each epoch',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'leak', label: 'Leak it adds', kind: 'number', min: 0, max: 100 },
  { key: 'until_epoch', label: 'Lingers until epoch', kind: 'number', min: 0 },
]
const ATTACK_FIELDS: readonly Field[] = [
  {
    key: 'delivery',
    label: 'How it reaches',
    kind: 'pick',
    table: table(DELIVERIES),
  },
  {
    key: 'effect',
    label: 'What it does',
    kind: 'pick',
    table: table(ATTACK_EFFECTS),
  },
  { key: 'range', label: 'Range', kind: 'pick', table: table(RANGES) },
  {
    key: 'recharge',
    label: 'Epochs between uses',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'permanent',
    label: 'Its effect lasts for good',
    kind: 'pick',
    table: YES_NO,
  },
]
const QUEST_FIELDS: readonly Field[] = [
  { key: 'aim', label: 'Aim', kind: 'pick', table: table(AIMS) },
  {
    key: 'target_kind',
    label: 'What it seeks',
    kind: 'pick',
    table: table(QUEST_TARGETS),
  },
  {
    key: 'obstacle',
    label: 'What stands in the way',
    kind: 'pick',
    table: table(OBSTACLES),
  },
  { key: 'reward', label: 'Reward', kind: 'pick', table: table(REWARDS) },
  { key: 'scale', label: 'Scale', kind: 'pick', table: table(SCALES) },
]
const ASPECT_FIELDS: readonly Field[] = [
  {
    key: 'form',
    label: 'Form of the world',
    kind: 'pick',
    table: { none: 'None', ...table(FORMS) },
  },
  {
    key: 'element',
    label: 'Matter',
    kind: 'pick',
    table: { none: 'None', ...table(ELEMENT_NAMES) },
  },
  { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
]

function Horror({
  row,
  blocked,
}: {
  row: HorrorEventView
  blocked: string | null
}) {
  const target = HORROR_TARGETS[row.target]
  const editing = useMadeAction(
    'horror_event:edit',
    (vars: Edit) => ({
      horror_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The horror is set so'
  )
  const removing = useMadeAction(
    'horror_event:delete',
    (_: void) => ({ horror_id: row.id }),
    'The horror is undone'
  )
  return (
    <RecordRow
      icon={target.icon}
      tone={target.tone ?? 'danger'}
      title={`${row.name ?? 'A horror'}: ${HORROR_EFFECTS[row.effect].label.toLowerCase()} ${target.label.toLowerCase()} in ${row.world.name}`}
      caption={`${HORROR_SCOPES[row.scope].label}; ${HORROR_SENSES[row.sense].label.toLowerCase()}; from ${HORROR_SOURCES[row.source].label.toLowerCase()}; epoch ${row.epoch}${row.until_epoch !== null ? ` until ${row.until_epoch}` : ''}; costs ${row.sanity_cost} sanity, adds ${row.leak} leak, lasts ${row.duration}`}
    >
      <Ref node={row.subject} empty='no one singled out' />
      <Ref node={row.source_node} empty='no named source' />
      <RecordEditor
        title='Set the horror'
        note={HOLD}
        fields={HORROR_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Undo it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Attack({
  row,
  blocked,
}: {
  row: CreatureAttackRecord
  blocked: string | null
}) {
  const delivery = DELIVERIES[row.delivery]
  const editing = useMadeAction(
    'creature_attack:edit',
    (vars: Edit) => ({
      attack_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The attack is set so'
  )
  const removing = useMadeAction(
    'creature_attack:delete',
    (_: void) => ({ attack_id: row.id }),
    'The attack is taken away'
  )
  return (
    <RecordRow
      icon={delivery.icon}
      tone={ATTACK_EFFECTS[row.effect].tone ?? 'danger'}
      title={`${delivery.label} of ${ATTACK_EFFECTS[row.effect].label.toLowerCase()}`}
      caption={`reaches ${RANGES[row.range].label.toLowerCase()}; ${row.recharge ? `rests ${row.recharge} epochs between uses` : 'ready every epoch'}${row.permanent ? '; its effect lasts for good' : ''}${row.last_used_epoch !== null ? `; last used in epoch ${row.last_used_epoch}` : ''}`}
    >
      <RecordEditor
        title='Set the attack'
        note={HOLD}
        fields={ATTACK_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Take it away'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Quest({
  row,
  blocked,
}: {
  row: HeroQuestView
  blocked: string | null
}) {
  const aim = AIMS[row.aim]
  const editing = useMadeAction(
    'hero_quest:edit',
    (vars: Edit) => ({
      quest_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The quest is set so'
  )
  return (
    <RecordRow
      icon={aim.icon}
      tone={aim.tone ?? 'info'}
      title={`${aim.label} ${QUEST_TARGETS[row.target_kind].label.toLowerCase()}: ${row.description}`}
      caption={`${SCALES[row.scale].label} quest, ${QUEST_STATES[row.status].label.toLowerCase()}; in the way: ${OBSTACLES[row.obstacle].label.toLowerCase()}; reward: ${REWARDS[row.reward].label.toLowerCase()}; from epoch ${row.started_epoch}${row.ended_epoch !== null ? ` to ${row.ended_epoch}` : ''}`}
    >
      <Ref node={row.target} empty='no target named' />
      <RecordEditor
        title='Set the quest'
        note={HOLD}
        fields={QUEST_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
    </RecordRow>
  )
}

function Aspect({ row, blocked }: { row: AspectView; blocked: string | null }) {
  const editing = useMadeAction(
    'dimension_aspect:edit',
    (vars: Edit) => ({
      aspect_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The aspect is set so'
  )
  const removing = useMadeAction(
    'dimension_aspect:delete',
    (_: void) => ({ aspect_id: row.id }),
    'The aspect fades'
  )
  const named = row.form
    ? FORMS[row.form]
    : {
        label: row.element ? ELEMENTS[row.element] : 'An aspect',
        icon: ASPECT_ICON,
        tone: 'info' as const,
      }
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone ?? 'info'}
      title={`${named.label}, strength ${row.strength}`}
      caption={row.form ? 'A form of the world' : 'A matter'}
    >
      <RecordEditor
        title='Set the aspect'
        note={HOLD}
        fields={ASPECT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Take it away'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Forges({
  view,
  nodeId,
  blocked,
}: {
  view: TypedModelsView
  nodeId: number
  blocked: string | null
}) {
  const [delivery, setDelivery] = useState<string>('touch')
  const [effect, setEffect] = useState<string>('force')
  const [range, setRange] = useState<string>('near')
  const [recharge, setRecharge] = useState('0')
  const [form, setForm] = useState<string>('space')
  const [strength, setStrength] = useState('50')
  const arming = useMadeAction(
    'creature_attack:create',
    (_: void) => ({
      node_id: nodeId,
      delivery: delivery as CreatureAttackRecord['delivery'],
      effect: effect as CreatureAttackRecord['effect'],
      range: range as CreatureAttackRecord['range'],
      recharge: Math.min(100, Math.max(0, Number(recharge) || 0)),
    }),
    'It has a new attack'
  )
  const shaping = useMadeAction(
    'dimension_aspect:create',
    (_: void) => ({
      dimension_id: nodeId,
      form: form in FORMS ? (form as NonNullable<AspectView['form']>) : null,
      element:
        form in ELEMENTS ? (form as NonNullable<AspectView['element']>) : null,
      strength: Math.min(100, Math.max(0, Number(strength) || 0)),
    }),
    'The dimension takes on a new aspect'
  )
  const notDimension = view.is_dimension ? null : NOT_DIMENSION
  return (
    <>
      <ForgeCard
        icon={CirclePlus}
        tone='danger'
        title='Give it an attack'
        note='Each attack adds to the harm of its raids; attacks that reach a whole town or work by sight make it more dreaded.'
        columns={2}
        action={
          <StepButton
            icon={ATTACK_ICON}
            label='Arm it'
            variant='default'
            busy={why(blocked, arming.isPending)}
            onClick={() => arming.mutate()}
          />
        }
      >
        <ChoiceField
          label='How it reaches'
          value={delivery}
          table={DELIVERIES}
          blocked={blocked}
          onPick={setDelivery}
        />
        <ChoiceField
          label='What it does'
          value={effect}
          table={ATTACK_EFFECTS}
          blocked={blocked}
          onPick={setEffect}
        />
        <ChoiceField
          label='Range'
          value={range}
          table={RANGES}
          blocked={blocked}
          onPick={setRange}
        />
        <NumberField
          label='Epochs between uses'
          value={recharge}
          min={0}
          max={100}
          onChange={setRecharge}
        />
      </ForgeCard>
      <ForgeCard
        icon={CirclePlus}
        tone='info'
        title='Give the dimension an aspect'
        note='Each aspect pulls the dimension its own way every epoch: its veil, stability, time, magic, hostility, sanity drain or leak.'
        columns={2}
        action={
          <StepButton
            icon={ASPECT_ICON}
            label='Shape it'
            variant='default'
            busy={why(blocked ?? notDimension, shaping.isPending)}
            onClick={() => shaping.mutate()}
          />
        }
      >
        <ChoiceField
          label='Form or matter'
          value={form}
          table={{ ...FORMS, ...ELEMENT_NAMES }}
          blocked={blocked ?? notDimension}
          onPick={setForm}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={100}
          onChange={setStrength}
        />
      </ForgeCard>
    </>
  )
}

function Listed<T>({
  rows,
  empty,
  render,
}: {
  rows: readonly T[]
  empty: string | null
  render: (row: T) => React.ReactNode
}) {
  const paged = useShowMore(rows, SHOWN, SHOWN)
  if (!rows.length)
    return empty ? <Chip icon={HORROR_ICON}>{empty}</Chip> : null
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {paged.visible.map(render)}
      </ul>
      <ShowMore state={paged} />
    </>
  )
}

export function TypedModelsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useTypedModels(nodeId)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-typed-models'
      title='Horrors, attacks, quests and aspects'
      description='Horrors that touched it, the attacks it can make, the quests it took up and, for a dimension, the aspects that pull it its own way.'
      icon={QUEST_ICON}
      tone='verdigris'
    >
      <div
        data-surface='TypedModelsSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its horrors, attacks, quests and aspects' />
        ) : query.isError ? (
          <EmptyState
            icon={QUEST_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Listed
              rows={query.data.horrors}
              empty={`No horror has touched ${query.data.node.name}`}
              render={(row) => (
                <Horror key={row.id} row={row} blocked={blocked} />
              )}
            />
            <Listed
              rows={query.data.attacks}
              empty='It has no attacks of its own'
              render={(row) => (
                <Attack key={row.id} row={row} blocked={blocked} />
              )}
            />
            <Listed
              rows={query.data.quests}
              empty={null}
              render={(row) => (
                <Quest key={row.id} row={row} blocked={blocked} />
              )}
            />
            <Listed
              rows={query.data.aspects}
              empty={
                query.data.is_dimension ? 'This dimension has no aspects' : null
              }
              render={(row) => (
                <Aspect key={row.id} row={row} blocked={blocked} />
              )}
            />
            <Forges view={query.data} nodeId={nodeId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
