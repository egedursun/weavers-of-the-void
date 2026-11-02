import { Skeleton } from '@/components/ui/skeleton'
import { Section, ServerLineList, revealTool } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useEntityOpportunities } from '../api/queries'

export function EntityOpportunities({ entityId }: { entityId: number }) {
  const query = useEntityOpportunities(entityId)
  const lines = (query.data?.lines ?? []).map((line, index) => ({
    key: `${line.kind}-${index}`,
    text: line.text,
    tension: line.tension,
    tools: line.tools,
  }))
  return (
    <Section
      id='section-opportunities'
      title='Opportunities'
      description='What this record sees when it is given a turn, exactly as the server phrases it.'
    >
      {query.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : query.isError ? (
        <Muted>{query.error.message}</Muted>
      ) : (
        <ServerLineList
          lines={lines}
          emptyText='Nothing stands out for it right now.'
          onTool={revealTool}
        />
      )}
    </Section>
  )
}
