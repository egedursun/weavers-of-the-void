import { type LucideIcon } from 'lucide-react'
import { type NumberFormat, formatInteger } from '@/lib/format'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import { Label, Stat } from '@/components/typography'

const PERCENT = 100

type StatBarProps = {
  label: string
  value: number
  max: number
  icon?: LucideIcon
  tone?: ProgressTone
  format?: NumberFormat
  showMax?: boolean
}

export function StatBar({
  label,
  value,
  max,
  icon: Icon,
  tone = 'default',
  format = 'integer',
  showMax = true,
}: StatBarProps) {
  const percent = max > 0 ? (value / max) * PERCENT : 0
  return (
    <div data-domain='stat-bar' className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 items-center gap-2'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-muted-foreground'
          />
        )}
        <Label truncate className='flex-1'>
          {label}
        </Label>
        <Stat
          value={value}
          format={format}
          unit={
            showMax
              ? `/ ${format === 'integer' ? formatInteger(max) : max}`
              : undefined
          }
        />
      </div>
      <Progress value={percent} size='sm' tone={tone} aria-label={label} />
    </div>
  )
}
