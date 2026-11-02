import { useEpochEstimate } from './api'
import { phaseRatio } from './runModel'
import { useEpochRun } from './runStore'
import { useNow } from './useNow'

const MILLISECONDS = 1000

export type EpochTiming = {
  active: boolean
  elapsedSeconds: number | null
  remainingSeconds: number | null
  averageSeconds: number | null
  samples: number
  overrun: boolean
  ratio: number | null
}

export function remainingFrom(
  serverRemaining: number | null | undefined,
  fetchedAt: number,
  now: number,
  average: number | null,
  elapsed: number | null
): number | null {
  if (serverRemaining !== null && serverRemaining !== undefined)
    return Math.max(0, serverRemaining - (now - fetchedAt) / MILLISECONDS)
  if (average !== null && elapsed !== null)
    return Math.max(0, average - elapsed)
  return null
}

export function useEpochTiming(serverRunning: boolean): EpochTiming {
  const run = useEpochRun()
  const estimate = useEpochEstimate()
  const active = run.active || serverRunning
  const now = useNow(active)
  const data = estimate.data
  const startedAt =
    run.startedAt ??
    (data?.elapsed_seconds !== null && data?.elapsed_seconds !== undefined
      ? estimate.dataUpdatedAt - data.elapsed_seconds * MILLISECONDS
      : null)
  const elapsed =
    active && startedAt !== null
      ? Math.max(0, (now - startedAt) / MILLISECONDS)
      : null
  const average = data?.average_epoch_seconds ?? null
  return {
    active,
    elapsedSeconds: elapsed,
    remainingSeconds: active
      ? remainingFrom(
          data?.running ? data.remaining_seconds : null,
          estimate.dataUpdatedAt,
          now,
          average,
          elapsed
        )
      : null,
    averageSeconds: average,
    samples: data?.samples ?? 0,
    overrun: data?.overrun ?? false,
    ratio: phaseRatio(run.phase),
  }
}
