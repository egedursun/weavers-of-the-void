import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronUp,
  ChevronsUp,
  Loader2,
  MessageCircle,
  Send,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState, Portrait, Section, FieldTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type SonRecord } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { refreshWorld } from '@/features/pantheon/godAction'
import { ATTITUDE_BADGE, ATTITUDE_LABEL } from '@/features/pantheon/labels'
import { type ChatReply, sonKeys, useSonChat } from './api'

const RECENT_MESSAGES = 12

type ChatMemory = { draft: string; reply: ChatReply | null }

const MEMORY = new Map<number, ChatMemory>()

function remembered(sonId: number): ChatMemory {
  return MEMORY.get(sonId) ?? { draft: '', reply: null }
}

function Bubble({
  mine,
  author,
  epoch,
  text,
  name,
  cover,
  pending = false,
}: {
  mine: boolean
  author: string
  epoch: string
  text: string
  name: string
  cover: string | null
  pending?: boolean
}) {
  return (
    <li
      className={cn(
        'flex min-w-0 items-end gap-2',
        mine ? 'justify-end' : 'justify-start'
      )}
    >
      {!mine && <Portrait name={name} src={cover} size='sm' />}
      <div
        className={cn(
          'flex max-w-reading min-w-0 flex-col gap-1 rounded-md border surface-framed border-gild/70 bg-card p-3',
          mine ? 'bg-primary/10' : 'bg-muted',
          pending && 'opacity-70'
        )}
      >
        <Label>{`${author} · ${epoch}`}</Label>
        <Text>{text}</Text>
      </div>
    </li>
  )
}

export function SonChat({
  son,
  cover,
}: {
  son: SonRecord
  cover: string | null
}) {
  const chat = useSonChat(son.id)
  const queryClient = useQueryClient()
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const memory = remembered(son.id)
  const [draft, setDraftState] = useState(memory.draft)
  const [reply, setReply] = useState<ChatReply | null>(memory.reply)
  const [sent, setSent] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const follow = useRef(false)
  const maxChars = rule('council.chat_max_chars')
  const dead = son.status === 'dead'
  const setDraft = (value: string) => {
    setDraftState(value)
    MEMORY.set(son.id, { draft: value, reply })
  }
  const send = useMutation({
    mutationFn: (text: string) =>
      unwrap(
        api.POST('/api/sons/{son_id}/chat', {
          params: { path: { son_id: son.id } },
          body: { text },
        })
      ),
    onMutate: (text) => {
      setSent(text)
      setDraft('')
    },
    onSuccess: (result) => {
      setReply(result)
      MEMORY.set(son.id, { draft: '', reply: result })
      void queryClient.invalidateQueries({ queryKey: sonKeys.chat(son.id) })
      refreshWorld(queryClient)
    },
    onError: (_error, text) => setDraft(text),
    onSettled: () => setSent(null),
  })
  const messages = chat.data ?? []
  const [earlier, setEarlier] = useState(0)
  const keep = RECENT_MESSAGES + earlier
  const shown = messages.length > keep ? messages.slice(-keep) : messages
  const hidden = messages.length - shown.length
  useEffect(() => {
    if (!follow.current) return
    endRef.current?.scrollIntoView({ block: 'nearest' })
    if (sent === null) follow.current = false
  }, [messages.length, sent])
  const blocked =
    reason({ llm: true }) ??
    (dead
      ? `${son.name} is dead; your voice does not reach the bones.`
      : null) ??
    (draft.trim() ? null : 'Write something first.')
  const submit = () => {
    if (blocked || send.isPending) return
    follow.current = true
    send.mutate(draft.trim())
  }
  return (
    <Section title='Talk with them' surface='card' level={3}>
      {chat.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : chat.isError ? (
        <Text tone='destructive'>{chat.error.message}</Text>
      ) : messages.length === 0 && !sent ? (
        <EmptyState
          icon={MessageCircle}
          size='compact'
          title={dead ? 'Too late' : 'No words yet'}
          description={
            dead
              ? `You never spoke with ${son.name}; now it is too late.`
              : `You have never spoken with ${son.name}. Say the first word.`
          }
        />
      ) : (
        <ul
          aria-label={`Conversation with ${son.name}`}
          className='flex min-w-0 flex-col gap-3'
        >
          {hidden > 0 && (
            <li className='flex min-w-0 flex-wrap items-center justify-center gap-1 rounded-md px-3 py-1.5 sealed-well'>
              <Muted as='span' variant='caption'>
                {`${hidden} earlier ${hidden === 1 ? 'message' : 'messages'}`}
              </Muted>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setEarlier(earlier + RECENT_MESSAGES)}
              >
                <ChevronUp />
                {`Show ${Math.min(hidden, RECENT_MESSAGES)} earlier`}
              </Button>
              {hidden > RECENT_MESSAGES && (
                <Button
                  variant='ghost'
                  size='sm'
                  onClick={() => setEarlier(messages.length)}
                >
                  <ChevronsUp />
                  Show the whole conversation
                </Button>
              )}
            </li>
          )}
          {earlier > 0 && hidden === 0 && (
            <li className='flex min-w-0 justify-center'>
              <Button variant='ghost' size='sm' onClick={() => setEarlier(0)}>
                <ChevronDown />
                Show only the latest
              </Button>
            </li>
          )}
          {shown.map((message) => {
            const mine = message.sender_node_id !== son.id
            return (
              <Bubble
                key={message.id}
                mine={mine}
                author={mine ? 'You' : son.name}
                epoch={`Epoch ${message.epoch}`}
                text={message.text}
                name={son.name}
                cover={cover}
              />
            )
          })}
          {sent && (
            <>
              <Bubble
                mine
                author='You'
                epoch='now'
                text={sent}
                name={son.name}
                cover={cover}
                pending
              />
              <li
                aria-live='polite'
                className='flex min-w-0 items-center gap-2'
              >
                <Loader2
                  aria-hidden='true'
                  className='size-icon-sm animate-spin text-muted-foreground'
                />
                <Muted variant='caption'>{`${son.name} is thinking...`}</Muted>
              </li>
            </>
          )}
        </ul>
      )}
      <div ref={endRef} />
      {reply && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label>Last reply</Label>
          <Badge size='sm' variant={ATTITUDE_BADGE[reply.attitude]}>
            {ATTITUDE_LABEL[reply.attitude]}
          </Badge>
          <Badge
            size='sm'
            variant={
              reply.change > 0
                ? 'success'
                : reply.change < 0
                  ? 'destructive'
                  : 'outline'
            }
          >
            {`Loyalty ${reply.change > 0 ? '+' : reply.change < 0 ? '' : '±'}${reply.change} → ${reply.loyalty}`}
          </Badge>
        </div>
      )}
      {send.isError && <Text tone='destructive'>{send.error.message}</Text>}
      <div className='flex min-w-0 flex-col gap-2'>
        <FieldTile
          id={`chat-${son.id}`}
          label={`What do you say to ${son.name}?`}
        >
          <Textarea
            id={`chat-${son.id}`}
            value={draft}
            maxLength={maxChars}
            disabled={dead || send.isPending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault()
                submit()
              }
            }}
          />
        </FieldTile>
        <div className='flex min-w-0 flex-wrap items-center gap-3'>
          <ActionButton
            label={send.isPending ? 'Waiting' : 'Say'}
            icon={Send}
            variant='default'
            blocked={blocked}
            pending={send.isPending}
            onRun={submit}
          />
          <Muted variant='caption'>
            Enter sends, Shift+Enter starts a new line. The answer takes a few
            seconds.
          </Muted>
        </div>
      </div>
    </Section>
  )
}
