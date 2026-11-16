import { Users } from 'lucide-react'
import { formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  Medallion,
  PagedList,
  Section,
} from '@/components/domain'
import { type EntitySummary } from '@/features/pantheon/api'
import { useLabels } from '@/features/pantheon/labels'

export function CreatorCult({
  cult,
  faith,
  essence,
}: {
  cult: EntitySummary[]
  faith: number
  essence: number
}) {
  const { entityType } = useLabels()
  return (
    <Section
      title='Cult'
      description={
        cult.length > 0
          ? `${plural(cult.length, 'community', 'communities')} worship the Creator directly · total faith ${formatDecimal(faith, 1)} · ${essence} essence an epoch`
          : undefined
      }
      level={3}
    >
      {cult.length === 0 ? (
        <EmptyState
          icon={Users}
          size='compact'
          title='No community worships the Creator directly yet'
          description="Answering mortals' prayers draws them closer."
        />
      ) : (
        <PagedList
          items={cult}
          initial={10}
          noun={['community', 'communities']}
          className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
          itemKey={(member) => member.id}
        >
          {(member) => (
            <li className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
              <Medallion icon={Users} size='sm' />
              <span className='min-w-0 flex-1 truncate'>
                <EntityLink kind='entity' id={String(member.id)}>
                  {member.name}
                </EntityLink>
              </span>
              <Badge size='sm' variant='outline'>
                {entityType(member.entity_type)}
              </Badge>
            </li>
          )}
        </PagedList>
      )}
    </Section>
  )
}
