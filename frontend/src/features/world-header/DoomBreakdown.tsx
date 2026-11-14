import { formatNumber } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Label, Muted, Text } from '@/components/typography'
import { useDoomForecast } from './api'

const PERCENT = 100

function signed(value: number): string {
  const shown = formatNumber(Math.abs(value), 'decimal')
  return value > 0 ? `+${shown}` : value < 0 ? `−${shown}` : '0'
}

function sentence(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1)
}

type Part = { key: string; label: string; value: number }

function PartRow({ part, scale }: { part: Part; scale: number }) {
  const share = scale > 0 ? (Math.abs(part.value) / scale) * PERCENT : 0
  const pushes = part.value > 0
  const holds = part.value < 0
  return (
    <li className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-baseline justify-between gap-2'>
        <Text
          as='span'
          variant='caption'
          truncate
          tone={part.value === 0 ? 'muted' : 'default'}
        >
          {sentence(part.label)}
        </Text>
        <Text
          as='span'
          variant='caption'
          weight='semibold'
          tone={pushes ? 'destructive' : holds ? 'success' : 'muted'}
        >
          {signed(part.value)}
        </Text>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-1'>
        <Progress
          size='sm'
          tone='success'
          className='-scale-x-100'
          value={holds ? share : 0}
          aria-label={`${part.label} holds the clock back`}
        />
        <Progress
          size='sm'
          tone='destructive'
          value={pushes ? share : 0}
          aria-label={`${part.label} pushes the clock`}
        />
      </div>
    </li>
  )
}

export function DoomBreakdown({ open }: { open: boolean }) {
  const forecast = useDoomForecast(open)
  if (forecast.isPending) return <Skeleton className='h-textarea w-full' />
  if (forecast.isError)
    return <Text tone='destructive'>{forecast.error.message}</Text>
  const data = forecast.data
  const parts = [...data.parts].sort((left, right) => right.value - left.value)
  const scale = Math.max(0, ...parts.map((part) => Math.abs(part.value)))
  const push = parts
    .filter((part) => part.value > 0)
    .reduce((sum, part) => sum + part.value, 0)
  const hold = parts
    .filter((part) => part.value < 0)
    .reduce((sum, part) => sum + part.value, 0)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Label variant='overline'>Next epoch, every force</Label>
        <Muted as='span' variant='caption'>
          {`${plural(parts.length, 'part', 'parts')}`}
        </Muted>
      </div>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Text as='span' variant='caption' tone='success'>
          Holds it back
        </Text>
        <Text as='span' variant='caption' tone='destructive'>
          Pushes it on
        </Text>
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {parts.map((part) => (
          <PartRow key={part.key} part={part} scale={scale} />
        ))}
      </ul>
      <div
        className={cn(
          'flex min-w-0 flex-col gap-1 rounded-lg border p-2',
          data.step > 0 ? 'border-destructive/40' : 'border-success/40'
        )}
      >
        <div className='flex min-w-0 justify-between gap-2'>
          <Muted as='span' variant='caption'>
            Pushing
          </Muted>
          <Text as='span' variant='caption' tone='destructive'>
            {signed(push)}
          </Text>
        </div>
        <div className='flex min-w-0 justify-between gap-2'>
          <Muted as='span' variant='caption'>
            Holding back
          </Muted>
          <Text as='span' variant='caption' tone='success'>
            {signed(hold)}
          </Text>
        </div>
        <div className='flex min-w-0 justify-between gap-2'>
          <Muted as='span' variant='caption'>
            Sum before speed
          </Muted>
          <Text as='span' variant='caption' weight='medium'>
            {signed(data.raw)}
          </Text>
        </div>
        <div className='flex min-w-0 justify-between gap-2'>
          <Muted as='span' variant='caption'>
            Apocalypse speed (world rule)
          </Muted>
          <Text as='span' variant='caption' weight='medium'>
            {`${data.speed_pct}%`}
          </Text>
        </div>
        <div className='flex min-w-0 justify-between gap-2'>
          <Text as='span' variant='caption' weight='semibold'>
            Clock moves per epoch
          </Text>
          <Text
            as='span'
            variant='caption'
            weight='semibold'
            tone={data.step > 0 ? 'destructive' : 'success'}
          >
            {signed(data.step)}
          </Text>
        </div>
        <Muted variant='caption'>
          {data.epochs_left !== null
            ? `At this pace the threshold is about ${formatNumber(Math.ceil(data.epochs_left), 'integer')} epochs away.`
            : 'At this pace the clock does not move toward the threshold.'}
        </Muted>
      </div>
    </div>
  )
}
