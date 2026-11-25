import { useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { fixedCost } from '@/features/entity/actions/gate'
import { JobRunRow } from '@/features/maintenance/JobRunRow'
import {
  useCostText,
  useGodGate,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { FATE_JOB_RUNNERS, type FateControls, fateKeys } from './api'
import { type FateJobSpec, jobBlocker } from './fateModel'

const RETRY_RUNNING = 'Another retry is still running.'
const RUNNING_NOW = 'Running now; see the progress below.'

type FateJobRowProps = {
  job: FateJobSpec
  controls: FateControls
}

export function FateJobRow({ job, controls }: FateJobRowProps) {
  const costOf = useCostText()
  const { reason } = useGodGate()
  const running = useRunningJob((item) => item.kind === 'retry')
  const [spent, setSpent] = useState(0)
  const action = useGodAction({
    run: () => FATE_JOB_RUNNERS[job.action](),
    invalidate: [fateKeys.controls],
    onDone: (result) => setSpent(result.essence_spent),
  })
  const cost = fixedCost(costOf(job.action)?.cost) ?? undefined
  const blocked =
    reason({ llm: true, world: true, cost }) ??
    jobBlocker(controls, job.action) ??
    (running
      ? running.id === action.jobId
        ? RUNNING_NOW
        : RETRY_RUNNING
      : null)
  return (
    <JobRunRow
      act={action}
      id={job.action}
      title={job.title}
      description={job.description}
      label='Run'
      icon={RotateCcw}
      cost={cost}
      rule={job.rule}
      blocked={blocked}
      pending={action.isPending}
      error={null}
      jobId={action.jobId}
      spent={spent}
      onRun={() => action.mutate()}
      onDismiss={action.clearJob}
    />
  )
}
