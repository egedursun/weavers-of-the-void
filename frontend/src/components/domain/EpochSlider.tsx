import { type ReactNode, useId } from 'react'
import { cn } from '@/lib/utils'
import { Label, Stat } from '@/components/typography'

type EpochSliderProps = {
  value: number
  max: number
  min?: number
  label: string
  onChange: (value: number) => void
  disabled?: boolean
  actions?: ReactNode
  valueLabel?: ReactNode
}

export function EpochSlider({
  value,
  max,
  min = 1,
  label,
  onChange,
  disabled = false,
  actions,
  valueLabel,
}: EpochSliderProps) {
  const id = useId()
  const span = Math.max(1, max - min)
  const filled = ((Math.min(max, Math.max(min, value)) - min) / span) * 100
  return (
    <div
      data-domain='epoch-slider'
      className='flex w-full min-w-0 items-center gap-3'
    >
      <Label as='label' htmlFor={id} className='shrink-0'>
        {label}
      </Label>
      <input
        id={id}
        type='range'
        min={min}
        max={Math.max(min, max)}
        step={1}
        value={value}
        disabled={disabled || max <= min}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{
          background: `linear-gradient(to right, var(--primary) ${filled}%, var(--muted) ${filled}%)`,
        }}
        className={cn(
          'h-meter-md min-w-0 flex-1 cursor-pointer appearance-none rounded-full accent-primary outline-none',
          'focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50',
          '[&::-webkit-slider-thumb]:size-icon-md [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary [&::-webkit-slider-thumb]:bg-background',
          '[&::-moz-range-thumb]:size-icon-md [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:bg-background'
        )}
      />
      <span className='shrink-0'>{valueLabel ?? <Stat value={value} />}</span>
      {actions}
    </div>
  )
}
