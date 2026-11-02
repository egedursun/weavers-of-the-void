import { Hammer, HandHeart, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  ExpandableText,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { humanize, useLabels } from '@/features/pantheon/labels'
import { NodeLink } from './SonBonds'
import { type SonDetail } from './api'

const ROWS_SHOWN = 10
const WORDS_SHOWN = 5

export function SonRecords({ detail }: { detail: SonDetail }) {
  const { entityType } = useLabels()
  const words = detail.messages.filter((message) => message.intent !== 'chat')
  const worshippers = useShowMore(detail.worshippers, ROWS_SHOWN)
  const creations = useShowMore(detail.creations, ROWS_SHOWN)
  const spoken = useShowMore(words, WORDS_SHOWN)
  return (
    <>
      <Section title='Worshippers' level={3}>
        {detail.worshippers.length === 0 ? (
          <EmptyState
            icon={HandHeart}
            size='compact'
            title='Nobody yet'
            description='Communities that worship him appear here.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
              {worshippers.visible.map((entity) => (
                <li key={entity.id} className='flex min-w-0 items-center gap-2'>
                  <Badge size='sm' variant='outline'>
                    {entityType(entity.entity_type)}
                  </Badge>
                  <EntityLink kind='entity' id={String(entity.id)}>
                    {entity.name}
                  </EntityLink>
                </li>
              ))}
            </ul>
            <ShowMore
              state={worshippers}
              noun={['worshipper', 'worshippers']}
            />
          </div>
        )}
      </Section>
      <Section title='Creations' level={3}>
        {detail.creations.length === 0 ? (
          <EmptyState
            icon={Hammer}
            size='compact'
            title='Nothing created yet'
            description='What he creates on his turns gathers here.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            <ul className='flex min-w-0 flex-col gap-2'>
              {creations.visible.map((entity) => {
                const gone =
                  entity.status === 'rejected' || entity.status === 'destroyed'
                return (
                  <li
                    key={entity.id}
                    className={cn(
                      'flex min-w-0 flex-wrap items-center gap-2',
                      gone && 'line-through opacity-70'
                    )}
                  >
                    <Badge size='sm' variant='outline'>
                      {entityType(entity.entity_type)}
                    </Badge>
                    <EntityLink kind='entity' id={String(entity.id)}>
                      {entity.name}
                    </EntityLink>
                    <Label>
                      {[
                        entity.subtype,
                        `Epoch ${entity.birth_epoch}`,
                        entity.status !== 'canon'
                          ? humanize(entity.status)
                          : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </Label>
                  </li>
                )
              })}
            </ul>
            <ShowMore state={creations} noun={['creation', 'creations']} />
          </div>
        )}
      </Section>
      <Section title='Words' level={3}>
        {words.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            size='compact'
            title='No words exchanged'
            description='Prayers, orders and messages appear here.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            <ul className='flex min-w-0 flex-col gap-3'>
              {spoken.visible.map((message) => (
                <li
                  key={message.id}
                  className='flex min-w-0 flex-col gap-1 rounded-lg border bg-card p-3'
                >
                  <div className='flex min-w-0 flex-wrap items-baseline gap-1.5'>
                    {message.sender ? (
                      <NodeLink node={message.sender} />
                    ) : (
                      <Muted>Unknown</Muted>
                    )}
                    <Label>{'→'}</Label>
                    {message.recipient ? (
                      <NodeLink node={message.recipient} />
                    ) : (
                      <Muted>Unknown</Muted>
                    )}
                    <Badge size='sm' variant='outline'>
                      {humanize(message.intent)}
                    </Badge>
                    <Label>{`Epoch ${message.epoch}`}</Label>
                  </div>
                  <ExpandableText
                    italic
                    lines={3}
                  >{`"${message.text}"`}</ExpandableText>
                </li>
              ))}
            </ul>
            <ShowMore state={spoken} noun={['message', 'messages']} />
          </div>
        )}
      </Section>
    </>
  )
}
