import { Ghost } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, PagedList, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { useForeignGods, useWorldState } from '@/features/pantheon/api'
import { ForeignGodCard } from './ForeignGodCard'
import { PlaceForeignGodForm } from './PlaceForeignGodForm'

export function ForeignGodsSection() {
  const gods = useForeignGods()
  const state = useWorldState()
  const worldName = (worldId: number) =>
    state.data?.worlds.find((world) => world.id === worldId)?.name ?? null
  const list = gods.data ?? []
  return (
    <Section
      title='Foreign gods'
      description='Old gods of other worlds: they wake, steal worshippers and go to war, or befriend the pantheon.'
    >
      <PlaceForeignGodForm />
      {gods.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : gods.isError ? (
        <Text tone='destructive'>{gods.error.message}</Text>
      ) : list.length === 0 ? (
        <EmptyState
          icon={Ghost}
          size='compact'
          title='No foreign god yet'
          description='Sleeping gods are born on godless worlds over time, or you can place one.'
        />
      ) : (
        <PagedList
          items={list}
          initial={9}
          noun={['god', 'gods']}
          as='div'
          className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3'
          itemKey={(god) => god.id}
        >
          {(god) => (
            <ForeignGodCard god={god} worldName={worldName(god.world_id)} />
          )}
        </PagedList>
      )}
    </Section>
  )
}
