import { useState } from 'react'
import {
  BookOpenCheck,
  CalendarDays,
  Plus,
  Spline,
  TrendingUp,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  FormRow,
  Medallion,
  PagedList,
  Section,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { ExpeditionNote } from '@/features/cosmos/ExpeditionCard'
import { useExpeditionOfThread } from '@/features/cosmos/expeditionsApi'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { humanize } from '@/features/entity/actions/schema'
import { useLoreMutation } from '@/features/entity/api/mutations'
import {
  useNames,
  useThreads,
  useWorldState,
} from '@/features/entity/api/queries'
import { type ThreadRecord, closeThread, openThread } from './api'

const THREAD_TEXT_MAX = 600
const PERCENT = 100

function ThreadCard({
  thread,
  onClose,
  blocked,
}: {
  thread: ThreadRecord
  onClose?: () => void
  blocked: string | null
}) {
  const open = thread.status === 'open'
  const related = thread.related ?? []
  const expedition = useExpeditionOfThread(thread.id)
  return (
    <li
      className={cn(
        'flex min-w-0 flex-col gap-2.5 rounded-xl border bg-card p-3',
        open ? 'border-primary/30' : 'opacity-85'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={open ? Spline : BookOpenCheck}
          tone={open ? 'gold' : 'muted'}
          size='sm'
        />
        <Text className='min-w-0 flex-1'>{thread.text}</Text>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge size='sm' variant={open ? 'default' : 'outline'}>
          {open ? 'Open' : 'Closed'}
        </Badge>
        <Badge size='sm' variant='outline'>
          <CalendarDays />
          {open
            ? `Since epoch ${formatInteger(thread.epoch)}`
            : `Epoch ${formatInteger(thread.epoch)}–${formatInteger(thread.closed_epoch ?? thread.epoch)}`}
        </Badge>
        {open && (
          <Badge size='sm' variant='info'>
            <TrendingUp />
            {`${plural(thread.progress, 'step', 'steps')}`}
          </Badge>
        )}
      </div>
      {expedition && <ExpeditionNote expedition={expedition} />}
      {open && !expedition && (
        <Progress
          value={Math.min(PERCENT, thread.progress)}
          size='sm'
          aria-label='How far the story has come'
        />
      )}
      {thread.closing_text && <Muted italic>{thread.closing_text}</Muted>}
      {related.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label>Woven with</Label>
          {related.map((ref) => (
            <Badge key={ref.id} size='sm' variant='outline'>
              <EntityLink kind='entity' id={String(ref.id)}>
                {ref.name}
              </EntityLink>
            </Badge>
          ))}
        </div>
      )}
      {onClose && (
        <Button
          variant='outline'
          size='sm'
          className='self-start'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onClose}
        >
          <BookOpenCheck />
          Close the story
        </Button>
      )}
    </li>
  )
}

function OpenThreadForm({ blocked }: { blocked: string | null }) {
  const names = useNames()
  const [text, setText] = useState('')
  const [related, setRelated] = useState<number[]>([])
  const create = useLoreMutation({
    run: () => openThread(text.trim(), related),
    success: 'A new story thread is woven',
    onDone: () => {
      setText('')
      setRelated([])
    },
  })
  const options = (names.data ?? [])
    .filter((entry) => entry.kind === 'entity' && !related.includes(entry.id))
    .map((entry) => ({
      value: String(entry.id),
      label: entry.name,
      hint: humanize(entry.type),
    }))
  const reason =
    blocked ??
    (text.trim() === '' ? 'Tell what the story is about.' : null) ??
    (create.isPending ? 'Working on it.' : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FormRow label='The story'>
        {(id) => (
          <Textarea
            id={id}
            maxLength={THREAD_TEXT_MAX}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Woven with'
        description='Optional; add records one by one'
      >
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-2'>
            <RecordCombobox
              id={id}
              options={options}
              value={null}
              onChange={(value) =>
                value && setRelated((current) => [...current, Number(value)])
              }
              placeholder='Add a record'
              aria-label='Add a record to the story'
            />
            {related.length > 0 && (
              <PagedList
                items={related}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1'
                itemKey={(id) => id}
              >
                {(id) => (
                  <Button
                    key={id}
                    variant='secondary'
                    size='sm'
                    aria-label={`Remove ${names.data?.find((entry) => entry.id === id)?.name ?? id}`}
                    onClick={() =>
                      setRelated((current) =>
                        current.filter((item) => item !== id)
                      )
                    }
                  >
                    {names.data?.find((entry) => entry.id === id)?.name ??
                      `Record ${id}`}
                  </Button>
                )}
              </PagedList>
            )}
          </div>
        )}
      </FormRow>
      <Button
        className='self-start'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => create.mutate()}
      >
        <Spline />
        Weave the story
      </Button>
    </div>
  )
}

export function ChronicleThreads() {
  const threads = useThreads()
  const state = useWorldState()
  const [closing, setClosing] = useState<ThreadRecord | null>(null)
  const [how, setHow] = useState('')
  const blocked = state.data?.read_only ? READ_ONLY_REASON : null
  const close = useLoreMutation({
    run: (thread: ThreadRecord) => closeThread(thread.id, how.trim()),
    success: 'The story is closed',
    onDone: () => setHow(''),
  })
  const all = threads.data ?? []
  const open = all.filter((thread) => thread.status === 'open')
  const closed = all.filter((thread) => thread.status === 'closed')
  return (
    <Section
      id='chronicle-threads'
      title='Stories'
      description='Open threads the sons and Fate keep weaving, and the ones that ended.'
      level={3}
    >
      {threads.isError && (
        <Text tone='destructive'>{threads.error.message}</Text>
      )}
      {threads.isSuccess && all.length === 0 && (
        <EmptyState
          size='compact'
          icon={Spline}
          title='No stories yet'
          description='Threads begin when a son or Fate starts a tale that outlives an epoch.'
        />
      )}
      {open.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
          {open.map((thread) => (
            <ThreadCard
              key={thread.id}
              thread={thread}
              blocked={blocked}
              onClose={() => setClosing(thread)}
            />
          ))}
        </ul>
      )}
      {closed.length > 0 && (
        <Collapsible className='flex min-w-0 flex-col gap-3'>
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm' className='self-start'>
              {`Closed stories · ${formatInteger(closed.length)}`}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
              {closed.map((thread) => (
                <ThreadCard key={thread.id} thread={thread} blocked={blocked} />
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      )}
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button variant='outline' className='self-start'>
            <Plus />
            Open a story
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <OpenThreadForm blocked={blocked} />
        </CollapsibleContent>
      </Collapsible>
      <ConfirmDialog
        open={closing !== null}
        onOpenChange={(value) => !value && setClosing(null)}
        title='Close this story?'
        desc='Say how it ended; the chronicle keeps it.'
        confirmText='Close the story'
        isLoading={close.isPending}
        handleConfirm={() => {
          if (closing) close.mutate(closing)
          setClosing(null)
        }}
      >
        <Textarea
          aria-label='How it ended'
          maxLength={THREAD_TEXT_MAX}
          value={how}
          onChange={(event) => setHow(event.target.value)}
        />
      </ConfirmDialog>
    </Section>
  )
}
