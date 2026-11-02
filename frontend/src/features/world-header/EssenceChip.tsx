import { Sparkles } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { RuleInfo } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type WorldState } from '@/features/pantheon/api'
import { HudChip } from './HudChip'

function signed(value: number): string {
  if (value > 0) return `+${formatInteger(value)}`
  if (value < 0) return `−${formatInteger(Math.abs(value))}`
  return '±0'
}

export function EssenceChip({ state }: { state: WorldState }) {
  const essence = state.creator?.essence ?? 0
  const items = [...(state.pulse?.essence_items ?? [])].sort(
    (left, right) => Math.abs(right.delta) - Math.abs(left.delta)
  )
  const net = items.reduce((sum, item) => sum + item.delta, 0)
  return (
    <Popover>
      <PopoverTrigger asChild>
        <HudChip
          icon={Sparkles}
          tone='gold'
          label='Essence'
          aria-label={`Divine essence ${essence}, open breakdown`}
          data-essence-chip
        >
          <Stat value={essence} />
          {items.length > 0 && net !== 0 && (
            <Text
              as='span'
              variant='caption'
              tone={net > 0 ? 'success' : 'destructive'}
              className='hidden sm:inline'
            >
              {signed(net)}
            </Text>
          )}
        </HudChip>
      </PopoverTrigger>
      <PopoverContent align='end' className='flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label variant='overline'>Divine essence</Label>
          <Stat value={essence} size='kpi' />
        </div>
        <Muted variant='caption'>
          Essence refills every epoch and pays for your acts: summoning,
          revelations, blessings and commands.
        </Muted>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>This epoch</Label>
          {items.length === 0 ? (
            <Muted>No essence has moved yet.</Muted>
          ) : (
            items.map((item) => (
              <div
                key={item.item}
                className='flex min-w-0 items-baseline justify-between gap-2'
              >
                <Text as='span' truncate>
                  {item.item}
                </Text>
                <Text
                  as='span'
                  tone={item.delta >= 0 ? 'success' : 'destructive'}
                >
                  {signed(item.delta)}
                </Text>
              </div>
            ))
          )}
          {items.length > 0 && (
            <div className='flex min-w-0 items-baseline justify-between gap-2'>
              <Text as='span' weight='medium'>
                Net
              </Text>
              <Text as='span' weight='medium'>
                {signed(net)}
              </Text>
            </div>
          )}
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-1'>
          <Muted variant='caption'>Costs set by</Muted>
          <RuleInfo rule='costs.summon_son' label='The summon cost' />
          <RuleInfo rule='costs.revelation' label='The revelation cost' />
        </div>
      </PopoverContent>
    </Popover>
  )
}
