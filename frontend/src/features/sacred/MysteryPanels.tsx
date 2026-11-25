import { useState } from 'react'
import {
  Eye,
  Flame,
  Footprints,
  Hourglass,
  Megaphone,
  Sun,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type SacredNodeView, useSacredAction } from './api'
import {
  CAUSES,
  MYSTIC_STATES,
  RESOLUTIONS,
  STAGES,
  VISION_KINDS,
} from './labels'
import {
  CHURCH_TYPES,
  GOD_KINDS,
  MANY,
  MORTAL_TYPES,
  PROPHECY_TYPES,
  SPAN,
  TOWN_TYPES,
  useSacredRow,
  useSacredStep,
} from './model'
import { Bars } from './parts'

type Mystic = SacredNodeView['mystics'][number]
type Vision = Mystic['history'][number]
type Movement = SacredNodeView['movements'][number]
type Crisis = SacredNodeView['crises'][number]

const FOUNDED = ['cult', 'faction'] as const
const RESOLVED = 'That crisis is already resolved'

function VisionCard({ row, blocked }: { row: Vision; blocked: string | null }) {
  const action = useSacredRow(
    'vision:edit',
    'vision:delete',
    { vision_id: row.id },
    blocked
  )
  const kind = VISION_KINDS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={row.genuine ? 'gold' : kind.tone}
      title={`${kind.label} in epoch ${row.epoch}`}
      caption={
        row.genuine
          ? `Real contact${row.sender ? ` from ${row.sender.name}` : ''}`
          : 'Its own imagining, though it cannot tell'
      }
      removeLabel='Strike the vision'
      editTitle='Set the vision'
      note='A vision is real contact when a god answers; otherwise it is the mystic’s own imagining, which feels the same to the mystic. Only the god that controls the world sees the difference.'
      fields={[
        {
          key: 'kind',
          label: 'Kind of experience',
          kind: 'pick',
          table: table(VISION_KINDS),
        },
        {
          key: 'sender_node_id',
          label: 'Sent by',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        { key: 'genuine', label: 'Real contact', kind: 'pick', table: YES_NO },
        { key: 'awe', label: 'Awe it left', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Awe (${row.awe} of ${SPAN})`}
        value={row.awe}
        tone='verdigris'
        icon={Sun}
      />
    </Held>
  )
}

function MysticCard({ row, blocked }: { row: Mystic; blocked: string | null }) {
  const action = useSacredRow(
    'mystic:edit',
    'mystic:delete',
    { mortal_id: row.mortal.id },
    blocked
  )
  const [god, setGod] = useState<number | null>(null)
  const [vision, setVision] = useState('')
  const sending = useSacredAction(
    'vision:create',
    (_: void) => ({
      mystic_id: row.mortal.id,
      sender_id: god,
      kind: vision === '' ? null : (vision as Vision['kind']),
    }),
    god === null
      ? 'Another vision comes of its own'
      : 'The god answers in a vision'
  )
  const state = MYSTIC_STATES[row.state]
  return (
    <Held
      icon={state.icon}
      tone={state.tone}
      title={row.mortal.name}
      caption={`${state.label} mystic since epoch ${row.since_epoch}${row.last_vision_epoch !== null ? ` · last vision in epoch ${row.last_vision_epoch}` : ''}`}
      removeLabel='Make it a mystic no more'
      editTitle='Set the mystic'
      note='A mystic draws followers outside the clergy with every vision. An orthodox church persecutes mystics who are not its clergy and a looser one reveres them. Past enough followers a revered mystic founds an order and a persecuted one a heresy. Without visions for long a mystic lapses.'
      fields={[
        {
          key: 'state',
          label: 'Standing',
          kind: 'pick',
          table: table(MYSTIC_STATES),
        },
        { key: 'visions', label: 'Visions', kind: 'number', min: 0, max: MANY },
        {
          key: 'genuine_visions',
          label: 'Real contacts',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'followers',
          label: 'Followers',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'answered_by_node_id',
          label: 'Answered by',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        {
          key: 'cult_entity_id',
          label: 'Church',
          kind: 'node',
          types: CHURCH_TYPES,
        },
        {
          key: 'founded_entity_id',
          label: 'Founded',
          kind: 'node',
          types: FOUNDED,
        },
        {
          key: 'reverence',
          label: 'Reverence',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'persecution',
          label: 'Persecution',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={state} />}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-3 gap-2'>
          <KpiTile
            label='Visions'
            value={row.visions}
            icon={Eye}
            tone='verdigris'
          />
          <KpiTile
            label='Real contacts'
            value={row.genuine_visions}
            icon={Sun}
            tone='gold'
          />
          <KpiTile
            label='Followers'
            value={row.followers}
            icon={Users}
            tone='info'
          />
        </div>
      </div>
      <Meter
        label={`Reverence (${row.reverence} of ${SPAN})`}
        value={row.reverence}
        tone='success'
        icon={Sun}
      />
      <Meter
        label={`Persecution (${row.persecution} of ${SPAN})`}
        value={row.persecution}
        tone='destructive'
        icon={Flame}
      />
      <Facts
        items={[
          ['Church', <Ref key='cult' node={row.cult} empty='none' />],
          [
            'Answered by',
            <Ref key='god' node={row.answered_by} empty='no god yet' />,
          ],
          [
            'Founded',
            <Ref key='founded' node={row.founded} empty='nothing yet' />,
          ],
        ]}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NodePicker
          label='Answer as'
          value={god}
          onChange={setGod}
          blocked={blocked}
          kinds={GOD_KINDS}
        />
        <MindPicker
          label='As'
          value={vision}
          table={table(VISION_KINDS)}
          placeholder='As it comes'
          blocked={blocked}
          onPick={setVision}
        />
        <StepButton
          act={sending}
          icon={Eye}
          label={
            god === null ? 'Another vision of its own' : 'Answer in a vision'
          }
          busy={why(blocked, sending.isPending)}
          onClick={() => sending.mutate()}
        />
      </div>
      <Listed
        title='Visions'
        items={row.history}
        empty='No vision is recorded.'
        noun={['vision', 'visions']}
        itemKey={(item) => item.id}
      >
        {(item) => <VisionCard row={item} blocked={blocked} />}
      </Listed>
    </Held>
  )
}

export function MysticsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: SacredNodeView
  blocked: string | null
}) {
  const everyone = [...(data.mystic ? [data.mystic] : []), ...data.mystics]
  const [mortal, setMortal] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [god, setGod] = useState<number | null>(
    kind === 'son' || kind === 'foreign_god' ? nodeId : null
  )
  const seizing = useSacredAction(
    'mystic:create',
    (_: void) => ({ mortal_id: mortal ?? 0, sender_id: god }),
    'A vision seizes the mortal'
  )
  const busy = why(
    blocked ?? (mortal === null ? 'Choose the mortal a vision seizes' : null),
    seizing.isPending
  )
  return (
    <div data-surface='MysticsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-mystic-visions'
        title='Visions of each mystic'
        legend={[
          { text: 'Real contact', variant: 'warning' },
          { text: 'Its own imagining', variant: 'secondary' },
        ]}
        rows={everyone.map((row) => ({
          key: row.mortal.id,
          caption: `${row.mortal.name}: ${plural(row.visions, 'vision', 'visions')}, ${row.genuine_visions} real, ${plural(row.followers, 'follower', 'followers')}`,
          segments: [
            { value: row.genuine_visions, fill: 'fill-primary' },
            {
              value: Math.max(0, row.visions - row.genuine_visions),
              fill: 'fill-info',
            },
          ],
        }))}
        noun={['mystic', 'mystics']}
        empty='No mystic is tied to this.'
      />
      <Listed
        title='Mystics'
        items={everyone}
        empty='No mystic is tied to this.'
        noun={['mystic', 'mystics']}
        itemKey={(item) => item.mortal.id}
      >
        {(item) => <MysticCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Eye}
        tone='verdigris'
        title='Seize a mortal with a vision'
        note='The mortal becomes a mystic, or a mystic sees again. Name a god to make it real contact; leave it empty and the vision is the mortal’s own.'
        columns={2}
        action={
          <Button
            act={seizing}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => seizing.mutate()}
          >
            <Eye />
            Send the vision
          </Button>
        }
      >
        <NodePicker
          label='Mortal'
          value={mortal}
          onChange={setMortal}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <NodePicker
          label='Sent by'
          value={god}
          onChange={setGod}
          blocked={blocked}
          kinds={GOD_KINDS}
        />
      </ForgeCard>
    </div>
  )
}

function MovementCard({
  row,
  blocked,
}: {
  row: Movement
  blocked: string | null
}) {
  const action = useSacredRow(
    'millenarian:edit',
    'millenarian:delete',
    { movement_id: row.id },
    blocked
  )
  const stage = STAGES[row.stage]
  return (
    <Held
      icon={stage.icon}
      tone={stage.tone}
      title={`The faithful of ${row.settlement.name}`}
      caption={`${stage.label} · awaiting the end in epoch ${row.end_epoch} · since epoch ${row.since_epoch}${row.ended_epoch !== null ? `, ended in epoch ${row.ended_epoch}` : ''}`}
      removeLabel='Strike the movement'
      editTitle='Set the movement'
      note='A millenarian movement gathers while the end it awaits draws near, gives away its goods and stops working in vigil, and marches against those it calls unclean when its conviction runs high. When the day passes it reads the prophecy anew and sets another date, hardens into a sect, or disperses.'
      fields={[
        {
          key: 'cult_entity_id',
          label: 'Church',
          kind: 'node',
          types: CHURCH_TYPES,
        },
        {
          key: 'prophet_entity_id',
          label: 'Prophet',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'prophecy_entity_id',
          label: 'Prophecy it follows',
          kind: 'node',
          types: PROPHECY_TYPES,
        },
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        {
          key: 'end_epoch',
          label: 'The end awaited in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'members', label: 'Members', kind: 'number', min: 0, max: MANY },
        {
          key: 'conviction',
          label: 'Conviction',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'given_up',
          label: 'Wealth given up',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'idle_share',
          label: 'Share that stopped working',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'attacks', label: 'Attacks', kind: 'number', min: 0, max: MANY },
        {
          key: 'dates_set',
          label: 'Dates set',
          kind: 'number',
          min: 1,
          max: MANY,
        },
        {
          key: 'sect_entity_id',
          label: 'Sect it became',
          kind: 'node',
          types: CHURCH_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={stage} />}
    >
      <Meter
        label={`Conviction (${row.conviction} of ${SPAN})`}
        value={row.conviction}
        tone='warning'
        icon={Flame}
      />
      <Meter
        label={`Stopped working (${row.idle_share} of ${SPAN})`}
        value={row.idle_share}
        tone='muted'
        icon={Hourglass}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @lg/tiles:grid-cols-4'>
          <KpiTile
            label='Members'
            value={row.members}
            icon={Users}
            tone='info'
          />
          <KpiTile
            label='Wealth given up'
            value={row.given_up}
            icon={Sun}
            tone='gold'
          />
          <KpiTile
            label='Attacks'
            value={row.attacks}
            icon={Footprints}
            tone={row.attacks > 0 ? 'danger' : 'muted'}
          />
          <KpiTile
            label='Dates set'
            value={row.dates_set}
            icon={Hourglass}
            tone='warning'
          />
        </div>
      </div>
      <Facts
        items={[
          ['Town', <Ref key='town' node={row.settlement} empty='none' />],
          ['Church', <Ref key='cult' node={row.cult} empty='none' />],
          ['Prophet', <Ref key='prophet' node={row.prophet} empty='none' />],
          [
            'Prophecy',
            <Ref key='prophecy' node={row.prophecy} empty='an omen alone' />,
          ],
          ['Sect', <Ref key='sect' node={row.sect} empty='none' />],
          [
            'Crowd it rides on',
            row.movement_id !== null ? 'a gathering of the town' : 'none',
          ],
        ]}
      />
    </Held>
  )
}

export function MovementsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: SacredNodeView
  blocked: string | null
}) {
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [prophet, setProphet] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [prophecy, setProphecy] = useState<number | null>(
    kind === 'prophecy' ? nodeId : null
  )
  const stirring = useSacredAction(
    'millenarian:create',
    (_: void) => ({
      town_id: town ?? 0,
      prophet_id: prophet,
      prophecy_id: prophecy,
    }),
    'The town begins to await the end'
  )
  const busy = why(
    blocked ?? (town === null ? 'Choose the town' : null),
    stirring.isPending
  )
  return (
    <div data-surface='MovementsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-millenarian'
        title='Conviction of each movement'
        legend={[
          { text: 'Conviction', variant: 'warning' },
          {
            text: 'The gold mark is the share that stopped working',
            variant: 'outline',
          },
        ]}
        rows={data.movements.map((row) => ({
          key: row.id,
          caption: `${row.settlement.name}: ${STAGES[row.stage].label.toLowerCase()}, the end awaited in epoch ${row.end_epoch}`,
          segments: [{ value: row.conviction, fill: 'fill-warning' }],
          mark: row.idle_share,
        }))}
        max={SPAN}
        noun={['movement', 'movements']}
        empty='No millenarian movement is tied to this.'
      />
      <Listed
        title='Millenarian movements'
        items={data.movements}
        empty='No millenarian movement is tied to this.'
        noun={['movement', 'movements']}
        itemKey={(item) => item.id}
      >
        {(item) => <MovementCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Megaphone}
        tone='warning'
        title='Stir a town to await the end'
        note='The faithful of a town begin to await an end a few epochs away, or by the deadline of the prophecy they follow.'
        columns={3}
        action={
          <Button
            act={stirring}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => stirring.mutate()}
          >
            <Megaphone />
            Stir it
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='Prophet'
          value={prophet}
          onChange={setProphet}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <NodePicker
          label='Prophecy it follows'
          value={prophecy}
          onChange={setProphecy}
          blocked={blocked}
          types={PROPHECY_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

function CrisisCard({ row, blocked }: { row: Crisis; blocked: string | null }) {
  const action = useSacredRow(
    'theodicy:edit',
    'theodicy:delete',
    { crisis_id: row.id },
    blocked
  )
  const answering = useSacredStep(
    'theodicy:answer',
    { crisis_id: row.id, god_id: row.god?.id ?? null },
    row.resolution === 'pending' ? blocked : RESOLVED,
    'The faithful see the answer'
  )
  const cause = CAUSES[row.cause]
  const resolution = RESOLUTIONS[row.resolution]
  return (
    <Held
      icon={cause.icon}
      tone={resolution.tone}
      title={`${cause.label} tests the faith of ${row.community.name}`}
      caption={`${resolution.label} · since epoch ${row.started_epoch}${row.resolved_epoch !== null ? `, resolved in epoch ${row.resolved_epoch}` : ''}`}
      removeLabel='Strike the crisis'
      editTitle='Set the crisis of faith'
      note='When great suffering finds the faithful and their god gives no answer they can see, the teaching is tested. A visible answer ends it with love; otherwise theologians may argue it away, the church may teach suffering as a trial, the faithful may turn from the silent god, or drift from faith.'
      fields={[
        {
          key: 'god_node_id',
          label: 'Patron god',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        { key: 'cause', label: 'Cause', kind: 'pick', table: table(CAUSES) },
        {
          key: 'suffering',
          label: 'Suffering',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'answered', label: 'Answered', kind: 'pick', table: YES_NO },
        {
          key: 'resolution',
          label: 'Resolution',
          kind: 'pick',
          table: table(RESOLUTIONS),
        },
        {
          key: 'theologian_entity_id',
          label: 'Theologian',
          kind: 'node',
          types: MORTAL_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Tag item={resolution} />
          <StepButton
            icon={Sun}
            label='Answer it visibly'
            busy={answering.busy}
            onClick={answering.run}
          />
        </div>
      }
    >
      <Meter
        label={`Suffering (${row.suffering} of ${SPAN})`}
        value={row.suffering}
        tone='destructive'
        icon={Flame}
      />
      <Facts
        items={[
          ['Church', <Ref key='cult' node={row.cult} empty='none' />],
          ['Town', <Ref key='town' node={row.community} empty='none' />],
          ['Patron god', <Ref key='god' node={row.god} empty='no god' />],
          [
            'Theologian',
            <Ref key='theologian' node={row.theologian} empty='none argued' />,
          ],
          ['Answered', row.answered ? 'yes' : 'no'],
        ]}
      />
    </Held>
  )
}

export function CrisesPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: SacredNodeView
  blocked: string | null
}) {
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [cause, setCause] = useState<keyof typeof CAUSES>('plague')
  const [suffering, setSuffering] = useState('60')
  const testing = useSacredAction(
    'theodicy:create',
    (_: void) => ({
      town_id: town ?? 0,
      cause,
      suffering: Number(suffering) || 0,
    }),
    'The teaching is put to the test'
  )
  const busy = why(
    blocked ?? (town === null ? 'Choose a town with a church' : null),
    testing.isPending
  )
  return (
    <div data-surface='CrisesPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Crises of faith'
        items={data.crises}
        empty='No crisis of faith is tied to this.'
        noun={['crisis', 'crises']}
        itemKey={(item) => item.id}
      >
        {(item) => <CrisisCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Flame}
        tone='danger'
        title='Put a teaching to the test'
        note='Suffering finds the faithful of a town with a church, and its teaching must answer for it.'
        columns={3}
        action={
          <Button
            act={testing}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => testing.mutate()}
          >
            <Flame />
            Test it
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='Cause'
          value={cause}
          table={table(CAUSES)}
          blocked={blocked}
          onPick={(value) => setCause(value as keyof typeof CAUSES)}
        />
        <NumberField
          label='Suffering'
          value={suffering}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setSuffering}
        />
      </ForgeCard>
    </div>
  )
}
