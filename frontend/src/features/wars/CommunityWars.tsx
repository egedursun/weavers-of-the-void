import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Section, Paged } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { WarsPanel } from './WarsPanel'
import { CaptivesList, TributesList } from './WarsTables'
import { useCommunityHeroes, useCommunityWars } from './api'

function Heroes({ entityId }: { entityId: number }) {
  const heroes = useCommunityHeroes(entityId)
  if (heroes.isPending) return <Skeleton className='h-control-lg w-full' />
  if (heroes.isError)
    return <Text tone='destructive'>{heroes.error.message}</Text>
  if (heroes.data.length === 0)
    return <Text>No living heroes stand for this community.</Text>
  return (
    <ul aria-label='Heroes' className='flex min-w-0 flex-wrap gap-2'>
      <Paged items={heroes.data} as='li'>
        {(hero) => (
          <li key={hero.hero.id} className='flex min-w-0 items-center gap-2'>
            <EntityLink kind='entity' id={String(hero.hero.id)}>
              {hero.hero.name}
            </EntityLink>
            {hero.role && (
              <Badge size='sm' variant='outline'>
                {humanize(hero.role)}
              </Badge>
            )}
          </li>
        )}
      </Paged>
    </ul>
  )
}

export function CommunityWars({ entityId }: { entityId: number }) {
  const [offset, setOffset] = useState(0)
  return (
    <Section
      id='section-wars'
      title='Wars and captives'
      description='Every war this community has fought, its captives, tributes and heroes.'
    >
      <WarsPanel
        query={useCommunityWars(entityId, offset)}
        offset={offset}
        onOffset={setOffset}
      />
      <Label variant='overline'>Captives</Label>
      <CaptivesList communityId={entityId} />
      <Label variant='overline'>Tributes</Label>
      <TributesList communityId={entityId} />
      <Label variant='overline'>Heroes</Label>
      <Heroes entityId={entityId} />
    </Section>
  )
}
