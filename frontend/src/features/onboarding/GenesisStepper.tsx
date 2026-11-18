import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { STEP_TITLE, WIZARD_STEPS, type WizardStep } from './wizardModel'
import { STEP_HINT, STEP_ICON } from './wizardVisuals'

type GenesisStepperProps = {
  current: number
  reachable: (index: number) => boolean
  onPick: (index: number) => void
}

function Track({ lit, hidden }: { lit: boolean; hidden: boolean }) {
  return (
    <span
      aria-hidden='true'
      className={cn(
        'h-0.5 min-w-0 flex-1 rounded-full transition-colors duration-500',
        hidden ? 'bg-transparent' : lit ? 'bg-primary' : 'bg-border'
      )}
    />
  )
}

export function GenesisStepper({
  current,
  reachable,
  onPick,
}: GenesisStepperProps) {
  const last = WIZARD_STEPS.length - 1
  return (
    <nav aria-label='Genesis steps' className='flex min-w-0 flex-col gap-3'>
      <ol className='grid min-w-0 grid-cols-7'>
        {WIZARD_STEPS.map((step: WizardStep, index) => {
          const done = index < current
          const active = index === current
          const open = active || reachable(index)
          return (
            <li key={step} className='min-w-0'>
              <Button
                variant='ghost'
                size='stage'
                aria-current={active ? 'step' : undefined}
                aria-label={`Stage ${index + 1}: ${STEP_TITLE[step]}${done ? ', done' : ''}`}
                disabled={!open}
                disabledReason='Finish the stages before it first'
                onClick={() => onPick(index)}
                className='hover:bg-transparent'
              >
                <span className='flex min-h-control-lg w-full min-w-0 items-center'>
                  <Track lit={index <= current} hidden={index === 0} />
                  <span
                    className={cn(
                      'rounded-full transition-shadow duration-500',
                      active &&
                        'shadow-lg ring-2 shadow-primary/40 ring-primary ring-offset-2 ring-offset-card'
                    )}
                  >
                    <Medallion
                      icon={done ? Check : STEP_ICON[step]}
                      tone={done || active ? 'gold' : 'muted'}
                      size={active ? 'md' : 'sm'}
                    />
                  </span>
                  <Track lit={index < current} hidden={index === last} />
                </span>
                <span className='flex min-w-0 flex-col items-center gap-0.5 px-0.5 text-center'>
                  <Label variant='overline' className='hidden sm:block'>
                    {`Stage ${index + 1}`}
                  </Label>
                  <Text
                    as='span'
                    variant='caption'
                    weight='semibold'
                    tone={active ? 'primary' : done ? 'default' : 'muted'}
                    truncate={2}
                    className='hidden md:block'
                  >
                    {STEP_TITLE[step]}
                  </Text>
                </span>
              </Button>
            </li>
          )
        })}
      </ol>
      <div className='flex min-w-0 flex-col items-center gap-0.5 text-center md:hidden'>
        <Text as='span' weight='semibold' tone='primary'>
          {`Stage ${current + 1} of ${WIZARD_STEPS.length}: ${STEP_TITLE[WIZARD_STEPS[current]]}`}
        </Text>
        <Muted as='span' variant='caption'>
          {STEP_HINT[WIZARD_STEPS[current]]}
        </Muted>
      </div>
    </nav>
  )
}
