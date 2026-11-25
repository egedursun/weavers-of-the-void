import { useState } from 'react'
import {
  CirclePlus,
  Eye,
  EyeOff,
  Search,
  Shield,
  Trash2,
  Zap,
} from 'lucide-react'
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
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction, useRowDelete, useRowEdit } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type HiddenTruthView,
  type PublicKnowledgeView,
  type TruthsNodeView,
  useNodeTruths,
} from './api'
import {
  AIMS,
  BREACH_CAUSES,
  KEEPER_ROLES,
  RESPONSES,
  SCOPES,
  TRUTH_ATTITUDES,
  TRUTH_KINDS,
  TRUTH_METHODS,
  TRUTHS_ICON,
} from './labels'

const SHOWN = 4
const YES_NO = { true: 'Yes', false: 'No' }

function truthFields(methods: readonly string[]): readonly Field[] {
  return [
    { key: 'title', label: 'What the truth is', kind: 'text' },
    { key: 'description', label: 'In more words', kind: 'text', long: true },
    {
      key: 'kind',
      label: 'What kind of truth',
      kind: 'pick',
      table: table(TRUTH_KINDS),
    },
    {
      key: 'hidden_from',
      label: 'Hidden from',
      kind: 'pick',
      table: table(SCOPES),
    },
    {
      key: 'scope_node_id',
      label: 'The people, realm or world it is hidden from',
      kind: 'node',
      types: [],
    },
    {
      key: 'strength',
      label: 'How well it is kept',
      kind: 'number',
      min: 0,
      max: 100,
    },
    {
      key: 'sanity_cost',
      label: 'How it harms those who learn it',
      kind: 'number',
      min: 0,
      max: 100,
    },
    {
      key: 'revealed',
      label: 'Known to all it was hidden from',
      kind: 'pick',
      table: YES_NO,
    },
    ...methods.map((method) => ({
      key: method,
      label: `Kept ${TRUTH_METHODS[method].label.toLowerCase()}`,
      kind: 'pick' as const,
      table: YES_NO,
    })),
  ]
}

const KEEPER_FIELDS: readonly Field[] = [
  {
    key: 'role',
    label: 'What they do for it',
    kind: 'pick',
    table: table(KEEPER_ROLES),
  },
]
const SEEKER_FIELDS: readonly Field[] = [
  {
    key: 'aim',
    label: 'What they want of it',
    kind: 'pick',
    table: table(AIMS),
  },
  {
    key: 'progress',
    label: 'How far along they are',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'began_epoch', label: 'Began in epoch', kind: 'number', min: 0 },
]
const KNOWLEDGE_FIELDS: readonly Field[] = [
  {
    key: 'know_pct',
    label: 'Share who know it',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'believe_pct',
    label: 'Share who believe it',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'attitude',
    label: 'How they hold it',
    kind: 'pick',
    table: table(TRUTH_ATTITUDES),
  },
  { key: 'revealed_epoch', label: 'Revealed in epoch', kind: 'number', min: 0 },
]

function Row({
  table: name,
  id,
  icon,
  tone,
  title,
  caption,
  fields,
  locked,
  blocked,
}: {
  table: string
  id: number
  icon: typeof Eye
  tone:
    'info' | 'warning' | 'muted' | 'gold' | 'danger' | 'success' | 'verdigris'
  title: string
  caption: string
  fields: readonly Field[]
  locked: string[]
  blocked: string | null
}) {
  const editing = useRowEdit(name, { id })
  const struck = useRowDelete(name, { id })
  return (
    <RecordRow icon={icon} tone={tone} title={title} caption={caption}>
      <RecordEditor
        act={editing}
        title='Set it'
        note='Values you set are held against the engine.'
        fields={fields}
        locked={locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={struck}
        icon={Trash2}
        label='Strike it'
        busy={why(blocked, struck.isPending)}
        onClick={() => struck.mutate()}
      />
    </RecordRow>
  )
}

function Known({
  row,
  blocked,
}: {
  row: PublicKnowledgeView
  blocked: string | null
}) {
  const attitude = TRUTH_ATTITUDES[row.attitude]
  return (
    <Row
      table='public_knowledge'
      id={row.id}
      icon={attitude.icon}
      tone={attitude.tone ?? 'info'}
      title={`${row.population.name} on ${row.truth_title}: ${attitude.label.toLowerCase()}`}
      caption={`${row.know_pct}% know it, ${row.believe_pct}% believe it${row.revealed_epoch !== null ? `, revealed in epoch ${row.revealed_epoch}` : ''}, weighed in epoch ${row.updated_epoch}`}
      fields={KNOWLEDGE_FIELDS}
      locked={row.locked}
      blocked={blocked}
    />
  )
}

function Truth({
  truth,
  methods,
  blocked,
}: {
  truth: HiddenTruthView
  methods: readonly string[]
  blocked: string | null
}) {
  const kind = TRUTH_KINDS[truth.kind]
  const kept = useShowMore(truth.methods, 3, 6)
  const [keeper, setKeeper] = useState<number | null>(null)
  const [seeker, setSeeker] = useState<number | null>(null)
  const [aim, setAim] = useState<string>('understand')
  const [population, setPopulation] = useState<number | null>(null)
  const [cause, setCause] = useState<string>('witness')
  const editing = useMadeAction(
    'truth:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      truth_id: truth.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The truth is set so'
  )
  const deleting = useMadeAction(
    'truth:delete',
    (_: void) => ({ truth_id: truth.id }),
    'The truth is no longer kept'
  )
  const revealing = useMadeAction(
    'truth:reveal',
    (_: void) => ({ truth_id: truth.id, population_id: population ?? 0 }),
    'They know it now'
  )
  const hiding = useMadeAction(
    'truth:hide',
    (_: void) => ({ truth_id: truth.id }),
    'The truth is hidden again'
  )
  const breaching = useMadeAction(
    'breach:trigger',
    (_: void) => ({
      truth_id: truth.id,
      cause: cause as HiddenTruthView['breaches'][number]['cause'],
      place_id: population,
    }),
    'The truth shows itself'
  )
  const keeping = useMadeAction(
    'record_row:create',
    (_: void) => ({
      table: 'truth_keepers',
      values: {
        truth_id: truth.id,
        keeper_node_id: keeper ?? 0,
        role: 'member',
      },
    }),
    'They keep it now'
  )
  const seeking = useMadeAction(
    'record_row:create',
    (_: void) => ({
      table: 'truth_seekers',
      values: {
        truth_id: truth.id,
        seeker_node_id: seeker ?? 0,
        aim,
        progress: 0,
        began_epoch: 0,
      },
    }),
    'They seek it now'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={truth.revealed ? 'muted' : (kind.tone ?? 'info')}
      title={truth.title}
      caption={`${kind.label}; hidden from ${SCOPES[truth.hidden_from].label.toLowerCase()}; kept at ${truth.strength}${truth.sanity_cost ? `, harms who learn it ${truth.sanity_cost}` : ''}; since epoch ${truth.founded_epoch}, tended in epoch ${truth.tended_epoch}${truth.revealed ? '; revealed' : ''}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {kept.visible.map((method) => (
            <Chip key={method} icon={TRUTH_METHODS[method].icon}>
              {TRUTH_METHODS[method].label}
            </Chip>
          ))}
          <ShowMore state={kept} />
        </div>
      }
    >
      <Ref node={truth.subject} empty='about nothing named' />
      <Ref node={truth.scope} empty='hidden from no single people' />
      {truth.description ? (
        <Muted variant='caption'>{truth.description}</Muted>
      ) : null}
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={truth.keepers} as='li'>
          {(row) => (
            <Row
              key={`k${row.id}`}
              table='truth_keepers'
              id={row.id}
              icon={KEEPER_ROLES[row.role].icon}
              tone='info'
              title={`${row.keeper.name} keeps it`}
              caption={KEEPER_ROLES[row.role].label}
              fields={KEEPER_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={truth.seekers} as='li'>
          {(row) => (
            <Row
              key={`s${row.id}`}
              table='truth_seekers'
              id={row.id}
              icon={Search}
              tone='warning'
              title={`${row.seeker.name} seeks it, ${AIMS[row.aim].label.toLowerCase()}`}
              caption={`${row.progress} of 100 of the way, since epoch ${row.began_epoch}`}
              fields={SEEKER_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={truth.knowledge} as='li'>
          {(row) => <Known key={`p${row.id}`} row={row} blocked={blocked} />}
        </Paged>
        <Paged items={truth.breaches} as='li'>
          {(row) => (
            <RecordRow
              key={`b${row.id}`}
              icon={BREACH_CAUSES[row.cause].icon}
              tone='warning'
              title={`It showed itself in epoch ${row.epoch}: ${BREACH_CAUSES[row.cause].label.toLowerCase()}`}
              caption={`spread ${row.spread}, answered by ${RESPONSES[row.response].label.toLowerCase()}${row.witnesses.length ? `, seen by ${row.witnesses.map((node) => node.name).join(', ')}` : ''}`}
            >
              <Ref node={row.place} empty='in no named place' />
            </RecordRow>
          )}
        </Paged>
      </ul>
      <ForgeCard
        icon={Shield}
        tone='info'
        title='Name who keeps it and who seeks it'
        note='Keepers tend it and answer its breaches; seekers wear it down until it shows itself.'
        columns={3}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              act={keeping}
              icon={Shield}
              label='Make them a keeper'
              busy={why(
                blocked ?? (keeper ? null : 'Choose a keeper'),
                keeping.isPending
              )}
              onClick={() => keeping.mutate()}
            />
            <StepButton
              act={seeking}
              icon={Search}
              label='Make them a seeker'
              busy={why(
                blocked ?? (seeker ? null : 'Choose a seeker'),
                seeking.isPending
              )}
              onClick={() => seeking.mutate()}
            />
          </div>
        }
      >
        <ThingPicker
          label='Keeper'
          value={keeper}
          onChange={setKeeper}
          blocked={blocked}
        />
        <ThingPicker
          label='Seeker'
          value={seeker}
          onChange={setSeeker}
          blocked={blocked}
        />
        <ChoiceField
          label='What the seeker wants'
          value={aim}
          table={AIMS}
          blocked={blocked}
          onPick={setAim}
        />
      </ForgeCard>
      <ForgeCard
        icon={Eye}
        tone='warning'
        title='Let it be known, or let it show itself'
        note='A revelation makes it known to a people, realm or town at once; a breach lets it slip by a cause, answered by its keepers.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              act={revealing}
              icon={Eye}
              label='Reveal it to them'
              busy={why(
                blocked ?? (population ? null : 'Choose who comes to know it'),
                revealing.isPending
              )}
              onClick={() => revealing.mutate()}
            />
            <StepButton
              act={breaching}
              icon={Zap}
              label='Let it show itself'
              busy={why(
                blocked ?? (truth.revealed ? 'It is already known' : null),
                breaching.isPending
              )}
              onClick={() => breaching.mutate()}
            />
            <StepButton
              act={hiding}
              icon={EyeOff}
              label='Hide it again'
              busy={why(blocked, hiding.isPending)}
              onClick={() => hiding.mutate()}
            />
          </div>
        }
      >
        <ThingPicker
          label='Who comes to know it, or where it shows'
          value={population}
          onChange={setPopulation}
          blocked={blocked}
        />
        <ChoiceField
          label='How it shows itself'
          value={cause}
          table={BREACH_CAUSES}
          blocked={blocked}
          onPick={setCause}
        />
      </ForgeCard>
      <RecordEditor
        act={editing}
        title='Set this truth'
        note='Values you set are held against the engine until you release them.'
        fields={truthFields(methods)}
        locked={truth.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={deleting}
        icon={Trash2}
        label='Let it go unkept'
        busy={why(blocked, deleting.isPending)}
        onClick={() => deleting.mutate()}
      />
    </RecordRow>
  )
}

function Truths({
  rows,
  methods,
  blocked,
  empty,
}: {
  rows: HiddenTruthView[]
  methods: readonly string[]
  blocked: string | null
  empty: string | null
}) {
  const page = useShowMore(rows, SHOWN, SHOWN * 2)
  if (!rows.length)
    return empty ? (
      <EmptyState
        icon={TRUTHS_ICON}
        size='inline'
        title='Nothing hidden'
        description={empty}
      />
    ) : null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul className='flex min-w-0 flex-col gap-2'>
        {page.visible.map((truth) => (
          <Truth
            key={truth.id}
            truth={truth}
            methods={methods}
            blocked={blocked}
          />
        ))}
      </ul>
      <ShowMore state={page} />
    </div>
  )
}

export function HiddenTruthsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeTruths(nodeId)
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<string>('existence')
  const [scope, setScope] = useState<string>('everyone')
  const [strength, setStrength] = useState('60')
  const [method, setMethod] = useState<string>('by_oath')
  const [keeper, setKeeper] = useState<number | null>(null)
  const creating = useMadeAction(
    'truth:create',
    (_: void) => ({
      title: title.trim(),
      subject_id: nodeId,
      kind: kind as HiddenTruthView['kind'],
      hidden_from: scope as HiddenTruthView['hidden_from'],
      strength: Math.min(100, Math.max(0, Number(strength) || 0)),
      methods: [method],
      keeper_id: keeper,
    }),
    'The truth is hidden'
  )
  const view: TruthsNodeView | undefined = query.data
  const blocked = readOnlyReason
  const untitled = title.trim() ? null : 'Say what the truth is'
  const methods = view?.methods ?? []
  return (
    <Section
      id='section-hidden-truths'
      title='Hidden truths: what is kept from whom'
      description='Truths hidden from a people, a realm or the world are kept, sought, breached, covered up, revealed and in time forgotten.'
      icon={TRUTHS_ICON}
      tone='muted'
    >
      <div
        data-surface='HiddenTruthsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading what is hidden' />
        ) : query.isError ? (
          <EmptyState
            icon={TRUTHS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Hidden about it'
                value={String(query.data.about.length)}
                icon={TRUTHS_ICON}
                tone='muted'
              />
              <KpiTile
                label='It keeps'
                value={String(query.data.kept.length)}
                icon={Shield}
                tone='info'
              />
              <KpiTile
                label='It seeks'
                value={String(query.data.sought.length)}
                icon={Search}
                tone='warning'
              />
              <KpiTile
                label='Known here'
                value={String(query.data.known_here.length)}
                icon={Eye}
                tone='gold'
              />
            </div>
            <Truths
              rows={query.data.about}
              methods={methods}
              blocked={blocked}
              empty={`Nothing about ${query.data.node.name} is hidden; hide something below.`}
            />
            <Truths
              rows={query.data.kept}
              methods={methods}
              blocked={blocked}
              empty={null}
            />
            <Truths
              rows={query.data.sought}
              methods={methods}
              blocked={blocked}
              empty={null}
            />
            {query.data.known_here.length ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={query.data.known_here} as='li'>
                  {(row) => <Known key={row.id} row={row} blocked={blocked} />}
                </Paged>
              </ul>
            ) : null}
            <ForgeCard
              icon={CirclePlus}
              tone='muted'
              title='Hide a truth about it'
              note='Name what is hidden, from whom and how it is kept; a keeper tends it and answers its breaches.'
              columns={3}
              action={
                <StepButton
                  act={creating}
                  icon={EyeOff}
                  label='Hide it'
                  variant='default'
                  busy={why(blocked ?? untitled, creating.isPending)}
                  onClick={() => creating.mutate()}
                />
              }
            >
              <TextField
                label='What the truth is'
                value={title}
                blocked={blocked}
                onChange={setTitle}
              />
              <ChoiceField
                label='What kind of truth'
                value={kind}
                table={TRUTH_KINDS}
                blocked={blocked}
                onPick={setKind}
              />
              <ChoiceField
                label='Hidden from'
                value={scope}
                table={SCOPES}
                blocked={blocked}
                onPick={setScope}
              />
              <NumberField
                label='How well it is kept'
                value={strength}
                min={0}
                max={100}
                onChange={setStrength}
              />
              <ChoiceField
                label='How it is kept'
                value={method}
                table={TRUTH_METHODS}
                blocked={blocked}
                onPick={setMethod}
              />
              <ThingPicker
                label='Its keeper'
                value={keeper}
                onChange={setKeeper}
                blocked={blocked}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
