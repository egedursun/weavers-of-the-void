import { Swords } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Text } from '@/components/typography'
import { WarCard } from './WarCard'
import { WAR_PAGE_SIZE, type WarSummary } from './api'

type Query = {
  isPending: boolean
  isError: boolean
  error: Error | null
  data: { items: WarSummary[]; total: number } | undefined
}

export function WarsPanel({
  query,
  offset,
  onOffset,
}: {
  query: Query
  offset: number
  onOffset: (offset: number) => void
}) {
  if (query.isPending) return <Skeleton className='h-textarea w-full' />
  if (query.isError)
    return <Text tone='destructive'>{query.error?.message}</Text>
  const data = query.data
  if (!data || data.items.length === 0)
    return (
      <EmptyState
        icon={Swords}
        title='No wars'
        description='Peace holds, for now.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      {data.items.map((war) => (
        <WarCard key={war.id} war={war} />
      ))}
      <PageControls
        offset={offset}
        limit={WAR_PAGE_SIZE}
        total={data.total}
        onChange={onOffset}
        label='Wars'
      />
    </div>
  )
}
