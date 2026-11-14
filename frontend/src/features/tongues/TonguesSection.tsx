import { useState } from 'react'
import {
  Feather,
  GitBranch,
  Handshake,
  Plus,
  RotateCcw,
  ScrollText,
  Sun,
  Trash2,
  UserPlus,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
  Timeline,
  TimelineItem,
  type TimelineTone,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { useEntityType } from '@/features/arcana/model'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { GOD_KINDS, why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { TextField } from '@/features/entity/economy/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type DecipherView,
  type DivineTongueView,
  type LanguagePolicy,
  type NodeTonguesView,
  type PolicyView,
  type ScriptChangeCause,
  type ShiftView,
  type SoundChangeKind,
  type SoundChangeView,
  type SoundEnvironment,
  type TongueGrammarView,
  type TongueMechanicsView,
  type WritingSystem,
  useNodeTongues,
  useScripts,
  useTongueAction,
} from './api'
import {
  CAUSES,
  CHANGE_KINDS,
  ENVIRONMENTS,
  MODALITIES,
  MORPHOLOGIES,
  NUMBERS,
  POLICIES,
  SCRIPT_CAUSES,
  SHIFTS,
  STAGES,
  SYSTEMS,
  TONGUE_ICON,
  WORD_ORDERS,
} from './labels'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

const BOOLEAN = { true: 'Yes', false: 'No' }
const HOLDER_TYPES = ['polity', 'cult', 'people', 'settlement', 'faction']
const COMMUNITY_TYPES = ['people', 'settlement', 'faction', 'cult']

function ProfileCard({
  languageId,
  data,
  blocked,
}: {
  languageId: number
  data: TongueMechanicsView
  blocked: string | null
}) {
  const edit = useTongueAction(
    'tongue:edit',
    (values: Values) => ({ language_id: languageId, values }),
    'The tongue is set'
  )
  const busy = why(blocked, edit.isPending)
  const modality = MODALITIES[data.modality]
  const stage = STAGES[data.stage]
  return (
    <RecordRow
      icon={modality.icon}
      tone={stage.tone}
      title={`${modality.label} · ${stage.label}`}
      caption={
        data.writing_system
          ? `Written in ${SYSTEMS[data.writing_system].label.toLowerCase()}`
          : 'Unwritten'
      }
    >
      <RecordEditor
        title='Reshape the tongue'
        note='A tongue that is scented or thought cannot be written; thought crosses every barrier between those who think it.'
        fields={[
          {
            key: 'modality',
            label: 'How it is made',
            kind: 'pick',
            table: table(MODALITIES),
          },
          { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        ]}
        locked={[]}
        busy={busy}
        onSave={(values) => edit.mutate(values)}
        onRelease={() => edit.mutate({})}
      />
    </RecordRow>
  )
}

function GrammarCard({
  languageId,
  grammar,
  blocked,
}: {
  languageId: number
  grammar: TongueGrammarView | null
  blocked: string | null
}) {
  const edit = useTongueAction(
    'grammar:edit',
    (vars: Edit) => ({ language_id: languageId, ...vars }),
    'The grammar is set'
  )
  const reset = useTongueAction(
    'grammar:reset',
    (_: void) => ({ language_id: languageId }),
    'The grammar is drawn anew'
  )
  const busy = why(blocked, edit.isPending, reset.isPending)
  return (
    <RecordRow
      icon={grammar ? MORPHOLOGIES[grammar.morphology].icon : TONGUE_ICON}
      tone='info'
      title={
        grammar ? MORPHOLOGIES[grammar.morphology].label : 'Grammar not yet set'
      }
      caption={
        grammar
          ? `${WORD_ORDERS[grammar.word_order].label} · since epoch ${grammar.updated_epoch}`
          : 'The engine draws it from the tongue’s roots'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => reset.mutate()}
        >
          <RotateCcw />
          Draw anew
        </Button>
      }
    >
      {grammar && (
        <>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Chip>{`${grammar.cases} cases`}</Chip>
            <Chip>{`${grammar.noun_classes} noun classes`}</Chip>
            <Chip>{`${grammar.honorific_levels} levels of honour`}</Chip>
            <Chip icon={NUMBERS[grammar.number_system].icon}>
              {NUMBERS[grammar.number_system].label}
            </Chip>
            {grammar.evidentiality && (
              <Chip variant='warning'>Marks how it is known</Chip>
            )}
          </div>
          <RecordEditor
            title='Reshape the grammar'
            note='Distant grammars make letters and treaties misread and art forms lose more in translation.'
            fields={[
              {
                key: 'word_order',
                label: 'Word order',
                kind: 'pick',
                table: table(WORD_ORDERS),
              },
              {
                key: 'morphology',
                label: 'Morphology',
                kind: 'pick',
                table: table(MORPHOLOGIES),
              },
              { key: 'cases', label: 'Cases', kind: 'number', min: 0, max: 20 },
              {
                key: 'noun_classes',
                label: 'Noun classes',
                kind: 'number',
                min: 0,
                max: 20,
              },
              {
                key: 'evidentiality',
                label: 'Marks how it is known',
                kind: 'pick',
                table: BOOLEAN,
              },
              {
                key: 'honorific_levels',
                label: 'Levels of honour',
                kind: 'number',
                min: 0,
                max: 6,
              },
              {
                key: 'number_system',
                label: 'Number',
                kind: 'pick',
                table: table(NUMBERS),
              },
            ]}
            locked={grammar.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </>
      )}
    </RecordRow>
  )
}

const TIMELINE_SHOWN = 8
const CAUSE_TONE: Record<SoundChangeView['cause'], TimelineTone> = {
  contact: 'primary',
  prestige: 'success',
  migration: 'warning',
  drift: 'default',
  decree: 'destructive',
  inherited: 'default',
}

function SoundTimeline({ changes }: { changes: SoundChangeView[] }) {
  if (changes.length === 0) return null
  const shown = [...changes]
    .sort((first, second) => first.position - second.position)
    .slice(-TIMELINE_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Timeline label='How its sounds changed'>
        {shown.map((change, index) => (
          <TimelineItem
            key={change.id}
            icon={CHANGE_KINDS[change.kind].icon}
            title={`${change.source} → ${change.target || 'nothing'}`}
            timestamp={`Epoch ${change.epoch}`}
            tone={CAUSE_TONE[change.cause]}
            last={index === shown.length - 1}
          >
            <Muted variant='caption'>
              {`${CHANGE_KINDS[change.kind].label}, ${ENVIRONMENTS[change.environment].label.toLowerCase()}; ${CAUSES[change.cause].label.toLowerCase()}`}
            </Muted>
          </TimelineItem>
        ))}
      </Timeline>
      {changes.length > shown.length && (
        <Muted variant='caption'>
          {`The latest ${shown.length} of ${plural(changes.length, 'change', 'changes')}; every change is listed below.`}
        </Muted>
      )}
    </div>
  )
}

function ChangeCard({
  change,
  blocked,
}: {
  change: SoundChangeView
  blocked: string | null
}) {
  const edit = useTongueAction(
    'sound_change:edit',
    (vars: Edit) => ({ change_id: change.id, ...vars }),
    'The sound change is set'
  )
  const remove = useTongueAction(
    'sound_change:delete',
    (_: void) => ({ change_id: change.id }),
    'The sound change is undone'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const kind = CHANGE_KINDS[change.kind]
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={`${change.position + 1}. ${change.source} → ${change.target || 'nothing'}`}
      caption={`${kind.label} · ${ENVIRONMENTS[change.environment].label.toLowerCase()} · epoch ${change.epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Undo
        </Button>
      }
    >
      <Chip icon={CAUSES[change.cause].icon}>{CAUSES[change.cause].label}</Chip>
      <RecordEditor
        title='Reshape the change'
        note='Every word of the tongue is derived again from its proto-form when a change moves.'
        fields={[
          {
            key: 'kind',
            label: 'Kind of change',
            kind: 'pick',
            table: table(CHANGE_KINDS),
          },
          { key: 'source', label: 'Sound', kind: 'text' },
          { key: 'target', label: 'Becomes', kind: 'text' },
          {
            key: 'environment',
            label: 'Where',
            kind: 'pick',
            table: table(ENVIRONMENTS),
          },
          { key: 'cause', label: 'Cause', kind: 'pick', table: table(CAUSES) },
          { key: 'position', label: 'Order', kind: 'number', min: 0 },
          { key: 'epoch', label: 'Epoch', kind: 'number', min: 0 },
        ]}
        locked={change.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ChangeForm({
  languageId,
  blocked,
}: {
  languageId: number
  blocked: string | null
}) {
  const [kind, setKind] = useState<SoundChangeKind>('shift')
  const [environment, setEnvironment] = useState<SoundEnvironment>('anywhere')
  const [source, setSource] = useState('')
  const [target, setTarget] = useState('')
  const add = useTongueAction(
    'sound_change:add',
    (_: void) => ({
      language_id: languageId,
      kind,
      source,
      target,
      environment,
    }),
    'The sound shifts'
  )
  const busy = why(blocked, add.isPending)
  const missing = source.trim() === '' ? 'Name the sound that changes' : null
  return (
    <ForgeCard
      icon={GitBranch}
      tone='verdigris'
      title='Decree a sound change'
      note='The change joins the end of the tongue’s list, and every word follows it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => add.mutate()}
        >
          <Plus />
          Decree it
        </Button>
      }
    >
      <MindPicker
        label='Kind of change'
        value={kind}
        table={table(CHANGE_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as SoundChangeKind)}
      />
      <MindPicker
        label='Where'
        value={environment}
        table={table(ENVIRONMENTS)}
        blocked={busy}
        onPick={(value) => setEnvironment(value as SoundEnvironment)}
      />
      <TextField
        label='Sound'
        value={source}
        disabled={busy !== null}
        onChange={setSource}
      />
      <TextField
        label='Becomes (empty when lost)'
        value={target}
        disabled={busy !== null}
        onChange={setTarget}
      />
    </ForgeCard>
  )
}

function ScriptCard({
  languageId,
  data,
  blocked,
}: {
  languageId: number
  data: TongueMechanicsView
  blocked: string | null
}) {
  const scripts = useScripts()
  const [chosen, setChosen] = useState('')
  const [system, setSystem] = useState<WritingSystem>('alphabet')
  const [cause, setCause] = useState<ScriptChangeCause>('invention')
  const script = data.script
  const edit = useTongueAction(
    'script:edit',
    (vars: Edit) => ({ script_id: script?.id ?? 0, ...vars }),
    'The script is set'
  )
  const remove = useTongueAction(
    'script:delete',
    (_: void) => ({ script_id: script?.id ?? 0 }),
    'The script is forgotten'
  )
  const assign = useTongueAction(
    'script:assign',
    (scriptId: number | null) => ({
      language_id: languageId,
      script_id: scriptId,
    }),
    'The tongue’s script is set'
  )
  const create = useTongueAction(
    'script:create',
    (_: void) => ({
      language_id: languageId,
      system,
      cause,
      parent_id: script?.id ?? null,
    }),
    'A script is made'
  )
  const busy = why(
    blocked,
    edit.isPending,
    remove.isPending,
    assign.isPending,
    create.isPending
  )
  const options = Object.fromEntries(
    (scripts.data ?? []).map((row) => [String(row.id), row.name])
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Script</Label>
      {script ? (
        <RecordRow
          icon={SYSTEMS[script.system].icon}
          tone={SYSTEMS[script.system].tone}
          title={script.name}
          caption={`${SYSTEMS[script.system].label} · ${script.signs} signs · ${SCRIPT_CAUSES[script.cause].label.toLowerCase()} in epoch ${script.epoch}`}
          aside={
            <div className='flex shrink-0 flex-wrap items-center gap-1'>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => assign.mutate(null)}
              >
                <Feather />
                Leave unwritten
              </Button>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => remove.mutate()}
              >
                <Trash2 />
                Forget
              </Button>
            </div>
          }
        >
          <Facts
            items={[
              [
                'First written by',
                <Ref
                  key='origin'
                  node={script.origin_language}
                  empty='unknown'
                />,
              ],
              [
                'Descends from',
                script.parent_script_id !== null
                  ? data.lineage
                      .slice(1)
                      .map((row) => row.name)
                      .join(' ← ') || `script ${script.parent_script_id}`
                  : 'no older script',
              ],
            ]}
          />
          <RecordEditor
            title='Reshape the script'
            note='Every tongue written in this script follows its system.'
            fields={[
              { key: 'name', label: 'Script name', kind: 'text' },
              {
                key: 'system',
                label: 'System',
                kind: 'pick',
                table: table(SYSTEMS),
              },
              { key: 'signs', label: 'Signs', kind: 'number', min: 0 },
              {
                key: 'cause',
                label: 'How it came to be',
                kind: 'pick',
                table: table(SCRIPT_CAUSES),
              },
              {
                key: 'parent_script_id',
                label: 'Descends from (script id)',
                kind: 'number',
                min: 1,
              },
              {
                key: 'origin_language_id',
                label: 'First written by (tongue id)',
                kind: 'number',
                min: 1,
              },
              { key: 'epoch', label: 'Epoch', kind: 'number', min: 0 },
            ]}
            locked={script.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </RecordRow>
      ) : (
        <Muted variant='caption'>
          This tongue is unwritten; it may borrow a script from a tongue its
          speakers know.
        </Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <MindPicker
          label='Write it in a known script'
          value={chosen}
          table={options}
          blocked={
            busy ?? (scripts.data?.length ? null : 'No script exists yet')
          }
          onPick={setChosen}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || chosen === ''}
          disabledReason={
            busy ?? (chosen === '' ? 'Choose a script first' : undefined)
          }
          onClick={() => assign.mutate(Number(chosen))}
        >
          <ScrollText />
          Use this script
        </Button>
      </div>
      <ForgeCard
        icon={Feather}
        tone='gold'
        title={script ? 'Give it a new script' : 'Give it a script'}
        note='A new script descends from the one it replaces.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => create.mutate()}
          >
            <Plus />
            Make it
          </Button>
        }
      >
        <MindPicker
          label='System'
          value={system}
          table={table(SYSTEMS)}
          blocked={busy}
          onPick={(value) => setSystem(value as WritingSystem)}
        />
        <MindPicker
          label='How it comes to be'
          value={cause}
          table={table(SCRIPT_CAUSES)}
          blocked={busy}
          onPick={(value) => setCause(value as ScriptChangeCause)}
        />
      </ForgeCard>
    </div>
  )
}

function DecipherCard({
  languageId,
  work,
  blocked,
}: {
  languageId: number
  work: DecipherView | null
  blocked: string | null
}) {
  const [scholar, setScholar] = useState<number | null>(null)
  const start = useTongueAction(
    'decipherment:start',
    (_: void) => ({ language_id: languageId, scholar_id: scholar }),
    'Scholars take up the script'
  )
  const edit = useTongueAction(
    'decipherment:edit',
    (vars: Edit) => ({ language_id: languageId, ...vars }),
    'The decipherment is set'
  )
  const remove = useTongueAction(
    'decipherment:delete',
    (_: void) => ({ language_id: languageId }),
    'The decipherment is struck out'
  )
  const busy = why(blocked, start.isPending, edit.isPending, remove.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Decipherment</Label>
      {work ? (
        <RecordRow
          icon={ScrollText}
          tone={work.progress >= 100 ? 'success' : 'info'}
          title={work.progress >= 100 ? 'Deciphered' : 'Being deciphered'}
          caption={`Begun in epoch ${work.started_epoch}, last worked in epoch ${work.updated_epoch}`}
          aside={
            <Button
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => remove.mutate()}
            >
              <Trash2 />
              Strike out
            </Button>
          }
        >
          <Meter label='Read' value={work.progress} tone='success' />
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Chip>{`${work.corpus} surviving texts`}</Chip>
            <Chip variant={work.errors ? 'warning' : undefined}>
              {`${work.errors} misreadings`}
            </Chip>
            {work.bilingual && <Chip variant='success'>A bilingual text</Chip>}
          </div>
          <Facts
            items={[
              [
                'Scholar',
                <Ref key='scholar' node={work.scholar} empty='no one yet' />,
              ],
            ]}
          />
          <RecordEditor
            title='Reshape the decipherment'
            note='A finished decipherment makes the script readable to all.'
            fields={[
              {
                key: 'progress',
                label: 'Read',
                kind: 'number',
                min: 0,
                max: 100,
              },
              {
                key: 'corpus',
                label: 'Surviving texts',
                kind: 'number',
                min: 0,
              },
              {
                key: 'bilingual',
                label: 'A bilingual text is known',
                kind: 'pick',
                table: BOOLEAN,
              },
              { key: 'errors', label: 'Misreadings', kind: 'number', min: 0 },
              {
                key: 'scholar_entity_id',
                label: 'Scholar (mortal id)',
                kind: 'number',
                min: 1,
              },
              {
                key: 'started_epoch',
                label: 'Begun in epoch',
                kind: 'number',
                min: 0,
              },
            ]}
            locked={work.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </RecordRow>
      ) : (
        <Muted variant='caption'>No one works at this script.</Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Scholar who takes it up'
          value={scholar}
          onChange={setScholar}
          blocked={busy}
          types={['mortal']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => start.mutate()}
        >
          <ScrollText />
          {work ? 'Set the scholar' : 'Set scholars to it'}
        </Button>
      </div>
    </div>
  )
}

function PolicyCard({
  policy,
  blocked,
}: {
  policy: PolicyView
  blocked: string | null
}) {
  const keys = {
    holder_id: policy.holder?.id ?? 0,
    language_id: policy.language?.id ?? 0,
    policy: policy.policy,
  }
  const edit = useTongueAction(
    'language_policy:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The policy is set'
  )
  const remove = useTongueAction(
    'language_policy:delete',
    (_: void) => keys,
    'The policy is lifted'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const spec = POLICIES[policy.policy]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone}
      title={<Ref node={policy.language} empty='a lost tongue' />}
      caption={`${spec.label} under ${policy.holder?.name ?? 'no one'} since epoch ${policy.since_epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Lift
        </Button>
      }
    >
      <Meter label='Strength' value={policy.strength} tone='default' />
      <Facts items={[['Held by', <Ref key='holder' node={policy.holder} />]]} />
      <RecordEditor
        title='Reshape the policy'
        note='Suppression costs the speakers cohesion and raises unrest; an official or revived tongue spreads.'
        fields={[
          {
            key: 'strength',
            label: 'Strength',
            kind: 'number',
            min: 0,
            max: 100,
          },
        ]}
        locked={policy.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function PolicyForm({
  holderId,
  languageId,
  blocked,
}: {
  holderId: number | null
  languageId: number | null
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(holderId)
  const [language, setLanguage] = useState<number | null>(languageId)
  const [policy, setPolicy] = useState<LanguagePolicy>('official')
  const [strength, setStrength] = useState('50')
  const place = useTongueAction(
    'language_policy:set',
    (_: void) => ({
      holder_id: holder ?? 0,
      language_id: language ?? 0,
      policy,
      strength: Number(strength) || 0,
    }),
    'The policy is set'
  )
  const busy = why(blocked, place.isPending)
  const missing =
    holder === null
      ? 'Choose who holds it'
      : language === null
        ? 'Choose the tongue'
        : null
  return (
    <ForgeCard
      icon={POLICIES[policy].icon}
      tone={POLICIES[policy].tone}
      title='Set a policy on a tongue'
      note='Realms, faiths, peoples and towns can make a tongue official or sacred, suppress it or revive it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => place.mutate()}
        >
          <Plus />
          Set it
        </Button>
      }
    >
      {holderId === null && (
        <NodePicker
          label='Held by'
          value={holder}
          onChange={setHolder}
          blocked={busy}
          types={HOLDER_TYPES}
        />
      )}
      {languageId === null && (
        <NodePicker
          label='Tongue'
          value={language}
          onChange={setLanguage}
          blocked={busy}
          types={['language']}
        />
      )}
      <MindPicker
        label='Policy'
        value={policy}
        table={table(POLICIES)}
        blocked={busy}
        onPick={(value) => setPolicy(value as LanguagePolicy)}
      />
      <TextField
        label='Strength (0 to 100)'
        value={strength}
        disabled={busy !== null}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

function ShiftCard({
  shift,
  blocked,
}: {
  shift: ShiftView
  blocked: string | null
}) {
  const edit = useTongueAction(
    'meaning_shift:edit',
    (vars: Edit) => ({ shift_id: shift.id, ...vars }),
    'The record is set'
  )
  const remove = useTongueAction(
    'meaning_shift:delete',
    (_: void) => ({ shift_id: shift.id }),
    'The record is struck out'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const spec = SHIFTS[shift.shift]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone}
      title={shift.word}
      caption={`${spec.label} in epoch ${shift.epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Strike out
        </Button>
      }
    >
      <Facts
        items={[
          ['Meant', shift.old_meaning || 'nothing recorded'],
          ['Now means', shift.new_meaning || 'nothing recorded'],
          ['Took the place of', shift.absorbed_word ?? 'no other word'],
          [
            'For the name of',
            <Ref key='cause' node={shift.cause} empty='no one' />,
          ],
        ]}
      />
      <RecordEditor
        title='Reshape the record'
        note='The record of a shift is history; the word itself is edited in the dictionary.'
        fields={[
          { key: 'old_meaning', label: 'Meant', kind: 'text' },
          { key: 'new_meaning', label: 'Now means', kind: 'text' },
        ]}
        locked={[]}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={() => edit.mutate({ values: {}, release: [] })}
      />
    </RecordRow>
  )
}

function VeilForm({
  languageId,
  blocked,
}: {
  languageId: number
  blocked: string | null
}) {
  const [named, setNamed] = useState<number | null>(null)
  const veil = useTongueAction(
    'word:veil',
    (_: void) => ({ language_id: languageId, node_id: named ?? 0 }),
    'The name is veiled'
  )
  const busy = why(blocked, veil.isPending)
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <NodePicker
        label='Name no longer said aloud'
        value={named}
        onChange={setNamed}
        blocked={busy}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || named === null}
        disabledReason={
          busy ?? (named === null ? 'Choose whose name' : undefined)
        }
        onClick={() => veil.mutate()}
      >
        <Sun />
        Veil the name
      </Button>
    </div>
  )
}

function DivineCard({
  godId,
  tongue,
  blocked,
}: {
  godId: number
  tongue: DivineTongueView | null
  blocked: string | null
}) {
  const [language, setLanguage] = useState<number | null>(null)
  const [mortal, setMortal] = useState<number | null>(null)
  const choose = useTongueAction(
    'divine_tongue:set',
    (languageId: number | null) => ({ god_id: godId, language_id: languageId }),
    'The god speaks its tongue'
  )
  const edit = useTongueAction(
    'divine_tongue:edit',
    (vars: Edit) => ({ god_id: godId, ...vars }),
    'The tongue is set'
  )
  const remove = useTongueAction(
    'divine_tongue:delete',
    (_: void) => ({ god_id: godId }),
    'The tongue is taken away'
  )
  const teach = useTongueAction(
    'divine_tongue:teach',
    (_: void) => ({ god_id: godId, mortal_id: mortal ?? 0 }),
    'The mortal learns the tongue'
  )
  const busy = why(
    blocked,
    choose.isPending,
    edit.isPending,
    remove.isPending,
    teach.isPending
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Sacred tongue</Label>
      {tongue ? (
        <RecordRow
          icon={Sun}
          tone='gold'
          title={<Ref node={tongue.language} empty='a lost tongue' />}
          caption={`Spoken since epoch ${tongue.since_epoch}`}
          aside={
            <Button
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => remove.mutate()}
            >
              <Trash2 />
              Take away
            </Button>
          }
        >
          <RecordEditor
            title='Reshape the tongue'
            note='Rites cast in the god’s name grow stronger in a mouth that knows its tongue.'
            fields={[
              {
                key: 'language_entity_id',
                label: 'Tongue (id)',
                kind: 'number',
                min: 1,
              },
            ]}
            locked={tongue.locked}
            busy={busy}
            onSave={(values) => edit.mutate({ values, release: [] })}
            onRelease={(release) => edit.mutate({ values: {}, release })}
          />
        </RecordRow>
      ) : (
        <Muted variant='caption'>This god has no sacred tongue yet.</Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Make this its tongue'
          value={language}
          onChange={setLanguage}
          blocked={busy}
          types={['language']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => choose.mutate(language)}
        >
          <Sun />
          {language === null
            ? 'Give it a tongue of its own'
            : 'Make it its tongue'}
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Mortal to teach'
          value={mortal}
          onChange={setMortal}
          blocked={busy ?? (tongue ? null : 'Give the god a tongue first')}
          types={['mortal']}
        />
        <Button
          size='sm'
          disabled={busy !== null || mortal === null || tongue === null}
          disabledReason={
            busy ??
            (tongue === null
              ? 'Give the god a tongue first'
              : mortal === null
                ? 'Choose a mortal'
                : undefined)
          }
          onClick={() => teach.mutate()}
        >
          <UserPlus />
          Teach the tongue
        </Button>
      </div>
    </div>
  )
}

function PidginForm({
  firstId,
  blocked,
}: {
  firstId: number
  blocked: string | null
}) {
  const [second, setSecond] = useState<number | null>(null)
  const make = useTongueAction(
    'pidgin:make',
    (_: void) => ({ first_id: firstId, second_id: second ?? 0 }),
    'A pidgin is born'
  )
  const busy = why(blocked, make.isPending)
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <NodePicker
        label='Make a pidgin with'
        value={second}
        onChange={setSecond}
        blocked={busy}
        types={COMMUNITY_TYPES}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || second === null}
        disabledReason={
          busy ?? (second === null ? 'Choose the other community' : undefined)
        }
        onClick={() => make.mutate()}
      >
        <Handshake />
        Make the pidgin
      </Button>
    </div>
  )
}

function LanguageBody({
  languageId,
  data,
  blocked,
}: {
  languageId: number
  data: TongueMechanicsView
  blocked: string | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ProfileCard languageId={languageId} data={data} blocked={blocked} />
      <GrammarCard
        languageId={languageId}
        grammar={data.grammar}
        blocked={blocked}
      />
      <Label variant='overline'>{`Sound changes (${data.changes.length})`}</Label>
      <SoundTimeline changes={data.changes} />
      {data.changes.length === 0 ? (
        <Muted variant='caption'>
          Its words still sound as they were first spoken.
        </Muted>
      ) : (
        <PagedList
          items={data.changes}
          initial={4}
          noun={['change', 'changes']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <ChangeCard change={row} blocked={blocked} />}
        </PagedList>
      )}
      <ChangeForm languageId={languageId} blocked={blocked} />
      <ScriptCard languageId={languageId} data={data} blocked={blocked} />
      <DecipherCard
        languageId={languageId}
        work={data.decipher}
        blocked={blocked}
      />
      <Label variant='overline'>{`Policies on this tongue (${data.policies.length})`}</Label>
      {data.policies.length === 0 ? (
        <Muted variant='caption'>No realm or faith holds a policy on it.</Muted>
      ) : (
        <PagedList
          items={data.policies}
          initial={3}
          noun={['policy', 'policies']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => `${row.holder?.id}-${row.policy}`}
        >
          {(row) => <PolicyCard policy={row} blocked={blocked} />}
        </PagedList>
      )}
      <PolicyForm holderId={null} languageId={languageId} blocked={blocked} />
      <Label variant='overline'>{`Words that shifted (${data.shifts.length})`}</Label>
      {data.shifts.length === 0 ? (
        <Muted variant='caption'>
          Its words still mean what they first meant.
        </Muted>
      ) : (
        <PagedList
          items={data.shifts}
          initial={4}
          noun={['shift', 'shifts']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <ShiftCard shift={row} blocked={blocked} />}
        </PagedList>
      )}
      <VeilForm languageId={languageId} blocked={blocked} />
      {data.sacred_to && (
        <Facts
          items={[
            ['Sacred tongue of', <Ref key='god' node={data.sacred_to.god} />],
            ['Since epoch', String(data.sacred_to.since_epoch)],
          ]}
        />
      )}
    </div>
  )
}

function TonguesBody({
  data,
  type,
  blocked,
}: {
  data: NodeTonguesView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const god = (GOD_KINDS as readonly string[]).includes(data.node.kind)
  const holder = type !== null && HOLDER_TYPES.includes(type)
  const community = type !== null && COMMUNITY_TYPES.includes(type)
  const changes = data.language?.changes.length ?? 0
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Sound changes'
          value={changes}
          icon={GitBranch}
          tone='verdigris'
        />
        <KpiTile
          label='Read of its script'
          value={data.language?.decipher?.progress ?? 0}
          icon={ScrollText}
          tone='info'
        />
        <KpiTile
          label='Policies held'
          value={data.held_policies.length}
          icon={POLICIES.official.icon}
          tone='gold'
        />
        <KpiTile
          label='Sacred tongues known'
          value={data.known_divine.length}
          icon={Sun}
          tone='gold'
        />
      </div>
      {data.language ? (
        <LanguageBody
          languageId={nodeId}
          data={data.language}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>
          The sounds, grammar and script of a tongue live on the tongue’s own
          page.
        </Muted>
      )}
      <Label variant='overline'>{`Policies it holds (${data.held_policies.length})`}</Label>
      {data.held_policies.length === 0 ? (
        <Muted variant='caption'>Holds no policy on any tongue.</Muted>
      ) : (
        <PagedList
          items={data.held_policies}
          initial={3}
          noun={['policy', 'policies']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => `${row.language?.id}-${row.policy}`}
        >
          {(row) => <PolicyCard policy={row} blocked={blocked} />}
        </PagedList>
      )}
      <PolicyForm
        holderId={nodeId}
        languageId={null}
        blocked={
          blocked ??
          (holder
            ? null
            : 'Only a realm, faith, people, town or faction holds a policy on tongues')
        }
      />
      {community ? (
        <PidginForm firstId={nodeId} blocked={blocked} />
      ) : (
        <Muted variant='caption'>A pidgin is made between communities.</Muted>
      )}
      {god ? (
        <DivineCard
          godId={nodeId}
          tongue={data.divine_tongue}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>Sacred tongues belong to gods.</Muted>
      )}
      <Label variant='overline'>{`Sacred tongues it knows (${data.known_divine.length})`}</Label>
      {data.known_divine.length === 0 ? (
        <Muted variant='caption'>Knows no word of a god’s tongue.</Muted>
      ) : (
        <PagedList
          items={data.known_divine}
          initial={6}
          noun={['tongue', 'tongues']}
          className='flex min-w-0 flex-wrap gap-1.5'
          itemKey={(row) => row.id}
        >
          {(row) => (
            <li>
              <Chip icon={Sun}>{row.name}</Chip>
            </li>
          )}
        </PagedList>
      )}
    </div>
  )
}

export function TonguesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeTongues(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-tongues'
      title='Tongues'
      description='The sounds, grammar, scripts and words of tongues, their decipherment, the policies held on them and the sacred tongues of the gods.'
      icon={TONGUE_ICON}
      tone='verdigris'
    >
      <div
        data-surface='TonguesSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the tongues' />
        ) : query.isError ? (
          <EmptyState
            icon={TONGUE_ICON}
            size='inline'
            title='The tongues could not be read'
            description={query.error.message}
          />
        ) : (
          <TonguesBody data={query.data} type={type} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
