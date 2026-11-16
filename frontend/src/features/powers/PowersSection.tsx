import { useState } from 'react'
import {
  Activity,
  CirclePlus,
  Gift,
  Moon,
  ScrollText,
  Trash2,
  Undo2,
  Zap,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { FORMS, TECHNIQUES, table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import {
  useMadeAction,
  useProfileEdit,
  useRowDelete,
  useRowEdit,
} from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type PowersNodeView, type PowerView, useNodePowers } from './api'
import {
  ATTITUDES,
  BLOODLINES,
  ORIGINS,
  POWERS_ICON,
  RESTRICTIONS,
  STATES,
  TRIGGERS,
  VISIBILITIES,
} from './labels'

const SHOWN = 5
const NONE = 'none'
const YES_NO = { true: 'Yes', false: 'No' }
const GODS = ['son', 'foreign_god', 'creator']
const QUIET = new Set(['latent', 'burned_out', 'suppressed', 'lost'])

type Choice = PowersNodeView['sources'][number]

function picks(rows: readonly Choice[]): Record<string, string> {
  return Object.fromEntries(rows.map((row) => [String(row.id), row.name]))
}

function powerFields(view: PowersNodeView): readonly Field[] {
  return [
    {
      key: 'technique',
      label: 'What it does',
      kind: 'pick',
      table: table(TECHNIQUES),
    },
    {
      key: 'form',
      label: 'What it works on',
      kind: 'pick',
      table: table(FORMS),
    },
    { key: 'strength', label: 'Strength', kind: 'number', min: 1, max: 10 },
    { key: 'control', label: 'Control', kind: 'number', min: 0, max: 100 },
    { key: 'range_km', label: 'Reach in kilometres', kind: 'number', min: 0 },
    {
      key: 'duration_days',
      label: 'How long it lasts, in days',
      kind: 'number',
      min: 0,
    },
    { key: 'on_others', label: 'Works on others', kind: 'pick', table: YES_NO },
    {
      key: 'origin',
      label: 'Where it came from',
      kind: 'pick',
      table: table(ORIGINS),
    },
    { key: 'state', label: 'Its state', kind: 'pick', table: table(STATES) },
    {
      key: 'visibility',
      label: 'How plainly it shows',
      kind: 'pick',
      table: table(VISIBILITIES),
    },
    { key: 'strain', label: 'Strain now', kind: 'number', min: 0 },
    { key: 'strain_cap', label: 'Strain it bears', kind: 'number', min: 1 },
    {
      key: 'source_id',
      label: 'Source it draws on',
      kind: 'pick',
      table: picks(view.sources),
    },
    {
      key: 'system_id',
      label: 'System it belongs to',
      kind: 'pick',
      table: picks(view.systems),
    },
    {
      key: 'item_node_id',
      label: 'Thing it is held in',
      kind: 'node',
      types: ['item'],
    },
  ]
}

const RESTRICTION_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'What it asks',
    kind: 'pick',
    table: table(RESTRICTIONS),
  },
  {
    key: 'ref_node_id',
    label: 'Place, time or foe it names',
    kind: 'node',
    types: [],
  },
  { key: 'detail', label: 'In words', kind: 'text' },
  {
    key: 'strength_gain_pct',
    label: 'Strength it adds (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'broken', label: 'Broken', kind: 'pick', table: YES_NO },
]

const REGISTRY_FIELDS: readonly Field[] = [
  { key: 'licensed', label: 'Licensed', kind: 'pick', table: YES_NO },
  {
    key: 'conscripted',
    label: 'Called to serve in war',
    kind: 'pick',
    table: YES_NO,
  },
  {
    key: 'registered_epoch',
    label: 'Registered in epoch',
    kind: 'number',
    min: 0,
  },
]

const ATTITUDE_FIELDS: readonly Field[] = [
  {
    key: 'attitude',
    label: 'How they hold the gifted',
    kind: 'pick',
    table: table(ATTITUDES),
  },
  {
    key: 'gifted_share',
    label: 'Share who hold a power (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'registered_share',
    label: 'Share on a registry (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]

const BLOODLINE_FIELDS: readonly Field[] = [
  {
    key: 'bloodline_rule',
    label: 'How the line passes its powers',
    kind: 'pick',
    table: table(BLOODLINES),
  },
]

const SPAN_FIELDS: readonly Field[] = [
  { key: 'amount', label: 'Strength of the effect', kind: 'number', min: 0 },
  { key: 'until_epoch', label: 'Lasts until epoch', kind: 'number', min: 0 },
]

function Restriction({
  row,
  blocked,
}: {
  row: PowerView['restrictions'][number]
  blocked: string | null
}) {
  const named = RESTRICTIONS[row.kind]
  const editing = useMadeAction(
    'power_part:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      part: 'restriction',
      part_id: row.id,
      values: vars.values,
      hold: true,
    }),
    'The restriction is set so'
  )
  const dropping = useMadeAction(
    'power_part:delete',
    (_: void) => ({ part: 'restriction', part_id: row.id }),
    'The restriction is lifted'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={row.broken ? 'danger' : (named.tone ?? 'info')}
      title={named.label}
      caption={`${row.detail ?? 'no words given'}; adds ${row.strength_gain_pct}% to its strength${row.broken ? '; broken' : ''}`}
    >
      <Ref node={row.ref} empty='names no place, time or foe' />
      <RecordEditor
        title='Set this restriction'
        note='Values you set are held against the engine.'
        fields={RESTRICTION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={() => editing.mutate({ values: {}, release: [] })}
      />
      <StepButton
        icon={Trash2}
        label='Lift this restriction'
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function Trigger({
  row,
  blocked,
}: {
  row: PowerView['triggers'][number]
  blocked: string | null
}) {
  const named = TRIGGERS[row.trigger]
  const dropping = useMadeAction(
    'power_part:delete',
    (_: void) => ({ part: 'trigger', part_id: row.id }),
    'The trigger is gone'
  )
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2'>
      <Chip icon={named.icon}>{named.label}</Chip>
      <StepButton
        icon={Trash2}
        label={`Remove the trigger ${named.label.toLowerCase()}`}
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </li>
  )
}

function Span({
  row,
  blocked,
}: {
  row: PowerView['spans'][number]
  blocked: string | null
}) {
  const editing = useRowEdit('power_spans', { id: row.id })
  const struck = useRowDelete('power_spans', { id: row.id })
  return (
    <RecordRow
      icon={Activity}
      tone='info'
      title={`An effect lasting until epoch ${row.until_epoch}`}
      caption={`strength ${row.amount}`}
    >
      <Ref node={row.target} empty='on its user' />
      <RecordEditor
        title='Set this lasting effect'
        note='Values you set are held against the engine.'
        fields={SPAN_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='End it now'
        busy={why(blocked, struck.isPending)}
        onClick={() => struck.mutate()}
      />
    </RecordRow>
  )
}

function Power({
  power,
  view,
  blocked,
}: {
  power: PowerView
  view: PowersNodeView
  blocked: string | null
}) {
  const state = STATES[power.state]
  const triggers = useShowMore(power.triggers, 4, 8)
  const [restriction, setRestriction] = useState<string>('spoken_vow')
  const [gain, setGain] = useState('20')
  const [trigger, setTrigger] = useState<string>('stress')
  const editing = useMadeAction(
    'power:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      power_id: power.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The power is set so'
  )
  const waking = useMadeAction(
    'power:awaken',
    (_: void) => ({ power_id: power.id }),
    'The power wakes'
  )
  const stilling = useMadeAction(
    'power:suppress',
    (_: void) => ({ power_id: power.id }),
    'The power is stilled'
  )
  const deleting = useMadeAction(
    'power:delete',
    (_: void) => ({ power_id: power.id }),
    'The power is unmade'
  )
  const revoking = useMadeAction(
    'power:revoke',
    (_: void) => ({ power_id: power.id, god_id: power.granted_by?.id ?? 0 }),
    'The god takes the power back'
  )
  const restricting = useMadeAction(
    'power_part:create',
    (_: void) => ({
      owner_id: power.id,
      part: 'restriction',
      values: { kind: restriction, strength_gain_pct: Number(gain) || 0 },
    }),
    'The power takes a restriction'
  )
  const triggering = useMadeAction(
    'power_part:create',
    (_: void) => ({ owner_id: power.id, part: 'trigger', values: { trigger } }),
    'The power gains a trigger'
  )
  const ungiven = power.granted_by
    ? null
    : 'Only a power a god granted can be taken back'
  return (
    <RecordRow
      icon={TECHNIQUES[power.technique].icon}
      tone={state.tone ?? 'info'}
      title={`${TECHNIQUES[power.technique].label} ${FORMS[power.form].label.toLowerCase()}`}
      caption={`${state.label}, strength ${power.strength}, control ${power.control}, strain ${power.strain} of ${power.strain_cap}, used ${power.uses} times since epoch ${power.gained_epoch}${power.last_used_epoch !== null ? `, last in epoch ${power.last_used_epoch}` : ''}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip icon={ORIGINS[power.origin].icon}>
            {ORIGINS[power.origin].label}
          </Chip>
          <Chip icon={VISIBILITIES[power.visibility].icon}>
            {VISIBILITIES[power.visibility].label}
          </Chip>
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={ScrollText}>
          Source: {power.source_name ?? 'none named'}
        </Chip>
        <Chip icon={ScrollText}>
          System: {power.system_name ?? 'none named'}
        </Chip>
        <Chip icon={Activity}>
          Reach {power.range_km} km, lasts {power.duration_days} days,{' '}
          {power.on_others ? 'works on others' : 'works on itself'}
        </Chip>
      </div>
      <Ref node={power.granted_by} empty='granted by no god' />
      <Ref node={power.item} empty='held in no thing' />
      <ul className='flex min-w-0 flex-col gap-2'>
        {power.restrictions.map((row) => (
          <Restriction key={row.id} row={row} blocked={blocked} />
        ))}
      </ul>
      <ul className='flex min-w-0 flex-wrap gap-2'>
        {triggers.visible.map((row) => (
          <Trigger key={row.id} row={row} blocked={blocked} />
        ))}
      </ul>
      <ShowMore state={triggers} />
      <ul className='flex min-w-0 flex-col gap-2'>
        {power.spans.map((row) => (
          <Span key={row.id} row={row} blocked={blocked} />
        ))}
      </ul>
      <ForgeCard
        icon={CirclePlus}
        tone='warning'
        title='Bind it with a restriction'
        note='A restriction makes the power stronger; a broken vow or forbidden act ends it.'
        columns={2}
        action={
          <StepButton
            icon={CirclePlus}
            label='Add the restriction'
            busy={why(blocked, restricting.isPending)}
            onClick={() => restricting.mutate()}
          />
        }
      >
        <ChoiceField
          label='What it asks'
          value={restriction}
          table={RESTRICTIONS}
          blocked={blocked}
          onPick={setRestriction}
        />
        <NumberField
          label='Strength it adds (%)'
          value={gain}
          min={0}
          max={100}
          onChange={setGain}
        />
      </ForgeCard>
      <ForgeCard
        icon={Zap}
        tone='info'
        title='Give it a trigger'
        note='What wakes a latent power or sets loose an emerging one.'
        columns={2}
        action={
          <StepButton
            icon={CirclePlus}
            label='Add the trigger'
            busy={why(blocked, triggering.isPending)}
            onClick={() => triggering.mutate()}
          />
        }
      >
        <ChoiceField
          label='What sets it off'
          value={trigger}
          table={TRIGGERS}
          blocked={blocked}
          onPick={setTrigger}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this power'
        note='Values you set are held against the engine until you release them.'
        fields={powerFields(view)}
        locked={power.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Zap}
          label='Wake it'
          busy={why(
            blocked ??
              (power.state === 'active' ? 'It is already awake' : null),
            waking.isPending
          )}
          onClick={() => waking.mutate()}
        />
        <StepButton
          icon={Moon}
          label='Still it'
          busy={why(
            blocked ?? (QUIET.has(power.state) ? 'It is not awake' : null),
            stilling.isPending
          )}
          onClick={() => stilling.mutate()}
        />
        <StepButton
          icon={Undo2}
          label='Take it back for its god'
          busy={why(blocked ?? ungiven, revoking.isPending)}
          onClick={() => revoking.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Unmake it'
          busy={why(blocked, deleting.isPending)}
          onClick={() => deleting.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Registry({
  row,
  blocked,
}: {
  row: PowersNodeView['registry'][number]
  blocked: string | null
}) {
  const editing = useRowEdit('power_registry', { id: row.id })
  const struck = useRowDelete('power_registry', { id: row.id })
  return (
    <RecordRow
      icon={ScrollText}
      tone={row.conscripted ? 'warning' : 'info'}
      title={`${row.holder.name} on the registry of ${row.polity.name}`}
      caption={`since epoch ${row.registered_epoch}${row.licensed ? ', licensed' : ''}${row.conscripted ? ', called to serve in war' : ''}`}
    >
      <RecordEditor
        title='Set this entry'
        note='Values you set are held against the engine.'
        fields={REGISTRY_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike it from the registry'
        busy={why(blocked, struck.isPending)}
        onClick={() => struck.mutate()}
      />
    </RecordRow>
  )
}

export function PowersSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodePowers(nodeId)
  const page = useShowMore(query.data?.powers ?? [], SHOWN, SHOWN * 2)
  const [technique, setTechnique] = useState<string>('perceive')
  const [form, setForm] = useState<string>('mind')
  const [strength, setStrength] = useState('3')
  const [control, setControl] = useState('40')
  const [origin, setOrigin] = useState<string>('born')
  const [state, setState] = useState<string>('active')
  const [visibility, setVisibility] = useState<string>('subtle')
  const [source, setSource] = useState<string>(NONE)
  const [god, setGod] = useState<number | null>(null)
  const attitude = useProfileEdit(nodeId, 'gifted_attitudes')
  const bloodline = useProfileEdit(nodeId, 'house_profiles')
  const body = () => ({
    holder_id: nodeId,
    technique: technique as PowerView['technique'],
    form: form as PowerView['form'],
    strength: Math.min(10, Math.max(1, Number(strength) || 1)),
    control: Math.min(100, Math.max(0, Number(control) || 0)),
    origin: origin as PowerView['origin'],
    state: state as PowerView['state'],
    visibility: visibility as PowerView['visibility'],
    source_id: source === NONE ? null : Number(source),
  })
  const creating = useMadeAction(
    'power:create',
    (_: void) => body(),
    'The power is given'
  )
  const granting = useMadeAction(
    'power:grant',
    (_: void) => ({ ...body(), god_id: god ?? 0 }),
    'The god grants the power'
  )
  const view = query.data
  const blocked = readOnlyReason
  const noGod = god === null ? 'Choose the god who grants it' : null
  const sources = {
    [NONE]: {
      label: 'No source named',
      icon: POWERS_ICON,
      tone: 'muted' as const,
    },
    ...Object.fromEntries(
      (view?.sources ?? []).map((row) => [
        String(row.id),
        { label: row.name, icon: POWERS_ICON, tone: 'info' as const },
      ])
    ),
  }
  const awake =
    view?.powers.filter((power) => power.state === 'active').length ?? 0
  const strain =
    view?.powers.reduce((total, power) => total + power.strain, 0) ?? 0
  return (
    <Section
      id='section-powers'
      title='Powers: what it can do by its own being or a gift'
      description='Powers wake, are used, strain their holders, give out, grow and pass by line, gift or exposure; peoples judge the gifted and realms register or hunt them.'
      icon={POWERS_ICON}
      tone='gold'
    >
      <div data-surface='PowersSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading its powers' />
        ) : query.isError ? (
          <EmptyState
            icon={POWERS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Powers held'
                value={String(query.data.powers.length)}
                icon={POWERS_ICON}
                tone='gold'
              />
              <KpiTile
                label='Awake'
                value={String(awake)}
                icon={Zap}
                tone={awake ? 'success' : 'muted'}
              />
              <KpiTile
                label='Strain carried'
                value={String(strain)}
                icon={Activity}
                tone={strain ? 'warning' : 'muted'}
              />
              <KpiTile
                label='Powers it granted'
                value={String(query.data.granted.length)}
                icon={Gift}
                tone='info'
              />
            </div>
            {query.data.powers.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((power) => (
                    <Power
                      key={power.id}
                      power={power}
                      view={query.data}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={POWERS_ICON}
                size='inline'
                title='No powers'
                description={`${query.data.node.name} holds none yet; give one below.`}
              />
            )}
            {query.data.granted.length ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                {query.data.granted.map((power) => (
                  <Power
                    key={`granted-${power.id}`}
                    power={power}
                    view={query.data}
                    blocked={blocked}
                  />
                ))}
              </ul>
            ) : null}
            {query.data.registry.length ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                {query.data.registry.map((row) => (
                  <Registry key={row.id} row={row} blocked={blocked} />
                ))}
              </ul>
            ) : null}
            {query.data.attitude ? (
              <RecordRow
                icon={ATTITUDES[query.data.attitude.attitude].icon}
                tone={ATTITUDES[query.data.attitude.attitude].tone ?? 'info'}
                title={`They hold the gifted ${ATTITUDES[query.data.attitude.attitude].label.toLowerCase()}`}
                caption={`${query.data.attitude.gifted_share}% hold a power, ${query.data.attitude.registered_share}% of them on a registry, weighed in epoch ${query.data.attitude.updated_epoch}`}
              >
                <RecordEditor
                  title='Set how they hold the gifted'
                  note='Values you set are held against the engine.'
                  fields={ATTITUDE_FIELDS}
                  locked={query.data.attitude.locked}
                  busy={why(blocked, attitude.isPending)}
                  onSave={(values) => attitude.mutate({ values, release: [] })}
                  onRelease={(keys) =>
                    attitude.mutate({ values: {}, release: keys })
                  }
                />
              </RecordRow>
            ) : null}
            {query.data.bloodline_rule ? (
              <RecordRow
                icon={BLOODLINES[query.data.bloodline_rule].icon}
                tone={BLOODLINES[query.data.bloodline_rule].tone ?? 'info'}
                title={`Powers of the line: ${BLOODLINES[query.data.bloodline_rule].label.toLowerCase()}`}
                caption='How a power of this house passes to its children'
              >
                <RecordEditor
                  title='Set how the line passes its powers'
                  note='Values you set are held against the engine.'
                  fields={BLOODLINE_FIELDS}
                  locked={[]}
                  busy={why(blocked, bloodline.isPending)}
                  onSave={(values) => bloodline.mutate({ values, release: [] })}
                  onRelease={(keys) =>
                    bloodline.mutate({ values: {}, release: keys })
                  }
                />
              </RecordRow>
            ) : null}
            <ForgeCard
              icon={CirclePlus}
              tone='gold'
              title='Give it a power'
              note={`A god may grant it instead, at ${query.data.grant_cost} essence.`}
              columns={3}
              action={
                <div className='flex min-w-0 flex-wrap gap-2'>
                  <StepButton
                    icon={CirclePlus}
                    label='Give the power'
                    variant='default'
                    busy={why(blocked, creating.isPending)}
                    onClick={() => creating.mutate()}
                  />
                  <StepButton
                    icon={Gift}
                    label='Have the god grant it'
                    busy={why(blocked ?? noGod, granting.isPending)}
                    onClick={() => granting.mutate()}
                  />
                </div>
              }
            >
              <ChoiceField
                label='What it does'
                value={technique}
                table={TECHNIQUES}
                blocked={blocked}
                onPick={setTechnique}
              />
              <ChoiceField
                label='What it works on'
                value={form}
                table={FORMS}
                blocked={blocked}
                onPick={setForm}
              />
              <NumberField
                label='Strength'
                value={strength}
                min={1}
                max={10}
                onChange={setStrength}
              />
              <NumberField
                label='Control'
                value={control}
                min={0}
                max={100}
                onChange={setControl}
              />
              <ChoiceField
                label='Where it came from'
                value={origin}
                table={ORIGINS}
                blocked={blocked}
                onPick={setOrigin}
              />
              <ChoiceField
                label='Its state'
                value={state}
                table={STATES}
                blocked={blocked}
                onPick={setState}
              />
              <ChoiceField
                label='How plainly it shows'
                value={visibility}
                table={VISIBILITIES}
                blocked={blocked}
                onPick={setVisibility}
              />
              <ChoiceField
                label='Source it draws on'
                value={source}
                table={sources}
                blocked={blocked}
                onPick={setSource}
              />
              <ThingPicker
                label='God who grants it'
                value={god}
                onChange={setGod}
                blocked={blocked}
                types={GODS}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
