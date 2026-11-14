import { useState } from 'react'
import { Ban, Gift, HandHeart, Repeat, Route, Scale, Undo2 } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type CircuitView,
  type CyclesView,
  type GiftView,
  useCycleAction,
} from './api'
import { GIFT_STATES, OCCASIONS } from './labels'
import {
  clamp,
  COMMUNITY_TYPES,
  GIVING_TYPES,
  GOD_KINDS,
  MANY,
  STOP_TYPES,
  signed,
  useRow,
  useStep,
} from './model'
import { NodeChips, NodeListPicker, StepButton, TextField } from './parts'

type Debt = CyclesView['debts'][number]

const OWED = new Set(['open', 'destroyed'])

export function GiftCard({
  nodeId,
  row,
  blocked,
}: {
  nodeId: number | null
  row: GiftView
  blocked: string | null
}) {
  const action = useRow(
    'gift:edit',
    'gift:delete',
    { gift_id: row.id },
    blocked
  )
  const answering = useStep(
    'gift:return',
    { gift_id: row.id },
    blocked,
    'The gift is answered'
  )
  const refusing = useStep(
    'gift:refuse',
    { gift_id: row.id },
    blocked,
    'The gift is refused'
  )
  const state = GIFT_STATES[row.state]
  const occasion = OCCASIONS[row.occasion]
  const owed = OWED.has(row.state)
  const closed = owed ? null : 'The gift is settled'
  const direction =
    nodeId === null
      ? ''
      : row.giver.id === nodeId
        ? 'Given to '
        : 'Received from '
  return (
    <Held
      icon={occasion.icon}
      tone={state.tone}
      title={`${occasion.label}, worth ${row.value}`}
      caption={`${direction}${row.giver.id === nodeId ? row.receiver.name : row.giver.name} · epoch ${row.epoch}`}
      removeLabel='Strike from the ledger'
      editTitle='Set the gift'
      note='A gift binds its receiver to answer in kind and in time; a refusal is an insult, an unanswered gift costs face, and a rank-claiming gift must be answered with more.'
      fields={[
        { key: 'value', label: 'Worth', kind: 'number', min: 0 },
        {
          key: 'occasion',
          label: 'Occasion',
          kind: 'pick',
          table: table(OCCASIONS),
        },
        {
          key: 'item_entity_id',
          label: 'Thing given',
          kind: 'node',
          types: ['item', 'artwork'],
        },
        {
          key: 'state',
          label: 'Standing',
          kind: 'pick',
          table: table(GIFT_STATES),
        },
        { key: 'due_epoch', label: 'Due by epoch', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={state.icon}>{state.label}</Chip>
          {row.answers_gift_id !== null && (
            <Chip icon={Undo2}>{`Answers gift ${row.answers_gift_id}`}</Chip>
          )}
        </>
      }
    >
      <Facts
        items={[
          ['Giver', <Ref key='giver' node={row.giver} />],
          ['Receiver', <Ref key='receiver' node={row.receiver} />],
          [
            'Thing given',
            <Ref key='item' node={row.item} empty='coin alone' />,
          ],
          [
            'Due by',
            row.due_epoch !== null
              ? `epoch ${row.due_epoch}`
              : 'no return owed',
          ],
          [
            'Settled',
            row.settled_epoch !== null
              ? `epoch ${row.settled_epoch}`
              : 'not yet',
          ],
        ]}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Undo2}
          label='Answer it'
          busy={closed ?? answering.busy}
          onClick={answering.run}
        />
        <StepButton
          icon={Ban}
          label='Refuse it'
          busy={closed ?? refusing.busy}
          onClick={refusing.run}
        />
      </div>
    </Held>
  )
}

function GiftForge({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [receiver, setReceiver] = useState<number | null>(null)
  const [value, setValue] = useState('10')
  const [occasion, setOccasion] = useState<keyof typeof OCCASIONS>('courtesy')
  const [item, setItem] = useState<number | null>(null)
  const giving = useCycleAction(
    'gift:give',
    (_: void) => ({
      giver_id: nodeId,
      receiver_id: receiver ?? 0,
      value: clamp(value, MANY),
      occasion,
      item_id: item,
    }),
    'The gift is given'
  )
  const busy = why(
    blocked ??
      (receiver === null
        ? 'Choose who receives it'
        : receiver === nodeId
          ? 'A gift needs two sides'
          : null),
    giving.isPending
  )
  return (
    <ForgeCard
      icon={Gift}
      tone='gold'
      title='Give a gift'
      note='From this one to another; the giver pays its worth and the receiver owes a return.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => giving.mutate()}
        >
          <Gift />
          Give it
        </Button>
      }
    >
      <NodePicker
        label='Receiver'
        value={receiver}
        onChange={setReceiver}
        blocked={blocked}
        types={GIVING_TYPES}
        kinds={GOD_KINDS}
      />
      <NumberField
        label='Worth'
        value={value}
        min={0}
        blocked={blocked}
        onChange={setValue}
      />
      <MindPicker
        label='Occasion'
        value={occasion}
        table={table(OCCASIONS)}
        blocked={blocked}
        onPick={(next) => setOccasion(next as keyof typeof OCCASIONS)}
      />
      <NodePicker
        label='Thing given'
        value={item}
        onChange={setItem}
        blocked={blocked}
        types={['item', 'artwork']}
      />
    </ForgeCard>
  )
}

function DebtCard({ row, blocked }: { row: Debt; blocked: string | null }) {
  const action = useRow(
    'debt:edit',
    'debt:delete',
    { god_id: row.god.id, community_id: row.community.id },
    blocked
  )
  const owed = row.offered - row.answered
  return (
    <Held
      icon={HandHeart}
      tone={owed > 0 ? 'warning' : 'success'}
      title={`${row.community.name} to ${row.god.name}`}
      caption={
        owed > 0
          ? `${owed} offered and unanswered`
          : `${-owed} given back beyond the offerings`
      }
      removeLabel='Clear the ledger'
      editTitle='Set the ledger'
      note='Offerings bind a god to answer; gods who leave them unanswered breed neglect and lose love, gods who give back more are loved.'
      fields={[
        { key: 'offered', label: 'Offered', kind: 'number', min: 0 },
        { key: 'answered', label: 'Answered', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Answered of what was offered'
        value={Math.min(row.answered, row.offered)}
        max={Math.max(1, row.offered)}
        tone={owed > 0 ? 'warning' : 'success'}
        icon={Scale}
      />
      <Facts
        items={[
          ['God', <Ref key='god' node={row.god} />],
          ['Community', <Ref key='community' node={row.community} />],
          [
            'Last offering',
            row.last_offering_epoch !== null
              ? `epoch ${row.last_offering_epoch}`
              : 'none',
          ],
          [
            'Last answer',
            row.last_answer_epoch !== null
              ? `epoch ${row.last_answer_epoch}`
              : 'none',
          ],
        ]}
      />
    </Held>
  )
}

function DebtForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const isGod = kind === 'son' || kind === 'foreign_god'
  const isCommunity =
    kind !== null && (COMMUNITY_TYPES as readonly string[]).includes(kind)
  const [other, setOther] = useState<number | null>(null)
  const [offered, setOffered] = useState('30')
  const setting = useCycleAction(
    'debt:set',
    (_: void) => ({
      god_id: isGod ? nodeId : (other ?? 0),
      community_id: isGod ? (other ?? 0) : nodeId,
      offered: clamp(offered, MANY),
    }),
    'The ledger is set'
  )
  const wrong =
    isGod || isCommunity
      ? null
      : 'A ledger of offerings joins a god to a community'
  const busy = why(
    wrong ??
      (other === null
        ? isGod
          ? 'Choose the community'
          : 'Choose the god'
        : blocked),
    setting.isPending
  )
  return (
    <ForgeCard
      icon={HandHeart}
      tone='gold'
      title='Open a ledger of offerings'
      note='Set what a community has offered a god.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <HandHeart />
          Open it
        </Button>
      }
    >
      {isGod ? (
        <NodePicker
          label='Community'
          value={other}
          onChange={setOther}
          blocked={wrong ?? blocked}
          types={COMMUNITY_TYPES}
        />
      ) : (
        <NodePicker
          label='God'
          value={other}
          onChange={setOther}
          blocked={wrong ?? blocked}
          kinds={GOD_KINDS}
        />
      )}
      <NumberField
        label='Offered'
        value={offered}
        min={0}
        blocked={wrong ?? blocked}
        onChange={setOffered}
      />
    </ForgeCard>
  )
}

export function CircuitCard({
  row,
  blocked,
}: {
  row: CircuitView
  blocked: string | null
}) {
  const action = useRow(
    'circuit:edit',
    'circuit:delete',
    { circuit_id: row.id },
    blocked
  )
  const passing = useStep(
    'circuit:pass',
    { circuit_id: row.id },
    blocked,
    'The treasure moves on'
  )
  const [stops, setStops] = useState<number[]>(row.stops.map((stop) => stop.id))
  const routing = useCycleAction(
    'circuit:route',
    (_: void) => ({ circuit_id: row.id, stops }),
    'The circuit is laid anew'
  )
  const holder =
    row.stops.length > 0 ? row.stops[row.position % row.stops.length] : null
  return (
    <Held
      icon={Repeat}
      tone='verdigris'
      title={row.name}
      caption={`${plural(row.passes, 'pass', 'passes')} since epoch ${row.started_epoch}`}
      removeLabel='Stop the circuit'
      editTitle='Set the circuit'
      note='The treasure passes from each stop to the next every epoch, lending standing to its holder and binding the stops in regard.'
      fields={[
        { key: 'name', label: 'Called', kind: 'text' },
        {
          key: 'item_entity_id',
          label: 'Treasure',
          kind: 'node',
          types: ['item', 'artwork'],
        },
        { key: 'position', label: 'Stop it is at', kind: 'number', min: 0 },
        { key: 'passes', label: 'Passes', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Treasure',
            <Ref key='item' node={row.item} empty='a nameless gift' />,
          ],
          ['Held now by', <Ref key='holder' node={holder} empty='no one' />],
        ]}
      />
      <NodeChips nodes={row.stops} empty='No stops' icon={Route} />
      <NodeListPicker
        label='Stops'
        value={stops}
        types={STOP_TYPES}
        blocked={why(blocked, routing.isPending)}
        onChange={setStops}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Route}
          label='Lay these stops'
          busy={why(
            blocked ?? (stops.length < 2 ? 'A circuit needs two stops' : null),
            routing.isPending
          )}
          onClick={() => routing.mutate()}
        />
        <StepButton
          icon={Repeat}
          label='Pass the treasure on'
          busy={passing.busy}
          onClick={passing.run}
        />
      </div>
    </Held>
  )
}

export function CircuitForge({
  firstStop,
  blocked,
}: {
  firstStop: number | null
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [stops, setStops] = useState<number[]>(
    firstStop !== null ? [firstStop] : []
  )
  const creating = useCycleAction(
    'circuit:create',
    (_: void) => ({ name: name.trim(), stops, item_id: null }),
    'The circuit turns'
  )
  const busy = why(
    blocked ??
      (name.trim() === ''
        ? 'Name the circuit first'
        : stops.length < 2
          ? 'Choose at least two stops'
          : null),
    creating.isPending
  )
  return (
    <ForgeCard
      icon={Repeat}
      tone='verdigris'
      title='Set a ceremonial circuit turning'
      note='Choose the stops in order; the treasure passes around them forever.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => creating.mutate()}
        >
          <Repeat />
          Set it turning
        </Button>
      }
    >
      <TextField
        label='Called'
        value={name}
        blocked={blocked}
        onChange={setName}
      />
      <NodeListPicker
        label='Stops'
        value={stops}
        types={STOP_TYPES}
        blocked={blocked}
        onChange={setStops}
      />
    </ForgeCard>
  )
}

export function GiftLedger({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: CyclesView
  blocked: string | null
}) {
  const owed = data.gifts.filter(
    (gift) => OWED.has(gift.state) && gift.receiver.id === nodeId
  ).length
  const owing = data.gifts.filter(
    (gift) => OWED.has(gift.state) && gift.giver.id === nodeId
  ).length
  const isStop =
    kind !== null && (STOP_TYPES as readonly string[]).includes(kind)
  return (
    <div data-surface='GiftLedger' className='flex min-w-0 flex-col gap-4'>
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
          <KpiTile
            label='Balance of obligation'
            value={signed(data.gift_balance)}
            icon={Scale}
            tone={data.gift_balance >= 0 ? 'success' : 'warning'}
          />
          <KpiTile
            label='Returns it owes'
            value={owed}
            icon={Undo2}
            tone='warning'
          />
          <KpiTile
            label='Returns owed to it'
            value={owing}
            icon={Gift}
            tone='gold'
          />
        </div>
      </div>
      <Listed
        title='The gift ledger'
        items={data.gifts}
        empty='No gift has passed here.'
        noun={['gift', 'gifts']}
        itemKey={(item) => item.id}
      >
        {(item) => <GiftCard nodeId={nodeId} row={item} blocked={blocked} />}
      </Listed>
      <GiftForge nodeId={nodeId} blocked={blocked} />
      <Listed
        title='Gift debts with the gods'
        items={data.debts}
        empty='No ledger of offerings is kept here.'
        noun={['ledger', 'ledgers']}
        itemKey={(item) => `${item.god.id}-${item.community.id}`}
      >
        {(item) => <DebtCard row={item} blocked={blocked} />}
      </Listed>
      <DebtForge nodeId={nodeId} kind={kind} blocked={blocked} />
      <div data-surface='CircuitPanel' className='flex min-w-0 flex-col gap-4'>
        <Listed
          title='Ceremonial circuits'
          items={data.circuits}
          empty='No circuit passes through here.'
          noun={['circuit', 'circuits']}
          itemKey={(item) => item.id}
        >
          {(item) => <CircuitCard row={item} blocked={blocked} />}
        </Listed>
        <CircuitForge firstStop={isStop ? nodeId : null} blocked={blocked} />
      </div>
    </div>
  )
}
