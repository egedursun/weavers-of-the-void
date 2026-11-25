import { useState } from 'react'
import {
  Archive,
  Bird,
  Bug,
  CirclePlus,
  Copy,
  HeartPulse,
  Lock,
  Skull,
  Sprout,
  Trash2,
  Undo2,
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
import { COMMODITIES } from '@/features/entity/affairs/labels'
import { TEMPERAMENT_KIND } from '@/features/entity/wilds/anatomyLabels'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction, useProfileEdit } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type GeneBankView,
  type LivingLineView,
  type LivingNodeView,
  type SymbiontView,
  useNodeLiving,
} from './api'
import {
  FERTILITIES,
  LIVING_ICON,
  METABOLISMS,
  METHODS,
  OUTCOMES,
  PLACEMENTS,
  RELATIONS,
  STAGES,
  STANCES,
  TRAITS,
} from './labels'

const SHOWN = 4
const NONE = 'none'
const YES_NO = { true: 'Yes', false: 'No' }
const HOLD =
  'Values you set are held against the engine until you release them.'

type Edit = { values: EditValues; release: string[] }

function lineTable(view: LivingNodeView): Record<string, string> {
  return Object.fromEntries(
    view.every_line.map((row) => [String(row.id), row.name])
  )
}

function lineChoices(view: LivingNodeView) {
  return {
    [NONE]: { label: 'No line', icon: LIVING_ICON, tone: 'muted' as const },
    ...Object.fromEntries(
      view.every_line.map((row) => [
        String(row.id),
        { label: row.name, icon: LIVING_ICON, tone: 'info' as const },
      ])
    ),
  }
}

function lifeFields(view: LivingNodeView): readonly Field[] {
  return [
    {
      key: 'line_id',
      label: 'Line it belongs to',
      kind: 'pick',
      table: lineTable(view),
    },
    {
      key: 'metabolism',
      label: 'How it eats',
      kind: 'pick',
      table: table(METABOLISMS),
    },
    {
      key: 'feed_commodity',
      label: 'What it eats',
      kind: 'pick',
      table: COMMODITIES,
    },
    {
      key: 'feed_per_season',
      label: 'Feed each season',
      kind: 'number',
      min: 0,
    },
    {
      key: 'growth_stage',
      label: 'Stage of growth',
      kind: 'pick',
      table: table(STAGES),
    },
    {
      key: 'size_pct',
      label: 'Size against its design (%)',
      kind: 'number',
      min: 0,
      max: 400,
    },
    {
      key: 'regeneration',
      label: 'Regeneration',
      kind: 'number',
      min: 0,
      max: 100,
    },
    { key: 'health', label: 'Health', kind: 'number', min: 0, max: 100 },
    {
      key: 'temperament',
      label: 'Temperament',
      kind: 'pick',
      table: table(TEMPERAMENT_KIND),
    },
    {
      key: 'bonded_to_node_id',
      label: 'Handler it is bonded to',
      kind: 'node',
      types: [],
    },
    {
      key: 'bond',
      label: 'Bond with its handler',
      kind: 'number',
      min: 0,
      max: 100,
    },
    {
      key: 'fertility',
      label: 'How it breeds',
      kind: 'pick',
      table: table(FERTILITIES),
    },
    {
      key: 'lifespan_years',
      label: 'Lifespan in years',
      kind: 'number',
      min: 0,
    },
    { key: 'age_seasons', label: 'Age in seasons', kind: 'number', min: 0 },
    {
      key: 'designed_by_node_id',
      label: 'Designed by',
      kind: 'node',
      types: [],
    },
  ]
}

const LINE_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name of the line', kind: 'text' },
  {
    key: 'method',
    label: 'How it was made',
    kind: 'pick',
    table: table(METHODS),
  },
  {
    key: 'outcome',
    label: 'How it came out',
    kind: 'pick',
    table: table(OUTCOMES),
  },
  { key: 'stability', label: 'Stability', kind: 'number', min: 0, max: 100 },
  { key: 'generation', label: 'Generation', kind: 'number', min: 0 },
  { key: 'drift_pct', label: 'Drift (%)', kind: 'number', min: 0, max: 100 },
  {
    key: 'fertility',
    label: 'How it breeds',
    kind: 'pick',
    table: table(FERTILITIES),
  },
  {
    key: 'metabolism',
    label: 'How its things eat',
    kind: 'pick',
    table: table(METABOLISMS),
  },
  { key: 'owner_node_id', label: 'Owner of the line', kind: 'node', types: [] },
  { key: 'maker_node_id', label: 'Maker of the line', kind: 'node', types: [] },
  {
    key: 'species_entity_id',
    label: 'Kind of life behind it',
    kind: 'node',
    types: ['species'],
  },
  { key: 'licensed', label: 'Licensed to others', kind: 'pick', table: YES_NO },
  { key: 'escaped', label: 'Loose in the wild', kind: 'pick', table: YES_NO },
]

const SOURCE_FIELDS: readonly Field[] = [
  {
    key: 'organism_node_id',
    label: 'Organism it draws on',
    kind: 'node',
    types: [],
  },
]

const TRAIT_FIELDS: readonly Field[] = [
  {
    key: 'trait',
    label: 'Trait of the line',
    kind: 'pick',
    table: table(TRAITS),
  },
  { key: 'strength', label: 'Strength', kind: 'number', min: -100, max: 100 },
  { key: 'side_effect', label: 'A side effect', kind: 'pick', table: YES_NO },
]

function symbiontFields(view: LivingNodeView): readonly Field[] {
  return [
    {
      key: 'line_id',
      label: 'Line it comes of',
      kind: 'pick',
      table: lineTable(view),
    },
    { key: 'mind_node_id', label: 'Mind it carries', kind: 'node', types: [] },
    {
      key: 'placement',
      label: 'Where it lives',
      kind: 'pick',
      table: table(PLACEMENTS),
    },
    {
      key: 'relation',
      label: 'How it lives with its host',
      kind: 'pick',
      table: table(RELATIONS),
    },
    { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
  ]
}

const BANK_FIELDS: readonly Field[] = [
  {
    key: 'holder_node_id',
    label: 'Holder of the bank',
    kind: 'node',
    types: [],
  },
  { key: 'upkeep', label: 'Upkeep each epoch', kind: 'number', min: 0 },
  { key: 'unpaid_epochs', label: 'Epochs unpaid', kind: 'number', min: 0 },
]

const SAMPLE_FIELDS: readonly Field[] = [
  {
    key: 'organism_node_id',
    label: 'What the sample is of',
    kind: 'node',
    types: [],
  },
  {
    key: 'quality',
    label: 'Quality of the sample',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'taken_epoch', label: 'Taken in epoch', kind: 'number', min: 0 },
]

const STANCE_FIELDS: readonly Field[] = [
  {
    key: 'living_craft_stance',
    label: 'The faith holds living craft',
    kind: 'pick',
    table: table(STANCES),
  },
  {
    key: 'germline_stance',
    label: 'The faith holds changing a line of descent',
    kind: 'pick',
    table: table(STANCES),
  },
  {
    key: 'clone_stance',
    label: 'The faith holds clones',
    kind: 'pick',
    table: table(STANCES),
  },
]

function Trait({
  row,
  blocked,
}: {
  row: LivingLineView['traits'][number]
  blocked: string | null
}) {
  const named = TRAITS[row.trait]
  const editing = useMadeAction(
    'line_part:edit',
    (vars: Edit) => ({
      part: 'trait',
      part_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The trait is set so'
  )
  const dropping = useMadeAction(
    'line_part:delete',
    (_: void) => ({ part: 'trait', part_id: row.id }),
    'The trait is bred out'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={row.side_effect ? 'warning' : (named.tone ?? 'info')}
      title={`${named.label} ${row.strength > 0 ? '+' : ''}${row.strength}`}
      caption={
        row.side_effect
          ? 'A side effect of the making'
          : 'Designed into the line'
      }
    >
      <RecordEditor
        act={editing}
        title='Set this trait'
        note={HOLD}
        fields={TRAIT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={dropping}
        icon={Trash2}
        label='Breed it out'
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function Source({
  row,
  blocked,
}: {
  row: LivingLineView['sources'][number]
  blocked: string | null
}) {
  const dropping = useMadeAction(
    'line_part:delete',
    (_: void) => ({ part: 'source', part_id: row.id }),
    'The source organism is taken from the line'
  )
  const editing = useMadeAction(
    'line_part:edit',
    (vars: Edit) => ({
      part: 'source',
      part_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The source organism is set so'
  )
  return (
    <RecordRow
      icon={Sprout}
      tone='info'
      title={`Drawn from ${row.organism.name}`}
      caption='An organism the line borrows its traits from'
    >
      <Ref node={row.organism} />
      <RecordEditor
        act={editing}
        title='Set this source'
        note={HOLD}
        fields={SOURCE_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={dropping}
        icon={Trash2}
        label={`Take ${row.organism.name} from the line`}
        busy={why(blocked, dropping.isPending)}
        onClick={() => dropping.mutate()}
      />
    </RecordRow>
  )
}

function Line({
  line,
  blocked,
}: {
  line: LivingLineView
  blocked: string | null
}) {
  const traits = useShowMore(line.traits, SHOWN, SHOWN * 2)
  const sources = useShowMore(line.sources, SHOWN, SHOWN * 2)
  const [trait, setTrait] = useState<string>('yield')
  const [strength, setStrength] = useState('30')
  const [organism, setOrganism] = useState<number | null>(null)
  const editing = useMadeAction(
    'line:edit',
    (vars: Edit) => ({
      line_id: line.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The line is set so'
  )
  const loosing = useMadeAction(
    'line:escape',
    (_: void) => ({ line_id: line.id }),
    'The line runs wild'
  )
  const containing = useMadeAction(
    'line:contain',
    (_: void) => ({ line_id: line.id }),
    'The line is held in again'
  )
  const deleting = useMadeAction(
    'line:delete',
    (_: void) => ({ line_id: line.id }),
    'The line is unmade'
  )
  const adding = useMadeAction(
    'line_part:create',
    (_: void) => ({
      owner_id: line.id,
      part: 'trait',
      values: {
        trait,
        strength: Math.min(100, Math.max(-100, Number(strength) || 0)),
      },
    }),
    'The line carries a new trait'
  )
  const sourcing = useMadeAction(
    'line_part:create',
    (_: void) => ({
      owner_id: line.id,
      part: 'source',
      values: { organism_node_id: organism ?? 0 },
    }),
    'The line draws on a new organism'
  )
  const method = METHODS[line.method]
  const outcome = OUTCOMES[line.outcome]
  const noSpecies = line.species
    ? null
    : 'A line with no kind of life behind it has nowhere wild to go'
  const notLoose = line.escaped ? null : 'It has not got loose'
  const noOrganism = organism === null ? 'Choose the organism' : null
  return (
    <RecordRow
      icon={method.icon}
      tone={line.escaped ? 'danger' : (outcome.tone ?? 'info')}
      title={line.name}
      caption={`${method.label}, ${outcome.label.toLowerCase()}; stability ${line.stability}, generation ${line.generation}, drift ${line.drift_pct}%, ${line.living_count} living, founded in epoch ${line.founded_epoch}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip icon={FERTILITIES[line.fertility].icon}>
            {FERTILITIES[line.fertility].label}
          </Chip>
          <Chip icon={METABOLISMS[line.metabolism].icon}>
            {METABOLISMS[line.metabolism].label}
          </Chip>
          {line.licensed ? <Chip icon={Lock}>Licensed</Chip> : null}
          {line.escaped ? <Chip icon={Bird}>Loose in the wild</Chip> : null}
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={line.owner} empty='owned by no one' />
        <Ref node={line.maker} empty='made by no one named' />
        <Ref node={line.species} empty='no kind of life behind it' />
        {line.drifted_from_name ? (
          <Chip icon={Sprout}>Drifted from {line.drifted_from_name}</Chip>
        ) : null}
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {traits.visible.map((row) => (
          <Trait key={row.id} row={row} blocked={blocked} />
        ))}
      </ul>
      <ShowMore state={traits} />
      <ul className='flex min-w-0 flex-col gap-2'>
        {sources.visible.map((row) => (
          <Source key={row.id} row={row} blocked={blocked} />
        ))}
      </ul>
      <ShowMore state={sources} />
      <ForgeCard
        icon={CirclePlus}
        tone='success'
        title='Give it a trait'
        note='Each trait makes the line less stable.'
        columns={2}
        action={
          <StepButton
            act={adding}
            icon={CirclePlus}
            label='Add the trait'
            busy={why(blocked, adding.isPending)}
            onClick={() => adding.mutate()}
          />
        }
      >
        <ChoiceField
          label='Trait of the line'
          value={trait}
          table={TRAITS}
          blocked={blocked}
          onPick={setTrait}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={-100}
          max={100}
          onChange={setStrength}
        />
      </ForgeCard>
      <ForgeCard
        icon={CirclePlus}
        tone='info'
        title='Draw on another organism'
        note='A line borrows its traits from the organisms it is made from.'
        columns={2}
        action={
          <StepButton
            act={sourcing}
            icon={CirclePlus}
            label='Add the organism'
            busy={why(blocked ?? noOrganism, sourcing.isPending)}
            onClick={() => sourcing.mutate()}
          />
        }
      >
        <ThingPicker
          label='Organism it draws on'
          value={organism}
          onChange={setOrganism}
          blocked={blocked}
        />
      </ForgeCard>
      <RecordEditor
        act={editing}
        title='Set this line'
        note={HOLD}
        fields={LINE_FIELDS}
        locked={line.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={loosing}
          icon={Bird}
          label='Let it loose'
          busy={why(blocked ?? noSpecies, loosing.isPending)}
          onClick={() => loosing.mutate()}
        />
        <StepButton
          act={containing}
          icon={Undo2}
          label='Hunt it down and hold it in'
          busy={why(blocked ?? notLoose, containing.isPending)}
          onClick={() => containing.mutate()}
        />
        <StepButton
          act={deleting}
          icon={Trash2}
          label='Unmake the line'
          busy={why(blocked, deleting.isPending)}
          onClick={() => deleting.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Symbiont({
  row,
  view,
  blocked,
}: {
  row: SymbiontView
  view: LivingNodeView
  blocked: string | null
}) {
  const relation = RELATIONS[row.relation]
  const editing = useMadeAction(
    'symbiont:edit',
    (vars: Edit) => ({
      symbiont_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'What lives within is set so'
  )
  const removing = useMadeAction(
    'symbiont:remove',
    (_: void) => ({ symbiont_id: row.id }),
    'What lived within is taken out'
  )
  return (
    <RecordRow
      icon={PLACEMENTS[row.placement].icon}
      tone={relation.tone ?? 'info'}
      title={`${row.line_name ?? 'An unnamed line'}, ${PLACEMENTS[row.placement].label.toLowerCase()}`}
      caption={`${relation.label}, strength ${row.strength}, since epoch ${row.since_epoch}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={row.host} />
        <Ref node={row.mind} empty='carries no mind of its own' />
      </div>
      <RecordEditor
        act={editing}
        title='Set what lives within'
        note={HOLD}
        fields={symbiontFields(view)}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Take it out'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Sample({
  row,
  nodeId,
  blocked,
}: {
  row: GeneBankView['samples'][number]
  nodeId: number
  blocked: string | null
}) {
  const editing = useMadeAction(
    'sample:edit',
    (vars: Edit) => ({
      part: 'sample',
      part_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The sample is set so'
  )
  const dropping = useMadeAction(
    'sample:delete',
    (_: void) => ({ part: 'sample', part_id: row.id }),
    'The sample is taken from the bank'
  )
  const raising = useMadeAction(
    'sample:raise',
    (_: void) => ({ sample_id: row.id, maker_id: nodeId }),
    'A line is raised from the sample'
  )
  return (
    <RecordRow
      icon={Archive}
      tone='info'
      title={`A sample of ${row.organism.name}`}
      caption={`quality ${row.quality}, taken in epoch ${row.taken_epoch}`}
    >
      <Ref node={row.organism} />
      <RecordEditor
        act={editing}
        title='Set this sample'
        note={HOLD}
        fields={SAMPLE_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={raising}
          icon={Sprout}
          label='Raise a line from it'
          busy={why(blocked, raising.isPending)}
          onClick={() => raising.mutate()}
        />
        <StepButton
          act={dropping}
          icon={Trash2}
          label='Take it out of the bank'
          busy={why(blocked, dropping.isPending)}
          onClick={() => dropping.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Bank({
  bank,
  nodeId,
  blocked,
}: {
  bank: GeneBankView
  nodeId: number
  blocked: string | null
}) {
  const samples = useShowMore(bank.samples, SHOWN, SHOWN * 2)
  const [organism, setOrganism] = useState<number | null>(null)
  const editing = useMadeAction(
    'bank:edit',
    (vars: Edit) => ({
      structure_id: bank.structure.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The bank is set so'
  )
  const closing = useMadeAction(
    'bank:delete',
    (_: void) => ({ structure_id: bank.structure.id }),
    'The bank of life is closed'
  )
  const sampling = useMadeAction(
    'sample:create',
    (_: void) => ({
      owner_id: bank.structure.id,
      part: 'sample',
      values: { organism_node_id: organism ?? 0, quality: 80 },
    }),
    'The bank keeps a new sample'
  )
  const noOrganism = organism === null ? 'Choose what to sample' : null
  return (
    <RecordRow
      icon={Archive}
      tone={bank.unpaid_epochs ? 'warning' : 'verdigris'}
      title={`The bank of life in ${bank.structure.name}`}
      caption={`${bank.samples.length} kept, upkeep ${bank.upkeep} each epoch, ${bank.unpaid_epochs} epochs unpaid`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={bank.structure} />
        <Ref node={bank.holder} empty='held by no one' />
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {samples.visible.map((row) => (
          <Sample key={row.id} row={row} nodeId={nodeId} blocked={blocked} />
        ))}
      </ul>
      <ShowMore state={samples} />
      <ForgeCard
        icon={CirclePlus}
        tone='verdigris'
        title='Keep a sample'
        note='A bank keeps the traits of what it holds; losing the bank loses them.'
        columns={2}
        action={
          <StepButton
            act={sampling}
            icon={CirclePlus}
            label='Keep the sample'
            busy={why(blocked ?? noOrganism, sampling.isPending)}
            onClick={() => sampling.mutate()}
          />
        }
      >
        <ThingPicker
          label='What to sample'
          value={organism}
          onChange={setOrganism}
          blocked={blocked}
        />
      </ForgeCard>
      <RecordEditor
        act={editing}
        title='Set this bank'
        note={HOLD}
        fields={BANK_FIELDS}
        locked={bank.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={closing}
        icon={Trash2}
        label='Close the bank'
        busy={why(blocked, closing.isPending)}
        onClick={() => closing.mutate()}
      />
    </RecordRow>
  )
}

function Profile({
  view,
  nodeId,
  blocked,
}: {
  view: LivingNodeView
  nodeId: number
  blocked: string | null
}) {
  const [metabolism, setMetabolism] = useState<string>('feeding')
  const [lifespan, setLifespan] = useState('40')
  const [line, setLine] = useState<string>(NONE)
  const editing = useMadeAction(
    'living:edit',
    (vars: Edit) => ({
      thing_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'Its life is set so'
  )
  const giving = useMadeAction(
    'living:create',
    (_: void) => ({
      thing_id: nodeId,
      line_id: line === NONE ? null : Number(line),
      metabolism: metabolism as LivingNodeView['lines'][number]['metabolism'],
      lifespan: Math.max(1, Number(lifespan) || 1),
    }),
    'It lives'
  )
  const ending = useMadeAction(
    'living:end',
    (_: void) => ({ thing_id: nodeId }),
    'Its life ends'
  )
  const unmaking = useMadeAction(
    'living:delete',
    (_: void) => ({ thing_id: nodeId }),
    'It is no longer a living thing'
  )
  const life = view.profile
  if (!life) {
    return (
      <ForgeCard
        icon={HeartPulse}
        tone='success'
        title='Bring it to life'
        note={
          view.alive_reason ??
          'A living thing eats, grows, heals, ages, breeds and dies.'
        }
        columns={3}
        action={
          <StepButton
            act={giving}
            icon={HeartPulse}
            label='Give it life'
            variant='default'
            busy={why(blocked ?? view.alive_reason, giving.isPending)}
            onClick={() => giving.mutate()}
          />
        }
      >
        <ChoiceField
          label='How it eats'
          value={metabolism}
          table={METABOLISMS}
          blocked={blocked ?? view.alive_reason}
          onPick={setMetabolism}
        />
        <NumberField
          label='Lifespan in years'
          value={lifespan}
          min={1}
          onChange={setLifespan}
        />
        <ChoiceField
          label='Line it belongs to'
          value={line}
          table={lineChoices(view)}
          blocked={blocked ?? view.alive_reason}
          onPick={setLine}
        />
      </ForgeCard>
    )
  }
  const stage = STAGES[life.growth_stage]
  const temper = life.temperament ? TEMPERAMENT_KIND[life.temperament] : null
  const dead = life.growth_stage === 'dead' ? 'It is already dead' : null
  return (
    <RecordRow
      icon={stage.icon}
      tone={stage.tone ?? 'info'}
      title={`${stage.label}, health ${life.health}`}
      caption={`size ${life.size_pct}% of its design, regeneration ${life.regeneration}, ${life.age_seasons} seasons old of a lifespan of ${life.lifespan_years} years, alive since epoch ${life.planted_epoch}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip icon={METABOLISMS[life.metabolism].icon}>
            {METABOLISMS[life.metabolism].label}
            {life.feed_commodity
              ? `: ${life.feed_per_season} ${COMMODITIES[life.feed_commodity] ?? life.feed_commodity} each season`
              : ''}
          </Chip>
          <Chip icon={FERTILITIES[life.fertility].icon}>
            {FERTILITIES[life.fertility].label}
          </Chip>
          {temper ? <Chip icon={temper.icon}>{temper.label}</Chip> : null}
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Chip icon={LIVING_ICON}>Line: {life.line_name ?? 'none'}</Chip>
        <Chip icon={HeartPulse}>Bond {life.bond}</Chip>
        <Ref node={life.bonded_to} empty='bonded to no handler' />
        <Ref node={life.designed_by} empty='designed by no one named' />
      </div>
      <RecordEditor
        act={editing}
        title='Set its life'
        note={HOLD}
        fields={lifeFields(view)}
        locked={life.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={ending}
          icon={Skull}
          label='End its life'
          busy={why(blocked ?? dead, ending.isPending)}
          onClick={() => ending.mutate()}
        />
        <StepButton
          act={unmaking}
          icon={Trash2}
          label='Make it no longer a living thing'
          busy={why(blocked, unmaking.isPending)}
          onClick={() => unmaking.mutate()}
        />
      </div>
    </RecordRow>
  )
}

export function LivingSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeLiving(nodeId)
  const lines = useShowMore(query.data?.lines ?? [], SHOWN, SHOWN * 2)
  const symbionts = useShowMore(query.data?.symbionts ?? [], SHOWN, SHOWN * 2)
  const banks = useShowMore(query.data?.banks ?? [], SHOWN, SHOWN * 2)
  const kin = useShowMore(
    [...(query.data?.clone_of ?? []), ...(query.data?.clones ?? [])],
    SHOWN * 2,
    SHOWN * 4
  )
  const [name, setName] = useState('')
  const [method, setMethod] = useState<string>('selective_breeding')
  const [fertility, setFertility] = useState<string>('breeds_true')
  const [hostLine, setHostLine] = useState<string>(NONE)
  const [placement, setPlacement] = useState<string>('skin')
  const [relation, setRelation] = useState<string>('mutual')
  const [holder, setHolder] = useState<number | null>(null)
  const stances = useProfileEdit(nodeId, 'cult_doctrines')
  const making = useMadeAction(
    'line:create',
    (_: void) => ({
      name: name.trim(),
      method: method as LivingLineView['method'],
      maker_id: nodeId,
      fertility: fertility as LivingLineView['fertility'],
    }),
    'A living line comes to be'
  )
  const hosting = useMadeAction(
    'symbiont:host',
    (_: void) => ({
      host_id: nodeId,
      line_id: hostLine === NONE ? null : Number(hostLine),
      placement: placement as SymbiontView['placement'],
      relation: relation as SymbiontView['relation'],
    }),
    'Something lives within it now'
  )
  const banking = useMadeAction(
    'bank:create',
    (_: void) => ({ structure_id: nodeId, holder_id: holder }),
    'A bank of life is kept here now'
  )
  const cloning = useMadeAction(
    'clone:create',
    (_: void) => ({ source_id: nodeId }),
    'A clone is grown'
  )
  const view = query.data
  const blocked = readOnlyReason
  const unnamed = name.trim() ? null : 'Name the line'
  const notMortal = view?.clone_reason ?? null
  const kept = view?.banks.some((bank) => bank.structure.id === nodeId)
    ? 'A bank of life is kept here already'
    : (view?.alive_reason ?? null)
  const loose = view?.lines.filter((line) => line.escaped).length ?? 0
  return (
    <Section
      id='section-living'
      title='Living craft: what is alive, bred, banked and lives within'
      description='Living things eat, grow, heal, age, breed and die; lines are made, drift and escape; banks keep traits; symbionts live within hosts; clones are grown from bodies.'
      icon={LIVING_ICON}
      tone='success'
    >
      <div data-surface='LivingSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading its living craft' />
        ) : query.isError ? (
          <EmptyState
            icon={LIVING_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Lines held or made'
                value={String(query.data.lines.length)}
                icon={LIVING_ICON}
                tone='success'
              />
              <KpiTile
                label='Loose in the wild'
                value={String(loose)}
                icon={Bird}
                tone={loose ? 'danger' : 'muted'}
              />
              <KpiTile
                label='Living within'
                value={String(query.data.symbionts.length)}
                icon={Bug}
                tone='info'
              />
              <KpiTile
                label='Clones and sources'
                value={String(
                  query.data.clone_of.length + query.data.clones.length
                )}
                icon={Copy}
                tone='gold'
              />
            </div>
            <Profile view={query.data} nodeId={nodeId} blocked={blocked} />
            {query.data.lines.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {lines.visible.map((line) => (
                    <Line key={line.id} line={line} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={lines} />
              </div>
            ) : (
              <EmptyState
                icon={LIVING_ICON}
                size='inline'
                title='No living lines'
                description={`${query.data.node.name} holds and has made none yet; make one below.`}
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='success'
              title='Make a living line'
              note={`Made by ${query.data.node.name}; give it traits and organisms once it stands.`}
              columns={3}
              action={
                <StepButton
                  act={making}
                  icon={CirclePlus}
                  label='Make the line'
                  variant='default'
                  busy={why(blocked ?? unnamed, making.isPending)}
                  onClick={() => making.mutate()}
                />
              }
            >
              <TextField
                label='Name of the line'
                value={name}
                blocked={blocked}
                onChange={setName}
              />
              <ChoiceField
                label='How it is made'
                value={method}
                table={METHODS}
                blocked={blocked}
                onPick={setMethod}
              />
              <ChoiceField
                label='How it breeds'
                value={fertility}
                table={FERTILITIES}
                blocked={blocked}
                onPick={setFertility}
              />
            </ForgeCard>
            <ul className='flex min-w-0 flex-col gap-2'>
              {symbionts.visible.map((row) => (
                <Symbiont
                  key={row.id}
                  row={row}
                  view={query.data}
                  blocked={blocked}
                />
              ))}
            </ul>
            <ShowMore state={symbionts} />
            <ForgeCard
              icon={Bug}
              tone='info'
              title='Set something to live within it'
              note='A host gains what lives within and pays its upkeep; taking it out harms by where it lived.'
              columns={3}
              action={
                <StepButton
                  act={hosting}
                  icon={CirclePlus}
                  label='Let it live within'
                  busy={why(blocked, hosting.isPending)}
                  onClick={() => hosting.mutate()}
                />
              }
            >
              <ChoiceField
                label='Line it comes of'
                value={hostLine}
                table={lineChoices(query.data)}
                blocked={blocked}
                onPick={setHostLine}
              />
              <ChoiceField
                label='Where it lives'
                value={placement}
                table={PLACEMENTS}
                blocked={blocked}
                onPick={setPlacement}
              />
              <ChoiceField
                label='How it lives with its host'
                value={relation}
                table={RELATIONS}
                blocked={blocked}
                onPick={setRelation}
              />
            </ForgeCard>
            <ul className='flex min-w-0 flex-col gap-2'>
              {banks.visible.map((bank) => (
                <Bank
                  key={bank.structure.id}
                  bank={bank}
                  nodeId={nodeId}
                  blocked={blocked}
                />
              ))}
            </ul>
            <ShowMore state={banks} />
            <ForgeCard
              icon={Archive}
              tone='verdigris'
              title='Keep a bank of life here'
              note='A bank keeps samples of living things so their traits are never lost.'
              columns={2}
              action={
                <StepButton
                  act={banking}
                  icon={CirclePlus}
                  label='Found the bank'
                  busy={why(blocked ?? kept, banking.isPending)}
                  onClick={() => banking.mutate()}
                />
              }
            >
              <ThingPicker
                label='Holder who pays its upkeep'
                value={holder}
                onChange={setHolder}
                blocked={blocked ?? kept}
              />
            </ForgeCard>
            <div className='flex min-w-0 flex-col gap-2'>
              <ul className='flex min-w-0 flex-wrap gap-2'>
                {kin.visible.map((node) => (
                  <li key={node.id} className='flex min-w-0 items-center gap-2'>
                    <Chip icon={Copy}>
                      {query.data.clone_of.some((row) => row.id === node.id)
                        ? 'Grown from'
                        : 'Clone'}
                    </Chip>
                    <Ref node={node} />
                  </li>
                ))}
              </ul>
              <ShowMore state={kin} />
              <StepButton
                act={cloning}
                icon={Copy}
                label='Grow a clone of this body'
                busy={why(blocked ?? notMortal, cloning.isPending)}
                onClick={() => cloning.mutate()}
              />
            </div>
            {query.data.stances ? (
              <RecordRow
                icon={STANCES[query.data.stances.living_craft_stance].icon}
                tone={
                  STANCES[query.data.stances.living_craft_stance].tone ?? 'info'
                }
                title={`This faith holds living craft ${STANCES[query.data.stances.living_craft_stance].label.toLowerCase()}`}
                caption={`changing a line of descent: ${STANCES[query.data.stances.germline_stance].label.toLowerCase()}; clones: ${STANCES[query.data.stances.clone_stance].label.toLowerCase()}`}
              >
                <RecordEditor
                  act={stances}
                  title='Set the faith’s stances on living craft'
                  note={HOLD}
                  fields={STANCE_FIELDS}
                  locked={[]}
                  busy={why(blocked, stances.isPending)}
                  onSave={(values) => stances.mutate({ values, release: [] })}
                  onRelease={(keys) =>
                    stances.mutate({ values: {}, release: keys })
                  }
                />
              </RecordRow>
            ) : null}
          </>
        )}
      </div>
    </Section>
  )
}
