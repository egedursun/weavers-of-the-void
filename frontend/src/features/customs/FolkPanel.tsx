import { useState } from 'react'
import { Feather, Landmark, Plus, RefreshCcw } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { CLASSES } from '@/features/entity/affairs/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { STAGES as LIFE_STAGES } from '@/features/entity/mortal/labels'
import { NumberField } from '@/features/entity/realm/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type CustomsNodeView, useCustomsAction } from './api'
import {
  DUTIES,
  WAYS,
  GOALS,
  GRADES,
  INTOXICANTS,
  MARK_KINDS,
  MEANINGS,
  PATTERNS,
  STAGES,
  USES,
} from './labels'
import { MANY, SPAN, useCustomsRow, useCustomsStep } from './model'

type View = CustomsNodeView
type Revival = View['revivals'][number]
type Intox = View['intoxicants'][number]
type MarkCustom = View['mark_customs'][number]
type Budget = View['budgets'][number]
type Naming = NonNullable<View['naming']>
type AgeSet = View['age_sets'][number]

const NO_PEOPLE = 'Only a people, or one of its folk, keeps customs'
const SHARES = [
  'work',
  'rest',
  'worship',
  'leisure',
  'travel',
  'service',
  'learning',
  'care',
  'art',
  'housework',
  'sleep',
  'civic',
  'training',
] as const

function RevivalCard({
  row,
  blocked,
}: {
  row: Revival
  blocked: string | null
}) {
  const action = useCustomsRow(
    'revival:edit',
    'revival:delete',
    { record_id: row.id },
    blocked
  )
  const stage = STAGES[row.stage]
  return (
    <Held
      icon={stage.icon}
      tone={stage.tone}
      title={GOALS[row.goal].label}
      caption={`${WAYS[row.way].label} · ${stage.label} · from epoch ${row.started_epoch}${row.ended_epoch !== null ? ` to ${row.ended_epoch}` : ''}${row.dominant ? ` · against ${row.dominant.name}` : ''}${row.prophet ? ` · led by ${row.prophet.name}` : ''}`}
      removeLabel='Strike the movement'
      editTitle='Set the movement'
      note='A movement rises when rulers, conquerors or neighbours press their ways on a people. It passes through stress and distortion to revival, when it works its way toward its goal, and settles into a new steady way or meets its goal.'
      fields={[
        { key: 'way', label: 'Way', kind: 'pick', table: table(WAYS) },
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        { key: 'goal', label: 'Goal', kind: 'pick', table: table(GOALS) },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'prophet_node_id',
          label: 'Prophet',
          kind: 'node',
          types: ['mortal'],
        },
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
      extra={<Tag item={GOALS[row.goal]} />}
    >
      <Meter
        label={`Strength toward the next stage (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='warning'
        icon={RefreshCcw}
      />
    </Held>
  )
}

function IntoxCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Intox
  blocked: string | null
}) {
  const action = useCustomsRow(
    'intoxicant_custom:edit',
    'intoxicant_custom:delete',
    { people_id: people, intoxicant: row.intoxicant },
    blocked
  )
  const spec = INTOXICANTS[row.intoxicant]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`${USES[row.use].label} · accepted ${row.acceptance} of ${SPAN}`}
      removeLabel='Strike the custom'
      editTitle='Set the custom'
      note='Taken daily it breeds dependence, at feasts it breeds brawls, in rites it gives mystics visions; brewing uses the brew base of the towns.'
      fields={[
        { key: 'use', label: 'When taken', kind: 'pick', table: table(USES) },
        {
          key: 'acceptance',
          label: 'Acceptance',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={USES[row.use]} />}
    />
  )
}

function MarkCustomCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: MarkCustom
  blocked: string | null
}) {
  const action = useCustomsRow(
    'mark_custom:edit',
    'mark_custom:delete',
    { people_id: people, kind: row.kind },
    blocked
  )
  const spec = MARK_KINDS[row.kind]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={`${spec.label} means ${MEANINGS[row.meaning].label.toLowerCase()}`}
      caption='A mark the people give and read'
      removeLabel='Strike the custom'
      editTitle='Set the custom'
      note='The people place this mark when its meaning comes to pass: a deed, a marriage, a mourning, a birth, an initiation, a rise to rule, a faith taken up, a guild joined or a betrothal.'
      fields={[
        {
          key: 'meaning',
          label: 'Meaning',
          kind: 'pick',
          table: table(MEANINGS),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function BudgetCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Budget
  blocked: string | null
}) {
  const action = useCustomsRow(
    'time_budget:edit',
    'time_budget:delete',
    {
      people_id: people,
      social_class: row.social_class,
      life_stage: row.life_stage,
    },
    blocked
  )
  const stage = LIFE_STAGES[row.life_stage]
  return (
    <Held
      icon={stage.icon}
      tone='info'
      title={`${CLASSES[row.social_class] ?? row.social_class}, ${stage.label.toLowerCase()}`}
      caption={SHARES.map((key) => `${key} ${row[key]}`).join(' · ')}
      removeLabel='Strike the budget'
      editTitle='Set the budget'
      note="A class's year: work sets a town's output, leisure its satisfaction, worship its piety, rest eases unrest, travel brings trade, service guards the walls, learning, care and art feed the needs they serve, housework keeps the home, sleep is the night a body needs, civic duty lowers crime and training sharpens skills."
      fields={SHARES.map((key) => ({
        key,
        label: key[0].toUpperCase() + key.slice(1),
        kind: 'number' as const,
        min: 0,
        max: SPAN,
      }))}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function NamingCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Naming
  blocked: string | null
}) {
  const action = useCustomsRow(
    'naming_custom:edit',
    'naming_custom:delete',
    { people_id: people },
    blocked
  )
  return (
    <Held
      icon={Feather}
      tone='gold'
      title={PATTERNS[row.pattern].label}
      caption={`${row.secret_names ? 'secret names' : 'no secret names'} · names of the dead unspoken for ${plural(row.taboo_epochs, 'epoch', 'epochs')}`}
      removeLabel='Strike the custom'
      editTitle='Set how the people name'
      note='A secret name is the true name; the names of the dead go unspoken and cannot be learned while the taboo lasts; folk are renamed at initiation, marriage or a vow where the people do so.'
      fields={[
        {
          key: 'pattern',
          label: 'Pattern',
          kind: 'pick',
          table: table(PATTERNS),
        },
        {
          key: 'secret_names',
          label: 'Secret names',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'taboo_epochs',
          label: 'Names of the dead unspoken (epochs)',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'rename_on_initiation',
          label: 'Rename at initiation',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'rename_on_marriage',
          label: 'Rename at marriage',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'rename_on_vow',
          label: 'Rename at a vow',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'posthumous_names',
          label: 'Name the dead anew',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

type Duty = View['grade_duties'][number]

function DutyCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Duty
  blocked: string | null
}) {
  const action = useCustomsRow(
    'grade_duty:edit',
    'grade_duty:delete',
    { people_id: people, duty: row.duty },
    blocked
  )
  const duty = DUTIES[row.duty]
  return (
    <Held
      icon={duty.icon}
      tone={duty.tone}
      title={duty.label}
      caption={`Carried by the ${GRADES[row.grade].label.toLowerCase()}${row.held ? ' · held' : ''}`}
      removeLabel='Take the duty away'
      editTitle='Set the duty'
      note='A people gives a duty to the grade it chooses; with no grade named for war, it sends no grade to war.'
      fields={[
        { key: 'grade', label: 'Grade', kind: 'pick', table: table(GRADES) },
      ]}
      locked={row.held ? ['grade'] : []}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={duty} />}
    />
  )
}

function AgeSetCard({ row, blocked }: { row: AgeSet; blocked: string | null }) {
  const action = useCustomsRow(
    'age_set:edit',
    'age_set:delete',
    { record_id: row.id },
    blocked
  )
  const grade = GRADES[row.grade]
  return (
    <Held
      icon={grade.icon}
      tone={grade.tone}
      title={row.name}
      caption={`${grade.label} · ${plural(row.members, 'member', 'members')} · initiated from epoch ${row.initiated_from}${row.initiated_to !== null ? ` to ${row.initiated_to}` : ', still open'}`}
      removeLabel='Strike the age-set'
      editTitle='Set the age-set'
      note='Those initiated together move through the grades together; youths may not wed, a grade swells the levy only where the people gives it the duty of war, and a set waits while the set ahead holds its grade.'
      fields={[
        { key: 'name', label: 'Age-set name', kind: 'text' },
        {
          key: 'initiated_from',
          label: 'Initiated from epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'initiated_to',
          label: 'Initiated to epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'grade', label: 'Grade', kind: 'pick', table: table(GRADES) },
        {
          key: 'promoted_epoch',
          label: 'Promoted in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={grade} />}
    />
  )
}

export function FolkPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const people = data.people?.id ?? null
  const [goal, setGoal] = useState('revive_language')
  const [way, setWay] = useState('restore')
  const [duty, setDuty] = useState('council')
  const [dutyGrade, setDutyGrade] = useState('senior_elders')
  const [intox, setIntox] = useState('brew')
  const [mark, setMark] = useState('tattoo')
  const [meaning, setMeaning] = useState('deed')
  const [klass, setKlass] = useState('farmer')
  const [lifeStage, setLifeStage] = useState('adult')
  const [setName, setSetName] = useState('')
  const [work, setWork] = useState('55')
  const noPeople = people === null ? NO_PEOPLE : null
  const reviving = useCustomsAction(
    'revival:create',
    (_: void) => ({
      people_entity_id: people ?? 0,
      way: way as Revival['way'],
      goal: goal as Revival['goal'],
    }),
    'A movement rises'
  )
  const drinking = useCustomsAction(
    'intoxicant_custom:set',
    (_: void) => ({
      people_id: people ?? 0,
      intoxicant: intox as Intox['intoxicant'],
      use: 'feast',
      acceptance: 50,
    }),
    'The custom is set'
  )
  const marking = useCustomsAction(
    'mark_custom:set',
    (_: void) => ({
      people_id: people ?? 0,
      kind: mark as MarkCustom['kind'],
      meaning: meaning as MarkCustom['meaning'],
    }),
    'The mark is read so'
  )
  const budgeting = useCustomsAction(
    'time_budget:set',
    (_: void) => ({
      people_id: people ?? 0,
      social_class: klass as Budget['social_class'],
      life_stage: lifeStage as Budget['life_stage'],
      work: Number(work || '0'),
      rest: 20,
      worship: 10,
      leisure: 10,
      travel: 3,
      service: 2,
      learning: 0,
      care: 0,
      art: 0,
      housework: 0,
      sleep: 0,
      civic: 0,
      training: 0,
    }),
    'The year is set'
  )
  const naming = useCustomsAction(
    'naming_custom:set',
    (_: void) => ({
      people_id: people ?? 0,
      pattern: 'given',
      secret_names: false,
      taboo_epochs: 0,
    }),
    'The people name so'
  )
  const dutying = useCustomsAction(
    'grade_duty:set',
    (_: void) => ({
      people_id: people ?? 0,
      duty: duty as Duty['duty'],
      grade: dutyGrade as Duty['grade'],
      hold: true,
    }),
    'The duty is given'
  )
  const opening = useCustomsAction(
    'age_set:create',
    (_: void) => ({
      people_entity_id: people ?? 0,
      name: setName.trim(),
      grade: 'youths',
    }),
    'The age-set opens'
  )
  const running = useCustomsStep(
    'age_set:run',
    {},
    blocked,
    'The age-sets move'
  )
  const busy = (pending: boolean, extra: string | null = null) =>
    why(blocked ?? noPeople ?? extra, pending)
  return (
    <div data-surface='CustomsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-customs'
        title='Strength of the movements'
        legend={[{ text: 'Strength', variant: 'warning' }]}
        rows={data.revivals.map((row) => ({
          key: row.id,
          caption: `${GOALS[row.goal].label}: ${STAGES[row.stage].label}`,
          segments: [{ value: row.strength, fill: 'fill-warning' }],
        }))}
        max={SPAN}
        noun={['movement', 'movements']}
        empty='No movement stirs among its people.'
      />
      <Listed
        title='Movements'
        items={data.revivals}
        empty='No movement stirs among its people.'
        noun={['movement', 'movements']}
        itemKey={(item) => item.id}
      >
        {(item) => <RevivalCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Intoxicants'
        items={data.intoxicants}
        empty='Its people keeps no intoxicant custom.'
        noun={['custom', 'customs']}
        itemKey={(item) => item.intoxicant}
      >
        {(item) => (
          <IntoxCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Marks the people read'
        items={data.mark_customs}
        empty='Its people gives no mark a meaning.'
        noun={['mark', 'marks']}
        itemKey={(item) => item.kind}
      >
        {(item) => (
          <MarkCustomCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Time budgets'
        items={data.budgets}
        empty='No year is set for its classes.'
        noun={['budget', 'budgets']}
        itemKey={(item) => `${item.social_class}.${item.life_stage}`}
      >
        {(item) => (
          <BudgetCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      {data.naming ? (
        <NamingCard people={people ?? 0} row={data.naming} blocked={blocked} />
      ) : (
        <Muted variant='caption'>Its people keeps no naming custom yet.</Muted>
      )}
      <Listed
        title='Age-sets'
        items={data.age_sets}
        empty='Its people binds no age-sets.'
        noun={['age-set', 'age-sets']}
        itemKey={(item) => item.id}
      >
        {(item) => <AgeSetCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Duties of the grades'
        items={data.grade_duties}
        empty='No grade of its people carries a duty.'
        noun={['duty', 'duties']}
        itemKey={(item) => item.duty}
      >
        {(item) => (
          <DutyCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Landmark}
        tone='gold'
        title='Give a grade a duty'
        note='Name which grade carries war, herding, labour or council.'
        columns={2}
        action={
          <Button
            act={dutying}
            size='sm'
            disabled={busy(dutying.isPending) !== null}
            disabledReason={busy(dutying.isPending) ?? undefined}
            onClick={() => dutying.mutate()}
          >
            <Plus />
            Give the duty
          </Button>
        }
      >
        <MindPicker
          label='Duty'
          value={duty}
          table={table(DUTIES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setDuty}
        />
        <MindPicker
          label='Grade'
          value={dutyGrade}
          table={table(GRADES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setDutyGrade}
        />
      </ForgeCard>
      <ForgeCard
        icon={RefreshCcw}
        tone='gold'
        title='Stir a movement'
        note='A movement against the ways pressed on the people.'
        columns={2}
        action={
          <Button
            act={reviving}
            size='sm'
            disabled={busy(reviving.isPending) !== null}
            disabledReason={busy(reviving.isPending) ?? undefined}
            onClick={() => reviving.mutate()}
          >
            <Plus />
            Stir it
          </Button>
        }
      >
        <MindPicker
          label='Way'
          value={way}
          table={table(WAYS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setWay}
        />
        <MindPicker
          label='Goal'
          value={goal}
          table={table(GOALS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setGoal}
        />
      </ForgeCard>
      <ForgeCard
        icon={Feather}
        tone='info'
        title='Give the people a custom'
        note='An intoxicant they take, a mark they read, a year for a class and a way of naming.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              act={drinking}
              size='sm'
              variant='outline'
              disabled={busy(drinking.isPending) !== null}
              disabledReason={busy(drinking.isPending) ?? undefined}
              onClick={() => drinking.mutate()}
            >
              <Plus />
              Intoxicant
            </Button>
            <Button
              act={marking}
              size='sm'
              variant='outline'
              disabled={busy(marking.isPending) !== null}
              disabledReason={busy(marking.isPending) ?? undefined}
              onClick={() => marking.mutate()}
            >
              <Plus />
              Mark
            </Button>
            <Button
              act={budgeting}
              size='sm'
              variant='outline'
              disabled={busy(budgeting.isPending) !== null}
              disabledReason={busy(budgeting.isPending) ?? undefined}
              onClick={() => budgeting.mutate()}
            >
              <Plus />
              Year
            </Button>
            <Button
              act={naming}
              size='sm'
              disabled={
                busy(
                  naming.isPending,
                  data.naming ? 'It names already; adjust it above' : null
                ) !== null
              }
              disabledReason={
                busy(
                  naming.isPending,
                  data.naming ? 'It names already; adjust it above' : null
                ) ?? undefined
              }
              onClick={() => naming.mutate()}
            >
              <Plus />
              Naming
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Intoxicant'
          value={intox}
          table={table(INTOXICANTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setIntox}
        />
        <MindPicker
          label='Mark'
          value={mark}
          table={table(MARK_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMark}
        />
        <MindPicker
          label='Meaning'
          value={meaning}
          table={table(MEANINGS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMeaning}
        />
        <MindPicker
          label='Class'
          value={klass}
          table={CLASSES}
          placeholder='Choose'
          blocked={blocked}
          onPick={setKlass}
        />
        <MindPicker
          label='Time of life'
          value={lifeStage}
          table={table(LIFE_STAGES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setLifeStage}
        />
        <NumberField
          label='Work share'
          value={work}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setWork}
        />
      </ForgeCard>
      <ForgeCard
        icon={GRADES.youths.icon}
        tone='verdigris'
        title='Open an age-set'
        note='Youths of the people are initiated into the open set.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={RefreshCcw}
              label='Move the age-sets now'
              busy={running.busy}
              onClick={running.run}
            />
            <Button
              act={opening}
              size='sm'
              disabled={
                busy(
                  opening.isPending,
                  !setName.trim() ? 'Name the age-set' : null
                ) !== null
              }
              disabledReason={
                busy(
                  opening.isPending,
                  !setName.trim() ? 'Name the age-set' : null
                ) ?? undefined
              }
              onClick={() => opening.mutate()}
            >
              <Plus />
              Open it
            </Button>
          </div>
        }
      >
        <TextField
          label='Age-set name'
          value={setName}
          blocked={blocked}
          onChange={setSetName}
        />
      </ForgeCard>
    </div>
  )
}
