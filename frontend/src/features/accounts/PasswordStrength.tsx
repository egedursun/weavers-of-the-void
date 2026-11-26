import { Check, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import { Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type PasswordCheck, type Strength, strengthOf } from './passwordRules'

const STRENGTH: Record<Strength, { label: string; tone: ProgressTone }> = {
  0: { label: 'Not set yet', tone: 'muted' },
  1: { label: 'Too short', tone: 'destructive' },
  2: { label: 'Weak', tone: 'warning' },
  3: { label: 'Fair', tone: 'warning' },
  4: { label: 'Strong', tone: 'success' },
  5: { label: 'Very strong', tone: 'success' },
}

const STEPS = 5
const PERCENT = 100

export function PasswordStrength({
  password,
  checks,
  id,
  min,
}: {
  password: string
  checks: PasswordCheck[]
  id: string
  min: number
}) {
  const strength = strengthOf(password, min)
  const look = STRENGTH[strength]
  return (
    <div
      id={id}
      className='flex min-w-0 flex-col gap-2 rounded-md surface-well p-3'
    >
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted as='span' variant='caption'>
          Strength
        </Muted>
        <Text as='span' variant='caption' weight='semibold' role='status'>
          {look.label}
        </Text>
      </div>
      <Progress
        value={(strength / STEPS) * PERCENT}
        tone={look.tone}
        aria-label={`Password strength: ${look.label}`}
      />
      <ul aria-label='Password rules' className='flex min-w-0 flex-col gap-1'>
        <Paged items={checks} initial={checks.length} as='li'>
          {(check) => (
            <li key={check.key} className='flex min-w-0 items-center gap-2'>
              {check.met ? (
                <Check
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-success'
                />
              ) : (
                <Circle
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
              )}
              <Text
                as='span'
                variant='caption'
                className={cn(!check.met && 'text-muted-foreground')}
              >
                {check.label}
                <span className='sr-only'>
                  {check.met ? ' (met)' : ' (not met)'}
                </span>
              </Text>
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}
