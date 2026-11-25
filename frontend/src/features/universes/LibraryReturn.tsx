import { Link } from '@tanstack/react-router'
import { ArrowLeft, LibraryBig } from 'lucide-react'
import { useUniverseId } from '@/api/universeStore'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { UniverseCrest } from './UniverseCrest'
import { useShelf, useUniverse } from './api'

export function LibraryReturn() {
  const universeId = useUniverseId()
  const shelf = useShelf()
  const detail = useUniverse(universeId)
  const total = shelf.data?.total ?? null
  const name = detail.data?.name ?? null
  return (
    <nav
      aria-label='Leave the birth'
      className='relative flex w-full max-w-6xl min-w-0 flex-wrap items-center justify-between gap-3'
    >
      <Button asChild variant='outline' size='tile' className='w-auto'>
        <Link to='/' aria-label='Back to the Library of Universes'>
          <ArrowLeft aria-hidden='true' className='text-muted-foreground' />
          <Medallion icon={LibraryBig} tone='gold' size='sm' />
          <span className='flex min-w-0 flex-col'>
            <Text as='span' weight='semibold' className='font-display'>
              The Library of Universes
            </Text>
            <Muted as='span' variant='caption'>
              {total === null
                ? 'Back to your shelves'
                : `Back to your shelves · ${plural(total, 'universe')}`}
            </Muted>
          </span>
        </Link>
      </Button>
      {name && (
        <span className='flex min-w-0 items-center gap-2.5 rounded-lg surface-sheen px-3 py-2'>
          <UniverseCrest name={name} size='sm' />
          <span className='flex min-w-0 flex-col'>
            <Label variant='gilded'>Being born</Label>
            <Text as='span' weight='semibold' truncate className='font-display'>
              {name}
            </Text>
          </span>
        </span>
      )}
    </nav>
  )
}
