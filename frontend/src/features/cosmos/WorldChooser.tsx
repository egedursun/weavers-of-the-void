import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { ShowMore, useShowMore } from '@/components/domain'
import { type CosmosIndex } from './model/cosmosModel'

const WORLD_PAGE = 12

type WorldChooserProps = {
  index: CosmosIndex
  worldId: number | undefined
  onSelect: (worldId: number) => void
}

export function WorldChooser({ index, worldId, onSelect }: WorldChooserProps) {
  const more = useShowMore(index.worlds, WORLD_PAGE)
  if (index.worlds.length < 2) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={worldId === undefined ? '' : String(worldId)}
        onValueChange={(value) => value && onSelect(Number(value))}
        aria-label='Choose a world'
        className='flex-wrap'
      >
        {more.visible.map((item) => (
          <ToggleGroupItem
            key={item.world.id}
            value={String(item.world.id)}
            aria-label={
              item.world.discovery === 'forgotten'
                ? `${item.world.name}, forgotten`
                : item.world.name
            }
            className='max-w-full'
          >
            <span className='min-w-0 truncate'>
              {item.world.discovery === 'forgotten'
                ? `${item.world.name} · forgotten`
                : item.world.name}
            </span>
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <ShowMore state={more} noun={['world', 'worlds']} />
    </div>
  )
}
