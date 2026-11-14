import { useMemo } from 'react'
import { ArrowRight, SearchX } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { Highlight } from '@/features/atlas/Highlight'
import { SEARCH_MIN_LENGTH, type SearchHit, useWorldSearch } from './api'

type ChronicleSearchResultsProps = {
  query: string
  localMatches: number
  onGo: (epoch: number, line?: number) => void
}

const SHOWN_CATEGORIES = new Set(['chronicle', 'epoch'])

export function ChronicleSearchResults({
  query,
  localMatches,
  onGo,
}: ChronicleSearchResultsProps) {
  const search = useWorldSearch(query)
  const groups = useMemo(() => {
    const map = new Map<number, SearchHit[]>()
    for (const hit of search.data ?? []) {
      if (
        !SHOWN_CATEGORIES.has(hit.category) ||
        hit.epoch === null ||
        hit.epoch === undefined
      )
        continue
      map.set(hit.epoch, [...(map.get(hit.epoch) ?? []), hit])
    }
    return [...map.entries()].sort(([left], [right]) => right - left)
  }, [search.data])
  if (query.trim().length < SEARCH_MIN_LENGTH) return null
  const total = groups.reduce((sum, [, hits]) => sum + hits.length, 0)
  return (
    <Section
      id='chronicle-search'
      title='Across the whole chronicle'
      description={`${plural(total, 'match', 'matches')} found by the scribes · ${formatInteger(localMatches)} in the epochs open below`}
      level={3}
    >
      {search.isPending && <Skeleton className='h-textarea w-full' />}
      {search.isError && <Text tone='destructive'>{search.error.message}</Text>}
      {search.isSuccess && groups.length === 0 && (
        <EmptyState
          size='compact'
          icon={SearchX}
          title='Nothing found'
          description='No record of the chronicle holds these words.'
        />
      )}
      {groups.map(([epoch, hits]) => (
        <div key={epoch} className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 items-center gap-2'>
            <Label
              variant='overline'
              className='flex-1'
            >{`Epoch ${formatInteger(epoch)}`}</Label>
            <Button variant='ghost' size='sm' onClick={() => onGo(epoch)}>
              Go to epoch
              <ArrowRight />
            </Button>
          </div>
          <ul className='flex min-w-0 flex-col gap-1'>
            {hits.map((hit) => (
              <li
                key={`${hit.category}-${hit.id}`}
                className='flex min-w-0 items-start gap-2'
              >
                <Text as='div' className='min-w-0 flex-1'>
                  <Highlight text={hit.snippet ?? hit.title} query={query} />
                  {hit.subtitle && (
                    <Muted
                      as='span'
                      variant='caption'
                    >{` · ${hit.subtitle}`}</Muted>
                  )}
                </Text>
                {hit.category === 'chronicle' && (
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label='Go to this record'
                    onClick={() => onGo(epoch, hit.id)}
                  >
                    <ArrowRight />
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </Section>
  )
}
