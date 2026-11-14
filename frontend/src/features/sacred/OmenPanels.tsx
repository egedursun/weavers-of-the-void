import { useState } from 'react'
import {
  Archive,
  Eye,
  FlaskConical,
  Heart,
  Orbit,
  RefreshCw,
  Sparkles,
  Target,
  TrendingDown,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { EMOTION_ICONS } from '@/features/entity/mind/feelingLabels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type SacredNodeView, useSacredAction } from './api'
import {
  DIVINATIONS,
  FORESEEN,
  FORESIGHT_STATUS,
  QUESTIONS,
  SOURCES,
  VALIDITIES,
  VERDICTS,
} from './labels'
import {
  GOD_KINDS,
  MANY,
  MORTAL_TYPES,
  ORDER_TYPES,
  PEOPLE_TYPES,
  REALM_TYPES,
  SPAN,
  SUBJECT_TYPES,
  useSacredRow,
  useSacredStep,
} from './model'
import { Bars } from './parts'

type System = SacredNodeView['systems'][number]
type Reading = SacredNodeView['readings'][number]
type Foresight = SacredNodeView['foresights'][number]
type Model = SacredNodeView['models'][number]
type Feeding = SacredNodeView['feedings'][number]

const SEERS = ['mortal'] as const
const NOT_GOD =
  'Only a god feeds on feelings; sons and foreign gods show theirs here'
const FEELINGS = table(EMOTION_ICONS)

function SystemCard({ row, blocked }: { row: System; blocked: string | null }) {
  const action = useSacredRow(
    'divination_system:edit',
    'divination_system:delete',
    { system_id: row.id },
    blocked
  )
  const testing = useSacredStep(
    'divination_system:read',
    { system_id: row.id },
    blocked,
    'The way of reading is tested against the world'
  )
  const kind = DIVINATIONS[row.kind]
  const validity = VALIDITIES[row.validity]
  return (
    <Held
      icon={kind.icon}
      tone={row.validity === 'noise' ? 'muted' : 'success'}
      title={`${kind.label} of ${row.people.name}`}
      caption={`${validity.label} · taken up in epoch ${row.founded_epoch}`}
      removeLabel='Forget this way of reading'
      editTitle='Set the divination system'
      note='A way of reading omens is truly informative only where a god answers, a seer is born among its people or a law of nature makes signs real; otherwise it reads noise. Rulers who hold superstition dear heed it, and trust rises or falls as heeded readings prove true or false.'
      fields={[
        {
          key: 'kind',
          label: 'Way of reading',
          kind: 'pick',
          table: table(DIVINATIONS),
        },
        {
          key: 'validity',
          label: 'Validity',
          kind: 'pick',
          table: table(VALIDITIES),
        },
        { key: 'trust', label: 'Trust', kind: 'number', min: 0, max: SPAN },
        {
          key: 'diviners',
          label: 'Diviners',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Tag item={validity} />
          <StepButton
            icon={RefreshCw}
            label='Test it against the world'
            busy={testing.busy}
            onClick={testing.run}
          />
        </div>
      }
    >
      <Meter
        label={`Trust (${row.trust} of ${SPAN})`}
        value={row.trust}
        tone='info'
        icon={Sparkles}
      />
      <KpiTile
        label='Diviners'
        value={row.diviners}
        icon={Users}
        tone='verdigris'
      />
    </Held>
  )
}

function ReadingCard({
  row,
  systems,
  blocked,
}: {
  row: Reading
  systems: System[]
  blocked: string | null
}) {
  const action = useSacredRow(
    'divination:edit',
    'divination:delete',
    { reading_id: row.id },
    blocked
  )
  const question = QUESTIONS[row.question]
  const verdict = VERDICTS[row.verdict]
  const truth = VERDICTS[row.true_verdict]
  const system = systems.find((item) => item.id === row.system_id)
  return (
    <Held
      icon={question.icon}
      tone={row.verdict === row.true_verdict ? 'success' : 'warning'}
      title={`An ${verdict.label.toLowerCase()} omen on the ${question.label.toLowerCase()}`}
      caption={`Epoch ${row.epoch} · ${row.heeded ? 'heeded' : 'paid little mind'}${row.verdict === row.true_verdict ? ' · it read true' : ` · the truth was ${truth.label.toLowerCase()}`}`}
      removeLabel='Strike the reading'
      editTitle='Set the reading'
      note='A heeded ill omen on war holds a ruler back from declaring it; on battle, a heeded omen gives or takes from the army; on a coronation it moves the ruler’s legitimacy, on a wedding the ruler’s ease, and on the harvest an ill omen delays the sowing.'
      fields={[
        {
          key: 'diviner_entity_id',
          label: 'Diviner',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'client_entity_id',
          label: 'Read for',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'question',
          label: 'Question',
          kind: 'pick',
          table: table(QUESTIONS),
        },
        {
          key: 'verdict',
          label: 'Omen read',
          kind: 'pick',
          table: table(VERDICTS),
        },
        {
          key: 'true_verdict',
          label: 'True omen',
          kind: 'pick',
          table: table(VERDICTS),
        },
        { key: 'heeded', label: 'Heeded', kind: 'pick', table: YES_NO },
        {
          key: 'swayed_by_node_id',
          label: 'Swayed by',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={verdict} />}
    >
      <Facts
        items={[
          ['Read for', <Ref key='client' node={row.client} empty='no one' />],
          [
            'Diviner',
            <Ref key='diviner' node={row.diviner} empty='an unnamed diviner' />,
          ],
          [
            'Swayed by',
            <Ref key='swayed' node={row.swayed_by} empty='no god' />,
          ],
          [
            'Way of reading',
            system ? DIVINATIONS[system.kind].label : 'a way of another people',
          ],
        ]}
      />
    </Held>
  )
}

export function DivinationPanel({
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
  const [people, setPeople] = useState<number | null>(
    kind === 'people' ? nodeId : null
  )
  const [way, setWay] = useState<keyof typeof DIVINATIONS>('augury')
  const founding = useSacredAction(
    'divination_system:create',
    (_: void) => ({ people_id: people ?? 0, kind: way }),
    'The people take up a way of reading'
  )
  const [realm, setRealm] = useState<number | null>(
    kind === 'polity' ? nodeId : null
  )
  const [question, setQuestion] = useState<keyof typeof QUESTIONS>('war')
  const [verdict, setVerdict] = useState('')
  const reading = useSacredAction(
    'divination:create',
    (_: void) => ({
      realm_id: realm ?? 0,
      question,
      verdict: verdict === '' ? null : (verdict as Reading['verdict']),
      system_id: null,
    }),
    'The diviners read the omens'
  )
  const foundBusy = why(
    blocked ?? (people === null ? 'Choose the people' : null),
    founding.isPending
  )
  const readBusy = why(
    blocked ?? (realm === null ? 'Choose the realm whose ruler asks' : null),
    reading.isPending
  )
  return (
    <div data-surface='DivinationPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Ways of divination'
        items={data.systems}
        empty='This people keeps no way of divination.'
        noun={['way', 'ways']}
        itemKey={(item) => item.id}
      >
        {(item) => <SystemCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Orbit}
        tone='info'
        title='Give a people a way of divination'
        note='Its validity is read from the world at once and every epoch after.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={foundBusy !== null}
            disabledReason={foundBusy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <Orbit />
            Take it up
          </Button>
        }
      >
        <NodePicker
          label='People'
          value={people}
          onChange={setPeople}
          blocked={blocked}
          types={PEOPLE_TYPES}
        />
        <MindPicker
          label='Way of reading'
          value={way}
          table={table(DIVINATIONS)}
          blocked={blocked}
          onPick={(value) => setWay(value as keyof typeof DIVINATIONS)}
        />
      </ForgeCard>
      <Bars
        chart='chart-omens'
        title='Omens read against the truth'
        legend={[
          { text: 'Read true', variant: 'success' },
          { text: 'Read false', variant: 'destructive' },
        ]}
        rows={data.readings.map((row) => ({
          key: row.id,
          caption: `Epoch ${row.epoch}, ${QUESTIONS[row.question].label.toLowerCase()}: read ${VERDICTS[row.verdict].label.toLowerCase()}, truly ${VERDICTS[row.true_verdict].label.toLowerCase()}`,
          segments: [
            {
              value: 1,
              fill:
                row.verdict === row.true_verdict
                  ? 'fill-success'
                  : 'fill-destructive',
            },
          ],
        }))}
        max={1}
        noun={['reading', 'readings']}
        empty='No omen was read here.'
      />
      <Listed
        title='Readings'
        items={data.readings}
        empty='No omen was read here.'
        noun={['reading', 'readings']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <ReadingCard row={item} systems={data.systems} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Eye}
        tone='warning'
        title='Have a ruler’s diviners read the omens'
        note='Choose the omen to read it yourself; leave it empty and the diviners read what their way of reading shows.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={readBusy !== null}
            disabledReason={readBusy ?? undefined}
            onClick={() => reading.mutate()}
          >
            <Eye />
            Read them
          </Button>
        }
      >
        <NodePicker
          label='Realm'
          value={realm}
          onChange={setRealm}
          blocked={blocked}
          types={REALM_TYPES}
        />
        <MindPicker
          label='Question'
          value={question}
          table={table(QUESTIONS)}
          blocked={blocked}
          onPick={(value) => setQuestion(value as keyof typeof QUESTIONS)}
        />
        <MindPicker
          label='Omen read'
          value={verdict}
          table={table(VERDICTS)}
          placeholder='What the way shows'
          blocked={blocked}
          onPick={setVerdict}
        />
      </ForgeCard>
    </div>
  )
}

function ForesightCard({
  row,
  blocked,
}: {
  row: Foresight
  blocked: string | null
}) {
  const action = useSacredRow(
    'foresight:edit',
    'foresight:delete',
    { foresight_id: row.id },
    blocked
  )
  const status = FORESIGHT_STATUS[row.status]
  const source = SOURCES[row.source]
  const seen = row.predicate === 'falls' ? FORESEEN.falls : FORESEEN.dies
  return (
    <Held
      icon={status.icon}
      tone={status.tone}
      title={`${row.subject?.name ?? 'Someone'} ${seen.label.toLowerCase()} by epoch ${row.due_epoch}`}
      caption={`Foreseen by ${row.seer.name} in epoch ${row.made_epoch} · ${source.label.toLowerCase()}${row.checked_epoch !== null ? ` · judged in epoch ${row.checked_epoch}` : ''}`}
      removeLabel='Strike the foresight'
      editTitle='Set the foresight'
      note='A foresight is a probability, never a rewriting of what comes. It clouds near rival seers, sees nothing of outer beings, and the seer’s renown follows how true it proves.'
      fields={[
        {
          key: 'subject_node_id',
          label: 'Whose future',
          kind: 'node',
          types: SUBJECT_TYPES,
        },
        {
          key: 'predicate',
          label: 'What it foresees',
          kind: 'pick',
          table: table(FORESEEN),
        },
        {
          key: 'horizon',
          label: 'Years ahead',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'due_epoch',
          label: 'Due by epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'certainty',
          label: 'Certainty',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'source', label: 'Source', kind: 'pick', table: table(SOURCES) },
        {
          key: 'status',
          label: 'Standing',
          kind: 'pick',
          table: table(FORESIGHT_STATUS),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={status} />}
    >
      <Meter
        label={`Certainty (${row.certainty} of ${SPAN})`}
        value={row.certainty}
        tone='verdigris'
        icon={Target}
      />
      <Facts
        items={[
          ['Seer', <Ref key='seer' node={row.seer} empty='someone' />],
          [
            'Whose future',
            <Ref key='subject' node={row.subject} empty='no one' />,
          ],
          ['Years ahead', String(row.horizon)],
          ['From a reading', row.divination_id !== null ? 'yes' : 'no'],
        ]}
      />
    </Held>
  )
}

export function ForesightPanel({
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
  const [seer, setSeer] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [subject, setSubject] = useState<number | null>(
    kind === 'polity' || kind === 'settlement' ? nodeId : null
  )
  const [seen, setSeen] = useState<keyof typeof FORESEEN>('dies')
  const [certainty, setCertainty] = useState('60')
  const [proclaimed, setProclaimed] = useState('false')
  const granting = useSacredAction(
    'foresight:create',
    (_: void) => ({
      seer_id: seer ?? 0,
      subject_id: subject ?? 0,
      predicate: seen,
      certainty: Number(certainty) || 0,
      source: 'god' as const,
      proclaimed: proclaimed === 'true',
    }),
    'The seer foresees what is likely'
  )
  const busy = why(
    blocked ??
      (seer === null
        ? 'Choose the seer'
        : subject === null
          ? 'Choose whose future it shows'
          : null),
    granting.isPending
  )
  return (
    <div data-surface='ForesightPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Foresights'
        items={data.foresights}
        empty='Nothing was foreseen by or about this.'
        noun={['foresight', 'foresights']}
        itemKey={(item) => item.id}
      >
        {(item) => <ForesightCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Eye}
        tone='verdigris'
        title='Show a seer a likely future'
        note='Whether a mortal dies, or a realm or town falls. Proclaimed, it becomes a prophecy others act on.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => granting.mutate()}
          >
            <Eye />
            Show it
          </Button>
        }
      >
        <NodePicker
          label='Seer'
          value={seer}
          onChange={setSeer}
          blocked={blocked}
          types={SEERS}
        />
        <NodePicker
          label='Whose future'
          value={subject}
          onChange={setSubject}
          blocked={blocked}
          types={SUBJECT_TYPES}
        />
        <MindPicker
          label='What it foresees'
          value={seen}
          table={table(FORESEEN)}
          blocked={blocked}
          onPick={(value) => setSeen(value as keyof typeof FORESEEN)}
        />
        <NumberField
          label='Certainty'
          value={certainty}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setCertainty}
        />
        <MindPicker
          label='Proclaimed as prophecy'
          value={proclaimed}
          table={YES_NO}
          blocked={blocked}
          onPick={setProclaimed}
        />
      </ForgeCard>
    </div>
  )
}

function ModelCard({ row, blocked }: { row: Model; blocked: string | null }) {
  const action = useSacredRow(
    'forecast_model:edit',
    'forecast_model:delete',
    { model_id: row.id },
    blocked
  )
  return (
    <Held
      icon={FlaskConical}
      tone={row.disruption > 0 ? 'warning' : 'info'}
      title={`${row.order.name} forecasts ${row.subject?.name ?? 'a realm'}`}
      caption={`Built in epoch ${row.built_epoch} · looks ${row.horizon} epochs ahead${row.plan_id !== null ? ' · steering it by a long plan' : ''}`}
      removeLabel='Set the model aside'
      editTitle='Set the forecast model'
      note='A learned order with census and an archive forecasts its realm’s political stress. Close forecasts sharpen the model; accurate enough, the order steers the realm by a long plan that eases its stress, undone in part by great interventions such as miracles.'
      fields={[
        {
          key: 'subject_entity_id',
          label: 'Realm forecast',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'archive',
          label: 'Archived works',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'accuracy',
          label: 'Accuracy',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'forecast_psi',
          label: 'Forecast stress',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'actual_psi',
          label: 'Real stress',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'plan_id',
          label: 'Steering plan',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'disruption',
          label: 'Disruption',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'disrupted_by_node_id',
          label: 'Disrupted by',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        {
          key: 'horizon',
          label: 'Epochs ahead',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Bars
        chart='chart-forecast'
        title='Forecast against the realm’s real stress'
        legend={[
          { text: 'Forecast', variant: 'secondary' },
          { text: 'The gold mark is the real stress', variant: 'outline' },
        ]}
        rows={[
          {
            key: row.id,
            caption: `Forecast ${row.forecast_psi}, real ${row.actual_psi}`,
            segments: [{ value: row.forecast_psi, fill: 'fill-info' }],
            mark: row.actual_psi,
          },
        ]}
        max={SPAN}
        noun={['forecast', 'forecasts']}
        empty='No forecast yet.'
      />
      <Meter
        label={`Accuracy (${row.accuracy} of ${SPAN})`}
        value={row.accuracy}
        tone='success'
        icon={Target}
      />
      <Meter
        label={`Disruption (${row.disruption} of ${SPAN})`}
        value={row.disruption}
        tone='destructive'
        icon={TrendingDown}
      />
      <KpiTile
        label='Archived works'
        value={row.archive}
        icon={Archive}
        tone='gold'
      />
      <Facts
        items={[
          ['Order', <Ref key='order' node={row.order} empty='none' />],
          ['Realm', <Ref key='subject' node={row.subject} empty='none' />],
          [
            'Disrupted by',
            <Ref key='disruptor' node={row.disrupted_by} empty='nothing' />,
          ],
        ]}
      />
    </Held>
  )
}

export function ForecastPanel({
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
  const [order, setOrder] = useState<number | null>(
    kind === 'faction' ? nodeId : null
  )
  const [realm, setRealm] = useState<number | null>(
    kind === 'polity' ? nodeId : null
  )
  const building = useSacredAction(
    'forecast_model:create',
    (_: void) => ({ order_id: order ?? 0, realm_id: realm }),
    'The order begins its forecast'
  )
  const busy = why(
    blocked ?? (order === null ? 'Choose the learned order' : null),
    building.isPending
  )
  return (
    <div data-surface='ForecastPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Forecast models'
        items={data.models}
        empty='No forecast is made by or of this.'
        noun={['model', 'models']}
        itemKey={(item) => item.id}
      >
        {(item) => <ModelCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={FlaskConical}
        tone='info'
        title='Have a learned order forecast a realm'
        note='Leave the realm empty and the order forecasts the realm of its home.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => building.mutate()}
          >
            <FlaskConical />
            Begin the forecast
          </Button>
        }
      >
        <NodePicker
          label='Learned order'
          value={order}
          onChange={setOrder}
          blocked={blocked}
          types={ORDER_TYPES}
        />
        <NodePicker
          label='Realm'
          value={realm}
          onChange={setRealm}
          blocked={blocked}
          types={REALM_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

function FeedingCard({
  row,
  godId,
  blocked,
}: {
  row: Feeding
  godId: number
  blocked: string | null
}) {
  const action = useSacredRow(
    'god_feeding:edit',
    'god_feeding:delete',
    { god_id: godId, emotion: row.emotion },
    blocked
  )
  const feeling = EMOTION_ICONS[row.emotion]
  return (
    <Held
      icon={feeling.icon}
      tone={feeling.tone ?? 'info'}
      title={`Feeds on ${feeling.label.toLowerCase()}`}
      caption={`Weight ${row.weight} · drew ${row.harvested} essence in epoch ${row.epoch}`}
      removeLabel='Stop feeding on it'
      editTitle='Set the feeding'
      note='Each epoch the god draws essence from how strongly its faithful feel what it feeds on, scaled by the weight.'
      fields={[
        { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Weight (${row.weight} of ${SPAN})`}
        value={row.weight}
        tone='info'
        icon={Heart}
      />
    </Held>
  )
}

export function FeedingPanel({
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
  const god = kind === 'son' || kind === 'foreign_god'
  const gate = god ? blocked : NOT_GOD
  const [emotion, setEmotion] = useState<Feeding['emotion']>('awe')
  const [weight, setWeight] = useState('50')
  const setting = useSacredAction(
    'god_feeding:set',
    (_: void) => ({ god_id: nodeId, emotion, weight: Number(weight) || 0 }),
    'The god feeds on that feeling'
  )
  const busy = why(gate, setting.isPending)
  const drawn = new Map<string, number>()
  for (const item of data.harvests)
    drawn.set(item.emotion, (drawn.get(item.emotion) ?? 0) + item.essence)
  return (
    <div data-surface='FeedingPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-feelings'
        title='Essence drawn from each feeling, in all'
        legend={[{ text: 'Essence drawn', variant: 'success' }]}
        rows={[...drawn.entries()].map(([feeling, essence]) => ({
          key: feeling,
          caption: `${EMOTION_ICONS[feeling].label}: ${essence} essence over ${plural(data.harvests.filter((item) => item.emotion === feeling).length, 'epoch', 'epochs')}`,
          segments: [{ value: essence, fill: 'fill-success' }],
        }))}
        noun={['feeling', 'feelings']}
        empty={god ? 'This god has drawn nothing from feelings yet.' : NOT_GOD}
      />
      <Listed
        title='Harvests'
        items={data.harvests}
        empty='No feeling has fed this god yet.'
        noun={['harvest', 'harvests']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <Muted key={item.id} variant='caption'>
            {`Epoch ${item.epoch}: ${EMOTION_ICONS[item.emotion].label.toLowerCase()} felt ${item.count}, giving ${item.essence} essence`}
          </Muted>
        )}
      </Listed>
      <Listed
        title='Feelings it feeds on'
        items={data.feedings}
        empty={god ? 'It feeds on no feeling yet.' : NOT_GOD}
        noun={['feeling', 'feelings']}
        itemKey={(item) => item.emotion}
      >
        {(item) => <FeedingCard row={item} godId={nodeId} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Heart}
        tone='danger'
        title='Set a feeling the god feeds on'
        note='Feed on a feeling of the faithful, or set the weight of one already fed on.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Heart />
            Feed on it
          </Button>
        }
      >
        <MindPicker
          label='Feeling'
          value={emotion}
          table={FEELINGS}
          blocked={gate}
          onPick={(value) => setEmotion(value as Feeding['emotion'])}
        />
        <NumberField
          label='Weight'
          value={weight}
          min={0}
          max={SPAN}
          blocked={gate}
          onChange={setWeight}
        />
      </ForgeCard>
    </div>
  )
}
