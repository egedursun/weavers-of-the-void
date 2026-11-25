import { useState } from 'react'
import { CirclePlus, PenLine, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { entityTypeValues, naturalLawValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
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
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { wordOf } from '@/features/entity/affairs/labels'
import { words } from '@/features/entity/lore/api'
import { ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type LawExceptionView,
  type LawGrammarView,
  type LawTheoryView,
  useLawGrammar,
} from './api'
import {
  EXCEPTION_KINDS,
  LAW_CONDITIONS,
  LAW_GRAMMAR_ICON,
  LAW_OPERATORS,
  LAW_TARGETS,
  THEORY_ICON,
  WORKS_ICON,
} from './labels'

const SHOWN = 4
const HOLD =
  'Values you set are held against the engine until you release them.'
const PEOPLES = ['people'] as const
const KINDS = Object.fromEntries(
  entityTypeValues.map((value) => [
    value,
    {
      label: wordOf(entityTypeValues, value).toLowerCase(),
      icon: EXCEPTION_KINDS.kind.icon,
    },
  ])
)

type Edit = { values: EditValues; release: string[] }
type Target = NonNullable<LawGrammarView['target']>
type Operator = NonNullable<LawGrammarView['operator']>

const THEORY_FIELDS: readonly Field[] = [
  {
    key: 'believed_operator',
    label: 'What they believe it does',
    kind: 'pick',
    table: table(LAW_OPERATORS),
  },
  {
    key: 'believed_value',
    label: 'The amount they believe',
    kind: 'number',
    min: 0,
    max: 1000,
  },
  { key: 'confidence', label: 'Confidence', kind: 'number', min: 0, max: 100 },
  {
    key: 'adapted_epochs',
    label: 'Epochs they have lived under it',
    kind: 'number',
    min: 0,
  },
]
const EXCEPTION_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'Who it spares',
    kind: 'pick',
    table: table(EXCEPTION_KINDS),
  },
  { key: 'node_id', label: 'Spared one', kind: 'node', types: [] },
  {
    key: 'entity_type',
    label: 'Spared kind',
    kind: 'pick',
    table: table(KINDS),
  },
]

function Exception({
  row,
  blocked,
}: {
  row: LawExceptionView
  blocked: string | null
}) {
  const named = EXCEPTION_KINDS[row.kind]
  const editing = useMadeAction(
    'law_exception:edit',
    (vars: Edit) => ({
      exception_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The exception is set'
  )
  const removing = useMadeAction(
    'law_exception:delete',
    (_: void) => ({ exception_id: row.id }),
    'The law spares them no longer'
  )
  const spared = row.node
    ? row.node.name
    : row.entity_type
      ? `every ${wordOf(entityTypeValues, row.entity_type).toLowerCase()}`
      : 'no one named'
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone ?? 'info'}
      title={`Spares ${named.label.toLowerCase()}: ${spared}`}
      caption='The law does not touch them'
    >
      <RecordEditor
        act={editing}
        title='Set the exception'
        note={HOLD}
        fields={EXCEPTION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Remove it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Theory({
  row,
  blocked,
}: {
  row: LawTheoryView
  blocked: string | null
}) {
  const editing = useMadeAction(
    'law_theory:edit',
    (vars: Edit) => ({
      theory_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The theory is set'
  )
  const removing = useMadeAction(
    'law_theory:delete',
    (_: void) => ({ theory_id: row.id }),
    'The theory is forgotten'
  )
  return (
    <RecordRow
      icon={row.gap ? THEORY_ICON : WORKS_ICON}
      tone={row.gap > 50 ? 'danger' : row.gap ? 'warning' : 'success'}
      title={`${row.holder.name} believe it ${LAW_OPERATORS[row.believed_operator].label.toLowerCase()} at ${row.believed_value}`}
      caption={`Off from the truth by ${row.gap} of 100; confidence ${row.confidence}; lived under it ${row.adapted_epochs} epoch${row.adapted_epochs === 1 ? '' : 's'}; weighed in epoch ${row.updated_epoch}`}
    >
      <RecordEditor
        act={editing}
        title='Set the theory'
        note={HOLD}
        fields={THEORY_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Forget it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Held({
  view,
  lawId,
  blocked,
}: {
  view: LawGrammarView
  lawId: number
  blocked: string | null
}) {
  const releasing = useMadeAction(
    'law_profile:edit',
    (_: void) => ({ law_id: lawId, values: {}, release: view.locked }),
    'The world may move the law again'
  )
  const none = view.locked.length ? null : 'Nothing about the law is held'
  return (
    <RecordRow
      icon={LAW_GRAMMAR_ICON}
      tone='info'
      title={
        view.locked.length
          ? `You hold ${view.law.name}: ${view.locked.map(words).join(', ')}`
          : `The world moves ${view.law.name} freely`
      }
      caption='What you write is held until you let the world decide again'
    >
      <StepButton
        act={releasing}
        icon={PenLine}
        label='Let the world decide'
        busy={why(blocked ?? none, releasing.isPending)}
        onClick={() => releasing.mutate()}
      />
    </RecordRow>
  )
}

function Writing({
  view,
  lawId,
  blocked,
}: {
  view: LawGrammarView
  lawId: number
  blocked: string | null
}) {
  const [target, setTarget] = useState<string>(view.target ?? 'stat')
  const [operator, setOperator] = useState<string>(view.operator ?? 'multiply')
  const [key, setKey] = useState<string>(view.key ?? '')
  const [value, setValue] = useState(String(view.value))
  const [condition, setCondition] = useState<string>(view.condition)
  const [until, setUntil] = useState(
    view.until_epoch === null ? '' : String(view.until_epoch)
  )
  const keys = view.targets.find((item) => item.target === target)?.keys ?? []
  const keyTable = Object.fromEntries(
    keys.map((item) => [
      item,
      { label: words(item), icon: LAW_TARGETS[target as Target].icon },
    ])
  )
  const writing = useMadeAction(
    'law_grammar:set',
    (_: void) => ({
      law_id: lawId,
      target: target as Target,
      operator: operator as Operator,
      key: key.trim(),
      value: Math.max(0, Math.min(1000, Number(value) || 0)),
      condition: condition as LawGrammarView['condition'],
      until_epoch: until.trim() === '' ? null : Math.max(0, Number(until) || 0),
    }),
    'The law now works so'
  )
  const noKey = key.trim() === '' ? 'Name what the law works on first' : null
  return (
    <ForgeCard
      icon={PenLine}
      tone='gold'
      title='Write how the law works'
      note='Some things a law governs take only the workings the world already knows; a law over a measure of things or over made things may work on any of their values.'
      columns={3}
      action={
        <StepButton
          act={writing}
          icon={PenLine}
          label='Write it'
          variant='default'
          busy={why(blocked ?? noKey, writing.isPending)}
          onClick={() => writing.mutate()}
        />
      }
    >
      <ChoiceField
        label='What it governs'
        value={target}
        table={LAW_TARGETS}
        blocked={blocked}
        onPick={(next) => {
          setTarget(next)
          setKey('')
        }}
      />
      {keys.length ? (
        <ChoiceField
          label='Which of it'
          value={key}
          table={keyTable}
          blocked={blocked}
          onPick={setKey}
        />
      ) : (
        <TextField
          label='Which measure, by name'
          value={key}
          blocked={blocked}
          onChange={setKey}
        />
      )}
      <ChoiceField
        label='What it does'
        value={operator}
        table={LAW_OPERATORS}
        blocked={blocked}
        onPick={setOperator}
      />
      <NumberField
        label='Amount (100 leaves it as it is)'
        value={value}
        min={0}
        max={1000}
        onChange={setValue}
      />
      <ChoiceField
        label='When it holds'
        value={condition}
        table={LAW_CONDITIONS}
        blocked={blocked}
        onPick={setCondition}
      />
      <NumberField
        label='Ends at epoch (blank for never)'
        value={until}
        min={0}
        onChange={setUntil}
      />
    </ForgeCard>
  )
}

function Forges({ lawId, blocked }: { lawId: number; blocked: string | null }) {
  const [kind, setKind] = useState<string>('person')
  const [spared, setSpared] = useState<number | null>(null)
  const [sparedKind, setSparedKind] = useState<string>('mortal')
  const [holder, setHolder] = useState<number | null>(null)
  const [believed, setBelieved] = useState<string>('set')
  const [amount, setAmount] = useState('100')
  const sparing = useMadeAction(
    'law_exception:create',
    (_: void) => ({
      law_id: lawId,
      kind: kind as LawExceptionView['kind'],
      node_id: kind === 'kind' ? null : spared,
      entity_type:
        kind === 'kind'
          ? (sparedKind as LawExceptionView['entity_type'])
          : null,
    }),
    'The law now spares them'
  )
  const teaching = useMadeAction(
    'law_theory:create',
    (_: void) => ({
      law_id: lawId,
      holder_id: holder ?? 0,
      believed_operator: believed as LawTheoryView['believed_operator'],
      believed_value: Math.max(0, Math.min(1000, Number(amount) || 0)),
    }),
    'They now hold a theory of the law'
  )
  const noSpared =
    kind !== 'kind' && spared === null ? 'Pick who the law spares first' : null
  const noHolder = holder === null ? 'Pick a people first' : null
  return (
    <>
      <ForgeCard
        icon={CirclePlus}
        tone='info'
        title='Spare someone from the law'
        note='The law does not touch those it spares: a person, the members of a house or line, a people, every thing of a kind, or those in a place.'
        columns={2}
        action={
          <StepButton
            act={sparing}
            icon={CirclePlus}
            label='Spare them'
            variant='default'
            busy={why(blocked ?? noSpared, sparing.isPending)}
            onClick={() => sparing.mutate()}
          />
        }
      >
        <ChoiceField
          label='Who it spares'
          value={kind}
          table={EXCEPTION_KINDS}
          blocked={blocked}
          onPick={setKind}
        />
        {kind === 'kind' ? (
          <ChoiceField
            label='Kind of thing'
            value={sparedKind}
            table={KINDS}
            blocked={blocked}
            onPick={setSparedKind}
          />
        ) : (
          <ThingPicker
            label='The one spared'
            value={spared}
            onChange={setSpared}
            blocked={blocked}
          />
        )}
      </ForgeCard>
      <ForgeCard
        icon={THEORY_ICON}
        tone='verdigris'
        title='Give a people a theory of the law'
        note='A people works by what it believes the law does; the farther its theory from the truth, the less its craft can be trusted, until it has lived under the law long enough to adapt.'
        columns={3}
        action={
          <StepButton
            act={teaching}
            icon={THEORY_ICON}
            label='Give it'
            variant='default'
            busy={why(blocked ?? noHolder, teaching.isPending)}
            onClick={() => teaching.mutate()}
          />
        }
      >
        <ThingPicker
          label='People'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
          types={PEOPLES}
        />
        <ChoiceField
          label='What they believe it does'
          value={believed}
          table={LAW_OPERATORS}
          blocked={blocked}
          onPick={setBelieved}
        />
        <NumberField
          label='Amount they believe'
          value={amount}
          min={0}
          max={1000}
          onChange={setAmount}
        />
      </ForgeCard>
    </>
  )
}

export function LawGrammarSection({
  lawId,
  readOnlyReason = null,
}: {
  lawId: number
  readOnlyReason?: string | null
}) {
  const query = useLawGrammar(lawId)
  const exceptions = useShowMore(query.data?.exceptions ?? [], SHOWN, SHOWN)
  const theories = useShowMore(query.data?.theories ?? [], SHOWN, SHOWN)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-law-grammar'
      title='The writing of the law: what it governs, what it does and when'
      description='A natural law governs a thing, does something to it at an amount, holds under a condition and for a span, spares those it names, and is believed in by the peoples under it.'
      icon={LAW_GRAMMAR_ICON}
      tone='gold'
    >
      <div
        data-surface='LawGrammarSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading how the law is written' />
        ) : query.isError ? (
          <EmptyState
            icon={LAW_GRAMMAR_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <RecordRow
              icon={
                query.data.target
                  ? LAW_TARGETS[query.data.target].icon
                  : LAW_GRAMMAR_ICON
              }
              tone='gold'
              title={query.data.written}
              caption={
                query.data.until_epoch === null
                  ? 'It holds for as long as it is kept'
                  : `It ends at epoch ${query.data.until_epoch}`
              }
            >
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                {query.data.target && (
                  <Chip icon={LAW_TARGETS[query.data.target].icon}>
                    {LAW_TARGETS[query.data.target].label}
                  </Chip>
                )}
                {query.data.operator && (
                  <Chip icon={LAW_OPERATORS[query.data.operator].icon}>
                    {LAW_OPERATORS[query.data.operator].label}
                  </Chip>
                )}
                <Chip icon={LAW_CONDITIONS[query.data.condition].icon}>
                  {LAW_CONDITIONS[query.data.condition].label}
                </Chip>
                {query.data.preset !== 'none' && (
                  <Badge variant='outline'>{`Known of old as ${wordOf(naturalLawValues, query.data.preset).toLowerCase()}`}</Badge>
                )}
                {query.data.suspended && (
                  <Badge variant='warning'>
                    Suspended: a stronger law or its condition holds it back
                  </Badge>
                )}
                {query.data.contested && (
                  <Badge variant='warning'>
                    Deadlocked with a contrary law
                  </Badge>
                )}
              </div>
            </RecordRow>
            <Held view={query.data} lawId={lawId} blocked={blocked} />
            <Writing view={query.data} lawId={lawId} blocked={blocked} />
            {query.data.exceptions.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {exceptions.visible.map((row) => (
                    <Exception key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={exceptions} />
              </>
            ) : (
              <EmptyState
                icon={EXCEPTION_KINDS.person.icon}
                size='inline'
                title='It spares no one'
                description='Name those it spares below.'
              />
            )}
            {query.data.theories.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {theories.visible.map((row) => (
                    <Theory key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={theories} />
              </>
            ) : (
              <EmptyState
                icon={THEORY_ICON}
                size='inline'
                title='No people holds a theory of it yet'
                description='The peoples under it form theories as the epochs pass.'
              />
            )}
            <Forges lawId={lawId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
