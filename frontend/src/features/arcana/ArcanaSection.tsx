import { useState } from 'react'
import {
  Eraser,
  Hourglass,
  PenLine,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react'
import { naturalLawValues, riteEffectKindValues } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
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
import { wordOf } from '@/features/entity/affairs/labels'
import { TextField } from '@/features/entity/economy/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type ChargeView,
  type GrammarView,
  type LabTextView,
  type NodeArcanaView,
  type SpellForm,
  type UpkeepView,
  type VisView,
  useArcanaAction,
  useNodeArcana,
} from './api'
import {
  DURATIONS,
  FORMS,
  LAW_SOURCES,
  MAGIC_ICON,
  RANGES,
  RECHARGES,
  TARGETS,
  TECHNIQUES,
  listed,
  table,
} from './labels'
import { useEntityType } from './model'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

function GrammarCard({
  riteId,
  grammar,
  blocked,
}: {
  riteId: number
  grammar: GrammarView
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'rite_grammar:edit',
    (vars: Edit) => ({ rite_id: riteId, ...vars }),
    'The grammar is set'
  )
  const reset = useArcanaAction(
    'rite_grammar:delete',
    (_: void) => ({ rite_id: riteId }),
    'The grammar returns to its school'
  )
  const busy = why(blocked, edit.isPending, reset.isPending)
  const technique = TECHNIQUES[grammar.technique]
  const form = FORMS[grammar.form]
  return (
    <RecordRow
      icon={technique.icon}
      tone={form.tone}
      title={`${technique.label} ${form.label.toLowerCase()}`}
      caption={`Difficulty ${grammar.difficulty}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => reset.mutate()}
        >
          <RotateCcw />
          Back to its school
        </Button>
      }
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={RANGES[grammar.range].icon}>
          {RANGES[grammar.range].label}
        </Chip>
        <Chip icon={DURATIONS[grammar.duration].icon}>
          {DURATIONS[grammar.duration].label}
        </Chip>
        <Chip icon={TARGETS[grammar.target].icon}>
          {TARGETS[grammar.target].label}
        </Chip>
      </div>
      <Facts
        items={[
          [
            'Paradigm',
            <Ref
              key='paradigm'
              node={grammar.paradigm}
              empty='none; the local theory of magic applies'
            />,
          ],
          [
            'Myth it re-enacts',
            <Ref key='myth' node={grammar.myth} empty='none' />,
          ],
        ]}
      />
      <RecordEditor
        title='Reshape the grammar'
        note='Technique, form, range, duration and target set the difficulty, the price and the backlash of the rite.'
        fields={[
          {
            key: 'technique',
            label: 'Technique',
            kind: 'pick',
            table: table(TECHNIQUES),
          },
          { key: 'form', label: 'Form', kind: 'pick', table: table(FORMS) },
          { key: 'range', label: 'Range', kind: 'pick', table: table(RANGES) },
          {
            key: 'duration',
            label: 'Duration',
            kind: 'pick',
            table: table(DURATIONS),
          },
          {
            key: 'target',
            label: 'Target',
            kind: 'pick',
            table: table(TARGETS),
          },
          {
            key: 'paradigm_entity_id',
            label: 'Paradigm (theory id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'myth_entity_id',
            label: 'Myth (legend id)',
            kind: 'number',
            min: 1,
          },
        ]}
        locked={grammar.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function LabTextCard({
  text,
  blocked,
}: {
  text: LabTextView
  blocked: string | null
}) {
  const bookId = text.book?.id ?? 0
  const edit = useArcanaAction(
    'lab_text:edit',
    (vars: Edit) => ({ book_id: bookId, ...vars }),
    'The lab text is set'
  )
  const remove = useArcanaAction(
    'lab_text:delete',
    (_: void) => ({ book_id: bookId }),
    'The book no longer teaches its rite'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  return (
    <RecordRow
      icon={PenLine}
      tone='info'
      title={<Ref node={text.book} empty='a lost book' />}
      caption={`Written in epoch ${text.epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Strike the rite out
        </Button>
      }
    >
      <Meter label='Fidelity' value={text.fidelity} tone='info' />
      <Facts
        items={[
          ['Rite', <Ref key='rite' node={text.rite} empty='no rite' />],
          ['Author', <Ref key='author' node={text.author} empty='unknown' />],
        ]}
      />
      <RecordEditor
        title='Reshape the lab text'
        note='A truer text is learned more often by the mages who read it.'
        fields={[
          {
            key: 'fidelity',
            label: 'Fidelity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'rite_entity_id',
            label: 'Rite it teaches (rite id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'author_entity_id',
            label: 'Author (mortal id)',
            kind: 'number',
            min: 1,
          },
          { key: 'epoch', label: 'Written in epoch', kind: 'number', min: 0 },
        ]}
        locked={text.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function WriteTextForm({
  riteId,
  blocked,
}: {
  riteId: number
  blocked: string | null
}) {
  const [author, setAuthor] = useState<number | null>(null)
  const write = useArcanaAction(
    'lab_text:write',
    (_: void) => ({ rite_id: riteId, author_id: author ?? 0 }),
    'A lab text is written'
  )
  const busy = why(blocked, write.isPending)
  const missing = author === null ? 'Choose a mage to write it' : null
  return (
    <ForgeCard
      icon={PenLine}
      tone='info'
      title='Write a lab text'
      note='A mage sets the rite down in a book; mages near the book learn it over the epochs.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => write.mutate()}
        >
          <PenLine />
          Write
        </Button>
      }
    >
      <NodePicker
        label='Mage'
        value={author}
        onChange={setAuthor}
        blocked={busy}
        types={['mortal']}
      />
    </ForgeCard>
  )
}

function VisChips({
  holderId,
  vis,
  blocked,
}: {
  holderId: number
  vis: VisView[]
  blocked: string | null
}) {
  const remove = useArcanaAction(
    'vis:delete',
    (form: SpellForm) => ({ holder_id: holderId, form }),
    'The vis is gone'
  )
  const busy = why(blocked, remove.isPending)
  if (vis.length === 0)
    return <Muted variant='caption'>No vis is held here.</Muted>
  return (
    <PagedList
      items={vis}
      initial={8}
      noun={['form', 'forms']}
      className='flex min-w-0 flex-wrap gap-1.5'
      itemKey={(row) => row.form}
    >
      {(row) => {
        const form = FORMS[row.form]
        return (
          <li className='flex items-center gap-1'>
            <Chip icon={form.icon}>{`${form.label} ${row.amount}`}</Chip>
            {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label={`Take away the ${form.label.toLowerCase()} vis`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => remove.mutate(row.form)}
            >
              <Trash2 />
            </Button>
          </li>
        )
      }}
    </PagedList>
  )
}

function VisForm({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [form, setForm] = useState<SpellForm | ''>('')
  const [amount, setAmount] = useState('5')
  const set = useArcanaAction(
    'vis:set',
    (_: void) => ({
      holder_id: holderId,
      form: form as SpellForm,
      amount: Number(amount),
      hold: true,
    }),
    'The vis is held'
  )
  const busy = why(blocked, set.isPending)
  const missing =
    form === ''
      ? 'Choose a form of vis'
      : amount === '' || Number.isNaN(Number(amount))
        ? 'Type an amount'
        : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
      <MindPicker
        label='Form of vis'
        value={form}
        table={table(FORMS)}
        blocked={busy}
        onPick={(value) => setForm(value as SpellForm)}
      />
      <NumberField
        label='Amount'
        value={amount}
        min={0}
        disabled={busy !== null}
        onChange={setAmount}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => set.mutate()}
      >
        <Save />
        Hold this vis
      </Button>
    </div>
  )
}

function WarpingCard({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: NodeArcanaView
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'warping:edit',
    (vars: Edit) => ({ node_id: nodeId, ...vars }),
    'The warping is set'
  )
  const undo = useArcanaAction(
    'warping:delete',
    (_: void) => ({ node_id: nodeId }),
    'The warping is undone'
  )
  const busy = why(blocked, edit.isPending, undo.isPending)
  const warping = data.warping
  return (
    <RecordRow
      icon={Sparkles}
      tone='verdigris'
      title='Warping'
      caption={
        warping
          ? `Stage ${warping.stage} · last touched in epoch ${warping.updated_epoch}`
          : 'Untouched by long exposure to magic'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || warping === null}
          disabledReason={
            busy ?? (warping === null ? 'Nothing to undo' : undefined)
          }
          onClick={() => undo.mutate()}
        >
          <Eraser />
          Undo
        </Button>
      }
    >
      {warping && (
        <Meter label='Warping' value={warping.value} tone='verdigris' />
      )}
      <RecordEditor
        title='Set the warping'
        note='Past its marks, warping touches, then marks, then unmoors the mortal and slows its ageing.'
        fields={[
          { key: 'value', label: 'Warping', kind: 'number', min: 0, max: 100 },
          { key: 'stage', label: 'Stage', kind: 'number', min: 0, max: 3 },
        ]}
        locked={warping?.locked ?? []}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function LongevityCard({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: NodeArcanaView
  blocked: string | null
}) {
  const [form, setForm] = useState<SpellForm | ''>('')
  const begin = useArcanaAction(
    'longevity:begin',
    (_: void) => ({ mortal_id: nodeId, form: form as SpellForm }),
    'Longevity magic begins'
  )
  const edit = useArcanaAction(
    'longevity:edit',
    (vars: Edit) => ({ mortal_id: nodeId, ...vars }),
    'The longevity is set'
  )
  const end = useArcanaAction(
    'longevity:end',
    (_: void) => ({ mortal_id: nodeId }),
    'The longevity magic ends'
  )
  const busy = why(blocked, begin.isPending, edit.isPending, end.isPending)
  const longevity = data.longevity
  if (longevity === null) {
    return (
      <ForgeCard
        icon={Hourglass}
        tone='verdigris'
        title='Begin longevity magic'
        note='Each epoch it burns vis of its form to add years; the mortal comes to need it, and when it lapses the borrowed years fall away.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null || form === ''}
            disabledReason={
              busy ?? (form === '' ? 'Choose the vis it burns' : undefined)
            }
            onClick={() => begin.mutate()}
          >
            <Hourglass />
            Begin
          </Button>
        }
      >
        <MindPicker
          label='Vis it burns'
          value={form}
          table={table(FORMS)}
          blocked={busy}
          onPick={(value) => setForm(value as SpellForm)}
        />
      </ForgeCard>
    )
  }
  return (
    <RecordRow
      icon={Hourglass}
      tone='verdigris'
      title='Longevity magic'
      caption={`Since epoch ${longevity.since_epoch} · ${longevity.years_gained} borrowed years`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => end.mutate()}
        >
          <Eraser />
          End it
        </Button>
      }
    >
      <Meter label='Dependence' value={longevity.dependence} tone='warning' />
      <Facts
        items={[
          ['Vis it burns', FORMS[longevity.form].label],
          ['Dose each epoch', String(longevity.dose)],
          ['Borrowed years', String(longevity.years_gained)],
          ['Epochs lapsed', String(longevity.lapsed_epochs)],
        ]}
      />
      <RecordEditor
        title='Reshape the longevity'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'form',
            label: 'Vis it burns',
            kind: 'pick',
            table: table(FORMS),
          },
          { key: 'dose', label: 'Dose', kind: 'number', min: 0 },
          {
            key: 'dependence',
            label: 'Dependence',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'years_gained',
            label: 'Borrowed years',
            kind: 'number',
            min: 0,
          },
          {
            key: 'lapsed_epochs',
            label: 'Epochs lapsed',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={longevity.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ChargeCard({
  itemId,
  charge,
  blocked,
}: {
  itemId: number
  charge: ChargeView
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'item_charge:edit',
    (vars: { values: Values }) => ({
      item_id: itemId,
      effect: charge.effect,
      ...vars,
    }),
    'The charges are set'
  )
  const busy = why(blocked, edit.isPending)
  const recharge = RECHARGES[charge.recharge]
  return (
    <RecordRow
      icon={Wand2}
      tone='gold'
      title={wordOf(riteEffectKindValues, charge.effect)}
      caption={`Strength ${charge.strength}`}
    >
      <Meter
        label='Charges'
        value={charge.charges}
        max={Math.max(charge.capacity, 1)}
        tone='default'
      />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip
          icon={recharge.icon}
        >{`Recharges ${recharge.label.toLowerCase()}`}</Chip>
        {charge.overuse > 0 && (
          <Chip variant='destructive'>{`Cracked by ${plural(charge.overuse, 'overuse', 'overuses')}`}</Chip>
        )}
      </div>
      <RecordEditor
        title='Set the charges'
        note='An item used with no charge left cracks.'
        fields={[
          { key: 'charges', label: 'Charges', kind: 'number', min: 0 },
          { key: 'capacity', label: 'Capacity', kind: 'number', min: 0 },
          {
            key: 'recharge',
            label: 'Recharge',
            kind: 'pick',
            table: table(RECHARGES),
          },
          { key: 'overuse', label: 'Overuses', kind: 'number', min: 0 },
        ]}
        locked={[]}
        busy={busy}
        saveLabel='Set these values'
        onSave={(values) => edit.mutate({ values })}
        onRelease={() => undefined}
      />
    </RecordRow>
  )
}

function UpkeepCard({
  upkeep,
  blocked,
}: {
  upkeep: UpkeepView
  blocked: string | null
}) {
  const lawId = upkeep.law?.id ?? 0
  const edit = useArcanaAction(
    'law_upkeep:edit',
    (vars: Edit) => ({ law_id: lawId, ...vars }),
    'The upkeep is set'
  )
  const free = useArcanaAction(
    'law_upkeep:delete',
    (_: void) => ({ law_id: lawId }),
    'The law asks no upkeep'
  )
  const dispel = useArcanaAction(
    'enchantment:dispel',
    (_: void) => ({ law_id: lawId }),
    'The law is dispelled'
  )
  const busy = why(blocked, edit.isPending, free.isPending, dispel.isPending)
  const source = LAW_SOURCES[upkeep.source]
  return (
    <RecordRow
      icon={source.icon}
      tone={source.tone}
      title={<Ref node={upkeep.law} empty='a lost law' />}
      caption={`${source.label} · since epoch ${upkeep.since_epoch}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => free.mutate()}
          >
            <Eraser />
            Free it
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => dispel.mutate()}
          >
            <Trash2 />
            Dispel
          </Button>
        </div>
      }
    >
      <Meter
        label='Dispel resistance'
        value={upkeep.dispel_resistance}
        tone='info'
      />
      <Facts
        items={[
          ['Caster', <Ref key='caster' node={upkeep.caster} empty='no one' />],
          ['Essence each epoch', String(upkeep.essence_upkeep)],
          [
            'Vis each epoch',
            upkeep.vis_form
              ? `${upkeep.vis_upkeep} ${FORMS[upkeep.vis_form].label.toLowerCase()}`
              : 'None',
          ],
          ['Unpaid epochs', String(upkeep.unpaid_epochs)],
        ]}
      />
      <RecordEditor
        title='Reshape the upkeep'
        note='A law whose upkeep goes unpaid weakens; an enchantment lapses.'
        fields={[
          {
            key: 'source',
            label: 'Source',
            kind: 'pick',
            table: table(LAW_SOURCES),
          },
          {
            key: 'caster_node_id',
            label: 'Caster (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'essence_upkeep',
            label: 'Essence each epoch',
            kind: 'number',
            min: 0,
          },
          {
            key: 'vis_form',
            label: 'Vis form',
            kind: 'pick',
            table: { none: 'None', ...table(FORMS) },
          },
          {
            key: 'vis_upkeep',
            label: 'Vis each epoch',
            kind: 'number',
            min: 0,
          },
          {
            key: 'dispel_resistance',
            label: 'Dispel resistance',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'unpaid_epochs',
            label: 'Unpaid epochs',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={upkeep.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function EnchantForm({
  casterId,
  blocked,
}: {
  casterId: number
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [effect, setEffect] = useState('')
  const [world, setWorld] = useState<number | null>(null)
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('50')
  const [form, setForm] = useState<SpellForm | ''>('')
  const lay = useArcanaAction(
    'enchantment:lay',
    (_: void) => ({
      caster_id: casterId,
      name: name.trim(),
      effect: effect as (typeof naturalLawValues)[number],
      world_id: world,
      region_id: region,
      strength: Number(strength),
      vis_form: form === '' ? null : form,
    }),
    'A global enchantment is laid'
  )
  const busy = why(blocked, lay.isPending)
  const missing =
    effect === ''
      ? 'Choose the law it makes'
      : world === null && region === null
        ? 'Choose a world or a region'
        : null
  return (
    <ForgeCard
      icon={Wand2}
      tone='gold'
      title='Lay a global enchantment'
      note='A natural law that holds only while its caster pays its upkeep: essence for a god, power for a foreign god, vis for a mage or an order of mages, drawn from the members of the order and from the richest vis held when no form is chosen. Rivals may dispel it.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => lay.mutate()}
        >
          <Wand2 />
          Lay it
        </Button>
      }
    >
      <TextField
        label='Name of the enchantment'
        value={name}
        disabled={busy !== null}
        onChange={setName}
      />
      <MindPicker
        label='Law it makes'
        value={effect}
        table={listed(naturalLawValues.filter((value) => value !== 'none'))}
        blocked={busy}
        onPick={setEffect}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setStrength}
      />
      <NodePicker
        label='Over the world'
        value={world}
        onChange={setWorld}
        blocked={busy}
        kinds={['world']}
      />
      <NodePicker
        label='Or over one region'
        value={region}
        onChange={setRegion}
        blocked={busy}
        types={['region']}
      />
      <MindPicker
        label='Vis that keeps it (mages and orders)'
        value={form}
        table={table(FORMS)}
        blocked={busy}
        onPick={(value) => setForm(value as SpellForm)}
      />
    </ForgeCard>
  )
}

function ArcanaBody({
  data,
  type,
  blocked,
}: {
  data: NodeArcanaView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const kind = data.node.kind
  const god = (GOD_KINDS as readonly string[]).includes(kind)
  const mortal = type === 'mortal'
  const order = type === 'faction' || type === 'cult'
  const total = data.vis.reduce((sum, row) => sum + row.amount, 0)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile label='Vis held' value={total} icon={Sparkles} tone='gold' />
        <KpiTile
          label='Lab texts'
          value={data.lab_texts.length}
          icon={PenLine}
          tone='info'
        />
        <KpiTile
          label='Laws kept'
          value={data.kept.length}
          icon={Wand2}
          tone='verdigris'
        />
        <KpiTile
          label='Warping'
          value={data.warping?.value ?? 0}
          icon={MAGIC_ICON}
          tone='warning'
        />
      </div>
      {data.grammar && (
        <GrammarCard riteId={nodeId} grammar={data.grammar} blocked={blocked} />
      )}
      {type === 'rite' && data.grammar === null && (
        <Muted variant='caption'>
          This rite takes the grammar of its school the next time it is cast or
          edited.
        </Muted>
      )}
      <Label variant='overline'>Lab texts</Label>
      {data.lab_texts.length === 0 ? (
        <Muted variant='caption'>No lab text sets this down.</Muted>
      ) : (
        <PagedList
          items={data.lab_texts}
          initial={3}
          noun={['text', 'texts']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.book?.id ?? 0}
        >
          {(row) => <LabTextCard text={row} blocked={blocked} />}
        </PagedList>
      )}
      {type === 'rite' ? (
        <WriteTextForm riteId={nodeId} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          A lab text is written from a rite's own page.
        </Muted>
      )}
      <Label variant='overline'>Vis</Label>
      <VisChips holderId={nodeId} vis={data.vis} blocked={blocked} />
      <VisForm holderId={nodeId} blocked={blocked} />
      {mortal ? (
        <>
          <WarpingCard nodeId={nodeId} data={data} blocked={blocked} />
          <LongevityCard nodeId={nodeId} data={data} blocked={blocked} />
        </>
      ) : (
        <Muted variant='caption'>
          Warping and longevity magic belong to mortals; other kinds of thing
          hold vis and laws.
        </Muted>
      )}
      {data.charges.length > 0 && (
        <>
          <Label variant='overline'>Enchantments and their charges</Label>
          <PagedList
            items={data.charges}
            initial={3}
            noun={['enchantment', 'enchantments']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.effect}
          >
            {(row) => (
              <ChargeCard itemId={nodeId} charge={row} blocked={blocked} />
            )}
          </PagedList>
        </>
      )}
      {data.upkeep && (
        <>
          <Label variant='overline'>Upkeep of this law</Label>
          <UpkeepCard upkeep={data.upkeep} blocked={blocked} />
        </>
      )}
      <Label variant='overline'>Laws and enchantments kept</Label>
      {data.kept.length === 0 ? (
        <Muted variant='caption'>Keeps no law or enchantment.</Muted>
      ) : (
        <PagedList
          items={data.kept}
          initial={3}
          noun={['law', 'laws']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.law?.id ?? 0}
        >
          {(row) => <UpkeepCard upkeep={row} blocked={blocked} />}
        </PagedList>
      )}
      <EnchantForm
        casterId={nodeId}
        blocked={
          blocked ??
          (god || mortal || order
            ? null
            : 'Only a god, a mage or an order of mages can lay and keep a global enchantment')
        }
      />
    </div>
  )
}

export function ArcanaSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeArcana(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-arcana'
      title='Magic'
      description='The grammar of rites, lab texts, vis, warping, longevity magic, enchanted charges and the laws kept by their casters.'
      icon={MAGIC_ICON}
      tone='verdigris'
    >
      <div data-surface='ArcanaSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Reading the magic' />
        ) : query.isError ? (
          <EmptyState
            icon={MAGIC_ICON}
            size='inline'
            title='The magic could not be read'
            description={query.error.message}
          />
        ) : (
          <ArcanaBody data={query.data} type={type} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
