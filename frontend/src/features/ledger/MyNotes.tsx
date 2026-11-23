import { type ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  type LucideIcon,
  CalendarDays,
  Clock,
  ExternalLink,
  FileText,
  Globe2,
  Map as MapIcon,
  MapPin,
  NotebookPen,
  Plus,
  StickyNote,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { entityTypeValues } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  Medallion,
  MiniStat,
  Paged,
  Section,
} from '@/components/domain'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import {
  deleteEntityNote,
  useLoreMutation,
} from '@/features/entity/api/mutations'
import { useRemoveMapNote } from '@/features/map/api'
import { useAddNote, useNotifications } from '@/features/notifications/api'
import { useWorldState } from '@/features/overview/api'
import { ledgerKeys, type EntityNoteRecord, useNotes } from './api'

const NOTES_SHOWN = 50
const TITLE_LIMIT = 120

const dateTime = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function useMapNotes() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'map-notes'],
    queryFn: () => unwrap(api.GET('/api/map-notes')),
  })
}

function useSelfNotes() {
  return useNotifications({
    category: 'note',
    unreadOnly: false,
    limit: NOTES_SHOWN,
    before: null,
  })
}

function useWorldNames() {
  const state = useWorldState()
  return new Map(
    (state.data?.worlds ?? []).map((world) => [world.id, world.name])
  )
}

function NoteCard({
  icon,
  tone,
  title,
  body,
  badges,
  action,
}: {
  icon: LucideIcon
  tone: 'gold' | 'verdigris' | 'info'
  title: ReactNode
  body: string | null
  badges: ReactNode
  action?: ReactNode
}) {
  return (
    <li className='flex min-w-0 gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion icon={icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-start gap-2'>
          <div className='min-w-0 flex-1'>{title}</div>
          {action}
        </div>
        {body && (
          <Text variant='caption' truncate={4} className='whitespace-pre-line'>
            {body}
          </Text>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {badges}
        </div>
      </div>
    </li>
  )
}

function SelfNoteForm() {
  const add = useAddNote()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const empty = title.trim() === ''
  return (
    <form
      className='flex min-w-0 flex-col gap-2 rounded-md p-3 sealed-well'
      onSubmit={(event) => {
        event.preventDefault()
        if (empty) return
        add.mutate(
          { title: title.trim(), body: body.trim() || null },
          {
            onSuccess: () => {
              setTitle('')
              setBody('')
              toast.success('Note kept')
            },
            onError: (error) => toast.error(error.message),
          }
        )
      }}
    >
      <Input
        placeholder='A note to yourself'
        aria-label='Note title'
        maxLength={TITLE_LIMIT}
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />
      <Textarea
        placeholder='Details, if any'
        aria-label='Note body'
        value={body}
        onChange={(event) => setBody(event.target.value)}
      />
      <Button
        type='submit'
        size='sm'
        className='self-end'
        disabled={empty || add.isPending}
        disabledReason={empty ? 'Give the note a title first' : 'Saving'}
      >
        <Plus />
        Keep this note
      </Button>
    </form>
  )
}

function SelfNotes() {
  const notes = useSelfNotes()
  const items = notes.data?.items ?? []
  return (
    <Section
      id='notes-self'
      title={`Notes to yourself${notes.data ? ` · ${items.length}` : ''}`}
      description='Reminders you leave for later; they also appear among your notifications.'
      level={3}
    >
      <SelfNoteForm />
      {notes.isPending && <Skeleton className='h-24 w-full' />}
      {notes.isError && <Text tone='destructive'>{notes.error.message}</Text>}
      {notes.data && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={StickyNote}
          title='No notes to yourself'
          description='Write one above, or keep a chronicle line from its menu.'
        />
      )}
      {items.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
          <Paged items={items} as='li'>
            {(note) => (
              <NoteCard
                key={note.id}
                icon={StickyNote}
                tone='gold'
                title={
                  <Text weight='semibold' truncate={2}>
                    {note.title}
                  </Text>
                }
                body={note.body}
                badges={
                  <>
                    {note.epoch !== null && (
                      <Badge size='sm' variant='outline'>
                        <CalendarDays />
                        {`Epoch ${note.epoch}`}
                      </Badge>
                    )}
                    <Badge size='sm' variant='outline'>
                      <Clock />
                      {dateTime.format(new Date(note.created_at))}
                    </Badge>
                  </>
                }
              />
            )}
          </Paged>
        </ul>
      )}
    </Section>
  )
}

function RecordNotes() {
  const notes = useNotes()
  const worlds = useWorldNames()
  const [pending, setPending] = useState<EntityNoteRecord | null>(null)
  const remove = useLoreMutation({
    run: (note: EntityNoteRecord) => deleteEntityNote(note.entity_id),
    success: 'Note deleted',
    invalidate: [ledgerKeys.notes],
  })
  const items = notes.data?.entity_notes ?? []
  return (
    <Section
      id='notes-records'
      title={`Record notes${notes.data ? ` · ${items.length}` : ''}`}
      description='Your private notes on records; only you see them.'
      level={3}
    >
      {notes.isPending && <Skeleton className='h-24 w-full' />}
      {notes.isError && <Text tone='destructive'>{notes.error.message}</Text>}
      {notes.data && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={FileText}
          title='No record notes yet'
          description='Write a note on any record page and it is collected here.'
          action={
            <Button variant='outline' size='sm' asChild>
              <Link to='/atlas'>Open the atlas</Link>
            </Button>
          }
        />
      )}
      {items.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
          <Paged items={items} as='li'>
            {(note) => (
              <NoteCard
                key={note.entity_id}
                icon={ENTITY_TYPE_ICON[note.entity_type]}
                tone='verdigris'
                title={
                  <EntityLink kind='entity' id={String(note.entity_id)}>
                    {note.entity_name}
                  </EntityLink>
                }
                body={note.text}
                badges={
                  <>
                    <Badge size='sm' variant='outline'>
                      {wordOf(entityTypeValues, note.entity_type)}
                    </Badge>
                    <Badge size='sm' variant='outline'>
                      <Globe2 />
                      {worlds.get(note.world_id) ?? `World #${note.world_id}`}
                    </Badge>
                  </>
                }
                action={
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`Delete the note on ${note.entity_name}`}
                    onClick={() => setPending(note)}
                  >
                    <Trash2 />
                  </Button>
                }
              />
            )}
          </Paged>
        </ul>
      )}
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={`Delete the note on ${pending?.entity_name ?? 'this record'}?`}
        desc='Only your own note is removed. You can undo it right after.'
        destructive
        confirmText='Delete note'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (pending) remove.mutate(pending)
          setPending(null)
        }}
      />
    </Section>
  )
}

function MapNotes() {
  const notes = useMapNotes()
  const worlds = useWorldNames()
  const remove = useRemoveMapNote()
  const [pending, setPending] = useState<number | null>(null)
  const items = notes.data ?? []
  return (
    <Section
      id='notes-map'
      title={`Map notes${notes.data ? ` · ${items.length}` : ''}`}
      description='Pins you left on the map of a world.'
      level={3}
    >
      {notes.isPending && <Skeleton className='h-24 w-full' />}
      {notes.isError && <Text tone='destructive'>{notes.error.message}</Text>}
      {notes.data && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={MapPin}
          title='No map notes yet'
          description='Pin a note on the map and it stays there; every note is collected here.'
          action={
            <Button variant='outline' size='sm' asChild>
              <Link to='/map'>Open the map</Link>
            </Button>
          }
        />
      )}
      {items.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
          <Paged items={items} as='li'>
            {(note) => (
              <NoteCard
                key={note.id}
                icon={MapPin}
                tone='info'
                title={
                  <Text weight='semibold' truncate={2}>
                    {worlds.get(note.world_id) ?? `World #${note.world_id}`}
                  </Text>
                }
                body={note.text}
                badges={
                  <>
                    <Badge size='sm' variant='outline'>
                      <Clock />
                      {dateTime.format(new Date(note.created_at))}
                    </Badge>
                    <Button variant='link' size='sm' asChild>
                      <Link to='/map'>
                        <ExternalLink />
                        On the map
                      </Link>
                    </Button>
                  </>
                }
                action={
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label='Delete this map note'
                    onClick={() => setPending(note.id)}
                  >
                    <Trash2 />
                  </Button>
                }
              />
            )}
          </Paged>
        </ul>
      )}
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title='Delete this map note?'
        desc='The pin is taken off the map.'
        destructive
        confirmText='Delete note'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (pending !== null)
            remove.mutate(pending, {
              onError: (error) => toast.error(error.message),
            })
          setPending(null)
        }}
      />
    </Section>
  )
}

export function MyNotes() {
  const records = useNotes()
  const self = useSelfNotes()
  const map = useMapNotes()
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={StickyNote}
          label='Notes to yourself'
          value={self.data?.items.length ?? 0}
          tone='gold'
        />
        <MiniStat
          icon={NotebookPen}
          label='Record notes'
          value={records.data?.entity_notes.length ?? 0}
          tone='verdigris'
        />
        <MiniStat
          icon={MapIcon}
          label='Map notes'
          value={map.data?.length ?? 0}
          tone='info'
        />
      </div>
      <SelfNotes />
      <RecordNotes />
      <MapNotes />
    </div>
  )
}
