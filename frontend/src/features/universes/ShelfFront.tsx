import { Clock, LoaderCircle, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { UniverseCrest } from './UniverseCrest'
import { type UniverseSummary } from './types'
import { ageLine, frontRow, openedSince, timeLine } from './universeModel'

const FRONT_SHOWN = 6

function FrontBook({
  universe,
  opening,
  onOpen,
}: {
  universe: UniverseSummary
  opening: boolean
  onOpen: () => void
}) {
  return (
    <li className='flex min-w-0'>
      <Button
        type='button'
        variant='outline'
        size='card'
        aria-label={`Open ${universe.name}`}
        disabled={opening}
        disabledReason='The universe is being opened.'
        onClick={onOpen}
        className={cn(
          'group items-center text-center',
          universe.pinned && 'border-primary/70'
        )}
      >
        <span className='relative flex items-center justify-center transition-transform duration-200 group-hover:scale-105 motion-reduce:transition-none'>
          <UniverseCrest name={universe.name} size='md' />
          {opening && (
            <LoaderCircle
              aria-hidden='true'
              className='absolute size-icon-lg animate-spin text-primary motion-reduce:animate-none'
            />
          )}
        </span>
        <span className='flex min-h-portrait-lg w-full items-center justify-center'>
          <Text
            as='span'
            weight='semibold'
            truncate={2}
            className='w-full font-display'
          >
            {universe.name}
          </Text>
        </span>
        <Muted as='span' variant='caption' truncate className='w-full'>
          {timeLine(universe)}
        </Muted>
        <span className='mt-auto flex w-full justify-center pt-1'>
          {universe.pinned ? (
            <Badge variant='default' size='sm'>
              <Star className='fill-primary' />
              Pinned
            </Badge>
          ) : (
            <Badge variant='secondary' size='sm' title={ageLine(universe)}>
              <Clock />
              {openedSince(universe)}
            </Badge>
          )}
        </span>
      </Button>
    </li>
  )
}

export function ShelfFront({
  shelf,
  opening,
  onOpen,
}: {
  shelf: UniverseSummary[]
  opening: string | null
  onOpen: (universe: UniverseSummary) => void
}) {
  const front = frontRow(shelf)
  if (front.length === 0)
    return (
      <EmptyState
        size='inline'
        icon={Star}
        title='No favourites yet'
        description='Pin a universe with its star, or open one, and it waits here at the front of the hall.'
      />
    )
  return (
    <ul
      aria-label='Pinned and recent universes'
      className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6'
    >
      <Paged
        items={front}
        initial={FRONT_SHOWN}
        as='li'
        noun={['universe', 'universes']}
      >
        {(universe) => (
          <FrontBook
            key={universe.id}
            universe={universe}
            opening={opening === universe.id}
            onOpen={() => onOpen(universe)}
          />
        )}
      </Paged>
    </ul>
  )
}
