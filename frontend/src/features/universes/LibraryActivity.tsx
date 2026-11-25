import { History } from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ServerShowMore } from './ServerShowMore'
import { useLibraryEvents } from './api'
import { EVENT_LOOK } from './universeLook'

export function LibraryActivity() {
  const events = useLibraryEvents()
  const pages = events.data?.pages ?? []
  const shown = pages.flatMap((page) => page.items)
  const total = pages[0]?.total ?? 0
  if (events.isPending) return <LoadingBlock label='Reading the library log' />
  if (events.isError)
    return (
      <EmptyState
        size='compact'
        icon={History}
        title='The log could not be read'
        description={events.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void events.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  if (shown.length === 0)
    return (
      <EmptyState
        size='compact'
        icon={History}
        title='Nothing has happened yet'
        description='Every act on the library, from creating to purging, is kept here.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ol aria-label='Library log' className='flex min-w-0 flex-col gap-1.5'>
        {shown.map((event) => {
          const look = EVENT_LOOK[event.kind]
          return (
            <li
              key={event.id}
              className='flex min-w-0 items-start gap-2.5 rounded-md surface-sheen p-2'
            >
              <Medallion icon={look.icon} tone={look.tone} size='sm' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' variant='caption' weight='semibold' truncate>
                  {`${look.label} · ${event.universe_name}`}
                </Text>
                {event.detail && (
                  <Muted as='span' variant='caption' truncate={2}>
                    {event.detail}
                  </Muted>
                )}
                <Muted as='span' variant='caption'>
                  {event.account_name
                    ? `${formatDateTime(event.at)} · by ${event.account_name}`
                    : formatDateTime(event.at)}
                </Muted>
              </div>
            </li>
          )
        })}
      </ol>
      <ServerShowMore
        shown={shown.length}
        total={total}
        more={events.hasNextPage}
        loading={events.isFetchingNextPage}
        onMore={() => void events.fetchNextPage()}
      />
    </div>
  )
}
