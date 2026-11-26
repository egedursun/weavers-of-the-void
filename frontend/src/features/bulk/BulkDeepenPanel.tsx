import { useState } from 'react'
import {
  CircleCheck,
  CircleX,
  Hourglass,
  Layers,
  Square,
  Tags,
  WandSparkles,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatMilliseconds, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  MiniStat,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Stat, Text } from '@/components/typography'
import { stepAverageMs, useModelMetrics } from '@/features/metrics/api'
import { useWorldState } from '@/features/overview/api'
import { modelBlock } from '@/features/providers/modelReadiness'
import {
  type LogLine,
  useAssignNames,
  useBulkStatus,
  useStartBulk,
  useStopBulk,
} from './api'

const LOG_SHOWN = 200
const PERCENT = 100
const DEEPEN_STEP = 'deepen'

const clock = new Intl.DateTimeFormat('en-US', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

const LEVEL_TONE = {
  info: 'muted',
  warning: 'warning',
  error: 'destructive',
} as const

function BulkLog({ lines }: { lines: LogLine[] }) {
  if (lines.length === 0) return null
  return (
    <ol
      aria-label='Deepening log'
      className='flex max-h-64 min-w-0 flex-col gap-1 overflow-y-auto rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <Paged items={lines.slice(-LOG_SHOWN)} as='li'>
        {(line, index) => (
          <li key={`${line.at}-${index}`} className='flex min-w-0 gap-2'>
            <Muted
              as='span'
              variant='caption'
              className='shrink-0 tabular-nums'
            >
              {clock.format(new Date(line.at))}
            </Muted>
            <Text as='span' variant='caption' tone={LEVEL_TONE[line.level]}>
              {line.text}
            </Text>
          </li>
        )}
      </Paged>
    </ol>
  )
}

export function BulkDeepenPanel() {
  const status = useBulkStatus()
  const state = useWorldState()
  const metrics = useModelMetrics(null)
  const start = useStartBulk()
  const stop = useStopBulk()
  const names = useAssignNames()
  const [confirming, setConfirming] = useState(false)
  const llmBlock = modelBlock(state.data, 'writing')
  const readOnly = state.data?.read_only ?? false
  const averageMs = stepAverageMs(metrics.data, DEEPEN_STEP)

  return (
    <Section
      title='Bulk deepening'
      description='Every record not yet deepened is deepened in order of importance, one model call each. How many run at once is set in World rules, Batch jobs.'
      surface='card'
      level={3}
      icon={WandSparkles}
      tone='verdigris'
    >
      {status.isPending && <Skeleton className='h-24 w-full' />}
      {status.isError && <Text tone='destructive'>{status.error.message}</Text>}
      {status.data &&
        (() => {
          const { state: run, waiting, unnamed, log } = status.data
          const processed = run.done + run.failed + run.skipped
          const estimate =
            averageMs === null
              ? 'No deepening has been measured yet, so there is no time estimate.'
              : `About ${formatMilliseconds(averageMs * waiting)} for ${plural(waiting, 'record', 'records')}.`
          const blocked =
            llmBlock ?? (readOnly ? 'A guest world is read-only' : null)
          return (
            <div className='flex min-w-0 flex-col gap-4'>
              <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
                <MiniStat
                  icon={Hourglass}
                  label='Waiting'
                  value={waiting}
                  tone={waiting > 0 ? 'gold' : 'success'}
                />
                <MiniStat
                  icon={Tags}
                  label='Unnamed'
                  value={unnamed}
                  tone={unnamed > 0 ? 'warning' : 'muted'}
                />
                <MiniStat
                  icon={CircleCheck}
                  label='Deepened this run'
                  value={run.done}
                  tone='success'
                />
                <MiniStat
                  icon={CircleX}
                  label='Failed this run'
                  value={run.failed}
                  tone={run.failed > 0 ? 'danger' : 'muted'}
                />
              </div>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                {run.running ? (
                  <>
                    <Badge variant='default'>
                      {run.stop_requested ? 'Stopping' : 'Running'}
                    </Badge>
                    <Button
                      act={stop}
                      variant='destructive'
                      disabled={run.stop_requested || stop.isPending}
                      disabledReason='It stops when the current record finishes'
                      onClick={() =>
                        stop.mutate(undefined, {
                          onSuccess: () =>
                            toast.success(
                              'It stops when the current record finishes'
                            ),
                          onError: (error) => toast.error(error.message),
                        })
                      }
                    >
                      <Square />
                      Stop
                    </Button>
                  </>
                ) : (
                  <Button
                    act={start}
                    disabled={
                      blocked !== null || waiting === 0 || start.isPending
                    }
                    disabledReason={
                      blocked ??
                      (waiting === 0 ? 'Every record is deepened' : 'Starting')
                    }
                    onClick={() => setConfirming(true)}
                  >
                    <WandSparkles />
                    {`Deepen ${plural(waiting, 'record', 'records')}`}
                  </Button>
                )}
                {unnamed > 0 && (
                  <Button
                    act={names}
                    variant='outline'
                    disabled={blocked !== null || names.isPending}
                    disabledReason={blocked ?? 'Naming'}
                    onClick={() =>
                      names.mutate(undefined, {
                        onSuccess: () =>
                          toast.success('The unnamed records are being named'),
                        onError: (error) => toast.error(error.message),
                      })
                    }
                  >
                    <Tags />
                    {`Name ${unnamed} unnamed records`}
                  </Button>
                )}
              </div>
              <Muted>{estimate}</Muted>
              {unnamed > 0 && (
                <Muted variant='caption'>
                  The world engine opens some records with a temporary name.
                  They are also named at the end of each epoch, on startup and
                  before bulk deepening.
                </Muted>
              )}
              {(run.running || run.total > 0) && (
                <div className='flex min-w-0 flex-col gap-2'>
                  <Progress
                    value={
                      run.total > 0 ? (processed / run.total) * PERCENT : 0
                    }
                    aria-label='Bulk deepening progress'
                  />
                  <Muted variant='caption'>
                    <Stat value={processed} />
                    {` of ${run.total} processed · ${run.done} done · ${run.failed} failed · ${run.skipped} skipped`}
                  </Muted>
                  {(run.current ?? []).length > 0 && (
                    <Text variant='caption' truncate={2}>
                      {`Now: ${(run.current ?? []).map((item) => item.name).join(', ')}`}
                    </Text>
                  )}
                </div>
              )}
              {log.length === 0 && !run.running && run.total === 0 ? (
                <EmptyState
                  size='compact'
                  icon={Layers}
                  title='No deepening yet'
                  description='Start a run and every record it touches is logged here.'
                />
              ) : (
                <BulkLog lines={log} />
              )}
              <ConfirmDialog
                act={start}
                open={confirming}
                onOpenChange={setConfirming}
                title={`Deepen ${plural(waiting, 'record', 'records')}?`}
                desc={`Each record is one model call on your subscription. ${estimate}`}
                confirmText='Start deepening'
                isLoading={start.isPending}
                handleConfirm={() =>
                  start.mutate(undefined, {
                    onSuccess: () => {
                      setConfirming(false)
                      toast.success('Bulk deepening started')
                    },
                    onError: (error) => {
                      setConfirming(false)
                      toast.error(error.message)
                    },
                  })
                }
              />
            </div>
          )
        })()}
    </Section>
  )
}
