import { Link, useNavigate } from '@tanstack/react-router'
import { BookOpen, Check, ChevronsUpDown, LibraryBig } from 'lucide-react'
import { useUniverseId } from '@/api/universeStore'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Muted, Text } from '@/components/typography'
import { UniverseCrest } from './UniverseCrest'
import { useShelf, useUniverse } from './api'
import { ageLine, timeLine } from './universeModel'
import { useEnterUniverse } from './useEnterUniverse'

const RECENT_SHOWN = 6
const UNNAMED = 'This universe'

export function UniverseSwitcher({ compact = false }: { compact?: boolean }) {
  const universeId = useUniverseId()
  const shelf = useShelf()
  const detail = useUniverse(universeId)
  const navigate = useNavigate()
  const { enter, opening } = useEnterUniverse()
  const shelfItems = shelf.data?.items ?? []
  const here = shelfItems.find((item) => item.id === universeId)
  const name = detail.data?.name ?? here?.name ?? UNNAMED
  const recent = shelfItems
    .filter((item) => item.id !== universeId)
    .slice(0, RECENT_SHOWN)
  return (
    <span
      data-layout='universe-switcher'
      className='inline-flex min-w-0 items-center gap-1'
    >
      <Button
        asChild
        variant='outline'
        size={compact ? 'icon-sm' : 'sm'}
        aria-label='Back to the Library of Universes'
        title='Back to the Library of Universes'
      >
        <Link to='/'>
          <LibraryBig />
          {!compact && 'Library'}
        </Link>
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type='button'
            variant='outline'
            size='sm'
            aria-label={`${name}: switch universe`}
            className={cn('max-w-56', compact && 'max-w-32')}
          >
            <UniverseCrest name={name} size='xs' />
            <span className={cn('min-w-0 truncate', compact && 'sr-only')}>
              {name}
            </span>
            <ChevronsUpDown />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align='end' className='w-72'>
          <DropdownMenuLabel className='flex min-w-0 items-center gap-2'>
            <UniverseCrest name={name} size='sm' />
            <span className='flex min-w-0 flex-col'>
              <Text as='span' weight='semibold' truncate>
                {name}
              </Text>
              <Muted as='span' variant='caption' truncate>
                {here ? timeLine(here) : 'The universe you are in'}
              </Muted>
            </span>
            <Check
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-primary'
            />
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuLabel>
              <Muted as='span' variant='caption'>
                {shelf.isPending
                  ? 'Reading the shelves'
                  : recent.length === 0
                    ? 'No other universe stands on the shelf yet'
                    : 'Recent universes'}
              </Muted>
            </DropdownMenuLabel>
            {recent.map((universe) => (
              <DropdownMenuItem
                key={universe.id}
                disabled={opening !== null}
                onSelect={() => enter(universe)}
                className='flex min-w-0 items-center gap-2'
              >
                <UniverseCrest name={universe.name} size='xs' />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' truncate>
                    {universe.name}
                  </Text>
                  <Muted as='span' variant='caption' truncate>
                    {ageLine(universe)}
                  </Muted>
                </span>
                {opening === universe.id && (
                  <BookOpen
                    aria-hidden='true'
                    className='size-icon-sm animate-pulse text-primary motion-reduce:animate-none'
                  />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => void navigate({ to: '/' })}>
            <LibraryBig aria-hidden='true' />
            Every universe in the Library
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  )
}
