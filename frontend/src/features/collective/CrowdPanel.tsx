import { useState } from 'react'
import {
  Flame,
  Flag,
  Gauge,
  Megaphone,
  Shield,
  Sparkles,
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
} from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { Held, Listed } from './parts'

type Mood = NonNullable<CollectiveView['mood']>
type Cascade = CollectiveView['cascades'][number]
type Mob = CollectiveView['mobs'][number]
type Movement = CollectiveView['movements'][number]

const NOT_A_TOWN =
  'Crowds gather only in towns; choose a settlement to raise one.'

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
  return (
    <Held
      icon={SECTION_ICONS.crowds}
      tone={mood.anger >= 60 ? 'danger' : 'gold'}
      title='The mood of the town'
      caption={
        last
          ? `Last stirred by ${last.label.toLowerCase()}`
          : 'Nothing has stirred it this epoch'
      }
      removeLabel='Let it be read anew'
      editTitle='Set the mood'
      note='Anger feeds riots, fear feeds panics and fervour feeds faith’s mass acts; the watch deters them and a charismatic voice sways them.'
      fields={[
        { key: 'anger', label: 'Anger', kind: 'number', min: 0, max: SPAN },
        { key: 'anxiety', label: 'Fear', kind: 'number', min: 0, max: SPAN },
        { key: 'fervour', label: 'Fervour', kind: 'number', min: 0, max: SPAN },
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
      ]}
      locked={mood.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5'>
        <KpiTile
          label='Anger'
          value={mood.anger}
          icon={Flame}
          tone='danger'
          meter={{ value: mood.anger, max: SPAN, label: 'Anger' }}
        />
        <KpiTile
          label='Fear'
          value={mood.anxiety}
          icon={Wind}
          tone='warning'
          meter={{ value: mood.anxiety, max: SPAN, label: 'Fear' }}
        />
        <KpiTile
          label='Fervour'
          value={mood.fervour}
          icon={Sparkles}
          tone='gold'
          meter={{ value: mood.fervour, max: SPAN, label: 'Fervour' }}
        />
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
  const [anger, setAnger] = useState('40')
  const [anxiety, setAnxiety] = useState('20')
  const [fervour, setFervour] = useState('20')
  const setting = useCollectiveAction(
    'crowd_mood:set',
    (_: void) => ({
      town_id: townId,
      anger: clamp(anger),
      anxiety: clamp(anxiety),
      fervour: clamp(fervour),
    }),
    'The town is stirred so'
  )
  const busy = why(blocked, setting.isPending)
  return (
    <ForgeCard
      icon={Flame}
      tone='danger'
      title='Set the town’s mood'
      note='Fill the streets with anger, fear or fervour; the next trigger may turn it into a crowd.'
      columns={3}
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
      <NumberField
        label='Anger'
        value={anger}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setAnger}
      />
      <NumberField
        label='Fear'
        value={anxiety}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setAnxiety}
      />
      <NumberField
        label='Fervour'
        value={fervour}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setFervour}
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
        ]}
      />
    </Held>
  )
}

function MobCard({ row, blocked }: { row: Mob; blocked: string | null }) {
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
        { key: 'size', label: 'Size', kind: 'number', min: 0 },
        { key: 'anger', label: 'Anger', kind: 'number', min: 0, max: SPAN },
        {
          key: 'target',
          label: 'Target',
          kind: 'pick',
          table: table(MOB_TARGETS),
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
      title={`A movement that ${act.label.toLowerCase()}`}
      caption={`Since epoch ${row.since_epoch} over ${TRIGGERS[row.trigger].label.toLowerCase()}${row.ended_epoch !== null ? ` · faded in epoch ${row.ended_epoch}` : ''}`}
      removeLabel='Strike from the record'
      editTitle='Set the movement'
      note='A movement grows with grievance and fades without it; strong enough, it takes up arms as rebels or a holy movement.'
      fields={[
        { key: 'members', label: 'Members', kind: 'number', min: 0 },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
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
        {(row) => <MobCard row={row} blocked={blocked} />}
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
