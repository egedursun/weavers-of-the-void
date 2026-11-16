import { type ReactNode } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  type LucideIcon,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { GEM_CLASS, type GemTone, OrnateFrame } from '@/components/ui/ornate'
import { Progress } from '@/components/ui/progress'
import { Label, Muted, Stat } from '@/components/typography'

export type KpiTone = GemTone

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
        'medallion',
        size === 'md' ? 'size-control-lg' : 'size-control-sm',
        GEM_CLASS[tone]
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
    <OrnateFrame
      data-domain='kpi-tile'
      frame='tile'
      crest
      tone={tone}
      className='@container/kpi flex min-w-0 flex-col gap-3 p-4'
    >
      <div className='flex min-w-0 flex-col items-start gap-2 @tile/kpi:flex-row @tile/kpi:items-center @tile/kpi:gap-3'>
        <Medallion icon={icon} tone={tone} />
        <Label variant='gilded' className='min-w-0 flex-1 break-normal'>
          {label}
        </Label>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Stat
          value={value}
          size='kpi'
          tone={valueTone}
          className={cn(
            'font-display',
            valueTone === 'default' && 'text-gilded'
          )}
        />
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
    </OrnateFrame>
  )
}
