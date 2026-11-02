import { useState } from 'react'
import { ScrollText } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Text } from '@/components/typography'
import { ChronicleEntry } from '@/features/chronicle/ChronicleEntry'
import { useChronicleKindLabels } from '@/features/chronicle/api'
import { useEntityChronicle } from '../api/queries'
import { CHRONICLE_PAGE_SIZE } from '../constants'

type EntityChronicleProps = {
  entityId: number
  total: number
  highlightEpoch: number | null
}

export function EntityChronicle({
  entityId,
  total,
  highlightEpoch,
}: EntityChronicleProps) {
  const [offset, setOffset] = useState(0)
  const page = useEntityChronicle(entityId, offset, CHRONICLE_PAGE_SIZE)
  const labels = useChronicleKindLabels()
  const items = page.data?.items ?? []
  const shownTotal = page.data?.total ?? total
  return (
    <Section
      id='section-chronicle'
      title='In the chronicle'
      description={`${formatInteger(shownTotal)} records mention it.`}
    >
      {page.isPending && <Skeleton className='h-textarea w-full' />}
      {page.isError && <Text tone='destructive'>{page.error.message}</Text>}
      {page.isSuccess && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={ScrollText}
          title='No record'
          description='The chronicle has not named it yet.'
        />
      )}
      {items.length > 0 && (
        <ol className='flex min-w-0 flex-col gap-1'>
          {items.map((line, index) => (
            <ChronicleEntry
              key={line.id}
              line={line}
              selfId={entityId}
              kindLabel={labels.get(line.kind)}
              highlighted={
                highlightEpoch === line.epoch &&
                items[index - 1]?.epoch !== line.epoch
              }
            />
          ))}
        </ol>
      )}
      <PageControls
        offset={offset}
        limit={CHRONICLE_PAGE_SIZE}
        total={shownTotal}
        onChange={setOffset}
        label='Chronicle pages'
        busy={page.isFetching}
      />
    </Section>
  )
}
