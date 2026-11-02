import { useState } from 'react'
import { Hourglass } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Progress } from '@/components/ui/progress'
import { RuleInfo } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type WorldState } from '@/features/pantheon/api'
import { useRuleLookup } from '@/features/pantheon/gate'
import { DoomBreakdown } from './DoomBreakdown'
import { HudChip } from './HudChip'
import { bandRange, currentBand, doomBands } from './doomBands'

const PERCENT = 100

const CHIP_TONE = {
  success: 'success',
  secondary: 'info',
  warning: 'warning',
  destructive: 'danger',
} as const

const BAR_TONE = {
  success: 'success',
  secondary: 'default',
  warning: 'warning',
  destructive: 'destructive',
} as const

export function DoomChip({ state }: { state: WorldState }) {
  const [open, setOpen] = useState(false)
  const rule = useRuleLookup()
  const world = state.world
  const value = world?.doom_clock ?? 0
  const threshold = rule('balance.apocalypse_threshold')
  const first = rule('apocalypse.warning_1_pct')
  const second = rule('apocalypse.warning_2_pct')
  const known =
    threshold !== undefined && first !== undefined && second !== undefined
  const bands = known
    ? doomBands({ threshold, firstPct: first, secondPct: second })
    : []
  const band = known ? currentBand(bands, value) : null
  const items = [...(state.pulse?.doom_items ?? [])].sort(
    (left, right) => Math.abs(right.delta) - Math.abs(left.delta)
  )
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <HudChip
          icon={Hourglass}
          tone={band ? CHIP_TONE[band.tone] : 'muted'}
          label='Doom'
          aria-label={`Doom clock ${value}, open details`}
          data-doom-chip
        >
          <Stat value={value} />
          {threshold !== undefined && (
            <span className='hidden w-10 sm:block'>
              <Progress
                size='sm'
                tone={band ? BAR_TONE[band.tone] : 'muted'}
                value={Math.min((value / threshold) * PERCENT, PERCENT)}
                aria-hidden='true'
              />
            </span>
          )}
          {band && band.key !== 'calm' && (
            <Badge size='sm' variant={band.tone}>
              {band.label}
            </Badge>
          )}
        </HudChip>
      </PopoverTrigger>
      <PopoverContent
        align='end'
        className='flex max-h-160 w-96 min-w-0 flex-col gap-3 overflow-y-auto'
      >
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label variant='overline'>Doom clock</Label>
          <Stat
            value={value}
            size='kpi'
            unit={threshold === undefined ? undefined : `of ${threshold}`}
          />
        </div>
        {band && threshold !== undefined && (
          <Progress
            size='sm'
            tone={BAR_TONE[band.tone]}
            value={Math.min((value / threshold) * PERCENT, PERCENT)}
            aria-label='Doom clock progress'
          />
        )}
        <Muted variant='caption'>
          {`The clock runs on ${world?.name ?? 'the primary world'}. When it reaches the threshold the apocalypse begins.`}
        </Muted>
        <div className='flex min-w-0 flex-col gap-1'>
          {bands.map((entry) => (
            <div
              key={entry.key}
              className='flex min-w-0 items-center justify-between gap-2'
            >
              <Badge variant={entry.key === band?.key ? entry.tone : 'outline'}>
                {entry.label}
              </Badge>
              <Text
                as='span'
                tone={entry.key === band?.key ? 'default' : 'muted'}
              >
                {bandRange(entry)}
              </Text>
              <RuleInfo
                rule={entry.rule}
                label={`The ${entry.label.toLowerCase()} point`}
              />
            </div>
          ))}
        </div>
        <DoomBreakdown open={open} />
        {items.length > 0 && (
          <div className='flex min-w-0 flex-col gap-1 border-t pt-3'>
            <Label variant='overline'>{`Last epoch · ${items.length} parts`}</Label>
            {items.map((item) => (
              <div
                key={item.item}
                className='flex min-w-0 items-baseline justify-between gap-2'
              >
                <Text as='span' variant='caption' truncate>
                  {item.item}
                </Text>
                <Text
                  as='span'
                  variant='caption'
                  tone={
                    item.delta > 0
                      ? 'destructive'
                      : item.delta < 0
                        ? 'success'
                        : 'muted'
                  }
                >
                  {item.delta > 0 ? `+${item.delta}` : String(item.delta)}
                </Text>
              </div>
            ))}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
