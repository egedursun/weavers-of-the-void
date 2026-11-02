import { Link } from '@tanstack/react-router'
import { Scale } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { FateJobRow } from './FateJobRow'
import { type FateControls, useFateControls } from './api'
import { failedSteps, stepLabel, urgentJobs } from './fateModel'

function Summary({ controls }: { controls: FateControls }) {
  const failed = failedSteps(controls).filter(
    (state) => !(state.step === 'world_birth' && controls.failed_births > 0)
  )
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      {controls.fate_debt_epoch !== null && (
        <Badge size='sm' variant='warning'>
          {`Fate owes epoch ${formatInteger(controls.fate_debt_epoch)}`}
        </Badge>
      )}
      {controls.limbo.length > 0 && (
        <Badge size='sm' variant='secondary'>
          {`${formatInteger(controls.limbo.length)} in limbo`}
        </Badge>
      )}
      {controls.failed_births > 0 && (
        <Badge size='sm' variant='destructive'>
          {`${formatInteger(controls.failed_births)} failed world birth${controls.failed_births === 1 ? '' : 's'}`}
        </Badge>
      )}
      {failed.map((state) => (
        <Badge key={state.step} size='sm' variant='destructive'>
          {`${stepLabel(state.step)} failed`}
        </Badge>
      ))}
    </div>
  )
}

export function FateStatusCard() {
  const controls = useFateControls()
  const jobs = controls.data ? urgentJobs(controls.data) : []
  const calm =
    controls.data !== undefined &&
    jobs.length === 0 &&
    failedSteps(controls.data).length === 0 &&
    controls.data.limbo.length === 0
  return (
    <Section
      title='Fate after the epoch'
      description='Verdicts, the chronicle, the voices of the peoples and world births of the last epoch.'
      surface='card'
      actions={
        <Button variant='outline' size='sm' asChild>
          <Link to='/settings/fate'>
            <Scale />
            Fate controls
          </Link>
        </Button>
      }
    >
      {controls.isPending && <Skeleton className='h-control-lg w-full' />}
      {controls.isError && (
        <Text tone='destructive'>{controls.error.message}</Text>
      )}
      {controls.data && controls.data.last_epoch === null && (
        <Muted>
          No Fate run is recorded in this world yet. Fate judges at the end of
          the next epoch.
        </Muted>
      )}
      {controls.data && controls.data.last_epoch !== null && calm && (
        <Muted>
          {`Fate is at rest: everything of epoch ${formatInteger(controls.data.last_epoch)} was judged and written.`}
        </Muted>
      )}
      {controls.data && !calm && <Summary controls={controls.data} />}
      {controls.data && jobs.length > 0 && (
        <ul className='flex min-w-0 flex-col'>
          {jobs.map((job) => (
            <FateJobRow key={job.action} job={job} controls={controls.data} />
          ))}
        </ul>
      )}
    </Section>
  )
}
