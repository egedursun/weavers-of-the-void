import { useState } from 'react'
import { CirclePlus, Hand, Trash2, Unlock } from 'lucide-react'
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
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type OuterAgencyView,
  type OuterHeraldView,
  type OuterIncursionView,
  type OuterPactView,
  type OuterPlanView,
  type OuterRelationView,
  type OuterSealView,
  useOuterAgency,
} from './api'
import {
  FATES,
  GOALS,
  HERALD_ICON,
  OUTER_AGENCY_ICON,
  PACT_ICON,
  PLAN_STATES,
  PRICES,
  RELATIONS,
  SEAL_ICON,
  SEAL_KINDS,
  STAGES,
} from './labels'

const SHOWN = 4
const HOLD =
  'Values you set are held against the engine until you release them.'
const MORTALS = ['mortal'] as const
const REGIONS = ['region'] as const
const BEINGS = ['outer_being'] as const

type Edit = { values: EditValues; release: string[] }

const PLAN_FIELDS: readonly Field[] = [
  { key: 'goal', label: 'Aim', kind: 'pick', table: table(GOALS) },
  { key: 'progress', label: 'Progress', kind: 'number', min: 0, max: 100 },
  { key: 'stage', label: 'Stage reached', kind: 'number', min: 0, max: 20 },
  { key: 'state', label: 'State', kind: 'pick', table: table(PLAN_STATES) },
  { key: 'target_node_id', label: 'Its target', kind: 'node', types: [] },
]
const HERALD_FIELDS: readonly Field[] = [
  { key: 'zeal', label: 'Zeal', kind: 'number', min: 0, max: 100 },
  {
    key: 'outer_entity_id',
    label: 'Being it serves',
    kind: 'node',
    types: BEINGS,
  },
]
const INCURSION_FIELDS: readonly Field[] = [
  { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
  { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
  {
    key: 'region_entity_id',
    label: 'Land it presses into',
    kind: 'node',
    types: REGIONS,
  },
]
const PACT_FIELDS: readonly Field[] = [
  { key: 'price', label: 'Price', kind: 'pick', table: table(PRICES) },
  {
    key: 'paid',
    label: 'Paid',
    kind: 'pick',
    table: { true: 'Paid', false: 'Owed' },
  },
]
const RELATION_FIELDS: readonly Field[] = [
  { key: 'relation', label: 'Stance', kind: 'pick', table: table(RELATIONS) },
]
const SEAL_FIELDS: readonly Field[] = [
  { key: 'kind', label: 'Kind', kind: 'pick', table: table(SEAL_KINDS) },
  { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
  { key: 'sealer_node_id', label: 'Sealed by', kind: 'node', types: [] },
]

function Plan({
  row,
  blocked,
}: {
  row: OuterPlanView
  blocked: string | null
}) {
  const goal = GOALS[row.goal]
  const editing = useMadeAction(
    'outer_plan:edit',
    (vars: Edit) => ({
      plan_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The plan is set'
  )
  const removing = useMadeAction(
    'outer_plan:delete',
    (_: void) => ({ plan_id: row.id }),
    'The plan is undone'
  )
  return (
    <RecordRow
      icon={goal.icon}
      tone={PLAN_STATES[row.state].tone ?? 'warning'}
      title={`${goal.label}: ${PLAN_STATES[row.state].label.toLowerCase()}, ${row.progress} of 100`}
      caption={`stage ${row.stage} of ${row.stages}; begun in epoch ${row.started_epoch}${row.sign_epoch !== null ? `; last sign in epoch ${row.sign_epoch}` : '; no sign shown yet'}`}
    >
      <Ref node={row.target} empty='no target named' />
      <RecordEditor
        act={editing}
        title='Set the plan'
        note={HOLD}
        fields={PLAN_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Undo it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Herald({
  row,
  blocked,
}: {
  row: OuterHeraldView
  blocked: string | null
}) {
  const editing = useMadeAction(
    'outer_herald:edit',
    (vars: Edit) => ({
      herald_id: row.herald.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The herald is set'
  )
  const freeing = useMadeAction(
    'outer_herald:release',
    (_: void) => ({ herald_id: row.herald.id }),
    'The herald is freed'
  )
  return (
    <RecordRow
      icon={HERALD_ICON}
      tone='danger'
      title={`${row.herald.name} serves it with zeal ${row.zeal}`}
      caption={`bound in epoch ${row.bound_epoch}`}
    >
      <Ref node={row.herald} empty='no herald named' />
      <RecordEditor
        act={editing}
        title='Set the herald'
        note={HOLD}
        fields={HERALD_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={freeing}
        icon={Unlock}
        label='Free them'
        busy={why(blocked, freeing.isPending)}
        onClick={() => freeing.mutate()}
      />
    </RecordRow>
  )
}

function Incursion({
  row,
  blocked,
}: {
  row: OuterIncursionView
  blocked: string | null
}) {
  const stage = STAGES[row.stage]
  const editing = useMadeAction(
    'outer_incursion:edit',
    (vars: Edit) => ({
      incursion_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The incursion is set'
  )
  const ending = useMadeAction(
    'outer_incursion:end',
    (_: void) => ({ incursion_id: row.id }),
    'The incursion is driven back'
  )
  const over =
    row.ended_epoch !== null ? 'It has already been driven back' : null
  return (
    <RecordRow
      icon={stage.icon}
      tone={stage.tone ?? 'warning'}
      title={`${stage.label}, strength ${row.strength}${row.region ? ` in ${row.region.name}` : ''}`}
      caption={`began in epoch ${row.started_epoch}${row.ended_epoch !== null ? `, ended in epoch ${row.ended_epoch}` : row.rift_id !== null ? ', through a rift' : ', with no rift'}`}
    >
      <RecordEditor
        act={editing}
        title='Set the incursion'
        note={HOLD}
        fields={INCURSION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={ending}
        icon={Hand}
        label='Drive it back'
        busy={why(blocked ?? over, ending.isPending)}
        onClick={() => ending.mutate()}
      />
    </RecordRow>
  )
}

function Pact({
  row,
  blocked,
}: {
  row: OuterPactView
  blocked: string | null
}) {
  const editing = useMadeAction(
    'outer_pact:edit',
    (vars: Edit) => ({
      pact_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The bargain is set'
  )
  const voiding = useMadeAction(
    'outer_pact:void',
    (_: void) => ({ pact_id: row.id }),
    'The bargain is voided'
  )
  return (
    <RecordRow
      icon={PRICES[row.price].icon}
      tone={PRICES[row.price].tone ?? 'danger'}
      title={`${row.holder.name} paid with ${PRICES[row.price].label.toLowerCase()}${row.paid ? '' : ' (still owed)'}`}
      caption={`struck in epoch ${row.struck_epoch}; ${row.power_id !== null ? 'it gave them a bonded power' : 'it gave no power that remains'}`}
    >
      <Ref node={row.holder} empty='no one named' />
      <RecordEditor
        act={editing}
        title='Set the bargain'
        note={HOLD}
        fields={PACT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={voiding}
        icon={Trash2}
        label='Void it'
        busy={why(blocked, voiding.isPending)}
        onClick={() => voiding.mutate()}
      />
    </RecordRow>
  )
}

function Relation({
  row,
  beingId,
  blocked,
}: {
  row: OuterRelationView
  beingId: number
  blocked: string | null
}) {
  const pair = { being_id: beingId, other_id: row.other.id }
  const editing = useMadeAction(
    'outer_relation:edit',
    (vars: Edit) => ({
      ...pair,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The stance is set'
  )
  const removing = useMadeAction(
    'outer_relation:delete',
    (_: void) => pair,
    'The stance is undone'
  )
  return (
    <RecordRow
      icon={RELATIONS[row.relation].icon}
      tone={RELATIONS[row.relation].tone ?? 'muted'}
      title={`${RELATIONS[row.relation].label} ${row.other.name}`}
      caption={`since epoch ${row.since_epoch}`}
    >
      <Ref node={row.other} empty='no being named' />
      <RecordEditor
        act={editing}
        title='Set the stance'
        note={HOLD}
        fields={RELATION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Undo it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Seal({
  row,
  blocked,
}: {
  row: OuterSealView
  blocked: string | null
}) {
  const editing = useMadeAction(
    'outer_seal:edit',
    (vars: Edit) => ({
      seal_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The seal is set'
  )
  const breaking = useMadeAction(
    'outer_seal:break',
    (_: void) => ({ seal_id: row.id }),
    'The seal is broken'
  )
  const broken = row.broken_epoch !== null ? 'It is already broken' : null
  return (
    <RecordRow
      icon={SEAL_KINDS[row.kind].icon}
      tone={
        row.broken_epoch !== null
          ? 'muted'
          : (SEAL_KINDS[row.kind].tone ?? 'info')
      }
      title={`${SEAL_KINDS[row.kind].label}, strength ${row.strength}${row.sealer ? ` by ${row.sealer.name}` : ''}`}
      caption={`set in epoch ${row.sealed_epoch}${row.broken_epoch !== null ? `, broken in epoch ${row.broken_epoch}` : '; it weakens each epoch and breaks when the being outweighs it'}`}
    >
      <RecordEditor
        act={editing}
        title='Set the seal'
        note={HOLD}
        fields={SEAL_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={breaking}
        icon={Unlock}
        label='Break it'
        busy={why(blocked ?? broken, breaking.isPending)}
        onClick={() => breaking.mutate()}
      />
    </RecordRow>
  )
}

function Listing<T>({
  rows,
  render,
  empty,
}: {
  rows: T[]
  render: (row: T) => React.ReactNode
  empty: { title: string; description: string }
}) {
  const state = useShowMore(rows, SHOWN, SHOWN)
  if (!rows.length)
    return (
      <EmptyState
        icon={OUTER_AGENCY_ICON}
        size='inline'
        title={empty.title}
        description={empty.description}
      />
    )
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {state.visible.map(render)}
      </ul>
      <ShowMore state={state} />
    </>
  )
}

function Forges({
  view,
  beingId,
  blocked,
}: {
  view: OuterAgencyView
  beingId: number
  blocked: string | null
}) {
  const [goal, setGoal] = useState<string>('feed')
  const [target, setTarget] = useState<number | null>(null)
  const [progress, setProgress] = useState('0')
  const [herald, setHerald] = useState<number | null>(null)
  const [zeal, setZeal] = useState('50')
  const [region, setRegion] = useState<number | null>(null)
  const [holder, setHolder] = useState<number | null>(null)
  const [price, setPrice] = useState<string>('sanity')
  const [other, setOther] = useState<number | null>(null)
  const [relation, setRelation] = useState<string>('rival')
  const [sealKind, setSealKind] = useState<string>('seal')
  const [strength, setStrength] = useState('60')
  const ended =
    view.fate === 'starved' || view.fate === 'destroyed'
      ? 'It is no more'
      : null
  const stop = blocked ?? ended
  const aiming = useMadeAction(
    'outer_plan:set',
    (_: void) => ({
      being_id: beingId,
      goal: goal as OuterPlanView['goal'],
      target_id: target,
      progress: Math.max(0, Math.min(100, Number(progress) || 0)),
    }),
    'It works toward a new aim'
  )
  const binding = useMadeAction(
    'outer_herald:bind',
    (_: void) => ({
      being_id: beingId,
      herald_id: herald ?? 0,
      zeal: Math.max(0, Math.min(100, Number(zeal) || 0)),
    }),
    'A herald now serves it'
  )
  const opening = useMadeAction(
    'outer_incursion:open',
    (_: void) => ({ being_id: beingId, region_id: region }),
    'It presses into the cosmos'
  )
  const striking = useMadeAction(
    'outer_pact:strike',
    (_: void) => ({
      being_id: beingId,
      holder_id: holder ?? 0,
      price: price as OuterPactView['price'],
    }),
    'The bargain is struck'
  )
  const relating = useMadeAction(
    'outer_relation:set',
    (_: void) => ({
      being_id: beingId,
      other_id: other ?? 0,
      relation: relation as OuterRelationView['relation'],
    }),
    'Its stance is set'
  )
  const sealing = useMadeAction(
    'outer_seal:set',
    (_: void) => ({
      being_id: beingId,
      kind: sealKind as OuterSealView['kind'],
      strength: Math.max(1, Math.min(100, Number(strength) || 1)),
    }),
    'It is held'
  )
  const destroying = useMadeAction(
    'outer:destroy',
    (_: void) => ({ being_id: beingId }),
    'It is destroyed'
  )
  return (
    <>
      <ForgeCard
        icon={GOALS.feed.icon}
        tone='danger'
        title='Set its aim'
        note='It works toward its aim in stages, showing a sign at each; heralds and cults hasten it.'
        columns={3}
        action={
          <StepButton
            act={aiming}
            icon={CirclePlus}
            label='Set its aim'
            variant='default'
            busy={why(stop, aiming.isPending)}
            onClick={() => aiming.mutate()}
          />
        }
      >
        <ChoiceField
          label='Aim'
          value={goal}
          table={GOALS}
          blocked={stop}
          onPick={setGoal}
        />
        <ThingPicker
          label='Its target, if any'
          value={target}
          onChange={setTarget}
          blocked={stop}
        />
        <NumberField
          label='Progress to start from'
          value={progress}
          min={0}
          max={100}
          onChange={setProgress}
        />
      </ForgeCard>
      <ForgeCard
        icon={HERALD_ICON}
        tone='danger'
        title='Bind a herald'
        note='A herald pushes its aim each epoch by its zeal.'
        columns={2}
        action={
          <StepButton
            act={binding}
            icon={HERALD_ICON}
            label='Bind them'
            variant='default'
            busy={why(
              stop ?? (herald === null ? 'Pick a herald first' : null),
              binding.isPending
            )}
            onClick={() => binding.mutate()}
          />
        }
      >
        <ThingPicker
          label='Herald'
          value={herald}
          onChange={setHerald}
          blocked={stop}
          types={MORTALS}
        />
        <NumberField
          label='Zeal'
          value={zeal}
          min={0}
          max={100}
          onChange={setZeal}
        />
      </ForgeCard>
      <ForgeCard
        icon={STAGES.breach.icon}
        tone='danger'
        title='Open an incursion'
        note='An incursion grows through open rifts, drains the sanity of its land by its stage, and is warded off by sons with essence once manifest.'
        columns={2}
        action={
          <StepButton
            act={opening}
            icon={STAGES.breach.icon}
            label='Open it'
            variant='default'
            busy={why(stop, opening.isPending)}
            onClick={() => opening.mutate()}
          />
        }
      >
        <ThingPicker
          label='Land it presses into'
          value={region}
          onChange={setRegion}
          blocked={stop}
          types={REGIONS}
        />
      </ForgeCard>
      <ForgeCard
        icon={PACT_ICON}
        tone='warning'
        title='Strike a bargain'
        note='The one who strikes it gains a bonded power and pays the price at once.'
        columns={2}
        action={
          <StepButton
            act={striking}
            icon={PACT_ICON}
            label='Strike it'
            variant='default'
            busy={why(
              stop ?? (holder === null ? 'Pick who strikes it first' : null),
              striking.isPending
            )}
            onClick={() => striking.mutate()}
          />
        }
      >
        <ThingPicker
          label='Who strikes it'
          value={holder}
          onChange={setHolder}
          blocked={stop}
          types={MORTALS}
        />
        <ChoiceField
          label='Price'
          value={price}
          table={PRICES}
          blocked={stop}
          onPick={setPrice}
        />
      </ForgeCard>
      <ForgeCard
        icon={RELATIONS.rival.icon}
        tone='warning'
        title='Set its stance toward another outer being'
        note='A being that feeds on another takes from what it has fed; rivals with the same aim set each other back.'
        columns={2}
        action={
          <StepButton
            act={relating}
            icon={CirclePlus}
            label='Set its stance'
            variant='default'
            busy={why(
              stop ??
                (other === null
                  ? 'Pick the other being first'
                  : other === beingId
                    ? 'It holds no stance toward itself'
                    : null),
              relating.isPending
            )}
            onClick={() => relating.mutate()}
          />
        }
      >
        <ThingPicker
          label='Other outer being'
          value={other}
          onChange={setOther}
          blocked={stop}
          types={BEINGS}
        />
        <ChoiceField
          label='Stance'
          value={relation}
          table={RELATIONS}
          blocked={stop}
          onPick={setRelation}
        />
      </ForgeCard>
      <ForgeCard
        icon={SEAL_ICON}
        tone='info'
        title='Seal or banish it'
        note='A sealed being cannot feed or work its aims; a banished one also loses its reach and breach points. Seals weaken each epoch.'
        columns={2}
        action={
          <StepButton
            act={sealing}
            icon={SEAL_ICON}
            label='Hold it'
            variant='default'
            busy={why(stop, sealing.isPending)}
            onClick={() => sealing.mutate()}
          />
        }
      >
        <ChoiceField
          label='Kind'
          value={sealKind}
          table={SEAL_KINDS}
          blocked={stop}
          onPick={setSealKind}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={1}
          max={100}
          onChange={setStrength}
        />
      </ForgeCard>
      <RecordRow
        icon={FATES.destroyed.icon}
        tone='gold'
        title='Destroy it'
        caption='The Creator ends it for good, at a great cost of essence.'
      >
        <StepButton
          act={destroying}
          icon={FATES.destroyed.icon}
          label='Destroy it'
          busy={why(stop, destroying.isPending)}
          onClick={() => destroying.mutate()}
        />
      </RecordRow>
    </>
  )
}

export function OuterAgencySection({
  beingId,
  readOnlyReason = null,
}: {
  beingId: number
  readOnlyReason?: string | null
}) {
  const query = useOuterAgency(beingId)
  const blocked = readOnlyReason
  const plan = query.data?.plans.find((row) => row.state === 'active')
  return (
    <Section
      id='section-outer-agency'
      title='Its aims, servants and incursions'
      description='An outer being pursues aims in stages, binds heralds, presses into the cosmos through rifts, strikes bargains, stands toward other outer beings, and can be sealed, banished, starved or destroyed.'
      icon={OUTER_AGENCY_ICON}
      tone='danger'
    >
      <div
        data-surface='OuterAgencySection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading what it works toward' />
        ) : query.isError ? (
          <EmptyState
            icon={OUTER_AGENCY_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Fate'
                value={FATES[query.data.fate].label}
                icon={FATES[query.data.fate].icon}
                tone={FATES[query.data.fate].tone ?? 'info'}
              />
              <KpiTile
                label='Aim under way'
                value={
                  plan ? `${GOALS[plan.goal].label}, ${plan.progress}%` : 'None'
                }
                icon={plan ? GOALS[plan.goal].icon : OUTER_AGENCY_ICON}
                tone={plan ? 'warning' : 'muted'}
              />
              <KpiTile
                label='Epochs unfed'
                value={`${query.data.unfed_epochs} of ${query.data.starve_epochs}`}
                icon={GOALS.feed.icon}
                tone={query.data.unfed_epochs ? 'warning' : 'muted'}
              />
            </div>
            <Listing
              rows={query.data.plans}
              render={(row) => (
                <Plan key={row.id} row={row} blocked={blocked} />
              )}
              empty={{
                title: `${query.data.being.name} has no aim yet`,
                description:
                  'It takes up an aim at the next epoch, or set one below.',
              }}
            />
            <Listing
              rows={query.data.heralds}
              render={(row) => (
                <Herald key={row.herald.id} row={row} blocked={blocked} />
              )}
              empty={{
                title: 'No heralds',
                description: 'Bargains priced in service bind heralds.',
              }}
            />
            <Listing
              rows={query.data.incursions}
              render={(row) => (
                <Incursion key={row.id} row={row} blocked={blocked} />
              )}
              empty={{
                title: 'No incursions',
                description: 'It presses in once an aim to enter succeeds.',
              }}
            />
            <Listing
              rows={query.data.pacts}
              render={(row) => (
                <Pact key={row.id} row={row} blocked={blocked} />
              )}
              empty={{
                title: 'No bargains',
                description: 'Members of its cults strike bargains with it.',
              }}
            />
            <Listing
              rows={query.data.relations}
              render={(row) => (
                <Relation
                  key={row.other.id}
                  row={row}
                  beingId={beingId}
                  blocked={blocked}
                />
              )}
              empty={{
                title: 'No other outer beings',
                description:
                  'It stands toward each other outer being once there are others.',
              }}
            />
            <Listing
              rows={query.data.seals}
              render={(row) => (
                <Seal key={row.id} row={row} blocked={blocked} />
              )}
              empty={{
                title: 'Nothing holds it',
                description: 'Seal or banish it below.',
              }}
            />
            <Forges view={query.data} beingId={beingId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
