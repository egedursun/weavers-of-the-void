import { Skeleton } from '@/components/ui/skeleton'
import { Section, ServerLineList, revealTool } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useSonOpportunities } from './api'

type SonOpportunitiesProps = {
  sonId: number
  statusLines: string[]
}

export function SonOpportunities({
  sonId,
  statusLines,
}: SonOpportunitiesProps) {
  const query = useSonOpportunities(sonId)
  const lines = (query.data?.lines ?? []).map((line, index) => ({
    key: `${line.kind}-${index}`,
    text: line.text,
    tension: line.tension,
    tools: line.tools,
  }))
  return (
    <Section
      title='Opportunities'
      description='What this son sees when his turn begins, exactly as the server phrases it. The tools named are the ones he may use now.'
      level={3}
    >
      {statusLines.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-1'>
          {statusLines.map((line) => (
            <li key={line}>
              <Text>{line}</Text>
            </li>
          ))}
        </ul>
      )}
      {query.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : query.isError ? (
        <Muted>{query.error.message}</Muted>
      ) : (
        <ServerLineList
          lines={lines}
          emptyText='Nothing stands out for him right now.'
          onTool={revealTool}
        />
      )}
    </Section>
  )
}
