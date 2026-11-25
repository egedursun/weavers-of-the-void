import { useState } from 'react'
import {
  BookMarked,
  Crown,
  Flame,
  GraduationCap,
  Scale,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { KpiTile, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { VALUE_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { Ref } from '@/features/gatherings/parts'
import { type CollectiveView, useCollectiveAction } from './api'
import {
  BEHAVIOURS,
  BIASES,
  ELIGIBILITY,
  ETHICS,
  ROLES,
  SITUATIONS,
} from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { Held, Listed } from './parts'

type Norm = CollectiveView['norm_changes'][number]
type Custom = CollectiveView['norms'][number]
type Bias = NonNullable<CollectiveView['biases']>
type Lesson = CollectiveView['lessons'][number]
type Role = CollectiveView['roles'][number]

const CULTURES = ['people', 'cult']
const NO_CLASS = 'every'
const CLASS_PICK = { [NO_CLASS]: 'Every class', ...table(CLASS_SPEC) }

function CustomCard({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: Custom
  blocked: string | null
}) {
  const keys = {
    holder_id: holderId,
    situation: row.situation,
    behaviour: row.behaviour,
  }
  const action = useRow('social_norm:edit', 'social_norm:delete', keys, blocked)
  const behaviour = BEHAVIOURS[row.behaviour]
  const stance = ETHICS[row.stance]
  return (
    <Held
      icon={behaviour.icon}
      tone={stance.tone}
      title={`${behaviour.label} ${SITUATIONS[row.situation].label.toLowerCase()}`}
      caption={`Held so since epoch ${row.since_epoch}`}
      removeLabel='Let it lapse'
      editTitle='Set the custom'
      note='A conformist avoids what is shameful and seeks what is required; a scorner of tradition is drawn to the breach.'
      fields={[
        { key: 'stance', label: 'Stance', kind: 'pick', table: table(ETHICS) },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Chip icon={stance.icon}>{stance.label}</Chip>}
    />
  )
}

function CustomForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [situation, setSituation] = useState<keyof typeof SITUATIONS>('feast')
  const [behaviour, setBehaviour] = useState<keyof typeof BEHAVIOURS>('jest')
  const [stance, setStance] = useState('admirable')
  const setting = useCollectiveAction(
    'social_norm:set',
    (_: void) => ({
      holder_id: holderId,
      situation,
      behaviour,
      stance: stance as Custom['stance'],
    }),
    'The custom is set'
  )
  const busy = why(
    type !== null && CULTURES.includes(type)
      ? blocked
      : 'Only a people or cult keeps customs',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Scale}
      tone='gold'
      title='Set a custom'
      note='Decide what is required, admired, frowned on or forbidden in each situation; mortals weigh it whenever they act.'
      columns={3}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Scale />
          Make it custom
        </Button>
      }
    >
      <MindPicker
        label='Situation'
        value={situation}
        table={table(SITUATIONS)}
        blocked={busy}
        onPick={(value) => setSituation(value as keyof typeof SITUATIONS)}
      />
      <MindPicker
        label='Behaviour'
        value={behaviour}
        table={table(BEHAVIOURS)}
        blocked={busy}
        onPick={(value) => setBehaviour(value as keyof typeof BEHAVIOURS)}
      />
      <MindPicker
        label='Stance'
        value={stance}
        table={table(ETHICS)}
        blocked={busy}
        onPick={setStance}
      />
    </ForgeCard>
  )
}

function ChangeCard({ row, blocked }: { row: Norm; blocked: string | null }) {
  const action = useRemove('norm_change:delete', { change_id: row.id }, blocked)
  const after = ETHICS[row.after]
  return (
    <Held
      icon={BookMarked}
      tone={after.tone}
      title={`${BEHAVIOURS[row.behaviour].label} ${SITUATIONS[row.situation].label.toLowerCase()}`}
      caption={`Epoch ${row.epoch} · because of ${row.cause}`}
      removeLabel='Strike from the record'
      editTitle=''
      note=''
      fields={[]}
      locked={[]}
      blocked={action.busy}
      onEdit={null}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={row.before ? ETHICS[row.before].icon : undefined}>
            {row.before
              ? `Was ${ETHICS[row.before].label.toLowerCase()}`
              : 'No custom'}
          </Chip>
          <Chip icon={after.icon}>{after.label}</Chip>
        </>
      }
    />
  )
}

function BiasCard({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: Bias
  blocked: string | null
}) {
  const action = useRow(
    'learning_bias:edit',
    'learning_bias:delete',
    { holder_id: holderId },
    blocked
  )
  return (
    <Held
      icon={GraduationCap}
      tone='info'
      title='How this people learns'
      caption='Each epoch some copy the renowned, some the many and some what grips them.'
      removeLabel='Read it anew'
      editTitle='Set how they learn'
      note='Shares of the three ways mortals copy beliefs from one another.'
      fields={[
        {
          key: 'prestige_pct',
          label: 'Copy the renowned (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'conformity_pct',
          label: 'Copy the many (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'content_pct',
          label: 'Copy the gripping (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='grid min-w-0 gap-2 sm:grid-cols-3'>
        <KpiTile
          label='The renowned'
          value={`${row.prestige_pct}%`}
          icon={Crown}
          tone='gold'
        />
        <KpiTile
          label='The many'
          value={`${row.conformity_pct}%`}
          icon={Users}
          tone='info'
        />
        <KpiTile
          label='The gripping'
          value={`${row.content_pct}%`}
          icon={Flame}
          tone='warning'
        />
      </div>
    </Held>
  )
}

function BiasForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [prestige, setPrestige] = useState('40')
  const [conformity, setConformity] = useState('40')
  const [content, setContent] = useState('20')
  const setting = useCollectiveAction(
    'learning_bias:set',
    (_: void) => ({
      holder_id: holderId,
      prestige_pct: clamp(prestige),
      conformity_pct: clamp(conformity),
      content_pct: clamp(content),
    }),
    'The people learn so'
  )
  const busy = why(
    type === 'people' ? blocked : 'Only a people learns as a people',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={GraduationCap}
      tone='info'
      title='Set how they learn'
      note='Choose how strongly this people copies the renowned, the many and the gripping.'
      columns={3}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <GraduationCap />
          Teach them so
        </Button>
      }
    >
      <NumberField
        label='The renowned (%)'
        value={prestige}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setPrestige}
      />
      <NumberField
        label='The many (%)'
        value={conformity}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setConformity}
      />
      <NumberField
        label='The gripping (%)'
        value={content}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setContent}
      />
    </ForgeCard>
  )
}

function LessonCard({ row, blocked }: { row: Lesson; blocked: string | null }) {
  const action = useRemove(
    'learning_event:delete',
    { event_id: row.id },
    blocked
  )
  const bias = BIASES[row.bias]
  const axis = VALUE_ICONS[row.axis]
  return (
    <Held
      icon={bias.icon}
      tone={bias.tone}
      title={`${axis?.label ?? row.axis} moved by ${row.shift > 0 ? '+' : ''}${row.shift}`}
      caption={`Epoch ${row.epoch} · ${bias.label.toLowerCase()}`}
      removeLabel='Strike from the record'
      editTitle=''
      note=''
      fields={[]}
      locked={[]}
      blocked={action.busy}
      onEdit={null}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Copied from',
            <Ref key='model' node={row.model} empty='the many' />,
          ],
        ]}
      />
    </Held>
  )
}

function RoleCard({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: Role
  blocked: string | null
}) {
  const action = useRow(
    'role_norm:edit',
    'role_norm:delete',
    { holder_id: holderId, role: row.role },
    blocked
  )
  const [classes, setClasses] = useState<string[]>(row.classes)
  const classing = useCollectiveAction(
    'role_norm:edit',
    (_: void) => ({
      holder_id: holderId,
      role: row.role,
      values: { classes: classes as Role['classes'] },
      release: [],
    }),
    'The classes are set'
  )
  const unchanged =
    [...classes].sort().join() === [...row.classes].sort().join()
      ? 'Choose the classes first'
      : null
  const classBusy = why(action.busy ?? unchanged, classing.isPending)
  const role = ROLES[row.role]
  const rule = ELIGIBILITY[row.eligibility]
  const stance = ETHICS[row.stance]
  return (
    <Held
      icon={role.icon}
      tone={rule.tone}
      title={`${role.label}: ${rule.label.toLowerCase()}`}
      caption={`From age ${row.min_age} · since epoch ${row.since_epoch}`}
      removeLabel='Open it to all'
      editTitle='Set who may hold it'
      note='Only those the norm allows take up this career, stand in the succession, are levied or inherit; a frowned-on holder loses honour.'
      fields={[
        {
          key: 'eligibility',
          label: 'Who may',
          kind: 'pick',
          table: table(ELIGIBILITY),
        },
        { key: 'min_age', label: 'From age', kind: 'number', min: 0, max: 200 },
        {
          key: 'stance',
          label: 'Stance toward holders',
          kind: 'pick',
          table: table(ETHICS),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Chip icon={stance.icon}>{stance.label}</Chip>}
    >
      <Facts
        items={[
          [
            'Only for',
            row.classes.length > 0
              ? row.classes.map((item) => CLASS_SPEC[item].label).join(', ')
              : 'every class',
          ],
        ]}
      />
      <div className='flex min-w-0 flex-col gap-2'>
        <FieldTile group label='Open only to these classes'>
          <ToggleGroup
            type='multiple'
            variant='outline'
            size='sm'
            value={classes}
            onValueChange={setClasses}
            disabled={action.busy !== null}
            className='flex min-w-0 flex-wrap justify-start'
            aria-label='Classes the role is open to'
          >
            {Object.entries(CLASS_SPEC).map(([key, spec]) => (
              <ToggleGroupItem key={key} value={key} aria-label={spec.label}>
                <spec.icon />
                {spec.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </FieldTile>
        <Button
          act={classing}
          size='sm'
          variant='outline'
          disabled={classBusy !== null}
          disabledReason={classBusy ?? undefined}
          onClick={() => classing.mutate()}
        >
          <Users />
          {classes.length === 0 && row.classes.length > 0
            ? 'Open it to every class'
            : 'Set the classes'}
        </Button>
      </div>
    </Held>
  )
}

function RoleForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [role, setRole] = useState<keyof typeof ROLES>('office')
  const [eligibility, setEligibility] =
    useState<keyof typeof ELIGIBILITY>('any')
  const [age, setAge] = useState('16')
  const [only, setOnly] = useState(NO_CLASS)
  const setting = useCollectiveAction(
    'role_norm:set',
    (_: void) => ({
      holder_id: holderId,
      role,
      eligibility,
      min_age: clamp(age, 200),
      classes: only === NO_CLASS ? [] : [only as Role['classes'][number]],
    }),
    'The role is open so'
  )
  const busy = why(
    type === 'people' ? blocked : 'Only a people sets who may hold its roles',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Crown}
      tone='gold'
      title='Set who may hold a role'
      note='Open or close office, crafts, fighting, priesthood and inheritance by sex, age and class.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Crown />
          Decree it
        </Button>
      }
    >
      <MindPicker
        label='Role'
        value={role}
        table={table(ROLES)}
        blocked={busy}
        onPick={(value) => setRole(value as keyof typeof ROLES)}
      />
      <MindPicker
        label='Who may'
        value={eligibility}
        table={table(ELIGIBILITY)}
        blocked={busy}
        onPick={(value) => setEligibility(value as keyof typeof ELIGIBILITY)}
      />
      <NumberField
        label='From age'
        value={age}
        min={0}
        max={200}
        blocked={busy}
        onChange={setAge}
      />
      <MindPicker
        label='Only for'
        value={only}
        table={CLASS_PICK}
        blocked={busy}
        onPick={setOnly}
      />
    </ForgeCard>
  )
}

export function NormPanel({
  nodeId,
  type,
  data,
  blocked,
}: {
  nodeId: number
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  return (
    <div
      id='section-norms'
      data-surface='NormPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Customs, learning and roles</Label>
      <Listed
        title='Customs'
        items={data.norms}
        empty='No custom sets this apart; every behaviour is acceptable.'
        noun={['custom', 'customs']}
        itemKey={(row) => `${row.situation}-${row.behaviour}`}
      >
        {(row) => <CustomCard holderId={nodeId} row={row} blocked={blocked} />}
      </Listed>
      <CustomForge holderId={nodeId} type={type} blocked={blocked} />
      <Listed
        title='Changes of custom'
        items={data.norm_changes}
        empty='No custom has changed yet.'
        noun={['change', 'changes']}
        itemKey={(row) => row.id}
      >
        {(row) => <ChangeCard row={row} blocked={blocked} />}
      </Listed>
      {data.biases ? (
        <BiasCard holderId={nodeId} row={data.biases} blocked={blocked} />
      ) : (
        <BiasForge holderId={nodeId} type={type} blocked={blocked} />
      )}
      <Listed
        title='Lessons copied'
        items={data.lessons}
        empty='They have copied no one yet.'
        noun={['lesson', 'lessons']}
        itemKey={(row) => row.id}
      >
        {(row) => <LessonCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Roles'
        items={data.roles}
        empty='Every role is open to all here.'
        noun={['role', 'roles']}
        itemKey={(row) => row.role}
      >
        {(row) => <RoleCard holderId={nodeId} row={row} blocked={blocked} />}
      </Listed>
      <RoleForge holderId={nodeId} type={type} blocked={blocked} />
      <Muted variant='caption'>
        Customs and roles belong to peoples and cults; lessons belong to the
        mortals who copied them.
      </Muted>
    </div>
  )
}
