import { type HTMLAttributes, type ReactNode } from 'react'
import { type NumberFormat, formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useFitText } from '@/hooks/useFitText'
import { type TextTone, toneClass } from './textStyles'

type StatProps = Omit<HTMLAttributes<HTMLElement>, 'children'> & {
  value: number | string
  format?: NumberFormat
  size?: 'inline' | 'kpi'
  tone?: TextTone
  unit?: ReactNode
}

export function Stat({
  value,
  format = 'integer',
  size = 'inline',
  tone = 'inherit',
  unit,
  className,
  ...props
}: StatProps) {
  const shown = typeof value === 'number' ? formatNumber(value, format) : value
  const fitted = useFitText<HTMLDataElement>(shown)
  return (
    <data
      ref={fitted}
      value={String(value)}
      title={typeof shown === 'string' ? shown : undefined}
      data-typography={size === 'kpi' ? 'stat-kpi' : 'stat'}
      className={cn(
        'inline-flex min-w-0 items-baseline gap-1 whitespace-nowrap tabular-nums',
        size === 'kpi'
          ? 'max-w-full overflow-hidden text-kpi font-semibold data-[fit=1]:text-title data-[fit=2]:text-prose data-[fit=3]:text-body data-[fit=3]:break-words data-[fit=3]:whitespace-normal'
          : 'max-w-full font-medium data-[fit=1]:break-words data-[fit=1]:whitespace-normal data-[fit=2]:break-words data-[fit=2]:whitespace-normal data-[fit=3]:break-words data-[fit=3]:whitespace-normal',
        toneClass[tone],
        className
      )}
      {...props}
    >
      {shown}
      {unit !== undefined && (
        <span className='text-caption font-normal text-muted-foreground'>
          {unit}
        </span>
      )}
    </data>
  )
}
