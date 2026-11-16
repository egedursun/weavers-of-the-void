import { Link } from '@tanstack/react-router'
import {
  Globe2,
  type LucideIcon,
  Megaphone,
  Scale,
  ScrollText,
  Wrench,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { type KpiTone, Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type StepState } from './api'
import { STEP_STATUS_BADGE, STEP_STATUS_LABEL, stepLabel } from './fateModel'

const STEP_ICON: Partial<Record<StepState['step'], LucideIcon>> = {
  fate_judgment: Scale,
  chronicle: ScrollText,
  voices: Megaphone,
  world_birth: Globe2,
}

const STEP_TONE: Record<StepState['status'], KpiTone> = {
  pending: 'muted',
  running: 'info',
  done: 'success',
  failed: 'danger',
  skipped: 'muted',
}

type FateStepListProps = {
  steps: StepState[]
}

export function FateStepList({ steps }: FateStepListProps) {
  if (steps.length === 0)
    return (
      <Muted variant='caption'>
        No step of the last epoch has been recorded yet.
      </Muted>
    )
  return (
    <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
      <Paged items={steps} as='li'>
        {(state) => (
          <li
            key={state.step}
            data-fate-step={state.step}
            className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-3'
          >
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Medallion
                icon={STEP_ICON[state.step] ?? Scale}
                tone={STEP_TONE[state.status]}
                size='sm'
              />
              <Text as='span' weight='medium' truncate className='flex-1'>
                {stepLabel(state.step)}
              </Text>
              <Badge size='sm' variant={STEP_STATUS_BADGE[state.status]}>
                {STEP_STATUS_LABEL[state.status]}
              </Badge>
            </div>
            {state.error && (
              <Text variant='caption' tone='destructive' truncate={3}>
                {state.error}
              </Text>
            )}
            {state.step === 'chronicle' && state.status === 'failed' && (
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Button variant='link' size='sm' asChild>
                  <Link to='/settings/maintenance'>
                    <Wrench />
                    Write it in Maintenance
                  </Link>
                </Button>
              </div>
            )}
          </li>
        )}
      </Paged>
    </ul>
  )
}
