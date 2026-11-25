import { useState } from 'react'
import { Flag, Gauge, Radar, ShieldAlert, Swords, Users } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp } from '@/features/cycles/model'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { named, unitIcon } from '@/features/wars/military/labels'
import { Tag } from '@/features/wars/military/parts'
import { type OperationsNodeView, useOperationsAction } from './api'
import { ECHELONS, ORDERS } from './labels'
import {
  MANY,
  MORTAL_TYPES,
  OWNER_TYPES,
  REGION_TYPES,
  SPAN,
  useOpsRow,
} from './model'

type Echelon = OperationsNodeView['echelons'][number]
type Stack = OperationsNodeView['stacks'][number]
type Theatre = OperationsNodeView['theatres'][number]

const NOT_OWNER =
  'Only a realm, a town, a people, a faction or a house raises formations and fronts'
const NO_WARS =
  'This realm is at war with no one, so it has no front to share reserves with'
const OWNER_KINDS = new Set<string>(OWNER_TYPES)

function EchelonCard({
  row,
  echelons,
  blocked,
}: {
  row: Echelon
  echelons: Echelon[]
  blocked: string | null
}) {
  const action = useOpsRow(
    'echelon:edit',
    'echelon:delete',
    { echelon_id: row.id },
    blocked
  )
  const level = ECHELONS[row.level]
  const order = ORDERS[row.order]
  const parents = Object.fromEntries(
    echelons
      .filter((item) => item.id !== row.id)
      .map((item) => [String(item.id), item.name])
  )
  const left = Math.max(0, row.command_points - row.points_spent)
  return (
    <Held
      icon={level.icon}
      tone={level.tone}
      title={row.name}
      caption={`${level.label} · formed in epoch ${row.formed_epoch}`}
      removeLabel='Strike the formation'
      editTitle='Set the formation'
      note='A headquarters directs the formations under it within its command range, spending command points on each order: attack costs more than the rest. A formation out of range, or past its headquarters’ points, acts on standing orders and loses organisation; one ordered to attack fights harder, to hold digs in, to manoeuvre regains order and to resupply is fed first. Staff skill comes from the commander and from sub-commanders and quartermasters.'
      fields={[
        { key: 'name', label: 'Formation name', kind: 'text' },
        {
          key: 'level',
          label: 'Echelon',
          kind: 'pick',
          table: table(ECHELONS),
        },
        {
          key: 'parent_id',
          label: 'Answers to',
          kind: 'pick',
          table: parents,
        },
        {
          key: 'commander_entity_id',
          label: 'Commander',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'hq_region_entity_id',
          label: 'Headquarters land',
          kind: 'node',
          types: REGION_TYPES,
        },
        {
          key: 'staff',
          label: 'Staff skill',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'command_range',
          label: 'Command range (lands)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'command_points',
          label: 'Command points',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'points_spent',
          label: 'Points spent',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'order', label: 'Order', kind: 'pick', table: table(ORDERS) },
        { key: 'in_range', label: 'In range', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge size='sm' variant='outline'>
            <order.icon aria-hidden='true' />
            {order.label}
          </Badge>
          {!row.in_range && (
            <Badge size='sm' variant='warning'>
              <Radar aria-hidden='true' />
              Out of range
            </Badge>
          )}
          <Badge size='sm' variant='secondary'>
            <Users aria-hidden='true' />
            {row.stacks} stacks
          </Badge>
        </div>
      }
    >
      <Meter label='Staff skill' value={row.staff} tone='info' icon={Gauge} />
      {row.level !== 'brigade' && (
        <Meter
          label={`Command points left (${left} of ${row.command_points})`}
          value={left}
          max={Math.max(1, row.command_points)}
          tone='legendary'
          icon={Flag}
        />
      )}
      <Facts
        items={[
          [
            'Commander',
            <Ref key='commander' node={row.commander} empty='no commander' />,
          ],
          [
            'Headquarters',
            <Ref key='hq' node={row.hq} empty='nowhere fixed' />,
          ],
          ['Command range', `${plural(row.command_range, 'land', 'lands')}`],
          [
            'Answers to',
            echelons.find((item) => item.id === row.parent_id)?.name ??
              'no headquarters above',
          ],
          [
            'Army',
            <Ref key='army' node={row.army} empty='a group of armies' />,
          ],
        ]}
      />
    </Held>
  )
}

const INDENT = [
  'ps-0',
  'ps-3 border-s border-dashed',
  'ps-6 border-s border-dashed',
  'ps-9 border-s border-dashed',
  'ps-12 border-s border-dashed',
]

function treeOrder(echelons: Echelon[]): [Echelon, number][] {
  const known = new Set(echelons.map((item) => item.id))
  const found: [Echelon, number][] = []
  const seen = new Set<number>()
  const walk = (parent: number | null, depth: number) => {
    for (const item of echelons) {
      const top = item.parent_id === null || !known.has(item.parent_id)
      if (
        (parent === null ? top : item.parent_id === parent) &&
        !seen.has(item.id)
      ) {
        seen.add(item.id)
        found.push([item, depth])
        walk(item.id, depth + 1)
      }
    }
  }
  walk(null, 0)
  return found
}

function Overview({ echelons }: { echelons: Echelon[] }) {
  return (
    <div
      data-chart='chart-order-of-battle'
      className='flex min-w-0 flex-col gap-1 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <Label variant='overline'>The order of battle at a glance</Label>
      <ul className='flex min-w-0 flex-col gap-1' aria-label='Order of battle'>
        <Paged items={treeOrder(echelons)} as='li'>
          {([item, depth]) => {
            const level = ECHELONS[item.level]
            const order = ORDERS[item.order]
            return (
              <li
                key={item.id}
                className={`flex min-w-0 flex-wrap items-center gap-1.5 ${INDENT[Math.min(depth, INDENT.length - 1)]}`}
              >
                <Tag item={level} text={level.label} />
                <Text as='span' variant='caption' className='min-w-0 truncate'>
                  {item.name}
                </Text>
                <Tag item={order} />
                {!item.in_range && (
                  <Badge size='sm' variant='warning'>
                    <Radar aria-hidden='true' />
                    Out of range
                  </Badge>
                )}
                {item.level === 'brigade' ? (
                  <Muted as='span' variant='caption'>
                    {item.stacks} stacks
                  </Muted>
                ) : (
                  <Muted as='span' variant='caption'>
                    {Math.max(0, item.command_points - item.points_spent)} of{' '}
                    {item.command_points} points left
                  </Muted>
                )}
              </li>
            )
          }}
        </Paged>
      </ul>
    </div>
  )
}

function Tree({
  echelons,
  blocked,
}: {
  echelons: Echelon[]
  blocked: string | null
}) {
  return (
    <div
      className='flex min-w-0 flex-col gap-2'
      role='group'
      aria-label='The order of battle'
    >
      {treeOrder(echelons).map(([item, depth]) => (
        <ul
          key={item.id}
          className={`flex min-w-0 flex-col ${INDENT[Math.min(depth, INDENT.length - 1)]}`}
        >
          <EchelonCard row={item} echelons={echelons} blocked={blocked} />
        </ul>
      ))}
    </div>
  )
}

function StackRow({
  row,
  brigades,
  blocked,
}: {
  row: Stack
  brigades: Echelon[]
  blocked: string | null
}) {
  const [target, setTarget] = useState(
    row.echelon_id !== null ? String(row.echelon_id) : ''
  )
  const assigning = useOperationsAction(
    'echelon:assign',
    (_: void) => ({
      stack_id: row.id,
      echelon_id: target === '' ? null : Number(target),
    }),
    'The stack answers to its formation'
  )
  const options = Object.fromEntries(
    brigades.map((item) => [String(item.id), item.name])
  )
  const busy = why(
    brigades.length === 0 ? 'The army has no formation to answer to' : blocked,
    assigning.isPending
  )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 flex-1 flex-wrap items-center gap-2'>
        <Tag
          item={{
            label: named({}, row.unit_kind).label,
            icon: unitIcon(row.unit_kind, Users),
            tone: 'muted',
          }}
          text={`${named({}, row.unit_kind).label} · ${plural(row.count, 'soldier', 'soldiers')}`}
        />
        {row.locked.includes('echelon_id') && (
          <Muted variant='caption'>held to its formation</Muted>
        )}
      </div>
      <MindPicker
        label='Formation'
        value={target}
        table={options}
        blocked={busy}
        placeholder='No formation'
        onPick={setTarget}
      />
      <Button
        act={assigning}
        size='sm'
        variant='secondary'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => assigning.mutate()}
      >
        <Flag />
        Put it there
      </Button>
    </div>
  )
}

function EchelonForge({
  nodeId,
  kind,
  echelons,
  blocked,
}: {
  nodeId: number
  kind: string | null
  echelons: Echelon[]
  blocked: string | null
}) {
  const isArmy = kind === 'army'
  const isOwner = OWNER_KINDS.has(kind ?? '')
  const [level, setLevel] = useState<keyof typeof ECHELONS>(
    isArmy ? 'brigade' : 'army_group'
  )
  const [name, setName] = useState('')
  const [parent, setParent] = useState('')
  const [commander, setCommander] = useState<number | null>(null)
  const [owner, setOwner] = useState<number | null>(
    isOwner ? nodeId : (echelons[0]?.owner.id ?? null)
  )
  const forming = useOperationsAction(
    'echelon:create',
    (_: void) => ({
      owner_id: owner ?? 0,
      level,
      name: name.trim(),
      army_id: isArmy ? nodeId : null,
      parent_id: parent === '' ? null : Number(parent),
      commander_id: commander,
    }),
    'The formation takes its place'
  )
  const gate =
    isArmy || isOwner ? blocked : 'Only an army or its realm forms formations'
  const busy = why(
    gate ??
      (owner === null
        ? 'Choose the realm the formation serves'
        : name.trim() === ''
          ? 'Name the formation'
          : null),
    forming.isPending
  )
  return (
    <ForgeCard
      icon={Flag}
      tone='info'
      title='Form a formation'
      note='Add an army group, an army, a corps, a division or a brigade to the order of battle, under a headquarters of your choosing. The engine keeps forming brigades as stacks gather; a formation you raise keeps its place and its commander.'
      columns={3}
      action={
        <Button
          act={forming}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => forming.mutate()}
        >
          <Flag />
          Form it
        </Button>
      }
    >
      <MindPicker
        label='Echelon'
        value={level}
        table={table(ECHELONS)}
        blocked={gate}
        onPick={(value) => setLevel(value as keyof typeof ECHELONS)}
      />
      <TextField
        label='Formation name'
        value={name}
        blocked={gate}
        onChange={setName}
      />
      <MindPicker
        label='Answers to'
        value={parent}
        table={Object.fromEntries(
          echelons.map((item) => [String(item.id), item.name])
        )}
        blocked={gate}
        placeholder='No headquarters above'
        onPick={setParent}
      />
      <NodePicker
        label='Commander'
        value={commander}
        onChange={setCommander}
        blocked={gate}
        types={MORTAL_TYPES}
      />
      <NodePicker
        label='Realm it serves'
        value={owner}
        onChange={setOwner}
        blocked={gate}
        types={OWNER_TYPES}
      />
    </ForgeCard>
  )
}

export function OrderOfBattlePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: OperationsNodeView
  blocked: string | null
}) {
  const brigades = data.echelons.filter((item) => item.level === 'brigade')
  return (
    <div
      data-surface='OrderOfBattlePanel'
      className='flex min-w-0 flex-col gap-4'
    >
      {data.echelons.length > 0 ? (
        <>
          <Overview echelons={data.echelons} />
          <Tree echelons={data.echelons} blocked={blocked} />
        </>
      ) : (
        <Muted variant='caption'>
          No order of battle is drawn here yet. Armies form theirs on the next
          epoch, or you can form one below.
        </Muted>
      )}
      <Listed
        title='Stacks and the formations they answer to'
        items={data.stacks}
        empty='No stacks march here.'
        noun={['stack', 'stacks']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <StackRow row={item} brigades={brigades} blocked={blocked} />
        )}
      </Listed>
      <EchelonForge
        nodeId={nodeId}
        kind={kind}
        echelons={data.echelons}
        blocked={blocked}
      />
    </div>
  )
}

function TheatreCard({
  row,
  blocked,
}: {
  row: Theatre
  blocked: string | null
}) {
  const action = useOpsRow(
    'theatre:edit',
    'theatre:delete',
    { theatre_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Swords}
      tone={row.misjudged ? 'danger' : 'warning'}
      title={`Front against ${row.front?.name ?? 'an unknown land'}`}
      caption={`${row.war?.name ?? 'A war'} · read in epoch ${row.updated_epoch}`}
      removeLabel='Let the front be drawn anew'
      editTitle='Set the theatre'
      note='The marshal shares the realm’s reserves, levies and transport between its fronts by how great each threat looks. A marshal with little strategy misreads the threats, and a misjudged front starves the one that needed the soldiers; the share sent reinforces that front’s army each epoch.'
      fields={[
        {
          key: 'front_region_entity_id',
          label: 'Front land',
          kind: 'node',
          types: REGION_TYPES,
        },
        {
          key: 'marshal_entity_id',
          label: 'Marshal',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'priority',
          label: 'Share of reserves',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'believed_threat',
          label: 'Believed threat',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'true_threat',
          label: 'True threat',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'reserves',
          label: 'Reserves',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'levies', label: 'Levies', kind: 'number', min: 0, max: MANY },
        {
          key: 'transport',
          label: 'Transport',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'misjudged', label: 'Misjudged', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        row.misjudged ? (
          <Badge size='sm' variant='destructive'>
            <ShieldAlert aria-hidden='true' />
            Misjudged
          </Badge>
        ) : undefined
      }
    >
      <Meter
        label='Share of reserves'
        value={row.priority}
        tone='legendary'
        icon={Flag}
      />
      <Meter
        label='Believed threat'
        value={row.believed_threat}
        tone='warning'
        icon={Radar}
      />
      <Meter
        label='True threat'
        value={row.true_threat}
        tone='destructive'
        icon={Swords}
      />
      <Facts
        items={[
          [
            'Marshal',
            <Ref key='marshal' node={row.marshal} empty='no marshal' />,
          ],
          ['Reserves', String(row.reserves)],
          ['Levies', String(row.levies)],
          ['Transport', String(row.transport)],
        ]}
      />
    </Held>
  )
}

export function TheatresPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: OperationsNodeView
  blocked: string | null
}) {
  const [war, setWar] = useState(
    data.wars[0] ? String(data.wars[0].war_id) : ''
  )
  const [priority, setPriority] = useState('50')
  const setting = useOperationsAction(
    'theatre:set',
    (_: void) => ({
      owner_id: nodeId,
      war_id: Number(war),
      priority: clamp(priority),
    }),
    'The front’s share is set'
  )
  const gate = !OWNER_KINDS.has(kind ?? '')
    ? NOT_OWNER
    : data.wars.length === 0
      ? NO_WARS
      : blocked
  const busy = why(
    gate ?? (war === '' ? 'Choose the war' : null),
    setting.isPending
  )
  return (
    <div data-surface='TheatresPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Theatres of war'
        items={data.theatres}
        empty='No front is drawn here.'
        noun={['theatre', 'theatres']}
        itemKey={(item) => item.id}
      >
        {(item) => <TheatreCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Swords}
        tone='warning'
        title='Share the reserves of a front'
        note='Set how much of the realm’s reserves, levies and transport go to the front of one of its wars. The other fronts share what is left.'
        columns={2}
        action={
          <Button
            act={setting}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Swords />
            Set the share
          </Button>
        }
      >
        <MindPicker
          label='War'
          value={war}
          table={Object.fromEntries(
            data.wars.map((item) => [
              String(item.war_id),
              `${item.war?.name ?? 'A war'} against ${item.enemy.name}`,
            ])
          )}
          blocked={gate}
          onPick={setWar}
        />
        <NumberField
          label='Share of reserves'
          value={priority}
          min={0}
          max={SPAN}
          blocked={gate}
          onChange={setPriority}
        />
      </ForgeCard>
    </div>
  )
}
