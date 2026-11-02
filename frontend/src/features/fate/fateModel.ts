import { type FateControls, type FateJobAction, type StepState } from './api'

type StepKind = StepState['step']
type StepStatus = StepState['status']

export const STEP_LABEL: Partial<Record<StepKind, string>> = {
  fate_judgment: "Fate's judgment",
  chronicle: 'Chronicle',
  voices: 'Voices of the peoples',
  world_birth: 'World births',
}

export function stepLabel(step: StepKind): string {
  const known = STEP_LABEL[step]
  if (known) return known
  const spaced = step.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export const STEP_STATUS_LABEL: Record<StepStatus, string> = {
  pending: 'Waiting',
  running: 'Running',
  done: 'Done',
  failed: 'Failed',
  skipped: 'Skipped',
}

export const STEP_STATUS_BADGE: Record<
  StepStatus,
  'outline' | 'default' | 'success' | 'destructive' | 'secondary'
> = {
  pending: 'outline',
  running: 'default',
  done: 'success',
  failed: 'destructive',
  skipped: 'secondary',
}

export const NO_RUN_REASON = 'No epoch has run yet.'
export const NO_DEBT_REASON = 'Fate carries no debt.'
export const NO_LIMBO_REASON = 'No creation waits in limbo.'
export const NO_FAILED_BIRTH_REASON = 'No world birth failed.'

export type FateJobSpec = {
  action: FateJobAction
  title: string
  description: string
  rule: string
  step: StepKind | null
}

export const FATE_JOBS: readonly FateJobSpec[] = [
  {
    action: 'fate:retry',
    title: 'Retry Fate for the last epoch',
    description:
      'Fate weighs every creation of the last epoch again and commits new verdicts.',
    rule: 'costs.rejudge_fate',
    step: 'fate_judgment',
  },
  {
    action: 'fate:rejudge_debt',
    title: "Re-judge Fate's debt",
    description:
      'Fate could not weigh an epoch in time. Judge the creations it still owes now.',
    rule: 'costs.rejudge_fate',
    step: null,
  },
  {
    action: 'fate:rejudge_limbo',
    title: 'Re-judge the creations in limbo',
    description:
      'Creations Fate left undecided are weighed again from the oldest epoch on.',
    rule: 'costs.rejudge_fate',
    step: null,
  },
  {
    action: 'voices:retry',
    title: 'Run the voices of the peoples again',
    description:
      'The historians of every people write their account of the last epoch again.',
    rule: 'costs.retry_voices',
    step: 'voices',
  },
  {
    action: 'births:retry',
    title: 'Retry the births of sensed worlds',
    description:
      'Worlds sensed beyond the horizon that failed to be born are tried again.',
    rule: 'costs.retry_births',
    step: 'world_birth',
  },
]

function stepFailed(controls: FateControls, step: StepKind): boolean {
  return controls.steps.some(
    (state) => state.step === step && state.status === 'failed'
  )
}

export function jobBlocker(
  controls: FateControls,
  action: FateJobAction
): string | null {
  if (controls.last_epoch === null) return NO_RUN_REASON
  if (action === 'fate:rejudge_debt' && controls.fate_debt_epoch === null)
    return NO_DEBT_REASON
  if (action === 'fate:rejudge_limbo' && controls.limbo.length === 0)
    return NO_LIMBO_REASON
  if (
    action === 'births:retry' &&
    controls.failed_births === 0 &&
    !stepFailed(controls, 'world_birth')
  )
    return NO_FAILED_BIRTH_REASON
  return null
}

export function isUrgent(controls: FateControls, job: FateJobSpec): boolean {
  if (jobBlocker(controls, job.action) !== null) return false
  if (job.action === 'fate:rejudge_debt' || job.action === 'fate:rejudge_limbo')
    return true
  if (job.action === 'births:retry') return true
  return job.step !== null && stepFailed(controls, job.step)
}

export function urgentJobs(controls: FateControls): FateJobSpec[] {
  return FATE_JOBS.filter((job) => isUrgent(controls, job))
}

export function failedSteps(controls: FateControls): StepState[] {
  return controls.steps.filter((state) => state.status === 'failed')
}
