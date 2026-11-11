import { Activity, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Muted, Stat, Text } from '@/components/typography'
import { useFeedDock } from '@/features/feed/useFeedDock'
import { useSteadyPresence } from './steadyPresence'
import { useProgressSummary } from './useProgressSummary'

const PERCENT = 100

export function ActivityStrip() {
  const live = useProgressSummary()
  const { setOpen } = useFeedDock()
  const { shown, value: summary } = useSteadyPresence(live.visible, live)
  if (!shown) return null
  const detail = [...summary.parts, summary.subtitle]
    .filter(Boolean)
    .join(' · ')
  const text = [summary.title, detail].filter(Boolean).join(' · ')
  return (
    <div
      data-layout='activity-strip'
      role='status'
      className='relative flex min-w-0 items-center gap-3 border-b bg-primary/6 px-3 py-1.5 md:px-4'
    >
      <LoaderCircle
        aria-hidden='true'
        className='size-icon-sm shrink-0 animate-spin text-primary motion-reduce:animate-none'
      />
      <Text as='span' weight='semibold' className='shrink-0'>
        {summary.title}
      </Text>
      <Muted as='span' variant='caption' truncate className='flex-1'>
        {detail}
      </Muted>
      {summary.ratio !== null && (
        <Stat value={summary.ratio} format='percent' tone='primary' />
      )}
      <Button
        variant='ghost'
        size='sm'
        onClick={() => setOpen(true)}
        aria-label={`Open the live feed: ${text}`}
      >
        <Activity />
        <span className='hidden sm:inline'>Live feed</span>
      </Button>
      <div className='absolute inset-x-0 bottom-0'>
        <Progress
          size='sm'
          value={(summary.ratio ?? 0) * PERCENT}
          indeterminate={summary.ratio === null}
          aria-label={summary.title}
        />
      </div>
    </div>
  )
}
