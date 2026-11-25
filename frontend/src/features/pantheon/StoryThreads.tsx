import { useState } from 'react'
import { BookMarked, CheckCircle2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Paged, Section, FieldTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ExpeditionNote } from '@/features/cosmos/ExpeditionCard'
import { useExpeditionOfThread } from '@/features/cosmos/expeditionsApi'
import { NodeLink } from '@/features/son/SonBonds'
import { ActionButton } from './ActionButton'
import { NewThreadForm } from './NewThreadForm'
import { type ThreadRecord, godKeys, useThreads } from './api'
import { THREADS_SHOWN } from './constants'
import { useGodGate } from './gate'
import { useGodAction } from './godAction'

const HOW_MAX = 300

function CloseThread({ thread }: { thread: ThreadRecord }) {
  const [how, setHow] = useState('')
  const { reason } = useGodGate()
  const close = useGodAction({
    writes: [{ lever: 'thread:close' }],
    run: () =>
      unwrap(
        api.POST('/api/threads/{thread_id}/close', {
          params: { path: { thread_id: thread.id } },
          body: { how: how.trim() },
        })
      ),
    success: 'Story closed',
    invalidate: [godKeys.threads],
  })
  const inputId = `thread-close-${thread.id}`
  return (
    <Collapsible className='flex min-w-0 flex-col gap-2'>
      <CollapsibleTrigger asChild>
        <Button act={close} variant='ghost' size='sm' className='self-start'>
          <CheckCircle2 />
          Close the story
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 flex-col gap-2 sm:flex-row sm:items-end'>
          <FieldTile
            id={inputId}
            label='How did it close? (optional)'
            className='flex-1'
          >
            <Input
              id={inputId}
              value={how}
              maxLength={HOW_MAX}
              onChange={(event) => setHow(event.target.value)}
            />
          </FieldTile>
          <ActionButton
            act={close}
            label='Close'
            blocked={reason()}
            pending={close.isPending}
            onRun={() => close.mutate()}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function ThreadCard({ thread }: { thread: ThreadRecord }) {
  const open = thread.status === 'open'
  const expedition = useExpeditionOfThread(thread.id)
  const header = [
    `Story #${thread.id}`,
    `Epoch ${thread.epoch}`,
    thread.progress > 0
      ? `advanced ${plural(thread.progress, 'time', 'times')}`
      : null,
    thread.closed_epoch !== null
      ? `closed in Epoch ${thread.closed_epoch}`
      : null,
  ]
    .filter(Boolean)
    .join(' · ')
  return (
    <Card data-thread={thread.id}>
      <CardHeader>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Label className='min-w-0 flex-1'>{header}</Label>
          <Badge size='sm' variant={open ? 'default' : 'secondary'}>
            {open ? 'Open' : 'Closed'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className='flex flex-col gap-3'>
        <Text>{thread.text}</Text>
        {expedition && <ExpeditionNote expedition={expedition} />}
        {thread.closing_text && <Muted>{thread.closing_text}</Muted>}
        {(thread.related ?? []).length > 0 && (
          <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
            <Paged items={thread.related ?? []} noun={['name', 'names']}>
              {(node) => (
                <NodeLink key={`${node.kind}-${node.id}`} node={node} />
              )}
            </Paged>
          </div>
        )}
        {open && <CloseThread thread={thread} />}
      </CardContent>
    </Card>
  )
}

export function StoryThreads() {
  const threads = useThreads()
  const [all, setAll] = useState(false)
  const [closed, setClosed] = useState(false)
  const list = (threads.data ?? []).filter((thread) =>
    closed ? thread.status === 'closed' : thread.status === 'open'
  )
  const shown = all ? list : list.slice(0, THREADS_SHOWN)
  return (
    <Section
      title={closed ? 'Closed stories' : 'Open stories'}
      description='Storylines Fate is following through the epochs.'
      actions={
        <Button variant='ghost' size='sm' onClick={() => setClosed(!closed)}>
          {closed ? 'Show open stories' : 'Show closed stories'}
        </Button>
      }
    >
      <NewThreadForm />
      {threads.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : threads.isError ? (
        <Text tone='destructive'>{threads.error.message}</Text>
      ) : list.length === 0 ? (
        <EmptyState
          icon={BookMarked}
          size='compact'
          title={closed ? 'No closed story yet' : 'No open story'}
          description='Fate opens stories as the world grows, or you can open one yourself.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-2'>
          {shown.map((thread) => (
            <ThreadCard key={thread.id} thread={thread} />
          ))}
        </div>
      )}
      {list.length > THREADS_SHOWN && (
        <Button
          variant='ghost'
          size='sm'
          className='self-start'
          onClick={() => setAll(!all)}
        >
          {all
            ? 'Show less'
            : `Show all stories (${list.length - THREADS_SHOWN} more)`}
        </Button>
      )}
    </Section>
  )
}
