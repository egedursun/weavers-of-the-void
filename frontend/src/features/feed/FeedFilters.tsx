import {
  Crown,
  Globe,
  Layers,
  type LucideIcon,
  Scale,
  Users,
} from 'lucide-react'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  FEED_ACTORS,
  FEED_ACTOR_LABEL,
  FEED_CATEGORY_LABEL,
  type FeedActorFilter,
  type FeedCategory,
} from './feedModel'
import { useFeed } from './feedStore'

const ACTOR_ICON: Record<FeedActorFilter, LucideIcon> = {
  all: Layers,
  gods: Crown,
  mortals: Users,
  world: Globe,
  fate: Scale,
}

function isActor(value: string): value is FeedActorFilter {
  return (FEED_ACTORS as readonly string[]).includes(value)
}

type FeedFiltersProps = {
  categories: FeedCategory[]
}

export function FeedFilters({ categories }: FeedFiltersProps) {
  const actor = useFeed((state) => state.actor)
  const selected = useFeed((state) => state.categories)
  const setActor = useFeed((state) => state.setActor)
  const toggleCategory = useFeed((state) => state.toggleCategory)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ToggleGroup
        type='single'
        size='sm'
        variant='outline'
        value={actor}
        onValueChange={(value) => isActor(value) && setActor(value)}
        aria-label='Who acted'
        className='w-full'
      >
        {FEED_ACTORS.map((item) => (
          <ToggleGroupItem key={item} value={item} className='grow'>
            {(() => {
              const Icon = ACTOR_ICON[item]
              return <Icon aria-hidden='true' />
            })()}
            {FEED_ACTOR_LABEL[item]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      {categories.length > 0 && (
        <ToggleGroup
          type='multiple'
          size='sm'
          variant='outline'
          value={selected}
          onValueChange={(values) => {
            const next = new Set(values)
            for (const category of categories)
              if (next.has(category) !== selected.includes(category))
                toggleCategory(category)
          }}
          aria-label='World event categories'
          className='flex-wrap'
        >
          {categories.map((category) => (
            <ToggleGroupItem key={category} value={category}>
              {FEED_CATEGORY_LABEL[category]}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </div>
  )
}
