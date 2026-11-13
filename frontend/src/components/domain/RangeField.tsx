import { useId } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted, Stat, Text } from '@/components/typography'

type RangeFieldProps = {
  label: string
  icon: LucideIcon
  value: number
  min: number
  max: number
  level: string
  hint?: string
  lowLabel: string
  highLabel: string
  onChange: (value: number) => void
  disabledReason?: string | null
}

export function RangeField({
  label,
  icon: Icon,
  value,
  min,
  max,
  level,
  hint,
  lowLabel,
  highLabel,
  onChange,
  disabledReason = null,
}: RangeFieldProps) {
  const id = useId()
  const reasonId = useId()
  const disabled = disabledReason !== null
  const span = Math.max(1, max - min)
  const safe = Number.isFinite(value) ? value : min
  const filled = disabled
    ? 0
    : ((Math.min(max, Math.max(min, safe)) - min) / span) * 100
  return (
    <div
      data-domain='range-field'
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3',
        disabled && 'bg-muted/40'
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <span className='flex size-control-sm shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/12 text-primary'>
          <Icon aria-hidden='true' className='size-icon-sm' />
        </span>
        <div className='flex min-w-0 flex-1 flex-col'>
          <FieldLabel htmlFor={id}>{label}</FieldLabel>
          {hint && (
            <Muted as='span' variant='caption' truncate>
              {hint}
            </Muted>
          )}
        </div>
        <div className='flex shrink-0 flex-col items-end'>
          {disabled ? (
            <Text as='span' weight='semibold' tone='muted'>
              —
            </Text>
          ) : (
            <Stat value={safe} size='kpi' />
          )}
          <Text as='span' variant='caption' tone='primary' weight='medium'>
            {level}
          </Text>
        </div>
      </div>
      <input
        id={id}
        type='range'
        min={min}
        max={max}
        step={1}
        value={safe}
        disabled={disabled}
        aria-describedby={disabled ? reasonId : undefined}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{
          background: `linear-gradient(to right, var(--primary) ${filled}%, var(--muted) ${filled}%)`,
        }}
        className={cn(
          'h-meter-md w-full min-w-0 cursor-pointer appearance-none rounded-full accent-primary outline-none',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'focus-visible:ring-[3px] focus-visible:ring-ring/50',
          '[&::-webkit-slider-thumb]:size-icon-lg [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary [&::-webkit-slider-thumb]:bg-background [&::-webkit-slider-thumb]:shadow-md',
          '[&::-moz-range-thumb]:size-icon-lg [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:bg-background'
        )}
      />
      <div className='flex min-w-0 justify-between gap-2'>
        <Muted as='span' variant='caption'>
          {lowLabel}
        </Muted>
        <Muted as='span' variant='caption'>
          {highLabel}
        </Muted>
      </div>
      {disabled && (
        <Muted id={reasonId} variant='caption'>
          {disabledReason}
        </Muted>
      )}
    </div>
  )
}
