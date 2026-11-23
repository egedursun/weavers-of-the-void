import { useState } from 'react'
import {
  Backpack,
  Brain,
  Compass,
  FastForward,
  Flame,
  Gem,
  HeartPulse,
  Home,
  Pill,
  Snowflake,
  Sparkles,
  Telescope,
  Undo2,
  UserPlus,
  Wrench,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MODES } from '@/features/entity/environment/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type OperationsNodeView, useOperationsAction } from './api'
import {
  EVENTS,
  EXPEDITION_STATUS,
  GROUNDS,
  QUIRK_EFFECTS,
  QUIRK_LABELS,
  RESOLVES,
  ROLES,
} from './labels'
import {
  MANY,
  MORTAL_TYPES,
  SPAN,
  STRESS_SPAN,
  share,
  useOpsRow,
  useOpsStep,
} from './model'

type Expedition = OperationsNodeView['expeditions'][number]
type Member = Expedition['members'][number]
type Entry = Expedition['log'][number]
type Quirk = OperationsNodeView['quirks'][number]
type MovementMode = components['schemas']['MovementMode']

const NOT_MORTAL = 'Only a mortal bears quirks'
const NOT_LEADER = 'Only a mortal leads an expedition'
const OVER = 'That expedition is over'
const ANY_PLACE = [
  'region',
  'place',
  'structure',
  'spirit',
  'phenomenon',
  'settlement',
] as const

function MemberCard({ row, blocked }: { row: Member; blocked: string | null }) {
  const action = useOpsRow(
    'expedition_member:edit',
    'expedition_member:delete',
    { member_id: row.id },
    blocked
  )
  const role = ROLES[row.role]
  const resolve = RESOLVES[row.resolve]
  return (
    <Held
      icon={role.icon}
      tone={row.fallen ? 'danger' : resolve.tone}
      title={row.mortal.name}
      caption={`${role.label} · ${resolve.label}${row.fallen ? ' · fallen' : ''}`}
      removeLabel='Send home'
      editTitle='Set the member'
      note='Stress gathers on every leg, more in the dark and from harm. Past its limit a member breaks into an affliction that harms the party (paranoid, hopeless, selfish, abusive) or rises to a virtue that helps it (courageous, focused, stalwart). Cold, wet, hunger and fatigue gather too, and past their limit they harm.'
      fields={[
        {
          key: 'role',
          label: 'Role in the party',
          kind: 'pick',
          table: table(ROLES),
        },
        {
          key: 'stress',
          label: 'Stress',
          kind: 'number',
          min: 0,
          max: STRESS_SPAN,
        },
        {
          key: 'resolve',
          label: 'Resolve',
          kind: 'pick',
          table: table(RESOLVES),
        },
        { key: 'cold', label: 'Cold', kind: 'number', min: 0, max: SPAN },
        { key: 'wet', label: 'Wet', kind: 'number', min: 0, max: SPAN },
        { key: 'hunger', label: 'Hunger', kind: 'number', min: 0, max: SPAN },
        { key: 'fatigue', label: 'Fatigue', kind: 'number', min: 0, max: SPAN },
        { key: 'fallen', label: 'Fallen', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={resolve} />}
    >
      <Meter
        label={`Stress (${row.stress} of ${STRESS_SPAN})`}
        value={row.stress}
        max={STRESS_SPAN}
        tone='destructive'
        icon={Brain}
      />
      <Meter label='Cold' value={row.cold} tone='info' icon={Snowflake} />
      <Meter label='Wet' value={row.wet} tone='verdigris' icon={Snowflake} />
      <Meter label='Hunger' value={row.hunger} tone='warning' icon={Backpack} />
      <Meter
        label='Fatigue'
        value={row.fatigue}
        tone='muted'
        icon={HeartPulse}
      />
    </Held>
  )
}

function LogCard({ row, blocked }: { row: Entry; blocked: string | null }) {
  const action = useOpsRow(
    'expedition_log:edit',
    'expedition_log:delete',
    { log_id: row.id },
    blocked
  )
  const event = EVENTS[row.event]
  const details = [
    row.provisions_used > 0
      ? `${plural(row.provisions_used, 'provision', 'provisions')}`
      : null,
    row.light_used > 0 ? `${row.light_used} light` : null,
    row.resolve ? RESOLVES[row.resolve].label.toLowerCase() : null,
    row.quirk ? QUIRK_LABELS[row.quirk].label.toLowerCase() : null,
    row.stress > 0 ? `stress ${row.stress}` : null,
  ].filter((item) => item !== null)
  return (
    <Held
      icon={event.icon}
      tone={event.tone}
      title={`${event.label}${row.member ? `: ${row.member.name}` : ''}`}
      caption={`Leg ${row.leg} · epoch ${row.epoch}${details.length ? ` · ${details.join(', ')}` : ''}`}
      removeLabel='Strike the entry'
      editTitle='Set the entry'
      note='Each leg, room, camp, ambush and turn of mind on the way is kept in the expedition’s log.'
      fields={[
        {
          key: 'event',
          label: 'What happened',
          kind: 'pick',
          table: table(EVENTS),
        },
        { key: 'leg', label: 'Leg', kind: 'number', min: 0, max: MANY },
        {
          key: 'member_entity_id',
          label: 'Member',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'provisions_used',
          label: 'Provisions used',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'light_used',
          label: 'Light used',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'stress',
          label: 'Stress',
          kind: 'number',
          min: 0,
          max: STRESS_SPAN,
        },
        {
          key: 'resolve',
          label: 'Resolve',
          kind: 'pick',
          table: table(RESOLVES),
        },
        {
          key: 'quirk',
          label: 'Quirk',
          kind: 'pick',
          table: table(QUIRK_LABELS),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function MemberForge({
  row,
  blocked,
}: {
  row: Expedition
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(null)
  const [role, setRole] = useState<keyof typeof ROLES>('porter')
  const adding = useOperationsAction(
    'expedition_member:create',
    (_: void) => ({ expedition_id: row.id, mortal_id: mortal ?? 0, role }),
    'A member joins the party'
  )
  const busy = why(
    blocked ?? (mortal === null ? 'Choose who joins' : null),
    adding.isPending
  )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <NodePicker
        label='Who joins'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
      <MindPicker
        label='Role'
        value={role}
        table={table(ROLES)}
        blocked={blocked}
        onPick={(value) => setRole(value as keyof typeof ROLES)}
      />
      <Button
        size='sm'
        variant='secondary'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => adding.mutate()}
      >
        <UserPlus />
        Add to the party
      </Button>
    </div>
  )
}

function ExpeditionCard({
  row,
  blocked,
}: {
  row: Expedition
  blocked: string | null
}) {
  const action = useOpsRow(
    'expedition:edit',
    'expedition:delete',
    { expedition_id: row.id },
    blocked
  )
  const over = row.status === 'returned' || row.status === 'lost'
  const pressing = useOpsStep(
    'expedition:advance',
    { expedition_id: row.id, legs: 1 },
    over ? OVER : blocked,
    'The expedition presses on'
  )
  const recalling = useOpsStep(
    'expedition:recall',
    { expedition_id: row.id },
    over ? OVER : blocked,
    'The expedition turns for home'
  )
  const status = EXPEDITION_STATUS[row.status]
  const ground = GROUNDS[row.ground]
  return (
    <Held
      icon={ground.icon}
      tone={status.tone}
      title={row.name}
      caption={`${status.label} · ${ground.label.toLowerCase()} · set out in epoch ${row.started_epoch}${row.ended_epoch !== null ? `, ended in epoch ${row.ended_epoch}` : ''}`}
      removeLabel='Strike the expedition'
      editTitle='Set the expedition'
      note='An expedition goes leg by leg into a site, the wilds, an underworld or another realm. Each leg eats provisions and burns light; without light it walks in the dark, where danger and stress rise. Scouts and guides lower the danger, healers spend medicine on exposure, fighters turn aside ambushes, scholars read finds from inscriptions and porters carry more. Camps rest the party at the cost of provisions and may be ambushed at night.'
      fields={[
        { key: 'name', label: 'Expedition name', kind: 'text' },
        {
          key: 'leader_entity_id',
          label: 'Leader',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'sponsor_node_id',
          label: 'Sponsor',
          kind: 'node',
          types: ['polity', 'faction', 'cult', 'house', 'mortal'],
        },
        {
          key: 'target_entity_id',
          label: 'Destination',
          kind: 'node',
          types: ANY_PLACE,
        },
        { key: 'ground', label: 'Ground', kind: 'pick', table: table(GROUNDS) },
        {
          key: 'status',
          label: 'Status',
          kind: 'pick',
          table: table(EXPEDITION_STATUS),
        },
        {
          key: 'legs_done',
          label: 'Legs travelled',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'legs_total',
          label: 'Legs in all',
          kind: 'number',
          min: 1,
          max: SPAN,
        },
        {
          key: 'provisions',
          label: 'Provisions',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'light', label: 'Light', kind: 'number', min: 0, max: MANY },
        { key: 'tools', label: 'Tools', kind: 'number', min: 0, max: MANY },
        {
          key: 'medicine',
          label: 'Medicine',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'darkness',
          label: 'Darkness',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'danger', label: 'Danger', kind: 'number', min: 0, max: SPAN },
        { key: 'found', label: 'Finds', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Tag item={status} />
          <StepButton
            icon={FastForward}
            label='Press on a leg'
            busy={pressing.busy}
            onClick={pressing.run}
          />
          <StepButton
            icon={Undo2}
            label='Recall it'
            busy={recalling.busy}
            onClick={recalling.run}
          />
        </div>
      }
    >
      <div
        data-chart='chart-expedition-log'
        className='flex min-w-0 flex-col gap-3'
      >
        <Meter
          label={`Legs travelled (${row.legs_done} of ${row.legs_total})`}
          value={share(row.legs_done, row.legs_total)}
          tone='success'
          icon={Compass}
        />
        <div className='@container/tiles min-w-0'>
          <div className='grid min-w-0 grid-cols-2 gap-2 @lg/tiles:grid-cols-5'>
            <KpiTile
              label='Provisions'
              value={row.provisions}
              icon={Backpack}
              tone='gold'
            />
            <KpiTile
              label='Light'
              value={row.light}
              icon={Flame}
              tone='warning'
            />
            <KpiTile
              label='Tools'
              value={row.tools}
              icon={Wrench}
              tone='muted'
            />
            <KpiTile
              label='Medicine'
              value={row.medicine}
              icon={Pill}
              tone='success'
            />
            <KpiTile
              label='Finds'
              value={row.found}
              icon={Gem}
              tone='verdigris'
            />
          </div>
        </div>
        <Meter
          label='Darkness'
          value={row.darkness}
          tone='muted'
          icon={Telescope}
        />
        <Meter
          label='Danger'
          value={row.danger}
          tone='destructive'
          icon={Sparkles}
        />
        <Facts
          items={[
            [
              'Leader',
              <Ref key='leader' node={row.leader} empty='no leader' />,
            ],
            [
              'Destination',
              <Ref key='target' node={row.target} empty='nowhere' />,
            ],
            ['Sponsor', <Ref key='sponsor' node={row.sponsor} empty='none' />],
          ]}
        />
        {row.missing_roles.length > 0 ? (
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label>Missing roles, and the risk each leaves</Label>
            <PagedList
              items={row.missing_roles}
              initial={6}
              noun={['role', 'roles']}
              as='div'
              className='flex min-w-0 flex-wrap gap-1.5'
              itemKey={(item) => item}
            >
              {(item) => (
                <Tag
                  key={item}
                  item={{ ...ROLES[item], tone: 'warning' }}
                  text={`No ${ROLES[item].label.toLowerCase()}`}
                />
              )}
            </PagedList>
          </div>
        ) : (
          <Muted variant='caption'>Every role of the party is filled.</Muted>
        )}
        <Listed
          title='The party'
          items={row.members}
          empty='No one walks with it.'
          noun={['member', 'members']}
          itemKey={(item) => item.id}
        >
          {(item) => <MemberCard row={item} blocked={blocked} />}
        </Listed>
        <MemberForge row={row} blocked={blocked} />
        <Listed
          title='The log'
          items={row.log}
          empty='Nothing is written in its log yet.'
          noun={['entry', 'entries']}
          itemKey={(item) => item.id}
        >
          {(item) => <LogCard row={item} blocked={blocked} />}
        </Listed>
      </div>
    </Held>
  )
}

const BEST_WAY = 'best'
const WAY_TABLE = {
  [BEST_WAY]: 'The way with the best passage',
  ...table(MODES),
}

function ExpeditionForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [leader, setLeader] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [target, setTarget] = useState<number | null>(
    kind !== 'mortal' ? nodeId : null
  )
  const [first, setFirst] = useState<number | null>(null)
  const [second, setSecond] = useState<number | null>(null)
  const [way, setWay] = useState(BEST_WAY)
  const sending = useOperationsAction(
    'expedition:create',
    (_: void) => ({
      leader_id: leader ?? 0,
      target_id: target ?? 0,
      companion_ids: [first, second].filter(
        (item): item is number => item !== null
      ),
      mode: way === BEST_WAY ? null : (way as MovementMode),
    }),
    'The expedition sets out'
  )
  const busy = why(
    blocked ??
      (leader === null
        ? NOT_LEADER
        : target === null
          ? 'Choose where it goes'
          : null),
    sending.isPending
  )
  return (
    <ForgeCard
      icon={Compass}
      tone='success'
      title='Send an expedition'
      note='Choose a mortal to lead it, where it goes, how it travels and up to two companions. Its ground (a site, the wilds, an underworld or another realm), legs, provisions and light follow from where it goes and who it takes; a way of travel that finds little passage there adds legs, and your hand carries them by a way their bodies could not take alone.'

      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => sending.mutate()}
        >
          <Compass />
          Send it
        </Button>
      }
    >
      <NodePicker
        label='Leader'
        value={leader}
        onChange={setLeader}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
      <NodePicker
        label='Destination'
        value={target}
        onChange={setTarget}
        blocked={blocked}
        types={ANY_PLACE}
      />
      <MindPicker
        label='Way of travel'
        value={way}
        table={WAY_TABLE}
        placeholder='Choose'
        blocked={blocked}
        onPick={setWay}
      />
      <NodePicker
        label='A companion'
        value={first}
        onChange={setFirst}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
      <NodePicker
        label='Another companion'
        value={second}
        onChange={setSecond}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
    </ForgeCard>
  )
}

export function ExpeditionPanel({
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
  return (
    <div data-surface='ExpeditionPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Expeditions'
        items={data.expeditions}
        empty='No expedition has set out from here or for here.'
        noun={['expedition', 'expeditions']}
        itemKey={(item) => item.id}
      >
        {(item) => <ExpeditionCard row={item} blocked={blocked} />}
      </Listed>
      <ExpeditionForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}

function QuirkCard({
  row,
  expeditions,
  blocked,
}: {
  row: Quirk
  expeditions: Expedition[]
  blocked: string | null
}) {
  const origin = expeditions.find((item) => item.id === row.expedition_id)
  const action = useOpsRow(
    'quirk:edit',
    'quirk:delete',
    { quirk_id: row.id },
    blocked
  )
  const look = QUIRK_LABELS[row.quirk_kind]
  return (
    <Held
      icon={look.icon}
      tone={look.tone}
      title={look.label}
      caption={`Strength ${row.strength} · taken in epoch ${row.gained_epoch}`}
      removeLabel='Take the quirk away'
      editTitle='Set the quirk'
      note={QUIRK_EFFECTS[row.quirk_kind]}
      fields={[
        {
          key: 'kind',
          label: 'Quirk',
          kind: 'pick',
          table: table(QUIRK_LABELS),
        },
        {
          key: 'source_entity_id',
          label: 'Left by',
          kind: 'node',
          types: ANY_PLACE,
        },
        { key: 'strength', label: 'Strength', kind: 'number', min: 1, max: 3 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Muted variant='caption'>{QUIRK_EFFECTS[row.quirk_kind]}</Muted>
      <Facts
        items={[
          [
            'Left by',
            <Ref key='source' node={row.source} empty='its own nature' />,
          ],
          [
            'From expedition',
            origin
              ? origin.name
              : row.expedition_id !== null
                ? 'an expedition long past'
                : 'none',
          ],
        ]}
      />
    </Held>
  )
}

export function QuirksPanel({
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
  const gate = kind === 'mortal' ? blocked : NOT_MORTAL
  const [quirk, setQuirk] = useState<keyof typeof QUIRK_LABELS>('hardy')
  const [source, setSource] = useState<number | null>(null)
  const giving = useOperationsAction(
    'quirk:create',
    (_: void) => ({ mortal_id: nodeId, kind: quirk, source_id: source }),
    'The quirk marks the mortal'
  )
  const busy = why(gate, giving.isPending)
  return (
    <div data-surface='QuirksPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Quirks'
        items={data.quirks}
        empty='No quirk marks this mortal.'
        noun={['quirk', 'quirks']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <QuirkCard
            row={item}
            expeditions={data.expeditions}
            blocked={blocked}
          />
        )}
      </Listed>
      <ForgeCard
        icon={Sparkles}
        tone='info'
        title='Leave a quirk'
        note='Mark the mortal with a quirk, as a place or an event would. It stays with them and changes how they fare on expeditions and how often they set out; given again, it grows stronger.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => giving.mutate()}
          >
            <Home />
            Leave it
          </Button>
        }
      >
        <MindPicker
          label='Quirk'
          value={quirk}
          table={table(QUIRK_LABELS)}
          blocked={gate}
          onPick={(value) => setQuirk(value as keyof typeof QUIRK_LABELS)}
        />
        <NodePicker
          label='Left by'
          value={source}
          onChange={setSource}
          blocked={gate}
          types={ANY_PLACE}
        />
      </ForgeCard>
    </div>
  )
}
