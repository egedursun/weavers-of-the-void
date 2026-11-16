import { type components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { EntityLink, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NodeAvatar } from '@/features/images/NodeAvatar'

type RulingSky = components['schemas']['EpochStarWorld']

export function RulingSkyList({ entries }: { entries: RulingSky[] }) {
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      <Paged items={entries} as='li'>
        {(entry) => (
          <li
            key={entry.world_id}
            className='flex min-w-0 items-center gap-2.5 rounded-md border surface-sheen border-gild/60 bg-card px-2.5 py-1.5'
          >
            {entry.star ? (
              <NodeAvatar id={entry.star.id} name={entry.star.name} size='sm' />
            ) : (
              <NodeAvatar
                id={entry.world_id}
                name={entry.world_name}
                size='sm'
              />
            )}
            <span className='flex min-w-0 flex-1 flex-col'>
              <Muted as='span' variant='caption' truncate>
                <EntityLink kind='world' id={String(entry.world_id)}>
                  {entry.world_name}
                </EntityLink>
              </Muted>
              {entry.star ? (
                <Text as='span' truncate>
                  <EntityLink kind='entity' id={String(entry.star.id)}>
                    {entry.star.name}
                  </EntityLink>
                </Text>
              ) : (
                <Muted as='span' variant='caption'>
                  No body rules its sky yet
                </Muted>
              )}
            </span>
            {entry.star?.subtype && (
              <Badge size='sm' variant='outline' className='shrink-0'>
                {entry.star.subtype}
              </Badge>
            )}
          </li>
        )}
      </Paged>
    </ul>
  )
}
