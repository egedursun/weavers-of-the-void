import { navItem } from '@/config/navigation'
import {
  Activity,
  AlarmClock,
  CircleDashed,
  Crown,
  History,
  Hourglass,
  PauseCircle,
  Sunrise,
  Timer,
} from 'lucide-react'
import { formatDuration } from '@/lib/units'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  KpiTile,
  Medallion,
  PageHeader,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { FateStatusCard } from '@/features/fate/FateStatusCard'
import { EpochBreakdownPanel } from '@/features/overview/EpochBreakdownPanel'
import { type WorldState, useWorldState } from '@/features/overview/api'
import { CompleteEpochButton } from './CompleteEpochButton'
import { EpochProgress } from './EpochProgress'
import { PhasePipeline } from './PhasePipeline'
import { SonTurnControl } from './SonTurnControl'
import { StopEpochButton } from './StopEpochButton'
import { TurnOrderPanel } from './TurnOrderPanel'
import { useEpochEstimate } from './api'
import { stepLabel } from './epochSteps'
import { epochScopeText } from './epochText'
import { useEpochRun } from './runStore'
import { useEpochTiming } from './useEpochTiming'

const ITEM = navItem('epoch')
const BARS_SHOWN = 10
const PERCENT = 100

function CurrentRun({ state }: { state: WorldState }) {
  const timing = useEpochTiming(state.epoch_running)
  const phase = useEpochRun((run) => run.phase)
  const half = state.half_epoch
  const sons = state.sons.filter((item) => item.son.status === 'active').length
  const waiting = state.pending_son_ids.length
  return (
    <Section
      title='The current epoch'
      description={epochScopeText(
        waiting,
        state.world?.mortal_agents_per_epoch ?? null
      )}
      surface='card'
    >
      <PhasePipeline
        current={phase?.no ?? half?.phase ?? null}
        running={timing.active || half !== null}
      />
      {timing.active ? (
        <EpochProgress />
      ) : (
        <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
          <Medallion
            icon={half ? PauseCircle : CircleDashed}
            tone={half ? 'warning' : 'muted'}
            size='sm'
          />
          <Muted>
            {half
              ? `Epoch ${half.epoch} was interrupted at ${stepLabel(half.phase).toLowerCase()}. Completing it resumes from there.`
              : 'The world rests. Complete the epoch when the sons are ready.'}
          </Muted>
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <KpiTile
          label='Epoch'
          value={state.world?.epoch ?? 0}
          icon={Hourglass}
          tone='gold'
        />
        <KpiTile
          label='Sons still to act'
          value={`${waiting} of ${sons}`}
          icon={Crown}
          tone={waiting > 0 ? 'info' : 'success'}
          meter={{
            value: sons - waiting,
            max: Math.max(1, sons),
            label: `${sons - waiting} of ${sons} sons have acted`,
          }}
        />
        <KpiTile
          label='Average length'
          value={
            timing.averageSeconds !== null
              ? formatDuration(timing.averageSeconds)
              : '—'
          }
          icon={Timer}
          tone='verdigris'
          hint={
            timing.averageSeconds !== null
              ? `Over ${timing.samples} epochs`
              : 'Measured after the first run'
          }
        />
        <KpiTile
          label='Time left'
          value={
            timing.remainingSeconds !== null
              ? timing.overrun
                ? 'Overrunning'
                : formatDuration(timing.remainingSeconds)
              : '—'
          }
          icon={AlarmClock}
          tone={timing.overrun ? 'warning' : 'muted'}
          hint={
            timing.active
              ? 'Estimated from earlier runs'
              : 'Shown while an epoch runs'
          }
        />
      </div>
    </Section>
  )
}

type Bar = { key: string; label: string; seconds: number; failed?: boolean }

function DurationBars({ bars, unit }: { bars: Bar[]; unit: string }) {
  const longest = Math.max(...bars.map((bar) => bar.seconds), 1)
  const page = useShowMore(bars, BARS_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ul className='flex min-w-0 flex-col gap-3'>
        {page.visible.map((bar) => (
          <li key={bar.key} className='flex min-w-0 flex-col gap-1'>
            <div className='flex min-w-0 items-baseline justify-between gap-3'>
              <Text
                as='span'
                truncate
                className='min-w-0 flex-1'
                tone={bar.failed ? 'destructive' : 'default'}
              >
                {bar.failed ? `${bar.label} (failed)` : bar.label}
              </Text>
              <Muted as='span' variant='caption' className='shrink-0'>
                {`${unit}${formatDuration(bar.seconds)}`}
              </Muted>
            </div>
            <Progress
              size='sm'
              tone={bar.failed ? 'destructive' : 'default'}
              value={(bar.seconds / longest) * PERCENT}
              aria-label={`${bar.label} ${formatDuration(bar.seconds)}`}
            />
          </li>
        ))}
      </ul>
      <ShowMore state={page} noun={['step', 'steps']} />
    </div>
  )
}

function PhaseStarts() {
  const estimate = useEpochEstimate()
  const starts = Object.entries(
    estimate.data?.average_phase_start_seconds ?? {}
  ).sort((left, right) => left[1] - right[1])
  return (
    <Section
      title='Phase rhythm'
      description='When each phase usually begins, measured over recent epochs.'
      surface='card'
    >
      {estimate.isPending && <Skeleton className='h-24 w-full' />}
      {estimate.isError && (
        <Text tone='destructive'>{estimate.error.message}</Text>
      )}
      {estimate.data && starts.length === 0 && (
        <EmptyState
          size='compact'
          icon={Activity}
          title='No rhythm yet'
          description='After a few epochs run here, each phase shows when it usually begins.'
        />
      )}
      {starts.length > 0 && (
        <DurationBars
          unit='after '
          bars={starts.map(([phase, seconds]) => ({
            key: phase,
            label: stepLabel(phase),
            seconds,
          }))}
        />
      )}
    </Section>
  )
}

function LastRun() {
  const last = useEpochRun((run) => run.last)
  return (
    <Section
      title='The last run'
      description='How long the last epoch run in this session took, step by step.'
      surface='card'
    >
      {!last ? (
        <EmptyState
          size='compact'
          icon={History}
          title='No run in this session'
          description='Complete or resume an epoch and its timing appears here.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            <KpiTile
              label={last.stoppedAtPhase === null ? 'Epoch closed' : 'Stopped'}
              value={
                last.stoppedAtPhase === null
                  ? `${last.epoch} → ${last.newEpoch}`
                  : stepLabel(last.stoppedAtPhase)
              }
              icon={last.stoppedAtPhase === null ? Sunrise : PauseCircle}
              tone={last.stoppedAtPhase === null ? 'success' : 'warning'}
            />
            <KpiTile
              label='Duration'
              value={formatDuration(last.durationSeconds)}
              icon={Timer}
              tone='verdigris'
              hint={`${last.phases.length} engine steps`}
            />
          </div>
          {last.phases.length > 0 && (
            <DurationBars
              unit=''
              bars={[...last.phases]
                .sort((left, right) => right.seconds - left.seconds)
                .map((phase, index) => ({
                  key: `${phase.name}-${index}`,
                  label: phase.name,
                  seconds: phase.seconds,
                  failed: phase.failed,
                }))}
            />
          )}
        </div>
      )}
    </Section>
  )
}

export function EpochControlScreen() {
  const state = useWorldState()
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          <>
            <StopEpochButton />
            <CompleteEpochButton />
          </>
        }
      />
      {state.isPending && <Skeleton className='h-48 w-full' />}
      {state.isError && <Text tone='destructive'>{state.error.message}</Text>}
      {state.data && !state.data.world && (
        <EmptyState
          icon={Hourglass}
          title='No world yet'
          description='Epochs begin once genesis has created a world.'
        />
      )}
      {state.data?.world && (
        <>
          <div className='grid min-w-0 grid-cols-1 items-start gap-6 lg:grid-cols-2'>
            <div className='flex min-w-0 flex-col gap-6'>
              <CurrentRun state={state.data} />
              <TurnOrderPanel state={state.data} />
            </div>
            <div className='flex min-w-0 flex-col gap-6'>
              <SonTurnControl state={state.data} />
              <LastRun />
              <PhaseStarts />
            </div>
          </div>
          <FateStatusCard />
          <EpochBreakdownPanel state={state.data} />
        </>
      )}
    </>
  )
}
