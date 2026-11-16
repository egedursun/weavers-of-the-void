import { useState } from 'react'
import { Activity, CircleMinus, CirclePlus, Gauge, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  KpiTile,
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
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type AugmentView,
  useMadeAction,
  useNodeAugments,
  useRowDelete,
  useRowEdit,
} from './api'
import {
  AUGMENT_ICON,
  AUGMENT_KINDS,
  AUGMENT_MAKES,
  AUGMENT_SLOTS,
  BODY_PARTS,
  EFFECT_TARGETS,
  MIND_UPKEEPS,
} from './labels'

const SHOWN = 6
const NO_PART = 'whole'
const PARTS = {
  [NO_PART]: {
    label: 'No single part',
    icon: AUGMENT_ICON,
    tone: 'muted' as const,
  },
  ...BODY_PARTS,
}

const AUGMENT_FIELDS: readonly Field[] = [
  {
    key: 'slot',
    label: 'Where it sits',
    kind: 'pick',
    table: table(AUGMENT_SLOTS),
  },
  { key: 'part', label: 'Body part', kind: 'pick', table: table(BODY_PARTS) },
  {
    key: 'kind',
    label: 'What it does',
    kind: 'pick',
    table: table(AUGMENT_KINDS),
  },
  {
    key: 'make',
    label: 'How it is made',
    kind: 'pick',
    table: table(AUGMENT_MAKES),
  },
  { key: 'quality', label: 'Quality', kind: 'number', min: 0, max: 100 },
  {
    key: 'upkeep',
    label: 'What keeps it',
    kind: 'pick',
    table: table(MIND_UPKEEPS),
  },
  {
    key: 'integration',
    label: 'Integration',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'strain',
    label: 'Strain on its bearer',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'installed_by_node_id',
    label: 'Who installed it',
    kind: 'node',
    types: [],
  },
]

const EFFECT_FIELDS: readonly Field[] = [
  {
    key: 'target',
    label: 'What it changes',
    kind: 'pick',
    table: table(EFFECT_TARGETS),
  },
  { key: 'target_key', label: 'Which one, by its key', kind: 'text' },
  { key: 'amount', label: 'By how much', kind: 'number', min: -100, max: 100 },
]

function Effect({
  effect,
  blocked,
}: {
  effect: AugmentView['effects'][number]
  blocked: string | null
}) {
  const target = EFFECT_TARGETS[effect.target]
  const editing = useMadeAction(
    'augment:edit_effect',
    (vars: { values: EditValues; release: string[] }) => ({
      effect_id: effect.id,
      ...vars,
    }),
    'The effect is set so'
  )
  const dropping = useMadeAction(
    'augment:drop_effect',
    (_: void) => ({ effect_id: effect.id }),
    'The augment loses that effect'
  )
  return (
    <RecordRow
      icon={target.icon}
      tone={effect.amount < 0 ? 'danger' : 'success'}
      title={`${target.label}: ${effect.target_key.replaceAll('_', ' ')}`}
      caption={`${effect.amount > 0 ? '+' : ''}${effect.amount}`}
    >
      <RecordEditor
        title='Set this effect'
        note='Values you set are held against the engine until you release them.'
        fields={EFFECT_FIELDS}
        locked={effect.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Take this effect away'
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function Augment({
  augment,
  blocked,
}: {
  augment: AugmentView
  blocked: string | null
}) {
  const kind = AUGMENT_KINDS[augment.kind]
  const [target, setTarget] = useState<string>('skill')
  const [key, setKey] = useState('')
  const [amount, setAmount] = useState('10')
  const editing = useRowEdit('augments', { id: augment.id })
  const removing = useMadeAction(
    'augment:remove',
    (_: void) => ({ augment_id: augment.id }),
    'The augment is taken out'
  )
  const adding = useMadeAction(
    'augment:effect',
    (_: void) => ({
      augment_id: augment.id,
      target: target as AugmentView['effects'][number]['target'],
      key: key.trim(),
      amount: Number(amount) || 0,
    }),
    'The augment gains an effect'
  )
  const struck = useRowDelete('augments', { id: augment.id })
  const noKey = key.trim() ? null : 'Name what the effect changes by its key'
  return (
    <RecordRow
      icon={kind.icon}
      tone={augment.strain >= 40 ? 'warning' : kind.tone}
      title={`${kind.label}, ${augment.part ? BODY_PARTS[augment.part].label.toLowerCase() : AUGMENT_SLOTS[augment.slot].label.toLowerCase()}`}
      caption={`${AUGMENT_MAKES[augment.make].label}, quality ${augment.quality}, integration ${augment.integration}, strain ${augment.strain}, since epoch ${augment.installed_epoch}`}
      aside={
        <Chip icon={MIND_UPKEEPS[augment.upkeep].icon}>
          Kept by {MIND_UPKEEPS[augment.upkeep].label.toLowerCase()}
        </Chip>
      }
    >
      <Ref node={augment.installed_by} empty='installed by no one named' />
      <ul className='flex min-w-0 flex-col gap-2'>
        {augment.effects.map((effect) => (
          <Effect key={effect.id} effect={effect} blocked={blocked} />
        ))}
      </ul>
      <ForgeCard
        icon={CirclePlus}
        tone='success'
        title='Give it an effect'
        note='An effect lifts or lowers a skill, a body function, an attribute, a sense or a resistance of its bearer.'
        columns={3}
        action={
          <StepButton
            icon={CirclePlus}
            label='Add the effect'
            busy={why(blocked ?? noKey, adding.isPending)}
            onClick={() => adding.mutate()}
          />
        }
      >
        <ChoiceField
          label='What it changes'
          value={target}
          table={EFFECT_TARGETS}
          blocked={blocked}
          onPick={setTarget}
        />
        <TextField
          label='Which one, by its key'
          value={key}
          blocked={blocked}
          onChange={setKey}
        />
        <NumberField
          label='By how much'
          value={amount}
          min={-100}
          max={100}
          onChange={setAmount}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this augment'
        note='Values you set are held against the engine until you release them.'
        fields={AUGMENT_FIELDS}
        locked={augment.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={CircleMinus}
          label='Take it out'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike it from the record'
          busy={why(blocked, struck.isPending)}
          onClick={() => struck.mutate()}
        />
      </div>
    </RecordRow>
  )
}

export function AugmentsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeAugments(nodeId)
  const page = useShowMore(query.data?.augments ?? [], SHOWN, SHOWN * 2)
  const [slot, setSlot] = useState<string>('part')
  const [part, setPart] = useState<string>(NO_PART)
  const [kind, setKind] = useState<string>('enhancement')
  const [make, setMake] = useState<string>('made')
  const [quality, setQuality] = useState('50')
  const [surgeon, setSurgeon] = useState<number | null>(null)
  const installing = useMadeAction(
    'augment:install',
    (_: void) => ({
      bearer_id: nodeId,
      slot: slot as AugmentView['slot'],
      part: part === NO_PART ? null : (part as AugmentView['part']),
      kind: kind as AugmentView['kind'],
      make: make as AugmentView['make'],
      quality: Math.min(100, Math.max(0, Number(quality) || 0)),
      surgeon_id: surgeon,
      effects: [],
    }),
    'The augment is installed'
  )
  const view = query.data
  const blocked = readOnlyReason ?? (view && !view.bears ? view.reason : null)
  const partless =
    slot === 'part' && part === NO_PART
      ? 'An augment of a body part names the part'
      : null
  const strain =
    view?.augments.reduce((total, row) => total + row.strain, 0) ?? 0
  return (
    <Section
      id='section-augments'
      title='Augments: what has been added to its body'
      description='Made, rite-bound or grown parts that replace, lift or join a body; each integrates or strains its bearer, needs its upkeep and may be rejected.'
      icon={AUGMENT_ICON}
      tone='info'
    >
      <div
        data-surface='AugmentsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its augments' />
        ) : query.isError ? (
          <EmptyState
            icon={AUGMENT_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Augments borne'
                value={String(query.data.augments.length)}
                icon={AUGMENT_ICON}
                tone='info'
              />
              <KpiTile
                label='Strain they put on it'
                value={String(strain)}
                icon={Activity}
                tone={strain >= 40 ? 'warning' : 'muted'}
              />
              <KpiTile
                label='Can bear augments'
                value={query.data.bears ? 'Yes' : 'No'}
                icon={Gauge}
                tone={query.data.bears ? 'success' : 'muted'}
              />
            </div>
            {query.data.augments.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {page.visible.map((augment) => (
                    <Augment
                      key={augment.id}
                      augment={augment}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={page} />
              </div>
            ) : (
              <EmptyState
                icon={AUGMENT_ICON}
                size='inline'
                title='No augments'
                description={
                  query.data.reason ??
                  `${query.data.node.name} bears none yet; install one below.`
                }
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='info'
              title='Install an augment'
              note='Its surgeon’s skill and its quality set how well it integrates; the law of its realm is set aside by your hand.'
              columns={3}
              action={
                <StepButton
                  icon={CirclePlus}
                  label='Install it'
                  variant='default'
                  busy={why(blocked ?? partless, installing.isPending)}
                  onClick={() => installing.mutate()}
                />
              }
            >
              <ChoiceField
                label='Where it sits'
                value={slot}
                table={AUGMENT_SLOTS}
                blocked={blocked}
                onPick={setSlot}
              />
              <ChoiceField
                label='Body part'
                value={part}
                table={PARTS}
                blocked={blocked}
                onPick={setPart}
              />
              <ChoiceField
                label='What it does'
                value={kind}
                table={AUGMENT_KINDS}
                blocked={blocked}
                onPick={setKind}
              />
              <ChoiceField
                label='How it is made'
                value={make}
                table={AUGMENT_MAKES}
                blocked={blocked}
                onPick={setMake}
              />
              <NumberField
                label='Quality'
                value={quality}
                min={0}
                max={100}
                onChange={setQuality}
              />
              <ThingPicker
                label='Surgeon'
                value={surgeon}
                onChange={setSurgeon}
                blocked={blocked}
                types={['mortal']}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
