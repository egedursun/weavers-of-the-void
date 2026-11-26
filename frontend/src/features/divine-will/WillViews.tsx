import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  ArrowLeft,
  ChevronUp,
  CircleAlert,
  History,
  LibraryBig,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Medallion, Paged } from '@/components/domain'
import { DivineCrest } from '@/components/layout/divine-will/DivineCrest'
import { Label, Muted, Text } from '@/components/typography'
import { ModelNeeded } from '@/features/providers/ModelNeeded'
import { ShareToggle } from '@/features/team/share'
import { Composer } from './Composer'
import { IndexNotice } from './IndexNotice'
import { CycleList } from './Transcript'
import {
  usePastSession,
  useWillCycle,
  useWillSession,
  useWillSessions,
} from './api'
import { ArtifactBrowser } from './library/ArtifactBrowser'
import { ArtifactDetail } from './library/ArtifactDetail'
import { MODE_LOOK, MODE_ORDER } from './modes'
import {
  type WillActive,
  type WillCycle,
  type WillSessionSummary,
  type WillSessionView,
} from './types'
import { useWill } from './willStore'

const NEAR_BOTTOM_PX = 96
const SESSIONS_SHOWN = 10

function useStickToBottom(dependency: unknown) {
  const ref = useRef<HTMLDivElement>(null)
  const stuck = useRef(true)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const onScroll = () => {
      stuck.current =
        element.scrollHeight - element.scrollTop - element.clientHeight <
        NEAR_BOTTOM_PX
    }
    element.addEventListener('scroll', onScroll, { passive: true })
    return () => element.removeEventListener('scroll', onScroll)
  }, [])
  useLayoutEffect(() => {
    const element = ref.current
    if (element && stuck.current) element.scrollTop = element.scrollHeight
  }, [dependency])
  return ref
}

function Welcome() {
  const setMode = useWill((state) => state.setMode)
  const mode = useWill((state) => state.mode)
  return (
    <div
      data-domain='will-welcome'
      className='flex min-w-0 flex-col items-center gap-4 py-4 text-center'
    >
      <DivineCrest size='md' />
      <div className='flex max-w-md min-w-0 flex-col gap-1'>
        <Text weight='semibold' className='text-gilded font-display'>
          Your will, put into words
        </Text>
        <Muted>
          The Divine Will is your own hand on the world. Choose how it should
          work, then say what you wish. Every word and act is kept in the
          record.
        </Muted>
      </div>
      <div className='grid w-full min-w-0 grid-cols-1 gap-2 @md/will:grid-cols-2'>
        {MODE_ORDER.map((item) => {
          const look = MODE_LOOK[item]
          return (
            <Button
              key={item}
              variant='outline'
              size='tile'
              aria-pressed={mode === item}
              onClick={() => setMode(item)}
            >
              <Medallion icon={look.icon} tone={look.tone} size='sm' />
              <span className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='semibold'>
                  {look.label}
                </Text>
                <Muted as='span' variant='caption'>
                  {look.caption}
                </Muted>
              </span>
            </Button>
          )
        })}
      </div>
    </div>
  )
}

function useLatestCycles(pages: WillActive[]) {
  const ordered = useMemo(
    () => [...pages].reverse().flatMap((page) => page.cycles),
    [pages]
  )
  const active = [...ordered]
    .reverse()
    .find(
      (cycle) =>
        cycle.status === 'running' || cycle.status === 'awaiting_confirmation'
    )
  const fresh = useWillCycle(active?.id ?? null)
  const cycles: WillCycle[] = useMemo(
    () =>
      ordered.map((cycle) =>
        fresh.data && cycle.id === fresh.data.id ? fresh.data : cycle
      ),
    [ordered, fresh.data]
  )
  return cycles
}

export function ChatView() {
  const session = useWillSession()
  const live = useWill((state) => state.live)
  const pages = useMemo(() => session.data?.pages ?? [], [session.data])
  const head = pages[0] ?? null
  const cycles = useLatestCycles(pages)
  const running = cycles.find((cycle) => cycle.status === 'running') ?? null
  const awaiting = cycles.some(
    (cycle) => cycle.status === 'awaiting_confirmation'
  )
  const liveSize = Object.values(live).reduce(
    (sum, item) => sum + item.text.length + item.tools.length,
    0
  )
  const scroller = useStickToBottom(
    `${String(cycles.length)}:${String(liveSize)}:${cycles.at(-1)?.events.length ?? 0}`
  )

  return (
    <>
      <div
        ref={scroller}
        role='log'
        aria-label='Exchanges with the Divine Will'
        aria-busy={running !== null}
        className='flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto px-4 py-4'
      >
        <IndexNotice />
        {session.isPending ? (
          <LoadingBlock label='Opening the session' />
        ) : session.isError ? (
          <EmptyState
            icon={CircleAlert}
            title='The Divine Will cannot be reached'
            description={session.error.message}
            action={
              <Button
                variant='outline'
                size='sm'
                onClick={() => void session.refetch()}
              >
                <RefreshCw />
                Try again
              </Button>
            }
          />
        ) : cycles.length === 0 ? (
          <Welcome />
        ) : (
          <>
            {session.hasNextPage && (
              <Button
                variant='ghost'
                size='sm'
                className='self-center'
                disabled={session.isFetchingNextPage}
                disabledReason='Loading earlier exchanges.'
                onClick={() => void session.fetchNextPage()}
              >
                {session.isFetchingNextPage ? (
                  <Loader2 className='animate-spin' />
                ) : (
                  <ChevronUp />
                )}
                Show earlier exchanges
              </Button>
            )}
            <CycleList cycles={cycles} boundary={head?.memory_boundary ?? 0} />
          </>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2 border-t bg-linear-to-t from-primary/6 to-transparent px-4 py-3'>
        <ModelNeeded role='conversation' what='The Divine Will' />
        <Composer
          capabilities={head?.capabilities ?? null}
          runningCycleId={running?.id ?? null}
          awaiting={awaiting}
        />
      </div>
    </>
  )
}

function PastSession({ id, onBack }: { id: number; onBack: () => void }) {
  const session = usePastSession(id)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Button variant='ghost' size='sm' className='w-fit' onClick={onBack}>
        <ArrowLeft />
        Every past session
      </Button>
      {session.isPending ? (
        <LoadingBlock label='Opening the session' />
      ) : session.isError ? (
        <EmptyState
          size='compact'
          icon={CircleAlert}
          title='The session could not be opened'
          description={session.error.message}
          action={
            <Button
              variant='outline'
              size='sm'
              onClick={() => void session.refetch()}
            >
              <RefreshCw />
              Try again
            </Button>
          }
        />
      ) : (
        <PastTranscript view={session.data} />
      )}
    </div>
  )
}

function PastTranscript({ view }: { view: WillSessionView }) {
  const summary = view.session
  return (
    <>
      <div className='flex min-w-0 flex-col gap-1 rounded-md surface-sheen px-3 py-2.5'>
        <Text weight='semibold' className='text-gilded font-display'>
          {summary.title || `Session of epoch ${String(summary.opened_epoch)}`}
        </Text>
        <Muted variant='caption'>
          {[
            `Opened in epoch ${String(summary.opened_epoch)}, ${formatDateTime(summary.opened_at)}`,
            summary.closed_at
              ? `closed in epoch ${String(summary.closed_epoch ?? summary.opened_epoch)}, ${formatDateTime(summary.closed_at)}`
              : '',
            plural(summary.cycle_count, 'exchange'),
          ]
            .filter(Boolean)
            .join(' · ')}
        </Muted>
        {summary.closed_at && (
          <Muted variant='caption'>
            You began anew here, so the Divine Will no longer keeps this session
            in mind. Every exchange stays readable here, in the lore book and in
            the Codex.
          </Muted>
        )}
      </div>
      {view.cycles.length === 0 ? (
        <Muted variant='caption'>
          This session closed before any exchange.
        </Muted>
      ) : (
        <CycleList
          cycles={view.cycles}
          boundary={summary.closed_at ? 0 : view.memory_boundary}
        />
      )}
      {view.has_earlier && (
        <Muted variant='caption'>
          Earlier exchanges of this session are kept in the lore book.
        </Muted>
      )}
    </>
  )
}

type SessionItem = WillSessionSummary

function SessionGroup({
  title,
  items,
  empty,
  onOpen,
}: {
  title: string
  items: SessionItem[]
  empty: string
  onOpen: (id: number) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{title}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged
            items={items}
            initial={SESSIONS_SHOWN}
            as='li'
            noun={['session', 'sessions']}
          >
            {(item) => (
              <li
                key={item.id}
                className='flex min-w-0 items-center gap-1 rounded-md border surface-framed border-gild/60 bg-card p-1'
              >
                <Button
                  variant='ghost'
                  size='tile'
                  className='flex-1'
                  onClick={() => onOpen(item.id)}
                >
                  <History />
                  <span className='flex min-w-0 flex-1 flex-col'>
                    <Text as='span' weight='semibold' truncate>
                      {item.title ||
                        `Session of epoch ${String(item.opened_epoch)}`}
                    </Text>
                    <Muted as='span' variant='caption' truncate={2}>
                      {[
                        `Epoch ${String(item.opened_epoch)} to ${String(item.closed_epoch ?? item.opened_epoch)}`,
                        formatDateTime(item.opened_at),
                        item.closed_at
                          ? `closed ${formatDateTime(item.closed_at)}`
                          : '',
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </Muted>
                  </span>
                  <Badge size='sm' variant='outline'>
                    {plural(item.cycle_count, 'exchange')}
                  </Badge>
                </Button>
                <ShareToggle
                  kind='session'
                  id={item.id}
                  shared={item.shared}
                  mine={item.mine}
                  author={item.author?.name}
                  inline
                />
              </li>
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

export function PastSessionsView() {
  const sessions = useWillSessions()
  const [open, setOpen] = useState<number | null>(null)
  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4'>
      {open !== null ? (
        <PastSession id={open} onBack={() => setOpen(null)} />
      ) : sessions.isPending ? (
        <LoadingBlock label='Loading past sessions' />
      ) : sessions.isError ? (
        <EmptyState
          size='compact'
          icon={CircleAlert}
          title='Past sessions could not be loaded'
          description={sessions.error.message}
          action={
            <Button
              variant='outline'
              size='sm'
              onClick={() => void sessions.refetch()}
            >
              <RefreshCw />
              Try again
            </Button>
          }
        />
      ) : sessions.data.sessions.length === 0 ? (
        <EmptyState
          size='compact'
          icon={History}
          title='No past session'
          description='When you begin a new session, the one you close is kept here with every exchange.'
        />
      ) : (
        <>
          <SessionGroup
            title='Your sessions'
            items={sessions.data.sessions.filter((item) => item.mine)}
            empty='When you begin a new session, the one you close is kept here with every exchange.'
            onOpen={setOpen}
          />
          <SessionGroup
            title='Shared with the team'
            items={sessions.data.sessions.filter((item) => !item.mine)}
            empty='Sessions others share with the team show here, to read.'
            onOpen={setOpen}
          />
        </>
      )}
    </div>
  )
}

function LibraryLink({ artifact }: { artifact: number | null }) {
  return (
    <Button variant='outline' size='sm' asChild>
      <Link to='/library' search={artifact === null ? {} : { artifact }}>
        <LibraryBig />
        Open the Library
      </Link>
    </Button>
  )
}

export function WritingsView() {
  const [selected, setSelected] = useState<number | null>(null)
  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4'>
      {selected !== null && (
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <Button variant='ghost' size='sm' onClick={() => setSelected(null)}>
            <ArrowLeft />
            Every writing
          </Button>
          <LibraryLink artifact={selected} />
        </div>
      )}
      {selected === null ? (
        <ArtifactBrowser
          selected={null}
          onSelect={setSelected}
          compact
          actions={<LibraryLink artifact={null} />}
        />
      ) : (
        <ArtifactDetail
          key={selected}
          artifactId={selected}
          compact
          onDeleted={() => setSelected(null)}
        />
      )}
    </div>
  )
}
