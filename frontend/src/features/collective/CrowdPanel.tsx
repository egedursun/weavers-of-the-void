import { useState } from 'react'
import {
  Flag,
  Flame,
  Gauge,
  Lock,
  Megaphone,
  Shield,
  Unlock,
  Users,
  Wind,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type CollectiveView, useCollectiveAction } from './api'
import {
  ACTS,
  MOB_ENDS,
  MOB_STATES,
  MOB_TARGETS,
  OUTCOMES,
  SECTION_ICONS,
  TRIGGERS,
  FEELINGS,
} from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { Held, Listed } from './parts'

type Mood = NonNullable<CollectiveView['mood']>
type Cascade = CollectiveView['cascades'][number]
type Mob = CollectiveView['mobs'][number]
type Movement = CollectiveView['movements'][number]

const NOT_A_TOWN =
  'Crowds gather only in towns; choose a settlement to raise one.'

function FeelingTile({
  townId,
  feeling,
  blocked,
}: {
  townId: number
  feeling: Mood['feelings'][number]
  blocked: string | null
}) {
  const spec = FEELINGS[feeling.feeling]
  const [level, setLevel] = useState(String(feeling.level))
  const setting = useCollectiveAction(
    'crowd_feeling:set',
    (hold: boolean) => ({
      town_id: townId,
      feeling: feeling.feeling,
      level: clamp(level),
      hold,
    }),
    `${spec.label} is set`
  )
  const busy = why(blocked, setting.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md surface-sheen p-2'>
      <KpiTile
        label={spec.label}
        value={feeling.level}
        icon={spec.icon}
        tone={spec.tone}
        meter={{ value: feeling.level, max: SPAN, label: spec.label }}
      />
      <NumberField
        label={`Set ${spec.label.toLowerCase()}`}
        value={level}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setLevel}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate(true)}
        >
          <Lock />
          {feeling.held ? 'Keep held' : 'Set and hold'}
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate(false)}
        >
          <Unlock />
          Set free
        </Button>
      </div>
    </div>
  )
}

function MoodBoard({
  townId,
  mood,
  blocked,
}: {
  townId: number
  mood: Mood
  blocked: string | null
}) {
  const action = useRow(
    'crowd_mood:edit',
    'crowd_mood:delete',
    { town_id: townId },
    blocked
  )
  const last = mood.last_trigger ? TRIGGERS[mood.last_trigger] : null
  const peak = Math.max(0, ...mood.feelings.map((item) => item.level))
  return (
    <Held
      icon={SECTION_ICONS.crowds}
      tone={peak >= 60 ? 'danger' : 'gold'}
      title='The mood of the town'
      caption={
        last
          ? `Last stirred by ${last.label.toLowerCase()}`
          : 'Nothing has stirred it this epoch'
      }
      removeLabel='Let it be read anew'
      editTitle='Set the watch and the agitators'
      note='Each crowd act grows from the feeling its catalogue names; the watch deters every act and a charismatic voice sways them.'
      fields={[
        {
          key: 'deterrence',
          label: 'Deterrence of the watch',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'agitation',
          label: 'Sway of agitators',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'last_trigger',
          label: 'Last stirred by',
          kind: 'pick',
          table: { none: 'Nothing yet', ...table(TRIGGERS) },
        },
      ]}
      locked={mood.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-2 @3xl/tiles:grid-cols-3'>
          {mood.feelings.map((item) => (
            <FeelingTile
              key={item.feeling}
              townId={townId}
              feeling={item}
              blocked={action.busy}
            />
          ))}
          <KpiTile
            label='Deterrence'
            value={mood.deterrence}
            icon={Shield}
            tone='info'
            meter={{ value: mood.deterrence, max: SPAN, label: 'Deterrence' }}
          />
          <KpiTile
            label='Sway'
            value={mood.agitation}
            icon={Megaphone}
            tone='verdigris'
            meter={{ value: mood.agitation, max: SPAN, label: 'Sway' }}
          />
        </div>
      </div>
    </Held>
  )
}

function MoodForge({
  townId,
  blocked,
}: {
  townId: number
  blocked: string | null
}) {
  const [feeling, setFeeling] = useState<keyof typeof FEELINGS>('anger')
  const [level, setLevel] = useState('40')
  const setting = useCollectiveAction(
    'crowd_mood:set',
    (_: void) => ({
      town_id: townId,
      feelings: { [feeling]: clamp(level) },
    }),
    'The town is stirred so'
  )
  const busy = why(blocked, setting.isPending)
  return (
    <ForgeCard
      icon={Flame}
      tone='danger'
      title='Set the town’s mood'
      note='Fill the streets with one feeling; the next trigger may turn it into the act that grows from it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Flame />
          Stir the town
        </Button>
      }
    >
      <MindPicker
        label='Feeling'
        value={feeling}
        table={table(FEELINGS)}
        placeholder='Choose'
        blocked={blocked}
        onPick={(value) => setFeeling(value as keyof typeof FEELINGS)}
      />
      <NumberField
        label='Level'
        value={level}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setLevel}
      />
    </ForgeCard>
  )
}

function SparkForge({
  townId,
  blocked,
}: {
  townId: number | null
  blocked: string | null
}) {
  const [trigger, setTrigger] = useState<keyof typeof TRIGGERS>('famine')
  const sparking = useCollectiveAction(
    'cascade:spark',
    (_: void) => ({ town_id: townId ?? 0, trigger }),
    'The spark is struck'
  )
  const busy = why(townId === null ? NOT_A_TOWN : blocked, sparking.isPending)
  return (
    <ForgeCard
      icon={Gauge}
      tone='warning'
      title='Strike a spark'
      note='A trigger strikes a district; each dweller joins once enough others have, and the cascade ends as nothing, a mob, a panic or a movement.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => sparking.mutate()}
        >
          <Gauge />
          Strike it
        </Button>
      }
    >
      <MindPicker
        label='Trigger'
        value={trigger}
        table={table(TRIGGERS)}
        blocked={busy}
        onPick={(value) => setTrigger(value as keyof typeof TRIGGERS)}
      />
    </ForgeCard>
  )
}

function CascadeCard({
  row,
  blocked,
}: {
  row: Cascade
  blocked: string | null
}) {
  const action = useRemove('cascade:delete', { cascade_id: row.id }, blocked)
  const act = ACTS[row.act]
  const outcome = OUTCOMES[row.outcome]
  return (
    <Held
      icon={act.icon}
      tone={outcome.tone}
      title={`${act.label} over ${TRIGGERS[row.trigger].label.toLowerCase()}`}
      caption={`Epoch ${row.epoch}${row.district_name ? ` · ${row.district_name}` : ''}`}
      removeLabel='Strike from the record'
      editTitle=''
      note=''
      fields={[]}
      locked={[]}
      blocked={action.busy}
      onEdit={null}
      onRemove={action.onRemove}
      extra={<Chip icon={outcome.icon}>{outcome.label}</Chip>}
    >
      <Meter
        label='Share of the district that joined'
        value={row.share}
        max={SPAN}
        tone='destructive'
        icon={Users}
      />
      <Facts
        items={[
          ['Took part', row.participants],
          ['Fled', row.fled],
          ['Died', row.deaths],
          ['Recorded as', row.collection_name ?? 'no recorded event'],
        ]}
      />
    </Held>
  )
}

function MobCard({
  row,
  cascades,
  blocked,
}: {
  row: Mob
  cascades: Cascade[]
  blocked: string | null
}) {
  const source = cascades.find((item) => item.id === row.cascade_id)
  const action = useRow('mob:edit', 'mob:delete', { mob_id: row.id }, blocked)
  const [by, setBy] = useState<keyof typeof MOB_ENDS>('concession')
  const dispersing = useCollectiveAction(
    'mob:disperse',
    (_: void) => ({ mob_id: row.id, by }),
    'The crowd disperses'
  )
  const act = ACTS[row.act]
  const state = MOB_STATES[row.status]
  const ended = row.ended_by ? MOB_ENDS[row.ended_by] : null
  const over =
    row.status === 'dispersed' ? 'The crowd has already dispersed' : null
  const busy = why(over ?? action.busy, dispersing.isPending)
  return (
    <Held
      icon={act.icon}
      tone={state.tone}
      title={`${act.label} of ${row.size}`}
      caption={`Since epoch ${row.since_epoch} · going for ${MOB_TARGETS[row.target].label.toLowerCase()}`}
      removeLabel='Strike from the record'
      editTitle='Set the crowd'
      note='Size and anger decide what a crowd breaks and whether the watch can break it.'
      fields={[
        { key: 'act', label: 'What it does', kind: 'pick', table: table(ACTS) },
        { key: 'size', label: 'Size', kind: 'number', min: 0 },
        { key: 'anger', label: 'Anger', kind: 'number', min: 0, max: SPAN },
        { key: 'damage', label: 'Damage done', kind: 'number', min: 0 },
        {
          key: 'target',
          label: 'Target',
          kind: 'pick',
          table: table(MOB_TARGETS),
        },
        {
          key: 'target_entity_id',
          label: 'Scapegoat or target',
          kind: 'node',
          types: ['mortal', 'faction', 'structure', 'cult', 'house'],
        },
        {
          key: 'leader_entity_id',
          label: 'Led by',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'status',
          label: 'State',
          kind: 'pick',
          table: table(MOB_STATES),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={state.icon}>{state.label}</Chip>
          {ended && <Chip icon={ended.icon}>{ended.label}</Chip>}
        </>
      }
    >
      <Meter
        label='Anger'
        value={row.anger}
        max={SPAN}
        tone='destructive'
        icon={Flame}
      />
      <Facts
        items={[
          ['Damage done', row.damage],
          ['Gathered in', row.district_name ?? 'the whole town'],
          [
            'Rose from',
            source
              ? `${ACTS[source.act].label} over ${TRIGGERS[source.trigger].label.toLowerCase()}, epoch ${source.epoch}`
              : row.cascade_id !== null
                ? 'a cascade no longer recorded'
                : 'a god’s hand',
          ],
          [
            'Scapegoat or target',
            <Ref key='target' node={row.target_node} empty='none' />,
          ],
          ['Led by', <Ref key='leader' node={row.leader} empty='no one' />],
        ]}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='End it by'
          value={by}
          table={table(MOB_ENDS)}
          blocked={busy}
          onPick={(value) => setBy(value as keyof typeof MOB_ENDS)}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => dispersing.mutate()}
        >
          <Wind />
          Disperse it
        </Button>
      </div>
    </Held>
  )
}

function MobForge({
  townId,
  blocked,
}: {
  townId: number | null
  blocked: string | null
}) {
  const [act, setAct] = useState<keyof typeof ACTS>('riot')
  const [target, setTarget] = useState<keyof typeof MOB_TARGETS>('district')
  const [size, setSize] = useState('200')
  const [anger, setAnger] = useState('60')
  const raising = useCollectiveAction(
    'mob:raise',
    (_: void) => ({
      town_id: townId ?? 0,
      act,
      target,
      size: clamp(size, 1_000_000),
      anger: clamp(anger),
    }),
    'A crowd gathers'
  )
  const busy = why(townId === null ? NOT_A_TOWN : blocked, raising.isPending)
  return (
    <ForgeCard
      icon={Flame}
      tone='danger'
      title='Raise a crowd'
      note='Put a crowd on the streets with a target; it storms, lynches or marches until fatigue, force or a concession ends it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raising.mutate()}
        >
          <Users />
          Raise it
        </Button>
      }
    >
      <MindPicker
        label='What it does'
        value={act}
        table={table(ACTS)}
        blocked={busy}
        onPick={(value) => setAct(value as keyof typeof ACTS)}
      />
      <MindPicker
        label='Target'
        value={target}
        table={table(MOB_TARGETS)}
        blocked={busy}
        onPick={(value) => setTarget(value as keyof typeof MOB_TARGETS)}
      />
      <NumberField
        label='Size'
        value={size}
        min={0}
        blocked={busy}
        onChange={setSize}
      />
      <NumberField
        label='Anger'
        value={anger}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setAnger}
      />
    </ForgeCard>
  )
}

function MovementCard({
  row,
  blocked,
}: {
  row: Movement
  blocked: string | null
}) {
  const action = useRow(
    'popular_movement:edit',
    'popular_movement:delete',
    { movement_id: row.id },
    blocked
  )
  const act = ACTS[row.act]
  return (
    <Held
      icon={Flag}
      tone={act.tone}
      title={`A ${act.label.toLowerCase()} movement`}
      caption={`Since epoch ${row.since_epoch} over ${TRIGGERS[row.trigger].label.toLowerCase()}${row.ended_epoch !== null ? ` · faded in epoch ${row.ended_epoch}` : ''}`}
      removeLabel='Strike from the record'
      editTitle='Set the movement'
      note='A movement grows with grievance and fades without it; strong enough, it takes up arms as rebels or a holy movement.'
      fields={[
        { key: 'act', label: 'What it does', kind: 'pick', table: table(ACTS) },
        {
          key: 'trigger',
          label: 'Grievance',
          kind: 'pick',
          table: table(TRIGGERS),
        },
        { key: 'members', label: 'Members', kind: 'number', min: 0 },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'leader_entity_id',
          label: 'Led by',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'cult_entity_id',
          label: 'Its faith',
          kind: 'node',
          types: ['cult'],
        },
        {
          key: 'faction_entity_id',
          label: 'Its faction',
          kind: 'node',
          types: ['faction'],
        },
        {
          key: 'ended_epoch',
          label: 'Ended in epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Strength'
        value={row.strength}
        max={SPAN}
        tone='warning'
        icon={Flag}
      />
      <Facts
        items={[
          ['Members', row.members],
          ['Led by', <Ref key='leader' node={row.leader} empty='no one' />],
          ['Its faith', <Ref key='cult' node={row.cult} empty='none' />],
          [
            'Armed as',
            <Ref key='faction' node={row.faction} empty='not armed' />,
          ],
        ]}
      />
    </Held>
  )
}

function MovementForge({
  townId,
  blocked,
}: {
  townId: number | null
  blocked: string | null
}) {
  const [act, setAct] = useState<keyof typeof ACTS>('revival')
  const [trigger, setTrigger] = useState<keyof typeof TRIGGERS>('sermon')
  const [strength, setStrength] = useState('40')
  const founding = useCollectiveAction(
    'popular_movement:found',
    (_: void) => ({
      town_id: townId ?? 0,
      act,
      trigger,
      strength: clamp(strength),
    }),
    'A movement rises'
  )
  const busy = why(townId === null ? NOT_A_TOWN : blocked, founding.isPending)
  return (
    <ForgeCard
      icon={Flag}
      tone='gold'
      title='Raise a movement'
      note='Begin a lasting movement of the folk; its strength decides when it takes up arms.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => founding.mutate()}
        >
          <Flag />
          Raise it
        </Button>
      }
    >
      <MindPicker
        label='What it does'
        value={act}
        table={table(ACTS)}
        blocked={busy}
        onPick={(value) => setAct(value as keyof typeof ACTS)}
      />
      <MindPicker
        label='Grievance'
        value={trigger}
        table={table(TRIGGERS)}
        blocked={busy}
        onPick={(value) => setTrigger(value as keyof typeof TRIGGERS)}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

export function CrowdPanel({
  nodeId,
  isTown,
  data,
  blocked,
}: {
  nodeId: number
  isTown: boolean
  data: CollectiveView
  blocked: string | null
}) {
  const townId = isTown ? nodeId : null
  return (
    <div
      id='section-crowds'
      data-surface='CrowdPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Crowds, mobs and movements</Label>
      {data.mood ? (
        <MoodBoard townId={nodeId} mood={data.mood} blocked={blocked} />
      ) : isTown ? (
        <MoodForge townId={nodeId} blocked={blocked} />
      ) : (
        <Muted variant='caption'>{NOT_A_TOWN}</Muted>
      )}
      <SparkForge townId={townId} blocked={blocked} />
      <Listed
        title='Cascades'
        items={data.cascades}
        empty='No cascade has run here.'
        noun={['cascade', 'cascades']}
        itemKey={(row) => row.id}
      >
        {(row) => <CascadeCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Crowds'
        items={data.mobs}
        empty='No crowd has gathered here.'
        noun={['crowd', 'crowds']}
        itemKey={(row) => row.id}
      >
        {(row) => (
          <MobCard row={row} cascades={data.cascades} blocked={blocked} />
        )}
      </Listed>
      <MobForge townId={townId} blocked={blocked} />
      <Listed
        title='Movements'
        items={data.movements}
        empty='No movement stands here.'
        noun={['movement', 'movements']}
        itemKey={(row) => row.id}
      >
        {(row) => <MovementCard row={row} blocked={blocked} />}
      </Listed>
      <MovementForge townId={townId} blocked={blocked} />
    </div>
  )
}
