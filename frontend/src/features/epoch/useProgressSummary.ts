import { useEffect } from 'react'
import { formatClock, formatDuration, plural } from '@/lib/units'
import { JOB_KIND_LABEL, isJobKind } from '@/constants/jobs'
import { useWorldState } from '@/features/overview/api'
import { type Job, useRunningJobs } from './api'
import { isStaleRun } from './runModel'
import { useEpochRun } from './runStore'
import { useEpochTiming } from './useEpochTiming'

export type ProgressSummary = {
  visible: boolean
  title: string
  ratio: number | null
  parts: string[]
  subtitle: string | null
}

function jobTitle(job: Job): string {
  return isJobKind(job.kind) ? JOB_KIND_LABEL[job.kind] : job.kind
}

export function useProgressSummary(): ProgressSummary {
  const state = useWorldState()
  const run = useEpochRun()
  const jobs = useRunningJobs()
  const stale = isStaleRun(run, state.data?.epoch_running, state.dataUpdatedAt)
  const reset = run.reset
  useEffect(() => {
    if (stale) reset()
  }, [stale, reset])
  const timing = useEpochTiming(Boolean(state.data?.epoch_running))
  if (timing.active) {
    const parts = [
      run.phase
        ? `Phase ${run.phase.no}/${run.phase.total}: ${run.phase.name}`
        : 'Preparing the epoch',
      timing.elapsedSeconds !== null
        ? formatClock(timing.elapsedSeconds)
        : null,
      timing.remainingSeconds !== null
        ? timing.overrun
          ? 'running longer than usual'
          : `about ${formatDuration(timing.remainingSeconds)} left`
        : null,
      run.sonQueue ? `son ${run.sonQueue.no}/${run.sonQueue.total}` : null,
    ].filter((part) => part !== null)
    return {
      visible: true,
      title: run.epoch ? `Epoch ${run.epoch}` : 'Epoch',
      ratio: timing.ratio,
      parts,
      subtitle: run.stopRequested
        ? 'Stopping at the next safe point'
        : run.subtitle,
    }
  }
  const job = jobs.find((item) => item.status === 'running') ?? jobs[0]
  if (!job)
    return { visible: false, title: '', ratio: null, parts: [], subtitle: null }
  return {
    visible: true,
    title: jobTitle(job),
    ratio: job.status === 'running' && job.progress > 0 ? job.progress : null,
    parts: jobs.length > 1 ? [`${plural(jobs.length, 'job', 'jobs')}`] : [],
    subtitle: job.stage,
  }
}
