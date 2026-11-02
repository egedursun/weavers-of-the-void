import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type KpiTone, Medallion } from './KpiTile'

const PERCENT = 100

const ICON_TONE: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

type IconStatProps = {
  icon: LucideIcon
  label: string
  value: number | string
  tone?: KpiTone
  hint?: string
}

export function IconStat({
  icon: Icon,
  label,
  value,
  tone = 'muted',
  hint,
}: IconStatProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          data-domain='icon-stat'
          tabIndex={0}
          aria-label={`${label} ${value}`}
          className='inline-flex h-badge-md min-w-0 shrink-0 items-center gap-1.5 rounded-md border bg-muted/40 px-2'
        >
          <Icon
            aria-hidden='true'
            className={cn('size-icon-xs shrink-0', ICON_TONE[tone])}
          />
          <Stat value={value} />
        </span>
      </TooltipTrigger>
      <TooltipContent className='flex flex-col gap-0.5'>
        <Text as='span' weight='medium'>
          {label}
        </Text>
        {hint && <Muted variant='caption'>{hint}</Muted>}
      </TooltipContent>
    </Tooltip>
  )
}

type AttributeTileProps = {
  icon: LucideIcon
  abbr: string
  label: string
  value: number
  max: number
  hint?: string
  tone?: ProgressTone
}

export function AttributeTile({
  icon: Icon,
  abbr,
  label,
  value,
  max,
  hint,
  tone = 'default',
}: AttributeTileProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          data-domain='attribute-tile'
          tabIndex={0}
          aria-label={`${label} ${value}`}
          className='flex min-w-0 flex-col gap-1.5 rounded-md border bg-muted/30 px-2 py-1.5'
        >
          <div className='flex min-w-0 items-center gap-1.5'>
            <Icon
              aria-hidden='true'
              className='size-icon-xs shrink-0 text-muted-foreground'
            />
            <Label className='flex-1'>{abbr}</Label>
            <Stat value={value} />
          </div>
          <Progress
            value={max > 0 ? Math.min(PERCENT, (value / max) * PERCENT) : 0}
            size='sm'
            tone={tone}
            aria-label={label}
          />
        </div>
      </TooltipTrigger>
      <TooltipContent className='flex flex-col gap-0.5'>
        <Text as='span' weight='medium'>
          {`${label} · ${value}`}
        </Text>
        {hint && <Muted variant='caption'>{hint}</Muted>}
      </TooltipContent>
    </Tooltip>
  )
}

type LevelMeterProps = {
  level: number
  xp: number
  needed: number | null
}

export function LevelMeter({ level, xp, needed }: LevelMeterProps) {
  return (
    <div
      data-domain='level-meter'
      className='flex w-full min-w-0 items-center gap-2'
    >
      <span className='flex size-control-sm shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/12 text-primary'>
        <Stat value={level} />
      </span>
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label truncate>{`Level ${level}`}</Label>
          <Stat value={xp} unit={needed !== null ? `/ ${needed} XP` : 'XP'} />
        </div>
        <Progress
          value={
            needed !== null && needed > 0
              ? Math.min(PERCENT, (xp / needed) * PERCENT)
              : PERCENT
          }
          size='sm'
          aria-label={`Experience toward level ${level + 1}`}
        />
      </div>
    </div>
  )
}

type MiniStatProps = {
  icon: LucideIcon
  label: string
  value: number | string
  tone?: KpiTone
  hint?: string
}

export function MiniStat({
  icon,
  label,
  value,
  tone = 'muted',
  hint,
}: MiniStatProps) {
  const body = (
    <div
      data-domain='mini-stat'
      tabIndex={hint ? 0 : undefined}
      className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-background p-2'
    >
      <Medallion icon={icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Stat
          value={value}
          title={String(value)}
          className='block min-w-0 truncate'
        />
        <Label truncate>{label}</Label>
      </div>
    </div>
  )
  if (!hint) return body
  return (
    <Tooltip>
      <TooltipTrigger asChild>{body}</TooltipTrigger>
      <TooltipContent>{hint}</TooltipContent>
    </Tooltip>
  )
}
