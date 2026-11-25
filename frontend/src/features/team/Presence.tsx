import { useEffect, useRef } from 'react'
import { useLocation, useSearch } from '@tanstack/react-router'
import { Eye, PencilLine } from 'lucide-react'
import { useEditing } from '@/api/editSession'
import { formatDateTime, formatSince } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Paged } from '@/components/domain'
import {
  type EntrySearch,
  parseEntryStack,
} from '@/components/layout/entry/entryStack'
import { screenTitle } from '@/components/layout/screenTitle'
import { Label, Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { useNodeIndex } from '@/features/feed/nodes'
import { useLeavePresence, useMarkPresence, useNodeRevision } from './api'
import { useTeamContext } from './teamContext'
import { personTone } from './teamLook'
import { type PresentView } from './types'

const DEFAULT_TTL = 90
const DEFAULT_HEARTBEAT = 30
const SECOND_MS = 1000
const FACES_SHOWN = 4
const SOMEWHERE = 'somewhere in the universe'

function entryNode(search: EntrySearch): number | null {
  const top = parseEntryStack(search.entry).at(-1)
  const id = top?.id === undefined ? Number.NaN : Number(top.id)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function PresenceBeacon() {
  const screen = useLocation({ select: (location) => location.pathname })
  const search = useSearch({ strict: false }) as EntrySearch
  const node = entryNode(search)
  const editing = useEditing()
  const team = useTeamContext()
  const every = (team?.team?.heartbeat_seconds ?? DEFAULT_HEARTBEAT) * SECOND_MS
  const mark = useMarkPresence()
  const leave = useLeavePresence()
  const send = useRef(mark.mutate)
  const part = useRef(leave.mutate)
  useEffect(() => {
    send.current = mark.mutate
    part.current = leave.mutate
  })
  useEffect(() => {
    const beat = () =>
      send.current({ screen, node_id: node, editing: editing && node !== null })
    beat()
    const timer = setInterval(beat, every)
    return () => clearInterval(timer)
  }, [screen, node, editing, every])
  useEffect(() => {
    const away = () => part.current()
    window.addEventListener('pagehide', away)
    return () => {
      window.removeEventListener('pagehide', away)
      away()
    }
  }, [])
  return null
}

const NOW_SECONDS = 45

export function seenText(person: PresentView): string {
  const seconds = Math.round(person.seen_seconds_ago)
  return seconds < NOW_SECONDS ? 'here now' : `seen ${seconds} s ago`
}

function placeOf(person: PresentView, names: ReturnType<typeof useNodeIndex>) {
  const where = screenTitle(person.screen) ?? SOMEWHERE
  const node = person.node_id === null ? null : names.get(person.node_id)
  const doing = node
    ? `${person.editing ? 'Editing' : 'Reading'} ${node.name}`
    : `On ${where}`
  return `${doing} · ${seenText(person)}`
}

function others(
  present: readonly PresentView[],
  me: number | null,
  ttl: number
) {
  return present.filter(
    (person) => person.account_id !== me && person.seen_seconds_ago <= ttl
  )
}

function Face({ person, place }: { person: PresentView; place: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          className={cn(
            'relative inline-flex rounded-full ring-2 ring-background',
            person.editing && 'ring-warning'
          )}
        >
          <AccountAvatar
            name={person.name}
            tone={personTone(person.name)}
            size='xs'
          />
        </span>
      </TooltipTrigger>
      <TooltipContent>{`${person.name} · ${place}`}</TooltipContent>
    </Tooltip>
  )
}

function PersonLine({ person, place }: { person: PresentView; place: string }) {
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-md surface-sheen p-2'>
      <AccountAvatar
        name={person.name}
        tone={personTone(person.name)}
        size='sm'
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='semibold' truncate>
          {person.name}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {place}
        </Muted>
      </span>
      {person.editing && (
        <Badge variant='warning' size='sm'>
          <PencilLine />
          Editing
        </Badge>
      )}
    </li>
  )
}

export function PresentFaces() {
  const team = useTeamContext()
  const names = useNodeIndex()
  const present = others(
    team?.team?.present ?? [],
    team?.me ?? null,
    team?.team?.presence_ttl_seconds ?? DEFAULT_TTL
  )
  if (present.length === 0) return null
  const shown = present.slice(0, FACES_SHOWN)
  const more = present.length - shown.length
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type='button'
          variant='ghost'
          size='sm'
          aria-label={`Here now: ${present.map((person) => person.name).join(', ')}`}
        >
          <span className='flex items-center gap-0.5'>
            {shown.map((person, index) => (
              <span
                key={person.account_id}
                className={cn('inline-flex', index > 0 && 'max-sm:hidden')}
              >
                <AccountAvatar
                  name={person.name}
                  tone={personTone(person.name)}
                  size='xs'
                />
              </span>
            ))}
          </span>
          {present.length > 1 && (
            <Text
              as='span'
              variant='caption'
              weight='semibold'
              className='sm:hidden'
            >
              {`+${present.length - 1}`}
            </Text>
          )}
          {more > 0 && (
            <Text
              as='span'
              variant='caption'
              weight='semibold'
              className='max-sm:hidden'
            >
              {`+${more}`}
            </Text>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align='end' className='w-80'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='gilded'>Here now</Label>
          <ul
            aria-label='People here now'
            className='flex min-w-0 flex-col gap-1.5'
          >
            <Paged items={present} as='li' noun={['person', 'people']}>
              {(person) => (
                <PersonLine
                  key={person.account_id}
                  person={person}
                  place={placeOf(person, names)}
                />
              )}
            </Paged>
          </ul>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function LastChange({ nodeId }: { nodeId: number }) {
  const revision = useNodeRevision(nodeId)
  const data = revision.data
  if (!data || data.revision === 0 || !data.changed_by) return null
  return (
    <Muted
      as='span'
      variant='caption'
      className='max-md:sr-only'
      title={data.changed_at ? formatDateTime(data.changed_at) : undefined}
    >
      {`Last changed by ${data.changed_by}${data.changed_at ? ` ${formatSince(data.changed_at)}` : ''}`}
    </Muted>
  )
}

export function EntryActivity({ nodeId }: { nodeId: number | null }) {
  if (nodeId === null) return null
  return (
    <span className='flex shrink-0 items-center gap-2'>
      <LastChange nodeId={nodeId} />
      <EntryViewers nodeId={nodeId} />
    </span>
  )
}

function EntryViewers({ nodeId }: { nodeId: number | null }) {
  const team = useTeamContext()
  const names = useNodeIndex()
  if (nodeId === null) return null
  const here = others(
    team?.team?.present ?? [],
    team?.me ?? null,
    team?.team?.presence_ttl_seconds ?? DEFAULT_TTL
  ).filter((person) => person.node_id === nodeId)
  if (here.length === 0) return null
  const editing = here.filter((person) => person.editing)
  return (
    <div
      role='status'
      aria-label='Others in this entry'
      className='flex shrink-0 items-center gap-1.5'
    >
      <span className='flex items-center gap-0.5'>
        {here.slice(0, FACES_SHOWN).map((person) => (
          <Face
            key={person.account_id}
            person={person}
            place={placeOf(person, names)}
          />
        ))}
      </span>
      <Badge
        variant={editing.length > 0 ? 'warning' : 'secondary'}
        size='sm'
        className='max-sm:sr-only'
      >
        {editing.length > 0 ? <PencilLine /> : <Eye />}
        {editing.length > 0
          ? `${editing[0].name}${editing.length > 1 ? ` and ${editing.length - 1} more` : ''} editing`
          : `${here.map((person) => person.name).join(', ')} reading`}
      </Badge>
    </div>
  )
}
