import {
  CircleHelp,
  Globe2,
  Hourglass,
  Landmark,
  RotateCcw,
  Scale,
  TriangleAlert,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { FateJobRow } from './FateJobRow'
import { FateStepList } from './FateStepList'
import { HistorianViewsPanel } from './HistorianViewsPanel'
import { LimboPanel } from './LimboPanel'
import { type FateControls, useFateControls } from './api'
import { FATE_JOBS } from './fateModel'

function FateState({ controls }: { controls: FateControls }) {
  return (
    <Section
      title='The last epoch, step by step'
      description='What Fate, the chronicler and the historians finished after the last epoch.'
      surface='card'
      level={3}
      icon={Scale}
    >
      <FateStepList steps={controls.steps} />
    </Section>
  )
}

function FateCounters({ controls }: { controls: FateControls }) {
  const failed = controls.steps.filter((step) => step.status === 'failed')
  return (
    <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-5'>
      <MiniStat
        icon={Hourglass}
        label='Last epoch judged'
        value={
          controls.last_epoch === null
            ? 'None yet'
            : formatInteger(controls.last_epoch)
        }
        tone='gold'
      />
      <MiniStat
        icon={Landmark}
        label="Fate's debt"
        value={
          controls.fate_debt_epoch === null
            ? 'None'
            : `Epoch ${formatInteger(controls.fate_debt_epoch)}`
        }
        tone={controls.fate_debt_epoch === null ? 'success' : 'warning'}
      />
      <MiniStat
        icon={CircleHelp}
        label='In limbo'
        value={controls.limbo.length}
        tone={controls.limbo.length > 0 ? 'warning' : 'success'}
      />
      <MiniStat
        icon={Globe2}
        label='Failed world births'
        value={controls.failed_births}
        tone={controls.failed_births > 0 ? 'danger' : 'success'}
      />
      <MiniStat
        icon={TriangleAlert}
        label='Failed steps'
        value={failed.length}
        tone={failed.length > 0 ? 'danger' : 'success'}
      />
    </div>
  )
}

function FateJobs({ controls }: { controls: FateControls }) {
  return (
    <Section
      title='Retry and re-judge'
      description='These run by themselves at the end of every epoch. Run one again now; if it fails, the essence is returned.'
      surface='card'
      level={3}
      icon={RotateCcw}
      tone='verdigris'
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        {FATE_JOBS.map((job) => (
          <FateJobRow key={job.action} job={job} controls={controls} />
        ))}
      </ul>
    </Section>
  )
}

export function FateControlsPage() {
  const controls = useFateControls()
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Muted>
        Fate judges every creation when an epoch ends; then the chronicler and
        the voices of the peoples write. Here you see what they left undone, run
        it again, and overrule Fate yourself.
      </Muted>
      {controls.isPending && <Skeleton className='h-textarea w-full' />}
      {controls.isError && (
        <Text tone='destructive'>{controls.error.message}</Text>
      )}
      {controls.data && controls.data.last_epoch === null && (
        <EmptyState
          icon={Scale}
          title='Fate has not judged yet'
          description='Its controls fill in once the first epoch has ended.'
        />
      )}
      {controls.data && (
        <>
          <FateCounters controls={controls.data} />
          <FateState controls={controls.data} />
          <FateJobs controls={controls.data} />
          <LimboPanel limbo={controls.data.limbo} />
          <HistorianViewsPanel
            views={controls.data.views}
            epoch={controls.data.last_epoch}
          />
        </>
      )}
    </div>
  )
}
