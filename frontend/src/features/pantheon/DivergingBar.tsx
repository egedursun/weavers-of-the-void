import { Progress } from '@/components/ui/progress'
import { RELATION_SCALE } from './constants'

type DivergingBarProps = {
  value: number
  label: string
  scale?: number
}

const PERCENT = 100

export function DivergingBar({
  value,
  label,
  scale = RELATION_SCALE,
}: DivergingBarProps) {
  const magnitude = Math.min(PERCENT, (Math.abs(value) / scale) * PERCENT)
  return (
    <div
      role='meter'
      aria-label={label}
      aria-valuemin={-scale}
      aria-valuemax={scale}
      aria-valuenow={value}
      className='grid min-w-0 grid-cols-2 gap-0.5'
    >
      <Progress
        size='sm'
        tone='destructive'
        value={value < 0 ? magnitude : 0}
        className='rotate-180'
        aria-hidden='true'
      />
      <Progress
        size='sm'
        tone='success'
        value={value > 0 ? magnitude : 0}
        aria-hidden='true'
      />
    </div>
  )
}
