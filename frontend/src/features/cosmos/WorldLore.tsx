import { useState } from 'react'
import { ChevronDown, Scale } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import {
  CodeBlock,
  EmptyState,
  EntityLink,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type NaturalLaw, useWorldGeography, useWorldLaws } from './api'
import { humanize } from './model/labels'

const NO_MECHANIC: NaturalLaw = 'none'

export function WorldLaws({ worldId }: { worldId: number }) {
  const laws = useWorldLaws(worldId)
  return (
    <Section
      title='Laws of this world'
      description='Natural laws bend how life, death and war work here; written laws bind its peoples.'
      level={3}
    >
      {laws.isPending && <Skeleton className='h-control-lg w-full' />}
      {laws.isError && <Text tone='destructive'>{laws.error.message}</Text>}
      {laws.data &&
        (laws.data.length === 0 ? (
          <EmptyState
            icon={Scale}
            title='No laws yet'
            description='A son or a people may lay one down; until then the world runs on the common rules.'
          />
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={laws.data} as='li' noun={['law', 'laws']}>
              {(law) => (
                <li
                  key={law.entity.id}
                  className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'
                >
                  <EntityLink kind='entity' id={String(law.entity.id)}>
                    {law.entity.name}
                  </EntityLink>
                  <Badge size='sm' variant='outline'>
                    {law.entity.entity_type === 'natural_law'
                      ? 'Natural law'
                      : 'Law'}
                  </Badge>
                  {law.mechanic && law.mechanic !== NO_MECHANIC && (
                    <Badge size='sm' variant='secondary'>
                      {humanize(law.mechanic)}
                    </Badge>
                  )}
                </li>
              )}
            </Paged>
          </ul>
        ))}
    </Section>
  )
}

export function WorldGeography({ worldId }: { worldId: number }) {
  const [open, setOpen] = useState(false)
  const geography = useWorldGeography(worldId, open)
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' className='w-full justify-between'>
          Geography as the sons and mortals read it
          <ChevronDown
            className={cn('transition-transform', open && 'rotate-180')}
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <Muted variant='caption'>
          Drawn from the map: each known region with its height, coast, size,
          terrain and neighbours.
        </Muted>
        {geography.isPending && <Skeleton className='h-textarea w-full' />}
        {geography.isError && (
          <Text tone='destructive'>{geography.error.message}</Text>
        )}
        {geography.data && (
          <CodeBlock
            label='Geography'
            text={geography.data.text}
            empty='No region of this world has been mapped yet.'
          />
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
