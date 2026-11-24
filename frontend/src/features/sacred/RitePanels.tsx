import { useState } from 'react'
import {
  BookOpen,
  Ghost,
  Megaphone,
  Scale,
  Scroll,
  ShieldCheck,
  Sparkles,
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
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type SacredNodeView, useSacredAction } from './api'
import { AFTERLIVES, PROTECTIONS, SACRAMENTS } from './labels'
import {
  CHURCH_TYPES,
  GOD_KINDS,
  MANY,
  MORTAL_TYPES,
  SPAN,
  useSacredRow,
} from './model'
import { Bars } from './parts'

type Teaching = SacredNodeView['teachings'][number]
type Sacrament = SacredNodeView['sacraments'][number]
type Taught = SacredNodeView['afterlives'][number]
type Climate = NonNullable<SacredNodeView['climate']>

const PULL = -SPAN
const NOT_TOWN = 'Only a town weighs its faith'
const PULLS: [keyof Climate, string][] = [
  ['literacy_pull', 'Literacy'],
  ['science_pull', 'Sound theories'],
  ['prosperity_pull', 'Prosperity'],
  ['city_pull', 'City life'],
  ['silence_pull', 'Divine silence'],
  ['disaster_push', 'Disasters'],
  ['miracle_push', 'Miracles'],
  ['war_push', 'War'],
  ['dominion_push', 'A god’s dominion'],
]

function TeachingCard({
  row,
  blocked,
}: {
  row: Teaching
  blocked: string | null
}) {
  const action = useSacredRow(
    'doctrine_sacrament:edit',
    'doctrine_sacrament:delete',
    { cult_id: row.cult.id, kind: row.kind },
    blocked
  )
  const sacrament = SACRAMENTS[row.kind]
  const protection = PROTECTIONS[row.protection]
  return (
    <Held
      icon={sacrament.icon}
      tone={sacrament.tone}
      title={`${sacrament.label}, taught by ${row.cult.name}`}
      caption={`Protects against ${protection.label.toLowerCase()} · taught since epoch ${row.since_epoch}`}
      removeLabel='Stop teaching it'
      editTitle='Set the taught sacrament'
      note='A sacrament protects those who receive it in the church’s own terms: the soul’s way after death, possession, or unrest at death. A priest must be at hand; war, plague and distance keep priests away, and a missed sacrament leaves unease and no protection.'
      fields={[
        {
          key: 'protection',
          label: 'Protects against',
          kind: 'pick',
          table: table(PROTECTIONS),
        },
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
      extra={<Tag item={protection} />}
    >
      <Meter
        label={`Strength (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='info'
        icon={ShieldCheck}
      />
    </Held>
  )
}

function SacramentCard({
  row,
  blocked,
}: {
  row: Sacrament
  blocked: string | null
}) {
  const action = useSacredRow(
    'sacrament:edit',
    'sacrament:delete',
    { sacrament_id: row.id },
    blocked
  )
  const sacrament = SACRAMENTS[row.kind]
  return (
    <Held
      icon={sacrament.icon}
      tone={row.missed ? 'warning' : 'success'}
      title={`${sacrament.label} of ${row.mortal.name}`}
      caption={`${row.missed ? 'Missed' : 'Received'} in epoch ${row.epoch}`}
      removeLabel='Strike the sacrament'
      editTitle='Set the sacrament'
      note='Each sacrament given or missed is kept; what it protects follows the teaching of its church.'
      fields={[
        {
          key: 'kind',
          label: 'Sacrament',
          kind: 'pick',
          table: table(SACRAMENTS),
        },
        {
          key: 'cult_entity_id',
          label: 'Church',
          kind: 'node',
          types: CHURCH_TYPES,
        },
        {
          key: 'priest_entity_id',
          label: 'Priest',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        { key: 'missed', label: 'Missed', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Tag
          item={{ ...sacrament, tone: row.missed ? 'warning' : 'success' }}
          text={row.missed ? 'Missed' : 'Received'}
        />
      }
    >
      <Facts
        items={[
          ['Mortal', <Ref key='mortal' node={row.mortal} empty='someone' />],
          ['Church', <Ref key='cult' node={row.cult} empty='none' />],
          [
            'Priest',
            <Ref
              key='priest'
              node={row.priest}
              empty='no priest was at hand'
            />,
          ],
        ]}
      />
    </Held>
  )
}

export function RitesPanel({
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
  const [cult, setCult] = useState<number | null>(
    kind === 'cult' ? nodeId : null
  )
  const [taught, setTaught] =
    useState<keyof typeof SACRAMENTS>('birth_blessing')
  const [protection, setProtection] = useState('')
  const [strength, setStrength] = useState('60')
  const teaching = useSacredAction(
    'doctrine_sacrament:set',
    (_: void) => ({
      cult_id: cult ?? 0,
      kind: taught,
      protection:
        protection === '' ? null : (protection as Teaching['protection']),
      strength: Number(strength) || 0,
    }),
    'The church teaches the sacrament'
  )
  const [mortal, setMortal] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [given, setGiven] = useState<keyof typeof SACRAMENTS>('initiation')
  const [priest, setPriest] = useState<number | null>(null)
  const giving = useSacredAction(
    'sacrament:create',
    (_: void) => ({ mortal_id: mortal ?? 0, kind: given, priest_id: priest }),
    'The sacrament is given'
  )
  const teachBusy = why(
    blocked ?? (cult === null ? 'Choose the church' : null),
    teaching.isPending
  )
  const giveBusy = why(
    blocked ?? (mortal === null ? 'Choose the mortal' : null),
    giving.isPending
  )
  return (
    <div data-surface='RitesPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Sacraments taught'
        items={data.teachings}
        empty='This church teaches no sacrament, or this is not a church.'
        noun={['sacrament', 'sacraments']}
        itemKey={(item) => `${item.cult.id}-${item.kind}`}
      >
        {(item) => <TeachingCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Scroll}
        tone='info'
        title='Teach a sacrament'
        note='A church teaches a life-stage rite and what it protects against; leave the protection empty for the rite’s usual one.'
        columns={4}
        action={
          <Button
            size='sm'
            disabled={teachBusy !== null}
            disabledReason={teachBusy ?? undefined}
            onClick={() => teaching.mutate()}
          >
            <BookOpen />
            Teach it
          </Button>
        }
      >
        <NodePicker
          label='Church'
          value={cult}
          onChange={setCult}
          blocked={blocked}
          types={CHURCH_TYPES}
        />
        <MindPicker
          label='Sacrament'
          value={taught}
          table={table(SACRAMENTS)}
          blocked={blocked}
          onPick={(value) => setTaught(value as keyof typeof SACRAMENTS)}
        />
        <MindPicker
          label='Protects against'
          value={protection}
          table={table(PROTECTIONS)}
          placeholder='Its usual protection'
          blocked={blocked}
          onPick={setProtection}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setStrength}
        />
      </ForgeCard>
      <Listed
        title='Sacraments given and missed'
        items={data.sacraments}
        empty='No sacrament is recorded here.'
        noun={['sacrament', 'sacraments']}
        itemKey={(item) => item.id}
      >
        {(item) => <SacramentCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Sparkles}
        tone='success'
        title='Give a sacrament'
        note='A church near the mortal must teach the rite. Name a priest to be sure one is at hand.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={giveBusy !== null}
            disabledReason={giveBusy ?? undefined}
            onClick={() => giving.mutate()}
          >
            <Sparkles />
            Give it
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
        <MindPicker
          label='Sacrament'
          value={given}
          table={table(SACRAMENTS)}
          blocked={blocked}
          onPick={(value) => setGiven(value as keyof typeof SACRAMENTS)}
        />
        <NodePicker
          label='Priest'
          value={priest}
          onChange={setPriest}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

function AfterlifeCard({
  row,
  blocked,
}: {
  row: Taught
  blocked: string | null
}) {
  const action = useSacredRow(
    'doctrine_afterlife:edit',
    'doctrine_afterlife:delete',
    { cult_id: row.cult.id },
    blocked
  )
  const [god, setGod] = useState<number | null>(row.aligned_by?.id ?? null)
  const aligning = useSacredAction(
    'doctrine_afterlife:align',
    (_: void) => ({ cult_id: row.cult.id, god_id: god ?? 0 }),
    'The afterlife now matches the teaching'
  )
  const model = AFTERLIVES[row.model]
  const alignBusy = why(
    blocked ??
      (god === null ? 'Choose the god whose afterlife is made to match' : null),
    aligning.isPending
  )
  return (
    <Held
      icon={model.icon}
      tone={row.aligned ? 'gold' : row.doubt > 0 ? 'warning' : model.tone}
      title={`${row.cult.name} teaches ${model.label.toLowerCase()}`}
      caption={
        row.aligned
          ? `Made true${row.aligned_by ? ` by ${row.aligned_by.name}` : ''}`
          : `Read in epoch ${row.updated_epoch}`
      }
      removeLabel='Let it be read anew'
      editTitle='Set the taught afterlife'
      note='Souls who arrive somewhere other than the afterlife they were taught are shocked and grow restless. The dead who walk or speak in dreams testify against the doctrine, and doubt weakens its orthodoxy. A god may make the afterlife match the teaching.'
      fields={[
        {
          key: 'model',
          label: 'Afterlife taught',
          kind: 'pick',
          table: table(AFTERLIVES),
        },
        { key: 'aligned', label: 'Made true', kind: 'pick', table: YES_NO },
        {
          key: 'aligned_by_node_id',
          label: 'Made true by',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        {
          key: 'shocks',
          label: 'Souls shocked',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'testimonies',
          label: 'Testimonies of the dead',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'doubt', label: 'Doubt', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={model} />}
    >
      <Meter
        label={`Doubt (${row.doubt} of ${SPAN})`}
        value={row.doubt}
        tone='warning'
        icon={Scale}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile
            label='Souls shocked'
            value={row.shocks}
            icon={Ghost}
            tone={row.shocks > 0 ? 'danger' : 'muted'}
          />
          <KpiTile
            label='Testimonies'
            value={row.testimonies}
            icon={Megaphone}
            tone='verdigris'
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NodePicker
          label='Make it true as'
          value={god}
          onChange={setGod}
          blocked={blocked}
          kinds={GOD_KINDS}
        />
        <StepButton
          icon={Sparkles}
          label='Make the afterlife match'
          busy={alignBusy}
          onClick={() => aligning.mutate()}
        />
      </div>
    </Held>
  )
}

export function AfterlifePanel({
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
  const [cult, setCult] = useState<number | null>(
    kind === 'cult' ? nodeId : null
  )
  const [model, setModel] = useState('')
  const setting = useSacredAction(
    'doctrine_afterlife:set',
    (_: void) => ({
      cult_id: cult ?? 0,
      model: model === '' ? null : (model as Taught['model']),
    }),
    'The church teaches its afterlife'
  )
  const busy = why(
    blocked ?? (cult === null ? 'Choose the church' : null),
    setting.isPending
  )
  return (
    <div data-surface='AfterlifePanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Afterlives taught'
        items={data.afterlives}
        empty='No church here teaches an afterlife yet.'
        noun={['afterlife', 'afterlives']}
        itemKey={(item) => item.cult.id}
      >
        {(item) => <AfterlifeCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Ghost}
        tone='verdigris'
        title='Set the afterlife a church teaches'
        note='Leave it empty and it is read from the church’s tenets and its doctrine of judgement.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Ghost />
            Teach it
          </Button>
        }
      >
        <NodePicker
          label='Church'
          value={cult}
          onChange={setCult}
          blocked={blocked}
          types={CHURCH_TYPES}
        />
        <MindPicker
          label='Afterlife taught'
          value={model}
          table={table(AFTERLIVES)}
          placeholder='Read from its tenets'
          blocked={blocked}
          onPick={setModel}
        />
      </ForgeCard>
    </div>
  )
}

function ClimateCard({
  row,
  blocked,
}: {
  row: Climate
  blocked: string | null
}) {
  const action = useSacredRow(
    'faith_climate:edit',
    'faith_climate:delete',
    { town_id: row.community.id },
    blocked
  )
  return (
    <Held
      icon={Scale}
      tone={row.godless ? 'muted' : row.piety_drift < 0 ? 'warning' : 'success'}
      title={`Faith in ${row.community.name}`}
      caption={`${row.godless ? 'Godless · ' : ''}piety drifts by ${row.piety_drift} each epoch · weighed in epoch ${row.updated_epoch}`}
      removeLabel='Let it be weighed anew'
      editTitle='Set the pulls on its faith'
      note='Literacy, sound theories, prosperity, city life and long divine silence pull a town’s piety down; disasters, miracles, war and a god’s dominion push it up. A town with little piety and no god becomes godless, and returns to faith once its piety recovers.'
      fields={[
        {
          key: 'piety_drift',
          label: 'Drift each epoch',
          kind: 'number',
          min: PULL,
          max: SPAN,
        },
        ...PULLS.map(([key, label]) => ({
          key,
          label,
          kind: 'number' as const,
          min: PULL,
          max: SPAN,
        })),
        {
          key: 'silent_epochs',
          label: 'Epochs of divine silence',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'godless', label: 'Godless', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Bars
        chart='chart-faith-climate'
        title='What pulls and pushes its faith'
        legend={[
          { text: 'Pulls away from faith', variant: 'destructive' },
          { text: 'Pushes toward faith', variant: 'success' },
        ]}
        rows={PULLS.map(([key, label]) => {
          const value = Number(row[key])
          return {
            key,
            caption: `${label}: ${value > 0 ? '+' : ''}${value}`,
            segments: [
              {
                value: Math.abs(value),
                fill: value < 0 ? 'fill-destructive' : 'fill-success',
              },
            ],
          }
        })}
        max={SPAN}
        noun={['pull', 'pulls']}
        empty='Nothing moves its faith.'
      />
      <Muted variant='caption'>{`The gods have been silent here for ${plural(row.silent_epochs, 'epoch', 'epochs')}.`}</Muted>
    </Held>
  )
}

export function FaithClimatePanel({
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
  const town = kind === 'settlement'
  const weighing = useSacredAction(
    'faith_climate:set',
    (_: void) => ({ town_id: nodeId }),
    'The town’s faith is weighed'
  )
  const busy = why(town ? blocked : NOT_TOWN, weighing.isPending)
  return (
    <div
      data-surface='FaithClimatePanel'
      className='flex min-w-0 flex-col gap-4'
    >
      {data.climate ? (
        <ClimateCard row={data.climate} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {town
            ? 'This town’s faith has not been weighed yet.'
            : 'Faith is weighed town by town; a town’s entry shows its own.'}
        </Muted>
      )}
      <ForgeCard
        icon={Scale}
        tone='gold'
        title='Weigh the town’s faith'
        note='Open the record of what pulls this town’s faith down and pushes it up; the engine fills it each epoch.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => weighing.mutate()}
          >
            <Scale />
            Weigh it
          </Button>
        }
      >
        <Muted variant='caption'>
          {town ? 'The town of this entry.' : NOT_TOWN}
        </Muted>
      </ForgeCard>
    </div>
  )
}
