import { useState } from 'react'
import { CirclePlus, Gauge, Trash2, Users } from 'lucide-react'
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
import { FORMS, type Named, TECHNIQUES, table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type MagicSystemsNodeView,
  type MagicSystemView,
  useNodeSystems,
} from './api'
import {
  ACCESS,
  LEARNABILITY,
  RESTRICTIONS,
  STRUCTURES,
  SYSTEM_RELATIONS,
  SYSTEMS_ICON,
  VISIBILITIES,
} from './labels'

const SHOWN = 4
const ANY = 'any'

const SYSTEM_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name of the system', kind: 'text' },
  { key: 'description', label: 'What it is', kind: 'text', long: true },
  {
    key: 'structure',
    label: 'How it works',
    kind: 'pick',
    table: table(STRUCTURES),
  },
  {
    key: 'predictability',
    label: 'How far it follows known rules',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'prevalence',
    label: 'How common it is',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'cost_severity',
    label: 'How hard its costs fall',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'visibility',
    label: 'How plainly it shows',
    kind: 'pick',
    table: table(VISIBILITIES),
  },
  {
    key: 'access',
    label: 'Who may use it',
    kind: 'pick',
    table: table(ACCESS),
  },
  {
    key: 'learnability',
    label: 'Who can learn it',
    kind: 'pick',
    table: table(LEARNABILITY),
  },
]

const PART_FIELDS: Record<string, readonly Field[]> = {
  link: [
    {
      key: 'relation',
      label: 'How they stand',
      kind: 'pick',
      table: table(SYSTEM_RELATIONS),
    },
  ],
  grammar: [
    {
      key: 'technique',
      label: 'What it may do',
      kind: 'pick',
      table: table(TECHNIQUES),
    },
    {
      key: 'form',
      label: 'What it may work on',
      kind: 'pick',
      table: table(FORMS),
    },
  ],
  restriction: [
    {
      key: 'kind',
      label: 'What it asks',
      kind: 'pick',
      table: table(RESTRICTIONS),
    },
    { key: 'detail', label: 'In words', kind: 'text' },
  ],
  source: [],
}
const PART_LABELS: Record<string, string> = {
  source: 'source',
  link: 'link to another system',
  grammar: 'allowed working',
  restriction: 'restriction',
}

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
    'system_part:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      part: kind,
      part_id: id,
      values: vars.values,
      hold: true,
    }),
    `The ${PART_LABELS[kind]} is set so`
  )
  const dropping = useMadeAction(
    'system_part:delete',
    (_: void) => ({ part: kind, part_id: id }),
    `The ${PART_LABELS[kind]} is taken away`
  )
  return (
    <RecordRow icon={SYSTEMS_ICON} tone='info' title={title} caption={caption}>
      {PART_FIELDS[kind].length ? (
        <RecordEditor
          title={`Set this ${PART_LABELS[kind]}`}
          note='Values you set are held against the engine.'
          fields={PART_FIELDS[kind]}
          locked={locked}
          busy={why(blocked, editing.isPending)}
          onSave={(values) => editing.mutate({ values, release: [] })}
          onRelease={() => editing.mutate({ values: {}, release: [] })}
        />
      ) : null}
      <StepButton
        icon={Trash2}
        label={`Take the ${PART_LABELS[kind]} away`}
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function System({
  system,
  view,
  blocked,
}: {
  system: MagicSystemView
  view: MagicSystemsNodeView
  blocked: string | null
}) {
  const structure = STRUCTURES[system.structure]
  const [part, setPart] = useState<string>('grammar')
  const [technique, setTechnique] = useState<string>(ANY)
  const [form, setForm] = useState<string>(ANY)
  const [source, setSource] = useState<string>(
    String(view.every_source[0]?.id ?? '')
  )
  const [other, setOther] = useState<string>(
    String(view.every_system.find((row) => row.id !== system.id)?.id ?? '')
  )
  const [relation, setRelation] = useState<string>('same_root')
  const editing = useMadeAction(
    'magic_system:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      system_id: system.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The system is set so'
  )
  const deleting = useMadeAction(
    'magic_system:delete',
    (_: void) => ({ system_id: system.id }),
    'The system is unmade'
  )
  const partValues = (): Record<string, string | number | null> => {
    if (part === 'grammar')
      return {
        technique: technique === ANY ? null : technique,
        form: form === ANY ? null : form,
      }
    if (part === 'source') return { source_id: Number(source) }
    if (part === 'link') return { second_system_id: Number(other), relation }
    return { kind: 'spoken_vow' }
  }
  const adding = useMadeAction(
    'system_part:create',
    (_: void) => ({
      owner_id: system.id,
      part,
      values: partValues(),
    }),
    'The system gains its part'
  )
  const named = (rows: readonly { id: number; name: string }[]) =>
    Object.fromEntries(
      rows.map((row) => [
        String(row.id),
        { label: row.name, icon: SYSTEMS_ICON, tone: 'info' as const },
      ])
    )
  const anyOf = (record: Record<string, Named>): Record<string, Named> => ({
    [ANY]: { label: 'Any', icon: SYSTEMS_ICON, tone: 'muted' as const },
    ...record,
  })
  const missing =
    part === 'link' && !other
      ? 'There is no other system to link'
      : part === 'source' && !source
        ? 'There is no source to tie'
        : null
  return (
    <RecordRow
      icon={structure.icon}
      tone={structure.tone ?? 'info'}
      title={system.name}
      caption={`${structure.label}; predictability ${system.predictability}, prevalence ${system.prevalence}, costs ${system.cost_severity}; since epoch ${system.founded_epoch}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip icon={LEARNABILITY[system.learnability].icon}>
            {LEARNABILITY[system.learnability].label}
          </Chip>
          <Chip icon={ACCESS[system.access].icon}>
            Open to {ACCESS[system.access].label.toLowerCase()}
          </Chip>
          <Chip icon={VISIBILITIES[system.visibility].icon}>
            {VISIBILITIES[system.visibility].label}
          </Chip>
        </div>
      }
    >
      {system.description ? (
        <Muted variant='caption'>{system.description}</Muted>
      ) : null}
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={system.sources} as='li'>
          {(row) => (
            <Part
              key={`s${row.id}`}
              kind='source'
              id={row.id}
              title={`Draws on ${row.source_name}`}
              caption='A source of this system'
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={system.links} as='li'>
          {(row) => (
            <Part
              key={`l${row.id}`}
              kind='link'
              id={row.id}
              title={`${SYSTEM_RELATIONS[row.relation].label} ${row.other_name}`}
              caption='How the two systems stand'
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={system.grammar} as='li'>
          {(row) => (
            <Part
              key={`g${row.id}`}
              kind='grammar'
              id={row.id}
              title={`Allows ${row.technique ? TECHNIQUES[row.technique].label.toLowerCase() : 'any working'} on ${row.form ? FORMS[row.form].label.toLowerCase() : 'anything'}`}
              caption='A working this system allows'
              locked={row.locked}
              blocked={blocked}
            />
          )}
        </Paged>
        <Paged items={system.restrictions} as='li'>
          {(row) => (
            <Part
              key={`r${row.id}`}
              kind='restriction'
              id={row.id}
              title={RESTRICTIONS[row.kind].label}
              caption={row.detail ?? 'no words given'}
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
        note='A source it draws on, a link to another system, a working it allows or a restriction it lays on its users. A system with no allowed workings allows them all.'
        columns={3}
        action={
          <StepButton
            icon={CirclePlus}
            label='Add the part'
            busy={why(blocked ?? missing, adding.isPending)}
            onClick={() => adding.mutate()}
          />
        }
      >
        <ChoiceField
          label='Which part'
          value={part}
          table={Object.fromEntries(
            Object.entries(PART_LABELS).map(([key, label]) => [
              key,
              { label, icon: SYSTEMS_ICON, tone: 'info' as const },
            ])
          )}
          blocked={blocked}
          onPick={setPart}
        />
        <ChoiceField
          label='What it may do'
          value={technique}
          table={anyOf(TECHNIQUES)}
          blocked={
            blocked ??
            (part === 'grammar'
              ? null
              : 'Only an allowed working names what it does')
          }
          onPick={setTechnique}
        />
        <ChoiceField
          label='What it may work on'
          value={form}
          table={anyOf(FORMS)}
          blocked={
            blocked ??
            (part === 'grammar'
              ? null
              : 'Only an allowed working names what it works on')
          }
          onPick={setForm}
        />
        <ChoiceField
          label='Source'
          value={source}
          table={named(view.every_source)}
          blocked={
            blocked ??
            (part === 'source' ? null : 'Only a source part names a source')
          }
          onPick={setSource}
        />
        <ChoiceField
          label='Other system'
          value={other}
          table={named(view.every_system.filter((row) => row.id !== system.id))}
          blocked={
            blocked ??
            (part === 'link' ? null : 'Only a link names another system')
          }
          onPick={setOther}
        />
        <ChoiceField
          label='How they stand'
          value={relation}
          table={SYSTEM_RELATIONS}
          blocked={
            blocked ??
            (part === 'link' ? null : 'Only a link names how they stand')
          }
          onPick={setRelation}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this system'
        note='Values you set are held against the engine until you release them.'
        fields={SYSTEM_FIELDS}
        locked={system.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Unmake the system'
        busy={why(blocked, deleting.isPending)}
        onClick={() => deleting.mutate()}
      />
    </RecordRow>
  )
}

export function MagicSystemsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeSystems(nodeId)
  const page = useShowMore(query.data?.systems ?? [], SHOWN, SHOWN * 2)
  const [name, setName] = useState('')
  const [structure, setStructure] = useState<string>('rite')
  const [predictability, setPredictability] = useState('50')
  const [prevalence, setPrevalence] = useState('50')
  const [costs, setCosts] = useState('50')
  const [access, setAccess] = useState<string>('anyone')
  const [learnability, setLearnability] = useState<string>('anyone')
  const creating = useMadeAction(
    'magic_system:create',
    (_: void) => ({
      name: name.trim(),
      scope_id: nodeId,
      structure: structure as MagicSystemView['structure'],
      predictability: Math.min(100, Math.max(0, Number(predictability) || 0)),
      prevalence: Math.min(100, Math.max(0, Number(prevalence) || 0)),
      cost_severity: Math.min(100, Math.max(0, Number(costs) || 0)),
      access: access as MagicSystemView['access'],
      learnability: learnability as MagicSystemView['learnability'],
    }),
    'A system of power takes shape'
  )
  const blocked = readOnlyReason
  const unnamed = name.trim() ? null : 'Name the system'
  const mean = query.data?.systems.length
    ? Math.round(
        query.data.systems.reduce(
          (total, row) => total + row.predictability,
          0
        ) / query.data.systems.length
      )
    : 0
  return (
    <Section
      id='section-magic-systems'
      title='Systems of power: how power works here'
      description='A world or realm may hold no system, one or several: each sets how its powers work, how predictable and common they are, who can learn them and how it stands with the others.'
      icon={SYSTEMS_ICON}
      tone='info'
    >
      <div
        data-surface='MagicSystemsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its systems of power' />
        ) : query.isError ? (
          <EmptyState
            icon={SYSTEMS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Systems here'
                value={String(query.data.systems.length)}
                icon={SYSTEMS_ICON}
                tone='info'
              />
              <KpiTile
                label='Mean predictability'
                value={String(mean)}
                icon={Gauge}
                tone='muted'
              />
              <KpiTile
                label='Systems in the cosmos'
                value={String(query.data.every_system.length)}
                icon={Users}
                tone='muted'
              />
            </div>
            {query.data.systems.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((system) => (
                    <System
                      key={system.id}
                      system={system}
                      view={query.data}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={SYSTEMS_ICON}
                size='inline'
                title='No system of power here'
                description='Shape one below, or look at the world or realm whose powers you mean.'
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='info'
              title='Shape a system of power here'
              note='Its predictability sets how much its outcomes vary; its prevalence how common it is.'
              columns={3}
              action={
                <StepButton
                  icon={CirclePlus}
                  label='Shape it'
                  variant='default'
                  busy={why(blocked ?? unnamed, creating.isPending)}
                  onClick={() => creating.mutate()}
                />
              }
            >
              <TextField
                label='Name of the system'
                value={name}
                blocked={blocked}
                onChange={setName}
              />
              <ChoiceField
                label='How it works'
                value={structure}
                table={STRUCTURES}
                blocked={blocked}
                onPick={setStructure}
              />
              <NumberField
                label='How far it follows known rules'
                value={predictability}
                min={0}
                max={100}
                onChange={setPredictability}
              />
              <NumberField
                label='How common it is'
                value={prevalence}
                min={0}
                max={100}
                onChange={setPrevalence}
              />
              <NumberField
                label='How hard its costs fall'
                value={costs}
                min={0}
                max={100}
                onChange={setCosts}
              />
              <ChoiceField
                label='Who may use it'
                value={access}
                table={ACCESS}
                blocked={blocked}
                onPick={setAccess}
              />
              <ChoiceField
                label='Who can learn it'
                value={learnability}
                table={LEARNABILITY}
                blocked={blocked}
                onPick={setLearnability}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
