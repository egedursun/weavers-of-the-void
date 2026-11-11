import { useState } from 'react'
import {
  Activity,
  Crown,
  Gauge,
  History,
  Landmark,
  Swords,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type CyclesView, type ReadingView, useCycleAction } from './api'
import { CHALLENGES, COMPONENTS, PHASES, RESPONSES } from './labels'
import { clamp, SPAN, useRow } from './model'

type Challenge = CyclesView['challenges'][number]
type Stress = NonNullable<CyclesView['stress']>

const NOT_REALM = 'Only a realm carries these strains'
const SERIES = [
  { key: 'psi', label: 'Political stress', color: 'var(--color-destructive)' },
  { key: 'pressure', label: 'Population pressure', color: 'var(--color-info)' },
  { key: 'immiseration', label: 'Immiseration', color: 'var(--color-warning)' },
  {
    key: 'elite_overproduction',
    label: 'Elite overproduction',
    color: 'var(--color-brand-gold)',
  },
  {
    key: 'fiscal_distress',
    label: 'Fiscal distress',
    color: 'var(--color-brand-verdigris)',
  },
] as const

export function SecularCycleChart({
  readings,
  title,
}: {
  readings: ReadingView[]
  title: string
}) {
  if (readings.length < 2) {
    return (
      <Muted variant='caption'>
        The secular cycle shows once two epochs have been read.
      </Muted>
    )
  }
  return (
    <div
      data-surface='SecularCycleChart'
      id='cycles-psi-chart'
      className='min-w-0'
    >
      <LineChart
        title={title}
        max={SPAN}
        xLabel={(epoch) => `E${epoch}`}
        tooltipLabel={(epoch) => {
          const found = readings.find((item) => item.epoch === epoch)
          return found
            ? `Epoch ${epoch}: ${PHASES[found.phase].label}`
            : `Epoch ${epoch}`
        }}
        series={SERIES.map((line) => ({
          key: line.key,
          label: line.label,
          color: line.color,
          points: readings.map((item) => ({
            x: item.epoch,
            y: item[line.key],
          })),
        }))}
      />
    </div>
  )
}

function StressCard({
  polityId,
  row,
  blocked,
}: {
  polityId: number
  row: Stress
  blocked: string | null
}) {
  const action = useRow(
    'stress:edit',
    'stress:delete',
    { polity_id: polityId },
    blocked
  )
  const phase = PHASES[row.phase]
  return (
    <Held
      icon={phase.icon}
      tone={phase.tone}
      title={`In ${phase.label.toLowerCase()}`}
      caption={`Political stress ${row.psi} · read in epoch ${row.updated_epoch}`}
      removeLabel='Read anew'
      editTitle='Set the strains'
      note='The stress index is the cube root of immiseration, elite overproduction and fiscal distress; a realm above its crisis mark breeds coups, revolts and counter-elites.'
      fields={[
        {
          key: 'pressure',
          label: 'Population pressure',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'immiseration',
          label: 'Immiseration',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'elite_overproduction',
          label: 'Elite overproduction',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'fiscal_distress',
          label: 'Fiscal distress',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'aspirants', label: 'Aspirants', kind: 'number', min: 0 },
        { key: 'positions', label: 'Elite posts', kind: 'number', min: 0 },
        {
          key: 'challenge',
          label: 'Challenge index',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'phase',
          label: 'Phase of the cycle',
          kind: 'pick',
          table: table(PHASES),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          {row.parts.map((part) => {
            const spec = COMPONENTS[part.component]
            return (
              <KpiTile
                key={part.component}
                label={spec.label}
                value={part.value}
                icon={spec.icon}
                tone={spec.tone}
              />
            )
          })}
        </div>
      </div>
      <Meter
        label='Political stress index'
        value={row.psi}
        max={SPAN}
        tone={row.psi >= 55 ? 'destructive' : 'warning'}
        icon={Gauge}
      />
      <Meter
        label='Challenge index'
        value={row.challenge}
        max={SPAN}
        tone='info'
        icon={Zap}
      />
      <Facts
        items={[
          ['Aspirants to the elite', row.aspirants],
          ['Elite posts', row.positions],
          [
            'Aspirants per post',
            row.positions > 0
              ? (row.aspirants / row.positions).toFixed(2)
              : 'no posts',
          ],
        ]}
      />
    </Held>
  )
}

function ReadingRow({
  polityId,
  row,
  blocked,
}: {
  polityId: number
  row: ReadingView
  blocked: string | null
}) {
  const action = useRow(
    'stress_reading:edit',
    'stress_reading:delete',
    { polity_id: polityId, epoch: row.epoch },
    blocked
  )
  const phase = PHASES[row.phase]
  return (
    <Held
      icon={History}
      tone={phase.tone}
      title={`Epoch ${row.epoch}: ${phase.label}`}
      caption={`Stress ${row.psi} · pressure ${row.pressure} · misery ${row.immiseration} · elites ${row.elite_overproduction} · fiscal ${row.fiscal_distress}`}
      removeLabel='Strike the reading'
      editTitle='Set this reading'
      note='Past readings draw the secular cycle; they do not change the realm now.'
      fields={[
        {
          key: 'pressure',
          label: 'Population pressure',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'immiseration',
          label: 'Immiseration',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'elite_overproduction',
          label: 'Elite overproduction',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'fiscal_distress',
          label: 'Fiscal distress',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'psi',
          label: 'Political stress',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'phase',
          label: 'Phase of the cycle',
          kind: 'pick',
          table: table(PHASES),
        },
      ]}
      locked={[]}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function ChallengeRow({
  row,
  blocked,
}: {
  row: Challenge
  blocked: string | null
}) {
  const action = useRow(
    'challenge:edit',
    'challenge:delete',
    { challenge_id: row.id },
    blocked
  )
  const kind = CHALLENGES[row.kind]
  const response = RESPONSES[row.response]
  return (
    <Held
      icon={kind.icon}
      tone={response.tone}
      title={`${kind.label}, severity ${row.severity}`}
      caption={`Epoch ${row.epoch}`}
      removeLabel='Strike from the record'
      editTitle='Set the challenge'
      note='A challenge in the middle band spurs research and new ways; too slight a one leaves the realm idle, too heavy a one breaks it.'
      fields={[
        {
          key: 'kind',
          label: 'What tried the realm',
          kind: 'pick',
          table: table(CHALLENGES),
        },
        {
          key: 'severity',
          label: 'Severity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'response',
          label: 'Its answer',
          kind: 'pick',
          table: table(RESPONSES),
        },
        {
          key: 'source_node_id',
          label: 'Where it struck',
          kind: 'node',
          types: ['settlement', 'region', 'people'],
        },
      ]}
      locked={[]}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={response.icon}>{response.label}</Chip>
          <Chip icon={Landmark}>
            <Ref node={row.source} empty='the whole realm' />
          </Chip>
        </>
      }
    />
  )
}

function StressForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [phase, setPhase] = useState<keyof typeof PHASES>('growth')
  const [pressure, setPressure] = useState('30')
  const setting = useCycleAction(
    'stress:set',
    (_: void) => ({ polity_id: polityId, phase, pressure: clamp(pressure) }),
    'The strains are set'
  )
  const busy = why(isRealm ? blocked : NOT_REALM, setting.isPending)
  return (
    <ForgeCard
      icon={Activity}
      tone='warning'
      title='Set the strains of the realm'
      note='The engine reads them anew each epoch unless you hold a value.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Activity />
          Set them
        </Button>
      }
    >
      <MindPicker
        label='Phase of the cycle'
        value={phase}
        table={table(PHASES)}
        blocked={busy}
        onPick={(value) => setPhase(value as keyof typeof PHASES)}
      />
      <NumberField
        label='Population pressure'
        value={pressure}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setPressure}
      />
    </ForgeCard>
  )
}

function ReadingForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [epoch, setEpoch] = useState('0')
  const [psi, setPsi] = useState('20')
  const [phase, setPhase] = useState<keyof typeof PHASES>('growth')
  const writing = useCycleAction(
    'stress_reading:set',
    (_: void) => ({
      polity_id: polityId,
      epoch: clamp(epoch, 100_000),
      psi: clamp(psi),
      phase,
    }),
    'The reading is written'
  )
  const busy = why(isRealm ? blocked : NOT_REALM, writing.isPending)
  return (
    <ForgeCard
      icon={History}
      tone='info'
      title='Write a past reading'
      note='Fill a gap in the secular cycle of an earlier epoch.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => writing.mutate()}
        >
          <History />
          Write it
        </Button>
      }
    >
      <NumberField
        label='Epoch'
        value={epoch}
        min={0}
        blocked={busy}
        onChange={setEpoch}
      />
      <NumberField
        label='Political stress'
        value={psi}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setPsi}
      />
      <MindPicker
        label='Phase'
        value={phase}
        table={table(PHASES)}
        blocked={busy}
        onPick={(value) => setPhase(value as keyof typeof PHASES)}
      />
    </ForgeCard>
  )
}

function ChallengeForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [kind, setKind] = useState<keyof typeof CHALLENGES>('famine')
  const [severity, setSeverity] = useState('30')
  const striking = useCycleAction(
    'challenge:strike',
    (_: void) => ({ polity_id: polityId, kind, severity: clamp(severity) }),
    'The realm is tried'
  )
  const busy = why(isRealm ? blocked : NOT_REALM, striking.isPending)
  return (
    <ForgeCard
      icon={Swords}
      tone='danger'
      title='Try the realm'
      note='Lay a challenge on the realm and see whether it answers, idles or breaks.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => striking.mutate()}
        >
          <Swords />
          Try it
        </Button>
      }
    >
      <MindPicker
        label='What tries it'
        value={kind}
        table={table(CHALLENGES)}
        blocked={busy}
        onPick={(value) => setKind(value as keyof typeof CHALLENGES)}
      />
      <NumberField
        label='Severity'
        value={severity}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setSeverity}
      />
    </ForgeCard>
  )
}

export function StressPanel({
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
  const isRealm = kind === 'polity'
  return (
    <div data-surface='StressPanel' className='flex min-w-0 flex-col gap-4'>
      {data.stress ? (
        <StressCard polityId={nodeId} row={data.stress} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isRealm
            ? 'The strains of this realm are read at the next epoch.'
            : NOT_REALM}
        </Muted>
      )}
      <SecularCycleChart
        readings={data.readings}
        title={`The secular cycle of ${data.node.name}`}
      />
      <StressForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
      <Listed
        title='Past readings'
        items={[...data.readings].reverse()}
        empty='No epoch has been read yet.'
        noun={['reading', 'readings']}
        itemKey={(item) => item.epoch}
      >
        {(item) => (
          <ReadingRow polityId={nodeId} row={item} blocked={blocked} />
        )}
      </Listed>
      <ReadingForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
      <Listed
        title='Challenges met'
        items={data.challenges}
        empty='No loss has yet tried this realm.'
        noun={['challenge', 'challenges']}
        itemKey={(item) => item.id}
      >
        {(item) => <ChallengeRow row={item} blocked={blocked} />}
      </Listed>
      <ChallengeForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
      <Chip icon={Crown}>
        {isRealm
          ? 'Counter-elites gather when aspirants outnumber posts'
          : NOT_REALM}
      </Chip>
    </div>
  )
}
