import { type HTMLAttributes, type ReactNode } from 'react'
import { type NumberFormat, formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
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
  return (
    <data
      value={String(value)}
      data-typography={size === 'kpi' ? 'stat-kpi' : 'stat'}
      className={cn(
        'inline-flex min-w-0 items-baseline gap-1 whitespace-nowrap tabular-nums',
        size === 'kpi' ? 'text-kpi font-semibold' : 'font-medium',
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
