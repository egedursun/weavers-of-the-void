import {
  ArrowRight,
  Eye,
  Ghost,
  Globe,
  Moon,
  Skull,
  Swords,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { ForeignGodCard } from '@/features/foreign-god/ForeignGodCard'
import { PlaceForeignGodForm } from '@/features/foreign-god/PlaceForeignGodForm'
import { type ForeignGodRecord } from './api'
import { type CosmosIndex } from './model/cosmosModel'

const STATUS_ORDER: Record<ForeignGodRecord['status'], number> = {
  awake: 0,
  asleep: 1,
  defeated: 2,
  dead: 3,
}

type GodListProps = {
  gods: ForeignGodRecord[]
  index: CosmosIndex
  onSelectWorld: (worldId: number) => void
}

export function ForeignGodList({ gods, index, onSelectWorld }: GodListProps) {
  const { open } = useDrawerStack()
  const sorted = [...gods].sort(
    (first, second) =>
      STATUS_ORDER[first.status] - STATUS_ORDER[second.status] ||
      second.power - first.power
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {sorted.map((god) => (
        <ForeignGodCard
          key={god.id}
          god={god}
          worldName={index.worldName(god.world_id)}
          actions={
            <>
              <Button
                variant='outline'
                size='sm'
                onClick={() => onSelectWorld(god.world_id)}
              >
                <Globe />
                {`Show ${index.worldName(god.world_id)}`}
              </Button>
              <Button
                variant='ghost'
                size='sm'
                onClick={() =>
                  open({ kind: 'foreign-god', id: String(god.id) })
                }
              >
                <ArrowRight />
                Open
              </Button>
            </>
          }
        />
      ))}
    </div>
  )
}

type ForeignGodsPanelProps = {
  index: CosmosIndex
  onSelectWorld: (worldId: number) => void
}

export function ForeignGodsPanel({
  index,
  onSelectWorld,
}: ForeignGodsPanelProps) {
  const gods = index.data.foreign_gods
  const awake = gods.filter((god) => god.status === 'awake').length
  const asleep = gods.filter((god) => god.status === 'asleep').length
  const fallen = gods.length - awake - asleep
  const hostile = gods.filter(
    (god) => god.stance < 0 && god.status !== 'dead'
  ).length
  return (
    <Section
      title='Foreign gods'
      level={3}
      description='Gods worshipped in other worlds, before or unaware of the pantheon. Their attitudes are toward the pantheon.'
    >
      {gods.length > 0 && (
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <MiniStat icon={Eye} tone='warning' label='Awake' value={awake} />
          <MiniStat icon={Moon} tone='info' label='Asleep' value={asleep} />
          <MiniStat
            icon={Swords}
            tone={hostile > 0 ? 'danger' : 'muted'}
            label='Hostile'
            value={hostile}
          />
          <MiniStat icon={Skull} label='Fallen' value={fallen} />
        </div>
      )}
      <PlaceForeignGodForm />
      {gods.length === 0 ? (
        <EmptyState
          icon={Ghost}
          size='compact'
          title='No known foreign god yet'
          description='Sleeping gods are born on godless worlds over time, or you can place one.'
        />
      ) : (
        <ForeignGodList
          gods={gods}
          index={index}
          onSelectWorld={onSelectWorld}
        />
      )}
    </Section>
  )
}
