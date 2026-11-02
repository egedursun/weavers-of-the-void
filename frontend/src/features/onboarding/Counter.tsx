import { type LucideIcon, Minus, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted, Stat, Text } from '@/components/typography'

type CounterProps = {
  label: string
  hint: string
  icon: LucideIcon
  value: number
  min: number
  max: number
  onChange: (value: number) => void
}

export function Counter({
  label,
  hint,
  icon: Icon,
  value,
  min,
  max,
  onChange,
}: CounterProps) {
  const safe = Number.isFinite(value) ? value : min
  return (
    <div
      data-onboarding='counter'
      className='flex min-w-0 flex-wrap items-center gap-3 rounded-lg border bg-card p-3'
    >
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='semibold'>
          {label}
        </Text>
        <Muted as='span' variant='caption'>
          {hint}
        </Muted>
        <div className='flex min-w-0 flex-wrap gap-1 pt-1.5' aria-hidden='true'>
          {Array.from({ length: max }, (_, index) => (
            <Icon
              key={index}
              className={
                index < safe
                  ? 'size-icon-sm text-primary'
                  : 'size-icon-sm text-muted-foreground/40'
              }
            />
          ))}
        </div>
      </div>
      <div className='flex shrink-0 items-center gap-2'>
        <Button
          variant='outline'
          size='icon'
          aria-label={`Fewer: ${label}`}
          disabled={safe <= min}
          disabledReason={`At least ${min}`}
          onClick={() => onChange(Math.max(min, safe - 1))}
        >
          <Minus />
        </Button>
        <Stat value={safe} size='kpi' />
        <Button
          variant='outline'
          size='icon'
          aria-label={`More: ${label}`}
          disabled={safe >= max}
          disabledReason={`At most ${max}`}
          onClick={() => onChange(Math.min(max, safe + 1))}
        >
          <Plus />
        </Button>
      </div>
    </div>
  )
}
