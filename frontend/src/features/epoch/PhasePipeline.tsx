import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label, Text } from '@/components/typography'
import { EPOCH_STEPS } from './epochSteps'

type PhasePipelineProps = {
  current: number | null
  running: boolean
}

export function PhasePipeline({ current, running }: PhasePipelineProps) {
  return (
    <ol
      aria-label='Phases of an epoch'
      className='grid min-w-0 grid-cols-5 gap-1'
    >
      {EPOCH_STEPS.map((step) => {
        const done = running && current !== null && step.no < current
        const active = running && current === step.no
        const Icon = done ? Check : step.icon
        return (
          <li
            key={step.no}
            data-step-state={active ? 'active' : done ? 'done' : 'idle'}
            className='flex min-w-0 flex-col items-center gap-2 text-center'
          >
            <div className='flex w-full min-w-0 items-center'>
              <span
                className={cn(
                  'h-0.5 flex-1',
                  step.no === 1
                    ? 'bg-transparent'
                    : done || active
                      ? 'bg-primary'
                      : 'bg-border'
                )}
              />
              <span
                className={cn(
                  'flex size-control-lg shrink-0 items-center justify-center rounded-full border-2 transition-colors',
                  active &&
                    'animate-pulse border-primary bg-primary text-primary-foreground',
                  done && 'border-primary bg-primary/15 text-primary',
                  !active &&
                    !done &&
                    'border-border bg-background text-muted-foreground'
                )}
              >
                <Icon aria-hidden='true' className='size-icon-md' />
              </span>
              <span
                className={cn(
                  'h-0.5 flex-1',
                  step.no === EPOCH_STEPS.length
                    ? 'bg-transparent'
                    : done
                      ? 'bg-primary'
                      : 'bg-border'
                )}
              />
            </div>
            {active ? (
              <Text as='span' weight='semibold' tone='primary' truncate={2}>
                {step.label}
              </Text>
            ) : (
              <Label truncate={2}>{step.label}</Label>
            )}
          </li>
        )
      })}
    </ol>
  )
}
