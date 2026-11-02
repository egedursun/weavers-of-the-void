import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { type CosmosIndex } from './model/cosmosModel'

type WorldChooserProps = {
  index: CosmosIndex
  worldId: number | undefined
  onSelect: (worldId: number) => void
}

export function WorldChooser({ index, worldId, onSelect }: WorldChooserProps) {
  if (index.worlds.length < 2) return null
  return (
    <ToggleGroup
      type='single'
      variant='outline'
      size='sm'
      value={worldId === undefined ? '' : String(worldId)}
      onValueChange={(value) => value && onSelect(Number(value))}
      aria-label='Choose a world'
      className='flex-wrap'
    >
      {index.worlds.map((item) => (
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
  )
}
