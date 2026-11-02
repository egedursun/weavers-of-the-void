import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Muted, Text } from '@/components/typography'
import { STEP_TITLE, WIZARD_STEPS, type WizardStep } from './wizardModel'
import { STEP_HINT, STEP_ICON } from './wizardVisuals'

const PERCENT = 100

type GenesisStepperProps = {
  current: number
  reachable: (index: number) => boolean
  onPick: (index: number) => void
}

export function GenesisStepper({
  current,
  reachable,
  onPick,
}: GenesisStepperProps) {
  return (
    <nav aria-label='Genesis steps' className='flex min-w-0 flex-col gap-3'>
      <ol className='grid min-w-0 grid-cols-4 gap-1.5'>
        {WIZARD_STEPS.map((step: WizardStep, index) => {
          const Icon = STEP_ICON[step]
          const done = index < current
          const active = index === current
          return (
            <li key={step} className='min-w-0'>
              <Button
                variant='ghost'
                size='tile'
                aria-current={active ? 'step' : undefined}
                disabled={!active && !reachable(index)}
                disabledReason='Finish the steps before it first'
                onClick={() => onPick(index)}
                className={cn(
                  'flex-col items-center justify-start gap-1.5 text-center',
                  active && 'bg-primary/10'
                )}
              >
                <span
                  className={cn(
                    'flex size-control-md shrink-0 items-center justify-center rounded-full border-2 transition-colors',
                    active &&
                      'border-primary bg-primary text-primary-foreground shadow-md',
                    done && 'border-primary/60 bg-primary/15 text-primary',
                    !active &&
                      !done &&
                      'border-border bg-muted text-muted-foreground'
                  )}
                >
                  {done ? (
                    <Check aria-hidden='true' />
                  ) : (
                    <Icon aria-hidden='true' />
                  )}
                </span>
                <Text
                  as='span'
                  variant='caption'
                  weight='semibold'
                  tone={active ? 'primary' : done ? 'default' : 'muted'}
                  truncate
                >
                  {`${index + 1}. ${STEP_TITLE[step]}`}
                </Text>
                <span className='hidden w-full md:block'>
                  <Muted as='span' variant='caption' truncate={2}>
                    {STEP_HINT[step]}
                  </Muted>
                </span>
              </Button>
            </li>
          )
        })}
      </ol>
      <Progress
        size='sm'
        value={(current / (WIZARD_STEPS.length - 1)) * PERCENT}
        aria-label='Genesis progress'
      />
    </nav>
  )
}
