import { formatDecimal } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { EntityLink, PagedList, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { humanize } from '../actions/schema'
import { type SimilarRecord } from '../api/types'

export function EntityRelated({ similar }: { similar: SimilarRecord[] }) {
  if (similar.length === 0) return null
  return (
    <Section
      id='section-related'
      title='May be related'
      description='Shared bonds, the same land, the same maker.'
    >
      <PagedList
        items={similar}
        initial={6}
        noun={['record', 'records']}
        className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
        itemKey={(item) => item.entity.id}
      >
        {(item) => (
          <li className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'>
            <div className='flex min-w-0 items-center gap-2'>
              <EntityLink kind='entity' id={String(item.entity.id)}>
                {item.entity.name}
              </EntityLink>
              <Badge size='sm' variant='outline' className='ms-auto'>
                {formatDecimal(item.score)}
              </Badge>
            </div>
            <Muted variant='caption' truncate={2}>
              {[
                item.entity.subtype ?? humanize(item.entity.entity_type),
                ...item.reasons,
              ].join(' · ')}
            </Muted>
          </li>
        )}
      </PagedList>
    </Section>
  )
}
