import { useEffect, useId, useMemo, useState } from 'react'
import {
  ChevronDown,
  CircleAlert,
  Loader2,
  MessagesSquare,
  RefreshCw,
  Search,
  SearchX,
  Skull,
  UsersRound,
} from 'lucide-react'
import { nodeKindValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { EmptyState, LoadingBlock, Portrait } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { useLabels } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { type SpeakerFilters, useSpeakers } from './api'
import { GROUP_LOOK, GROUP_ORDER } from './looks'
import { type SpeakerGroup, type SpeakerSummary } from './types'

const SEARCH_DEBOUNCE_MS = 220
const EVERY_GROUP = 'every'

function useDebounced(value: string): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(
      () => setDebounced(value),
      SEARCH_DEBOUNCE_MS
    )
    return () => window.clearTimeout(handle)
  }, [value])
  return debounced
}

function groupOf(value: string): SpeakerGroup | null {
  return GROUP_ORDER.find((group) => group === value) ?? null
}

function SpeakerRow({
  speaker,
  selected,
  onSelect,
}: {
  speaker: SpeakerSummary
  selected: boolean
  onSelect: () => void
}) {
  const { entityType } = useLabels()
  const group = GROUP_LOOK[speaker.group]
  const GroupIcon = group.icon
  const kindLabel = speaker.entity_type
    ? entityType(speaker.entity_type)
    : wordOf(nodeKindValues, speaker.kind)
  return (
    <li>
      <Button
        variant='outline'
        size='tile'
        aria-pressed={selected}
        aria-label={`${speaker.name}, ${group.label}${speaker.dead ? ', dead' : ''}`}
        onClick={onSelect}
        className={cn(selected && 'border-primary bg-accent')}
      >
        <Portrait name={speaker.name} src={mediaUrl(speaker.cover)} size='md' />
        <span className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {speaker.dead ? `† ${speaker.name}` : speaker.name}
          </Text>
          <Muted
            as='span'
            variant='caption'
            className='flex min-w-0 items-center gap-1'
          >
            <GroupIcon aria-hidden='true' className='size-icon-xs shrink-0' />
            <span className='min-w-0 truncate'>{kindLabel}</span>
          </Muted>
        </span>
        <span className='flex shrink-0 flex-col items-end gap-1'>
          {speaker.dead && (
            <Badge size='sm' variant='destructive'>
              <Skull />
              Dead
            </Badge>
          )}
          {speaker.open_session_id !== null && (
            <Badge size='sm' variant='default'>
              <MessagesSquare />
              In audience
            </Badge>
          )}
        </span>
      </Button>
    </li>
  )
}

export function SpeakerRail({
  selected,
  onSelect,
}: {
  selected: number | null
  onSelect: (nodeId: number) => void
}) {
  const [text, setText] = useState('')
  const [group, setGroup] = useState<SpeakerGroup | null>(null)
  const [dead, setDead] = useState(false)
  const deadId = useId()
  const q = useDebounced(text)
  const filters: SpeakerFilters = useMemo(
    () => ({ q, group, dead }),
    [q, group, dead]
  )
  const query = useSpeakers(filters)
  const pages = query.data?.pages ?? []
  const shown = pages.flatMap((page) => page.speakers)
  const total = pages[0]?.total ?? 0
  const narrowed = text.trim() !== '' || group !== null
  return (
    <div data-domain='presence-rail' className='flex min-w-0 flex-col gap-3'>
      <Input
        type='search'
        leadingIcon={Search}
        value={text}
        placeholder='Search by name'
        aria-label='Search those who can be summoned'
        onChange={(event) => setText(event.target.value)}
      />
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        aria-label='Which kind of speaker'
        value={group ?? EVERY_GROUP}
        onValueChange={(value) => {
          if (value) setGroup(groupOf(value))
        }}
      >
        <ToggleGroupItem value={EVERY_GROUP} aria-label='Every kind'>
          <UsersRound />
          All
        </ToggleGroupItem>
        {GROUP_ORDER.map((item) => {
          const look = GROUP_LOOK[item]
          const Icon = look.icon
          return (
            <ToggleGroupItem key={item} value={item} aria-label={look.label}>
              <Icon />
              {look.label}
            </ToggleGroupItem>
          )
        })}
      </ToggleGroup>
      <div className='flex min-w-0 items-center justify-between gap-3 rounded-md surface-well px-3 py-2'>
        <div className='flex min-w-0 flex-col'>
          <FieldLabel htmlFor={deadId}>Include the dead</FieldLabel>
          <Muted variant='caption'>
            The dead can be summoned back to speak.
          </Muted>
        </div>
        <Switch id={deadId} checked={dead} onCheckedChange={setDead} />
      </div>
      <Muted as='span' variant='caption' role='status'>
        {query.isPending
          ? 'Looking for those who can speak…'
          : total === 1
            ? 'One can be summoned'
            : `${plural(total, 'speaker')} can be summoned`}
      </Muted>
      {query.isPending ? (
        <LoadingBlock label='Loading those who can be summoned' />
      ) : query.isError ? (
        <EmptyState
          size='compact'
          icon={CircleAlert}
          title='The speakers could not be loaded'
          description={query.error.message}
          action={
            <Button
              variant='outline'
              size='sm'
              onClick={() => void query.refetch()}
            >
              <RefreshCw />
              Try again
            </Button>
          }
        />
      ) : total === 0 ? (
        narrowed ? (
          <EmptyState
            size='compact'
            icon={SearchX}
            title='Nobody matches'
            description={
              dead
                ? 'No one living or dead fits this search. Loosen it or choose every kind.'
                : 'No living one fits this search. Loosen it, choose every kind or include the dead.'
            }
          />
        ) : (
          <EmptyState
            size='compact'
            icon={UsersRound}
            title='No one can speak yet'
            description='Sons, foreign gods, mortals, spirits, beings and minded beasts appear here once the world holds them.'
          />
        )
      ) : (
        <>
          <ul
            aria-label='Those who can be summoned'
            className='flex min-w-0 flex-col gap-1.5'
          >
            {shown.map((speaker) => (
              <SpeakerRow
                key={speaker.node_id}
                speaker={speaker}
                selected={speaker.node_id === selected}
                onSelect={() => onSelect(speaker.node_id)}
              />
            ))}
          </ul>
          {total > shown.length && (
            <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-md px-3 py-1.5 sealed-well'>
              <Muted as='span' variant='caption'>
                {`Showing ${formatInteger(shown.length)} of ${formatInteger(total)}`}
              </Muted>
              <Button
                variant='ghost'
                size='sm'
                disabled={query.isFetchingNextPage}
                disabledReason='Loading more speakers.'
                onClick={() => void query.fetchNextPage()}
              >
                {query.isFetchingNextPage ? (
                  <Loader2 className='animate-spin' />
                ) : (
                  <ChevronDown />
                )}
                Show more
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
