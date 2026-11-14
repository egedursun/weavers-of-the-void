import { useState } from 'react'
import {
  Anvil,
  BatteryMedium,
  Ghost,
  Hourglass,
  KeyRound,
  Plus,
  Power,
  ScrollText,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { SOURCES } from '@/features/entity/lore/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type PursuitsNodeView, usePursuitsAction } from './api'
import {
  BINDINGS,
  BUILD_ICON,
  CONDITIONS,
  ORDERS,
  TOKENS,
  WILLS,
} from './labels'
import {
  ENTITY_KINDS,
  GOD_KINDS,
  MANY,
  MORTAL_TYPES,
  OWNER_TYPES,
  PRIORITIES,
  SPAN,
  SPIRIT_TYPES,
  TOKEN_TYPES,
  usePursuitsRow,
  usePursuitsStep,
  withNone,
} from './model'

type Construct = PursuitsNodeView['made'][number]
type Rules = PursuitsNodeView['instructions'][number]
type Order = Rules['orders'][number]

const TARGET_TYPES = [
  'mortal',
  'settlement',
  'structure',
  'polity',
  'beast',
  'army',
  'faction',
  'place',
  'region',
] as const
const HOLDER_KINDS: readonly string[] = [...ENTITY_KINDS, ...GOD_KINDS]
const HOLDER_TYPES = ['mortal', 'polity', 'faction', 'army'] as const
const MATERIAL_TABLE: Record<string, string> = MATERIAL_LABEL
const NO_SOUL = 'It holds no soul to release'
const NOT_A_CONSTRUCT =
  'A soul can be bound only into a construct; this is not one'

function ConstructCard({
  row,
  blocked,
}: {
  row: Construct
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'construct:edit',
    'construct:delete',
    { construct_id: row.body.id },
    blocked
  )
  const unmaking = usePursuitsStep(
    'construct:unmake',
    { construct_id: row.body.id },
    blocked,
    'The construct is stilled'
  )
  const freeing = usePursuitsStep(
    'construct:ensoul',
    { construct_id: row.body.id, spirit_id: null },
    blocked ?? (row.soul ? null : NO_SOUL),
    'The soul is released'
  )
  const will = WILLS[row.will]
  const source = SOURCES[row.power_source]
  return (
    <Held
      icon={BUILD_ICON}
      tone={
        row.will === 'full' || row.will === 'exceeding' ? 'danger' : will.tone
      }
      title={row.body.name}
      caption={`${MATERIAL_LABEL[row.material]} moved by ${source.label.toLowerCase()} · made in epoch ${row.made_epoch}`}
      removeLabel='Strip its construct record'
      editTitle='Set the construct'
      note='A construct burns power each epoch and its body wears away by the softness of its material; a living maker renews its power, by blood, by reagents or by devotion as its source demands. Run down or worn through, it stops for good. A bound soul lets it grow a will: first stirring, then its own, then beyond every order it was given.'
      fields={[
        { key: 'material', label: 'Body', kind: 'pick', table: MATERIAL_TABLE },
        {
          key: 'power_source',
          label: 'Moved by',
          kind: 'pick',
          table: table(SOURCES),
        },
        { key: 'power', label: 'Power', kind: 'number', min: 0, max: SPAN },
        {
          key: 'upkeep',
          label: 'Power burnt each epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'maker_entity_id',
          label: 'Maker',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        { key: 'decay', label: 'Wear', kind: 'number', min: 0, max: SPAN },
        { key: 'will', label: 'Will', kind: 'pick', table: table(WILLS) },
        {
          key: 'soul_entity_id',
          label: 'Bound soul',
          kind: 'node',
          types: SPIRIT_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={will} />}
    >
      <Meter
        label={`Power (${row.power} of ${SPAN})`}
        value={row.power}
        tone='info'
        icon={BatteryMedium}
      />
      <Meter
        label={`Wear (${row.decay} of ${SPAN})`}
        value={row.decay}
        tone='warning'
        icon={Hourglass}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile
            label='Power burnt each epoch'
            value={row.upkeep}
            icon={Power}
            tone='warning'
          />
          <KpiTile
            label='Will'
            value={will.label}
            icon={will.icon}
            tone={will.tone}
          />
        </div>
      </div>
      <Facts
        items={[
          ['Maker', <Ref key='maker' node={row.maker} empty='unknown' />],
          ['Bound soul', <Ref key='soul' node={row.soul} empty='none' />],
        ]}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Ghost}
          label='Release its soul'
          busy={freeing.busy}
          onClick={freeing.run}
        />
        <StepButton
          icon={Power}
          label='Still it for good'
          busy={unmaking.busy}
          onClick={unmaking.run}
        />
      </div>
    </Held>
  )
}

function SoulBinder({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [spirit, setSpirit] = useState<number | null>(null)
  const binding = usePursuitsAction(
    'construct:ensoul',
    (_: void) => ({ construct_id: nodeId, spirit_id: spirit }),
    'A soul is bound into it'
  )
  const busy = why(
    blocked ?? (spirit === null ? 'Choose a spirit' : null),
    binding.isPending
  )
  return (
    <ForgeCard
      icon={Ghost}
      tone='verdigris'
      title='Bind a soul into it'
      note='A spirit bound into a construct may let it grow a will of its own.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => binding.mutate()}
        >
          <Ghost />
          Bind it
        </Button>
      }
    >
      <NodePicker
        label='Spirit'
        value={spirit}
        onChange={setSpirit}
        blocked={blocked}
        types={SPIRIT_TYPES}
      />
    </ForgeCard>
  )
}

function BuildForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [maker, setMaker] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [material, setMaterial] = useState('')
  const [source, setSource] = useState('')
  const [token, setToken] = useState('')
  const [name, setName] = useState('')
  const building = usePursuitsAction(
    'construct:create',
    (_: void) => ({
      maker_id: maker ?? 0,
      material: material === '' ? null : (material as Construct['material']),
      source: source === '' ? null : (source as Construct['power_source']),
      token: token === '' ? null : (token as Rules['command_token']),
      name: name.trim() === '' ? null : name.trim(),
    }),
    'A construct is built'
  )
  const busy = why(
    blocked ?? (maker === null ? 'Choose the mortal who builds it' : null),
    building.isPending
  )
  return (
    <ForgeCard
      icon={Anvil}
      tone='gold'
      title='Build a construct'
      note='A maker builds a body, moves it by a power source and binds it to a command token: whoever holds the token commands it. Left open, its body is the hardest its people can work and its source and token are chosen for it.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => building.mutate()}
        >
          <Anvil />
          Build it
        </Button>
      }
    >
      <NodePicker
        label='Maker'
        value={maker}
        onChange={setMaker}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
      <MindPicker
        label='Body'
        value={material}
        table={MATERIAL_TABLE}
        placeholder='The hardest they can work'
        blocked={blocked}
        onPick={setMaterial}
      />
      <MindPicker
        label='Moved by'
        value={source}
        table={table(SOURCES)}
        placeholder='Let the maker choose'
        blocked={blocked}
        onPick={setSource}
      />
      <MindPicker
        label='Command token'
        value={token}
        table={table(TOKENS)}
        placeholder='Let the maker choose'
        blocked={blocked}
        onPick={setToken}
      />
      <TextField
        label='Name, or empty to name it for its maker'
        value={name}
        blocked={blocked}
        onChange={setName}
      />
    </ForgeCard>
  )
}

export function ConstructPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const bodies = [
    ...(data.as_construct ? [data.as_construct] : []),
    ...data.made,
  ]
  return (
    <div data-surface='ConstructPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-constructs'
        title='Power and wear of each construct'
        legend={[
          { text: 'Power', variant: 'secondary' },
          { text: 'The mark is its wear', variant: 'outline' },
        ]}
        rows={bodies.map((row) => ({
          key: row.body.id,
          caption: `${row.body.name}: power ${row.power}, wear ${row.decay}, ${WILLS[row.will].label.toLowerCase()}`,
          segments: [{ value: row.power, fill: 'fill-info' }],
          mark: row.decay,
        }))}
        max={SPAN}
        noun={['construct', 'constructs']}
        empty='No construct is this or was made by it.'
      />
      <Listed
        title='Constructs'
        items={bodies}
        empty='No construct is this or was made by it.'
        noun={['construct', 'constructs']}
        itemKey={(item) => item.body.id}
      >
        {(item) => <ConstructCard row={item} blocked={blocked} />}
      </Listed>
      <SoulBinder
        nodeId={nodeId}
        blocked={blocked ?? (data.as_construct ? null : NOT_A_CONSTRUCT)}
      />
      <BuildForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}

function OrderCard({ row, blocked }: { row: Order; blocked: string | null }) {
  const action = usePursuitsRow(
    'instruction_order:edit',
    'instruction_order:delete',
    { order_id: row.id },
    blocked
  )
  const order = ORDERS[row.kind]
  const condition = CONDITIONS[row.condition]
  return (
    <Held
      icon={order.icon}
      tone={row.lapsed ? 'muted' : order.tone}
      title={`${row.priority}. ${order.label}`}
      caption={`${condition.label}${row.until_epoch !== null ? ` · until epoch ${row.until_epoch}` : ''}${row.lapsed ? ' · lapsed' : ''}`}
      removeLabel='Strike out the order'
      editTitle='Set the order'
      note='Orders run in their priority each epoch, to the letter: a lost target leaves a literal construct working at nothing, while a loose one turns the order on its holder. An order kept while its maker lives lapses at the maker’s death, and one kept until an epoch lapses after it. Holding still stops every order below it.'
      fields={[
        { key: 'kind', label: 'Order', kind: 'pick', table: table(ORDERS) },
        {
          key: 'target_node_id',
          label: 'Aimed at',
          kind: 'node',
          types: TARGET_TYPES,
          kinds: GOD_KINDS,
        },
        {
          key: 'priority',
          label: 'Priority',
          kind: 'number',
          min: 0,
          max: PRIORITIES,
        },
        {
          key: 'condition',
          label: 'Kept',
          kind: 'pick',
          table: table(CONDITIONS),
        },
        {
          key: 'until_epoch',
          label: 'Until epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'lapsed', label: 'Lapsed', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={condition} />}
    >
      <Facts
        items={[
          [
            'Aimed at',
            <Ref key='target' node={row.target} empty='no one in particular' />,
          ],
        ]}
      />
    </Held>
  )
}

function OrderForge({
  rules,
  blocked,
}: {
  rules: Rules
  blocked: string | null
}) {
  const [kind, setKind] = useState('guard')
  const [target, setTarget] = useState<number | null>(null)
  const [priority, setPriority] = useState('1')
  const [condition, setCondition] = useState('always')
  const [until, setUntil] = useState('')
  const writing = usePursuitsAction(
    'instruction_order:create',
    (_: void) => ({
      set_id: rules.id,
      kind: kind as Order['kind'],
      target_id: target,
      priority: Number(priority || '1'),
      condition: condition as Order['condition'],
      until_epoch: until === '' ? null : Number(until),
    }),
    'A new order is written'
  )
  const busy = why(
    blocked ??
      (condition === 'until_date' && until === ''
        ? 'An order kept until an epoch needs that epoch'
        : null),
    writing.isPending
  )
  return (
    <ForgeCard
      icon={ScrollText}
      tone='info'
      title='Write an order'
      note='The order joins the others at the priority you give it.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => writing.mutate()}
        >
          <Plus />
          Write it
        </Button>
      }
    >
      <MindPicker
        label='Order'
        value={kind}
        table={table(ORDERS)}
        placeholder='Choose an order'
        blocked={blocked}
        onPick={setKind}
      />
      <NodePicker
        label='Aimed at'
        value={target}
        onChange={setTarget}
        blocked={blocked}
        types={TARGET_TYPES}
        kinds={GOD_KINDS}
      />
      <NumberField
        label='Priority'
        value={priority}
        min={0}
        max={PRIORITIES}
        blocked={blocked}
        onChange={setPriority}
      />
      <MindPicker
        label='Kept'
        value={condition}
        table={table(CONDITIONS)}
        placeholder='Always'
        blocked={blocked}
        onPick={setCondition}
      />
      <NumberField
        label='Until epoch'
        value={until}
        min={0}
        max={MANY}
        placeholder='No end'
        blocked={blocked}
        onChange={setUntil}
      />
    </ForgeCard>
  )
}

function RulesCard({ row, blocked }: { row: Rules; blocked: string | null }) {
  const action = usePursuitsRow(
    'instruction_set:edit',
    'instruction_set:delete',
    { set_id: row.id },
    blocked
  )
  const resolving = usePursuitsStep(
    'instruction_set:resolve',
    { set_id: row.id },
    blocked,
    'The orders answer the holder'
  )
  const binding = BINDINGS[row.binding]
  const token = TOKENS[row.command_token]
  return (
    <Held
      icon={binding.icon}
      tone={binding.tone}
      title={`Orders of ${row.owner.name}`}
      caption={`${binding.label} by ${token.label.toLowerCase()} · ${row.orders.length} orders`}
      removeLabel='Strike the orders away'
      editTitle='Set the instruction set'
      note='Whoever holds the command token commands the orders: the owner of a held item or network key, the ruler of an office, the heir of a bloodline, or whoever the word was given to. Steal the token and the construct answers the thief. A kill switch stills the construct once its will passes every order, if the keeper of the switch lives.'
      fields={[
        {
          key: 'binding',
          label: 'Bound by',
          kind: 'pick',
          table: table(BINDINGS),
        },
        {
          key: 'command_token',
          label: 'Command token',
          kind: 'pick',
          table: table(TOKENS),
        },
        {
          key: 'token_entity_id',
          label: 'The token itself',
          kind: 'node',
          types: TOKEN_TYPES,
        },
        {
          key: 'holder_node_id',
          label: 'Holder',
          kind: 'node',
          types: HOLDER_TYPES,
          kinds: HOLDER_KINDS,
        },
        {
          key: 'kill_switch',
          label: 'Kill switch',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'kill_token_entity_id',
          label: 'Keeper of the kill switch',
          kind: 'node',
          types: TOKEN_TYPES,
        },
        {
          key: 'literalness',
          label: 'Literalness',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={token} />}
    >
      <Meter
        label={`Literalness (${row.literalness} of ${SPAN})`}
        value={row.literalness}
        tone='info'
        icon={ScrollText}
      />
      <Facts
        items={[
          ['Owner', <Ref key='owner' node={row.owner} empty='none' />],
          [
            'The token itself',
            <Ref key='token' node={row.token} empty='no object' />,
          ],
          ['Holder', <Ref key='holder' node={row.holder} empty='no one' />],
          ['Kill switch', row.kill_switch ? 'set' : 'none'],
          [
            'Keeper of the kill switch',
            <Ref key='kill' node={row.kill_token} empty='the holder' />,
          ],
        ]}
      />
      <StepButton
        icon={KeyRound}
        label='Answer the holder now'
        busy={resolving.busy}
        onClick={resolving.run}
      />
      <Listed
        title='Orders'
        items={row.orders}
        empty='It carries no order yet.'
        noun={['order', 'orders']}
        itemKey={(item) => item.id}
      >
        {(item) => <OrderCard row={item} blocked={blocked} />}
      </Listed>
      <OrderForge rules={row} blocked={action.busy} />
    </Held>
  )
}

export function OrdersPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const owner = (OWNER_TYPES as readonly string[]).includes(kind ?? '')
  const [token, setToken] = useState('word')
  const [holder, setHolder] = useState<number | null>(null)
  const writing = usePursuitsAction(
    'instruction_set:create',
    (_: void) => ({
      owner_id: nodeId,
      token: token as Rules['command_token'],
      token_id: null,
      holder_id: holder,
    }),
    'The orders are bound to a token'
  )
  const busy = why(
    blocked ??
      (owner
        ? null
        : 'Only a construct or an army with construct stacks carries orders'),
    writing.isPending
  )
  return (
    <div data-surface='OrdersPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Orders and their tokens'
        items={data.instructions}
        empty='No orders are carried, held or keyed by this.'
        noun={['set of orders', 'sets of orders']}
        itemKey={(item) => item.id}
      >
        {(item) => <RulesCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={KeyRound}
        tone='verdigris'
        title='Bind orders to a token'
        note='Give this construct or army a fresh set of orders and name what commands them and who holds it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => writing.mutate()}
          >
            <KeyRound />
            Bind them
          </Button>
        }
      >
        <MindPicker
          label='Command token'
          value={token}
          table={withNone(table(TOKENS), 'No token')}
          placeholder='A spoken word'
          blocked={blocked}
          onPick={setToken}
        />
        <NodePicker
          label='Holder'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
          types={HOLDER_TYPES}
          kinds={GOD_KINDS}
        />
      </ForgeCard>
    </div>
  )
}
