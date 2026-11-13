import { Globe2, Moon } from 'lucide-react'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Section, ShowMore, useShowMore } from '@/components/domain'
import { type CosmosWorld } from './api'
import { type CosmosIndex } from './model/cosmosModel'

const WORLD_PAGE = 12

function isMoon(item: CosmosWorld) {
  return item.world.parent_world_id !== null
}

function count(amount: number, one: string, many: string) {
  return `${amount} ${amount === 1 ? one : many}`
}

type WorldChooserProps = {
  index: CosmosIndex
  worldId: number | undefined
  onSelect: (worldId: number) => void
}

export function WorldChooser({ index, worldId, onSelect }: WorldChooserProps) {
  const more = useShowMore(index.worlds, WORLD_PAGE)
  if (index.worlds.length < 2) return null
  const moons = index.worlds.filter(isMoon).length
  const planets = index.worlds.length - moons
  const tally = [
    count(planets, 'planet', 'planets'),
    ...(moons > 0 ? [count(moons, 'moon', 'moons')] : []),
  ].join(' · ')
  return (
    <Section
      title='Worlds'
      level={3}
      icon={Globe2}
      tone='verdigris'
      description={`${tally}. Choose one to open it below.`}
    >
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
            {isMoon(item) ? (
              <Moon aria-hidden='true' />
            ) : (
              <Globe2 aria-hidden='true' />
            )}
            <span className='min-w-0 truncate'>
              {item.world.discovery === 'forgotten'
                ? `${item.world.name} · forgotten`
                : item.world.name}
            </span>
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <ShowMore state={more} noun={['world', 'worlds']} />
    </Section>
  )
}
