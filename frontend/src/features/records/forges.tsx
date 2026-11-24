import { useState } from 'react'
import {
  Check,
  Eye,
  Footprints,
  Lock,
  LockOpen,
  PenLine,
  Plus,
  ScrollText,
  Trash2,
  Undo2,
  X,
  LockKeyhole,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, RangeField, FieldTile } from '@/components/domain'
import { ForgeCard } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { DAMAGE } from '@/features/entity/body/labels'
import { type Named } from '@/features/entity/environment/labels'
import { RecordField } from '@/features/entity/realm/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type EventAccount,
  type EventChange,
  type EventFact,
  type EventParticipant,
  type EventStep,
  type FactUnit,
  type InstrumentKind,
  type StepAction,
  type StepLocus,
  type StepOutcome,
  type WitnessMode,
} from './api'
import {
  FACT_UNIT,
  INSTRUMENT_KIND,
  STEP_ACTION,
  STEP_LOCUS,
  STEP_OUTCOME,
  STEP_STATE,
  WITNESS_MODE,
} from './labels'

type DamageType = components['schemas']['DamageType']
type StepStateKind = NonNullable<EventStep['states']>[number]['state']

const FULL = 100
const KEY_SHAPE = /^[a-z][a-z0-9_]*$/
const HOLD_PARTS: Record<string, Named> = {
  text: { label: 'How it is told', icon: ScrollText },
  roles: { label: 'Who took part', icon: Eye },
  facts: { label: 'Its facts', icon: ScrollText },
  steps: { label: 'Its steps', icon: Footprints },
  witnesses: { label: 'Its witnesses', icon: Eye },
  moment: { label: 'When it happened', icon: Lock },
  place: { label: 'Where it happened', icon: LockKeyhole },
}
const VALUE_KINDS: Record<string, Named> = {
  number: { label: 'A number', icon: Plus },
  record: { label: 'A record', icon: Eye },
  name: { label: 'A name', icon: ScrollText },
}
const NO_OUTCOME = 'unknown'
const NO_DAMAGE = 'no_harm'
const NO_STATE = 'unchanged'
const DAMAGES: Record<string, Named> = {
  [NO_DAMAGE]: { label: 'No harm', icon: ScrollText },
  ...Object.fromEntries(
    Object.entries(DAMAGE).map(([key, label]) => [
      key,
      { label, icon: Footprints },
    ])
  ),
}
const STATES: Record<string, Named> = {
  [NO_STATE]: { label: 'Left as before', icon: ScrollText },
  ...STEP_STATE,
}
const OUTCOMES: Record<string, Named> = {
  [NO_OUTCOME]: { label: 'Not told', icon: ScrollText },
  ...STEP_OUTCOME,
}

function why(blocked: string | null, pending: boolean, busy: string) {
  return blocked ?? (pending ? busy : null)
}

export function HoldBar({
  account,
  blocked,
}: {
  account: EventAccount
  blocked: string | null
}) {
  const hold = useGodAction<{ part: string; held: boolean }>({
    run: ({ part, held }) =>
      unwrap(
        api.POST('/api/actions/incident:hold', {
          body: { incident_id: account.id, fields: [part], hold: !held },
        })
      ),
    success: (_, { held }) =>
      held ? 'That part is free to change again' : 'That part is held',
  })
  const busy = why(blocked, hold.isPending, 'Another part is being held.')
  return (
    <div className='flex min-w-0 flex-wrap gap-2'>
      {Object.entries(HOLD_PARTS).map(([part, spec]) => {
        const held = account.locked.includes(part)
        return (
          <StepButton
            key={part}
            icon={held ? Lock : LockOpen}
            label={`${held ? 'Held' : 'Hold'}: ${spec.label.toLowerCase()}`}
            variant={held ? 'default' : 'outline'}
            busy={busy}
            onClick={() => hold.mutate({ part, held })}
          />
        )
      })}
    </div>
  )
}

export function FactForge({
  account,
  blocked,
}: {
  account: EventAccount
  blocked: string | null
}) {
  const [key, setKey] = useState('')
  const [valueKind, setValueKind] = useState('number')
  const [amount, setAmount] = useState('1')
  const [unit, setUnit] = useState<FactUnit>('count')
  const [nodeId, setNodeId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_fact:create', {
          body: {
            incident_id: account.id,
            key,
            position: 0,
            number: valueKind === 'number' ? Number(amount) : null,
            unit: valueKind === 'number' ? unit : null,
            node_id: valueKind === 'record' ? nodeId : null,
            name: valueKind === 'name' ? name.trim() : null,
          },
        })
      ),
    success: 'The fact is set down',
    onDone: () => setKey(''),
  })
  const missing = !KEY_SHAPE.test(key)
    ? 'Name the fact in lower case words joined by underscores'
    : valueKind === 'number' && !Number.isFinite(Number(amount))
      ? 'Give the fact a number'
      : valueKind === 'record' && nodeId === null
        ? 'Choose the record the fact names'
        : valueKind === 'name' && name.trim() === ''
          ? 'Give the fact its name'
          : null
  const reason = why(blocked, add.isPending, 'The fact is being set down.')
  return (
    <ForgeCard
      icon={ScrollText}
      tone='gold'
      title='Set down a fact'
      note='A fact holds one value: a number with its unit, a record, or a name the world gave.'
      columns={3}
      action={
        <StepButton
          icon={Plus}
          label='Set it down'
          variant='default'
          busy={reason ?? missing}
          onClick={() => add.mutate()}
        />
      }
    >
      <FieldTile label='Name of the fact'>
        <Input
          aria-label='Name of the fact'
          value={key}
          disabled={reason !== null}
          onChange={(event) => setKey(event.target.value.trim().toLowerCase())}
        />
      </FieldTile>
      <ChoiceField
        label='What it holds'
        value={valueKind}
        table={VALUE_KINDS}
        blocked={reason}
        onPick={setValueKind}
      />
      {valueKind === 'number' ? (
        <>
          <NumberField
            label='Amount'
            value={amount}
            min={-1000000}
            onChange={setAmount}
          />
          <ChoiceField
            label='Unit'
            value={unit}
            table={FACT_UNIT}
            blocked={reason}
            onPick={(value) => setUnit(value as FactUnit)}
          />
        </>
      ) : valueKind === 'record' ? (
        <RecordField
          label='The record'
          types={null}
          value={nodeId}
          onChange={setNodeId}
          blocked={reason}
        />
      ) : (
        <FieldTile label='The name'>
          <Input
            aria-label='The name'
            value={name}
            disabled={reason !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
      )}
    </ForgeCard>
  )
}

export function StepForge({
  account,
  blocked,
}: {
  account: EventAccount
  blocked: string | null
}) {
  const [action, setAction] = useState<StepAction>('strike')
  const [actorId, setActorId] = useState<number | null>(null)
  const [targetId, setTargetId] = useState<number | null>(null)
  const [instrument, setInstrument] = useState<InstrumentKind>('none')
  const [locus, setLocus] = useState<StepLocus>('none')
  const [outcome, setOutcome] = useState(NO_OUTCOME)
  const [amount, setAmount] = useState('')
  const [unit, setUnit] = useState<FactUnit>('count')
  const [round, setRound] = useState('')
  const [parentId, setParentId] = useState('none')
  const [year, setYear] = useState('')
  const [season, setSeason] = useState('')
  const [day, setDay] = useState('')
  const [hour, setHour] = useState('')
  const [damage, setDamage] = useState(NO_DAMAGE)
  const [instrumentId, setInstrumentId] = useState<number | null>(null)
  const [locusId, setLocusId] = useState<number | null>(null)
  const [state, setState] = useState(NO_STATE)
  const parents: Record<string, Named> = {
    none: { label: 'At the top of the account', icon: Footprints },
    ...Object.fromEntries(
      account.steps.map((step) => [
        String(step.id),
        {
          label: `${step.position + 1}. ${STEP_ACTION[step.action].label}${step.actor_name ? ` by ${step.actor_name}` : ''}`,
          icon: STEP_ACTION[step.action].icon,
        },
      ])
    ),
  }
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_step:create', {
          body: {
            incident_id: account.id,
            step_action: action,
            actor_node_id: actorId,
            target_node_id: targetId,
            instrument_kind: instrument,
            locus_kind: locus,
            outcome: outcome === NO_OUTCOME ? null : (outcome as StepOutcome),
            amount: amount.trim() === '' ? null : Number(amount),
            unit: amount.trim() === '' ? null : unit,
            round: round.trim() === '' ? null : Number(round),
            parent_step_id: parentId === 'none' ? null : Number(parentId),
            year: year.trim() === '' ? null : Number(year),
            season: season.trim() === '' ? null : Number(season) - 1,
            day: day.trim() === '' ? null : Number(day) - 1,
            hour: hour.trim() === '' ? null : Number(hour) - 1,
            damage_type: damage === NO_DAMAGE ? null : (damage as DamageType),
            instrument_node_id: instrumentId,
            locus_node_id: locusId,
            states:
              state === NO_STATE || targetId === null
                ? []
                : [{ node_id: targetId, state: state as StepStateKind }],
          },
        })
      ),
    success: 'The step is added to how it unfolded',
  })
  const missing =
    amount.trim() !== '' && !Number.isFinite(Number(amount))
      ? 'The amount must be a number'
      : null
  const reason = why(blocked, add.isPending, 'The step is being added.')
  return (
    <ForgeCard
      icon={Footprints}
      tone='verdigris'
      title='Add a step'
      note='A step tells one moment of how the happening unfolded: who did what to whom, with what, where, how much and how it ended.'
      columns={3}
      action={
        <StepButton
          icon={Plus}
          label='Add the step'
          variant='default'
          busy={reason ?? missing}
          onClick={() => add.mutate()}
        />
      }
    >
      <ChoiceField
        label='What was done'
        value={action}
        table={STEP_ACTION}
        blocked={reason}
        onPick={(value) => setAction(value as StepAction)}
      />
      <RecordField
        label='Who acted'
        types={null}
        value={actorId}
        onChange={setActorId}
        blocked={reason}
      />
      <RecordField
        label='Who it was done to'
        types={null}
        value={targetId}
        onChange={setTargetId}
        blocked={reason}
      />
      <ChoiceField
        label='With what'
        value={instrument}
        table={INSTRUMENT_KIND}
        blocked={reason}
        onPick={(value) => setInstrument(value as InstrumentKind)}
      />
      <ChoiceField
        label='Where on or in it'
        value={locus}
        table={STEP_LOCUS}
        blocked={reason}
        onPick={(value) => setLocus(value as StepLocus)}
      />
      <ChoiceField
        label='How it ended'
        value={outcome}
        table={OUTCOMES}
        blocked={reason}
        onPick={setOutcome}
      />
      <NumberField
        label='How much'
        value={amount}
        min={-1000000}
        onChange={setAmount}
      />
      <ChoiceField
        label='Counted in'
        value={unit}
        table={FACT_UNIT}
        blocked={
          reason ?? (amount.trim() === '' ? 'Give an amount first' : null)
        }
        onPick={(value) => setUnit(value as FactUnit)}
      />
      <NumberField
        label='Round'
        value={round}
        min={0}
        max={500}
        onChange={setRound}
      />
      <ChoiceField
        label='Harm done'
        value={damage}
        table={DAMAGES}
        blocked={reason}
        onPick={setDamage}
      />
      <RecordField
        label='The thing used'
        types={null}
        value={instrumentId}
        onChange={setInstrumentId}
        blocked={
          reason ??
          (instrument === 'none'
            ? 'Say what kind of thing was used first'
            : null)
        }
      />
      <RecordField
        label='The place of the step'
        types={null}
        value={locusId}
        onChange={setLocusId}
        blocked={
          reason ?? (locus === 'none' ? 'Say where on or in it first' : null)
        }
      />
      <ChoiceField
        label='What it left the one acted on'
        value={state}
        table={STATES}
        blocked={
          reason ??
          (targetId === null ? 'Choose who it was done to first' : null)
        }
        onPick={setState}
      />
      <NumberField
        label='Year'
        value={year}
        min={-1000000}
        onChange={setYear}
      />
      <NumberField
        label='Season (from 1)'
        value={season}
        min={1}
        max={100}
        onChange={setSeason}
      />
      <NumberField
        label='Day (from 1)'
        value={day}
        min={1}
        max={1000}
        onChange={setDay}
      />
      <NumberField
        label='Hour (from 1)'
        value={hour}
        min={1}
        max={100}
        onChange={setHour}
      />
      <ChoiceField
        label='Inside which step'
        value={parentId}
        table={parents}
        blocked={reason}
        onPick={setParentId}
      />
    </ForgeCard>
  )
}

export function WitnessForge({
  account,
  blocked,
}: {
  account: EventAccount
  blocked: string | null
}) {
  const [nodeId, setNodeId] = useState<number | null>(null)
  const [mode, setMode] = useState<WitnessMode>('saw')
  const [fidelity, setFidelity] = useState(FULL)
  const [teller, setTeller] = useState('witness')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_witness:create', {
          body: {
            incident_id: account.id,
            node_id: nodeId ?? 0,
            witness_mode: mode,
            fidelity,
            teller: teller === 'teller',
          },
        })
      ),
    success: (_, __) =>
      teller === 'teller' ? 'The teller is named' : 'The witness is named',
    onDone: () => setNodeId(null),
  })
  const reason = why(blocked, add.isPending, 'The witness is being named.')
  return (
    <ForgeCard
      icon={Eye}
      tone='info'
      title='Name a witness or a teller'
      note='A witness saw, heard, took part or was told; a teller spread an account of it. Fidelity is how true their account stays.'
      columns={2}
      action={
        <StepButton
          icon={Plus}
          label='Name them'
          variant='default'
          busy={reason ?? (nodeId === null ? 'Choose who it is' : null)}
          onClick={() => add.mutate()}
        />
      }
    >
      <RecordField
        label='Who'
        types={null}
        value={nodeId}
        onChange={setNodeId}
        blocked={reason}
      />
      <ChoiceField
        label='Their place in it'
        value={teller}
        table={{
          witness: { label: 'A witness', icon: Eye },
          teller: { label: 'A teller', icon: ScrollText },
        }}
        blocked={reason}
        onPick={setTeller}
      />
      <ChoiceField
        label='How they knew it'
        value={mode}
        table={WITNESS_MODE}
        blocked={reason}
        onPick={(value) => setMode(value as WitnessMode)}
      />
      <RangeField
        label='Fidelity of their account'
        icon={Eye}
        value={fidelity}
        min={0}
        max={FULL}
        level={`${fidelity} of ${FULL}`}
        lowLabel='Garbled'
        highLabel='True'
        onChange={setFidelity}
        disabledReason={reason}
      />
    </ForgeCard>
  )
}

export function StruckButton({
  label,
  title,
  description,
  busy,
  onConfirm,
}: {
  label: string
  title: string
  description: string
  busy: string | null
  onConfirm: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <StepButton
        icon={Trash2}
        label={label}
        busy={busy}
        onClick={() => setOpen(true)}
      />
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={title}
        desc={description}
        confirmText={label}
        destructive
        handleConfirm={() => {
          setOpen(false)
          onConfirm()
        }}
      />
    </>
  )
}

export function ChangeControls({
  change,
  blocked,
}: {
  change: EventChange
  blocked: string | null
}) {
  const [confirming, setConfirming] = useState(false)
  const revert = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/state_change:revert', {
          body: { state_change_id: change.id },
        })
      ),
    success: 'The value is set back; the reversal is kept in history',
  })
  const erase = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/state_change:delete', {
          body: { state_change_id: change.id },
        })
      ),
    success: 'The change is erased from the record',
  })
  const busy = why(
    blocked,
    revert.isPending || erase.isPending,
    'The record is being rewritten.'
  )
  return (
    <div className='flex min-w-0 flex-wrap gap-2'>
      <StepButton
        icon={Undo2}
        label='Set it back'
        busy={busy}
        onClick={() => setConfirming(true)}
      />
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title='Set this value back?'
        desc='The value returns to what it was before this change. The reversal is written into history as a change of your own.'
        confirmText='Set it back'
        handleConfirm={() => {
          setConfirming(false)
          revert.mutate()
        }}
      />
      <StruckButton
        label='Erase'
        title='Erase this change from history?'
        description='The record of this change is removed. The value itself stays as it is now.'
        busy={busy}
        onConfirm={() => erase.mutate()}
      />
    </div>
  )
}

export function FactEditor({
  fact,
  blocked,
}: {
  fact: EventFact
  blocked: string | null
}) {
  const [open, setOpen] = useState(false)
  const [amount, setAmount] = useState(String(fact.number ?? ''))
  const [unit, setUnit] = useState<FactUnit>(fact.unit ?? 'count')
  const [nodeId, setNodeId] = useState<number | null>(fact.node_id)
  const [name, setName] = useState(fact.name ?? '')
  const kind =
    fact.node_id !== null
      ? 'record'
      : fact.number !== null
        ? 'number'
        : fact.enum_value !== null
          ? 'enum'
          : 'name'
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_fact:edit', {
          body: {
            incident_fact_id: fact.id,
            number: kind === 'number' ? Number(amount) : null,
            unit: kind === 'number' ? unit : null,
            node_id: kind === 'record' ? nodeId : null,
            name: kind === 'name' ? name.trim() : null,
            enum_name: kind === 'enum' ? fact.enum_name : null,
            enum_value: kind === 'enum' ? fact.enum_value : null,
          },
        })
      ),
    success: 'The fact is rewritten',
    onDone: () => setOpen(false),
  })
  const reason = why(blocked, edit.isPending, 'The fact is being rewritten.')
  const missing =
    kind === 'number' && !Number.isFinite(Number(amount))
      ? 'Give the fact a number'
      : kind === 'record' && nodeId === null
        ? 'Choose the record the fact names'
        : kind === 'name' && name.trim() === ''
          ? 'Give the fact its name'
          : kind === 'enum'
            ? 'A value from a fixed list is set by the world; strike it and set down another'
            : null
  if (!open)
    return (
      <StepButton
        icon={PenLine}
        label='Rewrite'
        busy={reason}
        onClick={() => setOpen(true)}
      />
    )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      {kind === 'number' ? (
        <>
          <NumberField
            label='Amount'
            value={amount}
            min={-1000000}
            onChange={setAmount}
          />
          <ChoiceField
            label='Unit'
            value={unit}
            table={FACT_UNIT}
            blocked={reason}
            onPick={(value) => setUnit(value as FactUnit)}
          />
        </>
      ) : kind === 'record' ? (
        <RecordField
          label='The record'
          types={null}
          value={nodeId}
          onChange={setNodeId}
          blocked={reason}
        />
      ) : kind === 'name' ? (
        <FieldTile label='The name'>
          <Input
            aria-label='The name'
            value={name}
            disabled={reason !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
      ) : null}
      <StepButton
        icon={Check}
        label='Keep it'
        variant='default'
        busy={reason ?? missing}
        onClick={() => edit.mutate()}
      />
      <StepButton
        icon={X}
        label='Leave it'
        variant='ghost'
        busy={null}
        onClick={() => setOpen(false)}
      />
    </div>
  )
}

export function StepEditor({
  step,
  blocked,
}: {
  step: EventStep
  blocked: string | null
}) {
  const [open, setOpen] = useState(false)
  const [action, setAction] = useState<StepAction>(step.action)
  const [outcome, setOutcome] = useState<string>(step.outcome ?? NO_OUTCOME)
  const [actorId, setActorId] = useState<number | null>(step.actor_node_id)
  const [targetId, setTargetId] = useState<number | null>(step.target_node_id)
  const [amount, setAmount] = useState(
    step.amount === null ? '' : String(step.amount)
  )
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_step:edit', {
          body: {
            incident_step_id: step.id,
            step_action: action,
            outcome: outcome === NO_OUTCOME ? null : (outcome as StepOutcome),
            actor_node_id: actorId,
            target_node_id: targetId,
            amount: amount.trim() === '' ? null : Number(amount),
            unit: amount.trim() === '' ? null : step.unit,
            round: step.round,
            parent_step_id: step.parent_step_id,
            year: step.moment.year,
            season: step.moment.season,
            day: step.moment.day,
            hour: step.moment.hour,
            instrument_kind: step.instrument_kind,
            instrument_node_id: step.instrument_node_id,
            instrument_key: step.instrument_key,
            locus_kind: step.locus_kind,
            locus_key: step.locus_key,
            locus_node_id: step.locus_node_id,
            damage_type: step.damage_type,
            states: (step.states ?? []).map((state) => ({
              node_id: state.node_id,
              state: state.state,
            })),
          },
        })
      ),
    success: 'The step is rewritten',
    onDone: () => setOpen(false),
  })
  const reason = why(blocked, edit.isPending, 'The step is being rewritten.')
  const missing =
    amount.trim() !== '' && !Number.isFinite(Number(amount))
      ? 'The amount must be a number'
      : null
  if (!open)
    return (
      <StepButton
        icon={PenLine}
        label='Rewrite the step'
        busy={reason}
        onClick={() => setOpen(true)}
      />
    )
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 @lg/event:grid-cols-2'>
      <ChoiceField
        label='What was done'
        value={action}
        table={STEP_ACTION}
        blocked={reason}
        onPick={(value) => setAction(value as StepAction)}
      />
      <ChoiceField
        label='How it ended'
        value={outcome}
        table={OUTCOMES}
        blocked={reason}
        onPick={setOutcome}
      />
      <RecordField
        label='Who acted'
        types={null}
        value={actorId}
        onChange={setActorId}
        blocked={reason}
      />
      <RecordField
        label='Who it was done to'
        types={null}
        value={targetId}
        onChange={setTargetId}
        blocked={reason}
      />
      <NumberField
        label='How much'
        value={amount}
        min={-1000000}
        onChange={setAmount}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Check}
          label='Keep it'
          variant='default'
          busy={reason ?? missing}
          onClick={() => edit.mutate()}
        />
        <StepButton
          icon={X}
          label='Leave it'
          variant='ghost'
          busy={null}
          onClick={() => setOpen(false)}
        />
      </div>
    </div>
  )
}

export function WitnessEditor({
  incidentId,
  witness,
  blocked,
}: {
  incidentId: number
  witness: EventParticipant
  blocked: string | null
}) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<WitnessMode>(witness.witness_mode ?? 'saw')
  const [fidelity, setFidelity] = useState(witness.fidelity ?? FULL)
  const teller = witness.role === 'teller'
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_witness:edit', {
          body: {
            incident_id: incidentId,
            node_id: witness.node_id,
            teller,
            witness_mode: mode,
            fidelity,
          },
        })
      ),
    success: 'How it was seen is rewritten',
    onDone: () => setOpen(false),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_witness:delete', {
          body: { incident_id: incidentId, node_id: witness.node_id, teller },
        })
      ),
    success: teller ? 'The teller is struck' : 'The witness is struck',
  })
  const reason = why(
    blocked,
    edit.isPending || strike.isPending,
    'The witness is being rewritten.'
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {open ? (
        <div className='grid min-w-0 grid-cols-1 items-end gap-2 @lg/event:grid-cols-2'>
          <ChoiceField
            label='How they knew it'
            value={mode}
            table={WITNESS_MODE}
            blocked={reason}
            onPick={(value) => setMode(value as WitnessMode)}
          />
          <RangeField
            label='Fidelity of their account'
            icon={Eye}
            value={fidelity}
            min={0}
            max={FULL}
            level={`${fidelity} of ${FULL}`}
            lowLabel='Garbled'
            highLabel='True'
            onChange={setFidelity}
            disabledReason={reason}
          />
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Check}
              label='Keep it'
              variant='default'
              busy={reason}
              onClick={() => edit.mutate()}
            />
            <StepButton
              icon={X}
              label='Leave it'
              variant='ghost'
              busy={null}
              onClick={() => setOpen(false)}
            />
          </div>
        </div>
      ) : (
        <div className='flex min-w-0 flex-wrap gap-2'>
          <StepButton
            icon={PenLine}
            label='Rewrite'
            busy={reason}
            onClick={() => setOpen(true)}
          />
          <StruckButton
            label='Strike'
            title={teller ? 'Strike this teller?' : 'Strike this witness?'}
            description='They no longer appear as knowing of this happening.'
            busy={reason}
            onConfirm={() => strike.mutate()}
          />
        </div>
      )}
    </div>
  )
}

export function IncidentEditor({
  account,
  blocked,
  onStruck,
}: {
  account: EventAccount
  blocked: string | null
  onStruck: () => void
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(account.line ?? '')
  const [magnitude, setMagnitude] = useState(account.magnitude)
  const [kind, setKind] = useState(account.kind)
  const [year, setYear] = useState(
    account.moment.year === null ? '' : String(account.moment.year)
  )
  const [hour, setHour] = useState(
    account.moment.hour === null ? '' : String(account.moment.hour + 1)
  )
  const [season, setSeason] = useState(
    account.moment.season === null ? '' : String(account.moment.season + 1)
  )
  const [day, setDay] = useState(
    account.moment.day === null ? '' : String(account.moment.day + 1)
  )
  const [placeId, setPlaceId] = useState<number | null>(account.place_id)
  const [originId, setOriginId] = useState<number | null>(account.origin_id)
  const [destinationId, setDestinationId] = useState<number | null>(
    account.destination_id
  )
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:edit', {
          body: {
            incident_id: account.id,
            text:
              text.trim() === '' || account.locked.includes('text')
                ? null
                : text,
            magnitude,
            kind: kind === account.kind ? null : kind,
            year: year.trim() === '' ? null : Number(year),
            hour: hour.trim() === '' ? null : Number(hour) - 1,
            season: season.trim() === '' ? null : Number(season) - 1,
            day: day.trim() === '' ? null : Number(day) - 1,
            place_entity_id: placeId,
            clear_place: placeId === null && account.place_id !== null,
            origin_entity_id: originId,
            clear_origin: originId === null && account.origin_id !== null,
            destination_entity_id: destinationId,
            clear_destination:
              destinationId === null && account.destination_id !== null,
          },
        })
      ),
    success: 'The happening is rewritten',
    onDone: () => setOpen(false),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:delete', {
          body: { incident_id: account.id },
        })
      ),
    success: 'The happening is struck from history',
    onDone: () => onStruck(),
  })
  const reason = why(
    blocked,
    edit.isPending || strike.isPending,
    'The happening is being rewritten.'
  )
  const badMoment =
    (season.trim() !== '' && !(Number(season) >= 1)) ||
    (day.trim() !== '' && !(Number(day) >= 1)) ||
    (hour.trim() !== '' && !(Number(hour) >= 1))
      ? 'Seasons, days and hours are counted from one'
      : !/^[a-z][a-z0-9_.]*$/.test(kind)
        ? 'Name the kind in lower case words joined by dots or underscores'
        : null
  if (!open)
    return (
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={PenLine}
          label='Rewrite the happening'
          busy={reason}
          onClick={() => setOpen(true)}
        />
        <StruckButton
          label='Strike it from history'
          title='Strike this happening from history?'
          description='It is removed from the record; what it caused now follows from its own cause. This cannot be undone here.'
          busy={reason}
          onConfirm={() => strike.mutate()}
        />
      </div>
    )
  return (
    <ForgeCard
      icon={PenLine}
      tone='gold'
      title='Rewrite the happening'
      note={
        account.locked.includes('text')
          ? 'Its telling is held; release it to rewrite the line.'
          : 'Change how it is told, when and where it happened, and how much it weighed.'
      }
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <StepButton
            icon={X}
            label='Leave it'
            variant='ghost'
            busy={null}
            onClick={() => setOpen(false)}
          />
          <StepButton
            icon={Check}
            label='Keep it'
            variant='default'
            busy={reason ?? badMoment}
            onClick={() => edit.mutate()}
          />
        </div>
      }
    >
      <FieldTile label='How it is told' className='@lg/forge:col-span-3'>
        <Textarea
          aria-label='How it is told'
          value={text}
          disabled={reason !== null || account.locked.includes('text')}
          onChange={(event) => setText(event.target.value)}
        />
      </FieldTile>
      <RangeField
        label='How much it weighed'
        icon={ScrollText}
        value={magnitude}
        min={0}
        max={FULL}
        level={`${magnitude} of ${FULL}`}
        lowLabel='Slight'
        highLabel='Great'
        onChange={setMagnitude}
        disabledReason={reason}
      />
      <FieldTile label='Kind of happening'>
        <Input
          aria-label='Kind of happening'
          value={kind}
          disabled={reason !== null}
          onChange={(event) => setKind(event.target.value.trim().toLowerCase())}
        />
      </FieldTile>
      <NumberField
        label='Year'
        value={year}
        min={-1000000}
        onChange={setYear}
      />
      <NumberField
        label='Season (from 1)'
        value={season}
        min={1}
        max={100}
        onChange={setSeason}
      />
      <NumberField
        label='Day (from 1)'
        value={day}
        min={1}
        max={1000}
        onChange={setDay}
      />
      <NumberField
        label='Hour (from 1)'
        value={hour}
        min={1}
        max={100}
        onChange={setHour}
      />
      <RecordField
        label='Where it happened'
        types={null}
        value={placeId}
        onChange={setPlaceId}
        blocked={reason}
      />
      <RecordField
        label='Set out from'
        types={null}
        value={originId}
        onChange={setOriginId}
        blocked={reason}
      />
      <RecordField
        label='Bound for'
        types={null}
        value={destinationId}
        onChange={setDestinationId}
        blocked={reason}
      />
    </ForgeCard>
  )
}
