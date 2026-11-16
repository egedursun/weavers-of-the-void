import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { Muted, Stat, Text } from '@/components/typography'
import { useProgressSummary } from './useProgressSummary'

const PERCENT = 100

type EpochProgressProps = {
  framed?: boolean
}

export function EpochProgress({ framed = false }: EpochProgressProps) {
  const summary = useProgressSummary()
  if (!summary.visible) return null
  return (
    <div
      data-feature='epoch-progress'
      className={cn(
        'flex min-w-0 flex-col gap-2',
        framed &&
          'rounded-md border surface-framed border-gild/70 bg-card p-5 text-card-foreground'
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Text as='span' weight='medium' truncate className='flex-1'>
          {summary.title}
        </Text>
        {summary.ratio !== null && (
          <Stat value={summary.ratio} format='percent' />
        )}
      </div>
      <Progress
        value={(summary.ratio ?? 0) * PERCENT}
        indeterminate={summary.ratio === null}
        aria-label={summary.title}
      />
      {summary.parts.length > 0 && (
        <Muted variant='caption' truncate>
          {summary.parts.join(' · ')}
        </Muted>
      )}
      {summary.subtitle && (
        <Muted variant='caption' truncate={2}>
          {summary.subtitle}
        </Muted>
      )}
    </div>
  )
}
