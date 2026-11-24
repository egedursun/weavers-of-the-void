import { Moon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  ExpandableText,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { entryKindOf } from '@/features/chronicle/linkTargets'
import { useEntityDreams } from '../api/queries'
import { type NodeRef } from '../api/types'

type Dream = {
  id: number
  epoch: number
  sender: NodeRef | null
  recipient: NodeRef | null
  text: string
  is_read: boolean
}

function Who({ node }: { node: NodeRef | null }) {
  if (!node) return <Text as='span'>Someone forgotten</Text>
  const kind = entryKindOf(node.kind)
  if (!kind) return <Text as='span'>{node.name}</Text>
  return (
    <EntityLink
      kind={kind}
      id={kind === 'creator' ? undefined : String(node.id)}
    >
      {node.name}
    </EntityLink>
  )
}

function DreamList({
  title,
  dreams,
  other,
}: {
  title: string
  dreams: Dream[]
  other: 'sender' | 'recipient'
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`${title} · ${dreams.length}`}</Label>
      {dreams.length === 0 ? (
        <Muted>None.</Muted>
      ) : (
        <PagedList
          items={dreams}
          initial={3}
          noun={['dream', 'dreams']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(dream) => dream.id}
        >
          {(dream) => (
            <li className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Badge
                  size='sm'
                  variant='outline'
                >{`Epoch ${dream.epoch}`}</Badge>
                <Who node={dream[other]} />
                {!dream.is_read && (
                  <Badge size='sm' variant='warning'>
                    unread
                  </Badge>
                )}
              </div>
              <ExpandableText italic lines={3}>
                {dream.text}
              </ExpandableText>
            </li>
          )}
        </PagedList>
      )}
    </div>
  )
}

export function EntityDreams({ entityId }: { entityId: number }) {
  const query = useEntityDreams(entityId)
  const data = query.data
  return (
    <Section
      id='section-dreams'
      title='Dreams'
      description='Dreams this record received and the ones it sent. Unread dreams reach it at its next turn.'
    >
      {query.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : query.isError ? (
        <Muted>{query.error.message}</Muted>
      ) : data && data.received.length + data.sent.length === 0 ? (
        <EmptyState
          icon={Moon}
          title='No dreams'
          description='No dream has passed to or from this record.'
        />
      ) : (
        data && (
          <div className='flex min-w-0 flex-col gap-4'>
            <DreamList title='Received' dreams={data.received} other='sender' />
            <DreamList title='Sent' dreams={data.sent} other='recipient' />
          </div>
        )
      )}
    </Section>
  )
}
