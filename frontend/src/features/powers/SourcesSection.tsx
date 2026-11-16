import { useState } from 'react'
import { CirclePlus, Gauge, Landmark, Trash2, TrendingDown } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import {
  useMadeAction,
  useProfileEdit,
  useRowDelete,
  useRowEdit,
} from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type SourcesNodeView,
  type PowerSourceView,
  useNodeSources,
} from './api'
import {
  ACCESS,
  COSTS,
  CYCLES,
  HAZARDS,
  LOCI,
  RELATIONS,
  RENEWALS,
  RESISTANCES,
  SOURCE_LAWS,
  SOURCES_ICON,
  STANCES,
  VISIBILITIES,
} from './labels'

const SHOWN = 5

const SOURCE_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name of the source', kind: 'text' },
  { key: 'description', label: 'What it is', kind: 'text', long: true },
  {
    key: 'scope_node_id',
    label: 'Where it can be drawn on',
    kind: 'node',
    types: [],
  },
  {
    key: 'drawn_from',
    label: 'What it is drawn from',
    kind: 'pick',
    table: table(LOCI),
  },
  {
    key: 'renewal',
    label: 'How it renews',
    kind: 'pick',
    table: table(RENEWALS),
  },
  {
    key: 'access',
    label: 'Who may draw on it',
    kind: 'pick',
    table: table(ACCESS),
  },
  {
    key: 'visibility',
    label: 'How plainly its use shows',
    kind: 'pick',
    table: table(VISIBILITIES),
  },
  {
    key: 'stability',
    label: 'How predictable its draws are',
    kind: 'number',
    min: 0,
    max: 100,
  },
]

const PARTS: Record<string, { label: string; fields: readonly Field[] }> = {
  cost: {
    label: 'cost',
    fields: [
      {
        key: 'cost',
        label: 'What it costs',
        kind: 'pick',
        table: table(COSTS),
      },
      { key: 'weight', label: 'How much', kind: 'number', min: 0, max: 100 },
    ],
  },
  resistance: {
    label: 'resistance',
    fields: [
      {
        key: 'resistance',
        label: 'What resists it',
        kind: 'pick',
        table: table(RESISTANCES),
      },
    ],
  },
  hazard: {
    label: 'hazard',
    fields: [
      {
        key: 'hazard',
        label: 'What can go wrong',
        kind: 'pick',
        table: table(HAZARDS),
      },
      { key: 'weight', label: 'How often', kind: 'number', min: 0, max: 100 },
    ],
  },
  tide: {
    label: 'tide',
    fields: [
      {
        key: 'cycle',
        label: 'What it follows',
        kind: 'pick',
        table: table(CYCLES),
      },
      { key: 'period', label: 'Period in epochs', kind: 'number', min: 1 },
      {
        key: 'amplitude',
        label: 'How far it swings',
        kind: 'number',
        min: 0,
        max: 100,
      },
      {
        key: 'phase',
        label: 'Where in its cycle it starts',
        kind: 'number',
        min: 0,
      },
    ],
  },
  interaction: {
    label: 'meeting with another source',
    fields: [
      {
        key: 'relation',
        label: 'How they meet',
        kind: 'pick',
        table: table(RELATIONS),
      },
      {
        key: 'strength',
        label: 'How strongly',
        kind: 'number',
        min: 0,
        max: 100,
      },
    ],
  },
}

const DENSITY_FIELDS: readonly Field[] = [
  { key: 'density', label: 'Density now', kind: 'number', min: 0, max: 100 },
  {
    key: 'base_density',
    label: 'Density at rest',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'renewal_pct',
    label: 'Renewal each epoch (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]

const KNOWLEDGE_FIELDS: readonly Field[] = [
  {
    key: 'level',
    label: 'How well it is known',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'learned_epoch', label: 'Learned in epoch', kind: 'number', min: 0 },
]
const LAW_FIELDS: readonly Field[] = [
  {
    key: 'level',
    label: 'Drawing on it is',
    kind: 'pick',
    table: table(SOURCE_LAWS),
  },
]
const STANCE_FIELDS: readonly Field[] = [
  {
    key: 'stance',
    label: 'The faith holds it',
    kind: 'pick',
    table: table(STANCES),
  },
]
const DOCTRINE_FIELDS: readonly Field[] = [
  {
    key: 'power_stance',
    label: 'The faith holds powers',
    kind: 'pick',
    table: table(STANCES),
  },
]

function Part({
  kind,
  id,
  title,
  caption,
  locked,
  blocked,
}: {
  kind: string
  id: number
  title: string
  caption: string
  locked: string[]
  blocked: string | null
}) {
  const editing = useMadeAction(
    'source_part:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      part: kind,
      part_id: id,
      values: vars.values,
      hold: true,
    }),
    `The ${PARTS[kind].label} is set so`
  )
  const dropping = useMadeAction(
    'source_part:delete',
    (_: void) => ({ part: kind, part_id: id }),
    `The ${PARTS[kind].label} is taken away`
  )
  return (
    <RecordRow icon={SOURCES_ICON} tone='info' title={title} caption={caption}>
      <RecordEditor
        title={`Set this ${PARTS[kind].label}`}
        note='Values you set are held against the engine.'
        fields={PARTS[kind].fields}
        locked={locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={() => editing.mutate({ values: {}, release: [] })}
      />
      <StepButton
        icon={Trash2}
        label={`Take the ${PARTS[kind].label} away`}
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function Source({
  source,
  view,
  blocked,
}: {
  source: PowerSourceView
  view: SourcesNodeView
  blocked: string | null
}) {
  const locus = LOCI[source.drawn_from]
  const [part, setPart] = useState<string>('cost')
  const [cost, setCost] = useState<string>('fatigue')
  const [weight, setWeight] = useState('50')
  const [other, setOther] = useState<string>(
    String(view.every_source.find((row) => row.id !== source.id)?.id ?? '')
  )
  const editing = useMadeAction(
    'source:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      source_id: source.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The source is set so'
  )
  const deleting = useMadeAction(
    'source:delete',
    (_: void) => ({ source_id: source.id }),
    'The source is unmade'
  )
  const partValues = (): Record<string, string | number | null> => {
    const amount = Number(weight) || 0
    if (part === 'cost') return { cost, weight: amount }
    if (part === 'resistance') return { resistance: 'will' }
    if (part === 'hazard') return { hazard: 'injury', weight: amount }
    if (part === 'tide')
      return { cycle: 'season', period: 4, amplitude: amount, phase: 0 }
    return {
      second_source_id: Number(other),
      relation: 'amplifies',
      strength: amount,
    }
  }
  const adding = useMadeAction(
    'source_part:create',
    (_: void) => ({
      owner_id: source.id,
      part,
      values: partValues(),
    }),
    'The source gains its part'
  )
  const others = Object.fromEntries(
    view.every_source
      .filter((row) => row.id !== source.id)
      .map((row) => [
        String(row.id),
        { label: row.name, icon: SOURCES_ICON, tone: 'info' as const },
      ])
  )
  const builtIn = source.built_in
    ? 'The sources the world was made with can be edited and held but not unmade'
    : null
  const lonely =
    part === 'interaction' && !other ? 'There is no other source to meet' : null
  return (
    <RecordRow
      icon={locus.icon}
      tone={locus.tone ?? 'info'}
      title={source.name}
      caption={`Drawn from ${locus.label.toLowerCase()}, renewed by ${RENEWALS[source.renewal].label.toLowerCase()}, open to ${ACCESS[source.access].label.toLowerCase()}, steadiness ${source.stability}, since epoch ${source.founded_epoch}`}
      aside={
        <Chip icon={VISIBILITIES[source.visibility].icon}>
          {VISIBILITIES[source.visibility].label}
        </Chip>
      }
    >
      <Ref node={source.scope} empty='drawn on everywhere' />
      {source.description ? (
        <Muted variant='caption'>{source.description}</Muted>
      ) : null}
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={source.costs} as='li'>
          {(row) => (
            <Part
              key={`c${row.id}`}
              kind='cost'
              id={row.id}
              title={`Costs ${COSTS[row.cost].label.toLowerCase()}`}
              caption={`weight ${row.weight}`}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={source.resistances} as='li'>
          {(row) => (
            <Part
              key={`r${row.id}`}
              kind='resistance'
              id={row.id}
              title={`Resisted by ${RESISTANCES[row.resistance].label.toLowerCase()}`}
              caption={
                row.material
                  ? `the material ${row.material.replaceAll('_', ' ')}`
                  : 'no material named'
              }
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={source.hazards} as='li'>
          {(row) => (
            <Part
              key={`h${row.id}`}
              kind='hazard'
              id={row.id}
              title={`Risks ${HAZARDS[row.hazard].label.toLowerCase()}`}
              caption={`weight ${row.weight}`}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={source.tides} as='li'>
          {(row) => (
            <Part
              key={`t${row.id}`}
              kind='tide'
              id={row.id}
              title={`Waxes and wanes with ${CYCLES[row.cycle].label.toLowerCase()}`}
              caption={`every ${row.period} epochs, swinging ${row.amplitude}, from step ${row.phase}`}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={source.interactions} as='li'>
          {(row) => (
            <Part
              key={`i${row.id}`}
              kind='interaction'
              id={row.id}
              title={`${RELATIONS[row.relation].label} ${row.other_name}`}
              caption={`strength ${row.strength}`}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
      </ul>
      <ForgeCard
        icon={CirclePlus}
        tone='info'
        title='Give it a part'
        note='A cost, a resistance, a hazard, a tide or how it meets another source.'
        columns={3}
        action={
          <StepButton
            icon={CirclePlus}
            label='Add the part'
            busy={why(blocked ?? lonely, adding.isPending)}
            onClick={() => adding.mutate()}
          />
        }
      >
        <ChoiceField
          label='Which part'
          value={part}
          table={Object.fromEntries(
            Object.entries(PARTS).map(([key, value]) => [
              key,
              { label: value.label, icon: SOURCES_ICON, tone: 'info' as const },
            ])
          )}
          blocked={blocked}
          onPick={setPart}
        />
        <ChoiceField
          label='What it costs'
          value={cost}
          table={COSTS}
          blocked={
            blocked ??
            (part === 'cost' ? null : 'Only a cost names what it costs')
          }
          onPick={setCost}
        />
        <NumberField
          label='Weight, swing or strength'
          value={weight}
          min={0}
          max={100}
          onChange={setWeight}
        />
        <ChoiceField
          label='The other source'
          value={other}
          table={others}
          blocked={
            blocked ??
            (part === 'interaction'
              ? null
              : 'Only a meeting names another source')
          }
          onPick={setOther}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this source'
        note='Values you set are held against the engine until you release them.'
        fields={SOURCE_FIELDS}
        locked={source.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Unmake the source'
        busy={why(blocked ?? builtIn, deleting.isPending)}
        onClick={() => deleting.mutate()}
      />
    </RecordRow>
  )
}

function Density({
  row,
  blocked,
}: {
  row: SourcesNodeView['densities'][number]
  blocked: string | null
}) {
  const editing = useRowEdit('source_density', { id: row.id })
  const struck = useRowDelete('source_density', { id: row.id })
  return (
    <RecordRow
      icon={row.depleted ? TrendingDown : Gauge}
      tone={row.depleted ? 'danger' : 'success'}
      title={`${row.source_name} here: density ${row.density} of ${row.base_density}`}
      caption={`renews ${row.renewal_pct}% each epoch${row.last_drawn_epoch !== null ? `, last drawn on in epoch ${row.last_drawn_epoch}` : ''}${row.depleted ? ', run thin' : ''}`}
    >
      <RecordEditor
        title='Set the density here'
        note='Values you set are held against the engine.'
        fields={DENSITY_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike this density'
        busy={why(blocked, struck.isPending)}
        onClick={() => struck.mutate()}
      />
    </RecordRow>
  )
}

function Held({
  table: name,
  row,
  title,
  caption,
  fields,
  blocked,
}: {
  table: string
  row: { id: number; locked: string[] }
  title: string
  caption: string
  fields: readonly Field[]
  blocked: string | null
}) {
  const editing = useRowEdit(name, { id: row.id })
  const struck = useRowDelete(name, { id: row.id })
  return (
    <RecordRow icon={SOURCES_ICON} tone='info' title={title} caption={caption}>
      <RecordEditor
        title='Set it'
        note='Values you set are held against the engine.'
        fields={fields}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike it'
        busy={why(blocked, struck.isPending)}
        onClick={() => struck.mutate()}
      />
    </RecordRow>
  )
}

export function SourcesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeSources(nodeId)
  const page = useShowMore(query.data?.sources ?? [], SHOWN, SHOWN * 2)
  const [name, setName] = useState('')
  const [locus, setLocus] = useState<string>('place')
  const [renewal, setRenewal] = useState<string>('time')
  const [access, setAccess] = useState<string>('anyone')
  const [visibility, setVisibility] = useState<string>('subtle')
  const [stability, setStability] = useState('60')
  const [known, setKnown] = useState<string>('')
  const doctrine = useProfileEdit(nodeId, 'cult_doctrines')
  const creating = useMadeAction(
    'source:create',
    (_: void) => ({
      name: name.trim(),
      scope_id: nodeId,
      locus: locus as PowerSourceView['drawn_from'],
      renewal: renewal as PowerSourceView['renewal'],
      access: access as PowerSourceView['access'],
      visibility: visibility as PowerSourceView['visibility'],
      stability: Math.min(100, Math.max(0, Number(stability) || 0)),
    }),
    'A source of power comes to be'
  )
  const knowing = useMadeAction(
    'record_row:create',
    (_: void) => ({
      table: 'power_source_knowledge',
      values: {
        source_id: Number(known),
        holder_node_id: nodeId,
        level: 50,
        learned_epoch: 0,
      },
    }),
    'The source is known here now'
  )
  const view = query.data
  const blocked = readOnlyReason
  const unnamed = name.trim() ? null : 'Name the source'
  const every = Object.fromEntries(
    (view?.every_source ?? []).map((row) => [
      String(row.id),
      { label: row.name, icon: SOURCES_ICON, tone: 'info' as const },
    ])
  )
  const thin = view?.densities.filter((row) => row.depleted).length ?? 0
  return (
    <Section
      id='section-sources'
      title='Sources of power: what power is drawn from here'
      description='Each source is drawn on, paid for, renews by its kind, runs thin where overdrawn, waxes and wanes, and is known, named in law and judged by faith.'
      icon={SOURCES_ICON}
      tone='verdigris'
    >
      <div
        data-surface='SourcesSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its sources' />
        ) : query.isError ? (
          <EmptyState
            icon={SOURCES_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Sources here'
                value={String(query.data.sources.length)}
                icon={SOURCES_ICON}
                tone='verdigris'
              />
              <KpiTile
                label='Densities kept'
                value={String(query.data.densities.length)}
                icon={Gauge}
                tone='info'
              />
              <KpiTile
                label='Run thin'
                value={String(thin)}
                icon={TrendingDown}
                tone={thin ? 'danger' : 'muted'}
              />
              <KpiTile
                label='Sources known'
                value={String(query.data.knowledge.length)}
                icon={Landmark}
                tone='gold'
              />
            </div>
            {query.data.sources.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((source) => (
                    <Source
                      key={source.id}
                      source={source}
                      view={query.data}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={SOURCES_ICON}
                size='inline'
                title='No source rises here'
                description='Bring one forth below, or look at the world or a land where sources are drawn.'
              />
            )}
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={query.data.densities} as='li'>
                {(row) => <Density key={row.id} row={row} blocked={blocked} />}
              </Paged>
              <Paged items={query.data.knowledge} as='li'>
                {(row) => (
                  <Held
                    key={`k${row.id}`}
                    table='power_source_knowledge'
                    row={row}
                    title={`Knows ${row.source_name}`}
                    caption={`${row.level} of 100, since epoch ${row.learned_epoch}`}
                    fields={KNOWLEDGE_FIELDS}
                    blocked={blocked}
                  />
                )}
              </Paged>
              <Paged items={query.data.laws} as='li'>
                {(row) => (
                  <Held
                    key={`l${row.id}`}
                    table='source_laws'
                    row={row}
                    title={`Law: drawing on ${row.source_name} is ${SOURCE_LAWS[row.level].label.toLowerCase()}`}
                    caption='Named in the law of this realm'
                    fields={LAW_FIELDS}
                    blocked={blocked}
                  />
                )}
              </Paged>
              <Paged items={query.data.stances} as='li'>
                {(row) => (
                  <Held
                    key={`s${row.id}`}
                    table='source_stances'
                    row={row}
                    title={`The faith holds ${row.source_name} ${STANCES[row.stance].label.toLowerCase()}`}
                    caption='A stance of this faith'
                    fields={STANCE_FIELDS}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
            {query.data.power_stance ? (
              <RecordRow
                icon={STANCES[query.data.power_stance].icon}
                tone={STANCES[query.data.power_stance].tone ?? 'info'}
                title={`This faith holds powers ${STANCES[query.data.power_stance].label.toLowerCase()}`}
                caption='Its stance moves how its people hold the gifted'
              >
                <RecordEditor
                  title='Set the faith’s stance on powers'
                  note='Values you set are held against the engine.'
                  fields={DOCTRINE_FIELDS}
                  locked={[]}
                  busy={why(blocked, doctrine.isPending)}
                  onSave={(values) => doctrine.mutate({ values, release: [] })}
                  onRelease={(keys) =>
                    doctrine.mutate({ values: {}, release: keys })
                  }
                />
              </RecordRow>
            ) : null}
            <ForgeCard
              icon={CirclePlus}
              tone='verdigris'
              title='Bring forth a source here'
              note='Every source is drawn from something, renews in its way and is open to some.'
              columns={3}
              action={
                <StepButton
                  icon={CirclePlus}
                  label='Bring it forth'
                  variant='default'
                  busy={why(blocked ?? unnamed, creating.isPending)}
                  onClick={() => creating.mutate()}
                />
              }
            >
              <TextField
                label='Name of the source'
                value={name}
                blocked={blocked}
                onChange={setName}
              />
              <ChoiceField
                label='What it is drawn from'
                value={locus}
                table={LOCI}
                blocked={blocked}
                onPick={setLocus}
              />
              <ChoiceField
                label='How it renews'
                value={renewal}
                table={RENEWALS}
                blocked={blocked}
                onPick={setRenewal}
              />
              <ChoiceField
                label='Who may draw on it'
                value={access}
                table={ACCESS}
                blocked={blocked}
                onPick={setAccess}
              />
              <ChoiceField
                label='How plainly its use shows'
                value={visibility}
                table={VISIBILITIES}
                blocked={blocked}
                onPick={setVisibility}
              />
              <NumberField
                label='How predictable its draws are'
                value={stability}
                min={0}
                max={100}
                onChange={setStability}
              />
            </ForgeCard>
            <ForgeCard
              icon={Landmark}
              tone='gold'
              title='Let it know a source'
              note='Only a source known to a people, an order or one of its folk can be drawn on.'
              columns={2}
              action={
                <StepButton
                  icon={CirclePlus}
                  label='Teach it'
                  busy={why(
                    blocked ?? (known ? null : 'Choose a source'),
                    knowing.isPending
                  )}
                  onClick={() => knowing.mutate()}
                />
              }
            >
              <ChoiceField
                label='Source'
                value={known}
                table={every}
                blocked={blocked}
                onPick={setKnown}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
