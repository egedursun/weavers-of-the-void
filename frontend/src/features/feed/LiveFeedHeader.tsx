import { type ReactNode } from 'react'
import { useRealtimeStatus } from '@/realtime'
import { Activity, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { StatusDot } from '@/components/layout/RealtimeIndicator'
import {
  STATUS_SHORT,
  STATUS_TEXT_CLASS,
} from '@/components/layout/realtimeStatus'
import { Muted, Text } from '@/components/typography'
import { useFeed } from './feedStore'

type LiveFeedHeaderProps = {
  title?: ReactNode
  description?: ReactNode
  onClose?: () => void
}

export function LiveFeedHeader({
  title,
  description,
  onClose,
}: LiveFeedHeaderProps) {
  const status = useRealtimeStatus()
  const total = useFeed((state) => state.lines.length)
  return (
    <div
      data-feature='live-feed-header'
      className='flex min-w-0 items-center gap-3'
    >
      <Medallion icon={Activity} />
      <div className='flex min-w-0 flex-1 flex-col'>
        <div className='flex min-w-0 items-center gap-2'>
          {title ?? (
            <Text as='span' weight='semibold' truncate>
              Live feed
            </Text>
          )}
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5',
              STATUS_TEXT_CLASS[status]
            )}
          >
            <StatusDot status={status} />
            <Text as='span' variant='caption' tone='inherit' weight='medium'>
              {STATUS_SHORT[status]}
            </Text>
          </span>
        </div>
        {description ?? (
          <Muted as='span' variant='caption' truncate>
            {total === 0
              ? 'Waiting for the world to stir'
              : `${total} ${total === 1 ? 'event' : 'events'} this session`}
          </Muted>
        )}
      </div>
      {onClose && (
        <Button
          variant='ghost'
          size='icon'
          aria-label='Hide the live feed'
          onClick={onClose}
        >
          <X />
        </Button>
      )}
    </div>
  )
}
