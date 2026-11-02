import { type ReactNode } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  type LucideIcon,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { Label, Muted, Stat } from '@/components/typography'

export type KpiTone =
  'gold' | 'verdigris' | 'info' | 'success' | 'warning' | 'danger' | 'muted'

const MEDALLION: Record<KpiTone, string> = {
  gold: 'border-primary/30 bg-primary/12 text-primary',
  verdigris:
    'border-brand-verdigris/30 bg-brand-verdigris/12 text-brand-verdigris',
  info: 'border-info/30 bg-info/12 text-info',
  success: 'border-success/30 bg-success/12 text-success',
  warning: 'border-warning/30 bg-warning/12 text-warning',
  danger: 'border-destructive/30 bg-destructive/12 text-destructive',
  muted: 'border-border bg-muted text-muted-foreground',
}

const ACCENT: Record<KpiTone, string> = {
  gold: 'before:bg-primary',
  verdigris: 'before:bg-brand-verdigris',
  info: 'before:bg-info',
  success: 'before:bg-success',
  warning: 'before:bg-warning',
  danger: 'before:bg-destructive',
  muted: 'before:bg-border',
}

const METER_TONE = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
} as const

const PERCENT = 100

type MedallionProps = {
  icon: LucideIcon
  tone?: KpiTone
  size?: 'sm' | 'md'
}

export function Medallion({
  icon: Icon,
  tone = 'gold',
  size = 'md',
}: MedallionProps) {
  return (
    <span
      data-domain='medallion'
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full border',
        size === 'md' ? 'size-control-lg' : 'size-control-sm',
        MEDALLION[tone]
      )}
    >
      <Icon
        aria-hidden='true'
        className={size === 'md' ? 'size-icon-lg' : 'size-icon-sm'}
      />
    </span>
  )
}

type ChangeChipProps = {
  value: number
  harmful?: boolean
  label?: string
  icon?: LucideIcon
}

export function ChangeChip({
  value,
  harmful = false,
  label,
  icon,
}: ChangeChipProps) {
  const good = value === 0 ? null : value > 0 !== harmful
  const Icon = value > 0 ? ArrowUpRight : value < 0 ? ArrowDownRight : Minus
  const Lead = icon
  return (
    <span
      data-domain='change-chip'
      data-change={value > 0 ? 'up' : value < 0 ? 'down' : 'flat'}
      className={cn(
        'inline-flex h-badge-md shrink-0 items-center gap-1 rounded-md border px-1.5 text-caption font-medium tabular-nums',
        good === null && 'border-border bg-muted text-muted-foreground',
        good === true && 'border-success/30 bg-success/12 text-success',
        good === false &&
          'border-destructive/30 bg-destructive/12 text-destructive'
      )}
    >
      {Lead && <Lead aria-hidden='true' className='size-icon-xs' />}
      {label ? `${label} ` : ''}
      <Icon aria-hidden='true' className='size-icon-xs' />
      {value === 0 ? '0' : formatInteger(Math.abs(value))}
    </span>
  )
}

type KpiTileProps = {
  label: string
  value: number | string
  icon: LucideIcon
  tone?: KpiTone
  hint?: ReactNode
  change?: number
  harmful?: boolean
  meter?: { value: number; max: number; label: string }
  valueTone?: 'default' | 'warning' | 'destructive'
}

export function KpiTile({
  label,
  value,
  icon,
  tone = 'gold',
  hint,
  change,
  harmful,
  meter,
  valueTone = 'default',
}: KpiTileProps) {
  return (
    <div
      data-domain='kpi-tile'
      className={cn(
        'relative flex min-w-0 flex-col gap-3 overflow-hidden rounded-xl border bg-background p-4 before:absolute before:inset-x-0 before:top-0 before:h-0.5',
        ACCENT[tone]
      )}
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={icon} tone={tone} />
        <Label className='min-w-0 flex-1'>{label}</Label>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Stat value={value} size='kpi' tone={valueTone} />
        {change !== undefined && (
          <ChangeChip value={change} harmful={harmful} />
        )}
      </div>
      {meter && (
        <Progress
          size='sm'
          tone={METER_TONE[tone]}
          value={Math.min(
            PERCENT,
            (meter.value / Math.max(1, meter.max)) * PERCENT
          )}
          aria-label={meter.label}
        />
      )}
      {hint && (
        <Muted variant='caption' truncate={2}>
          {hint}
        </Muted>
      )}
    </div>
  )
}
