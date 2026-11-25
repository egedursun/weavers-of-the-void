import { useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { Brain, CircleAlert, MessagesSquare, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  RuleInfo,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ExchangeList } from './AudienceTranscript'
import { BeginAnewButton } from './BeginAnewButton'
import { DeadSeal } from './DeadSeal'
import { PresenceComposer } from './PresenceComposer'
import { useSession } from './api'
import { GUISE_LOOK, RECORD_LOOK, audienceSpeaker, deathText } from './looks'
import { usePresence } from './presenceStore'
import {
  type PresenceSessionSummary,
  type PresenceSessionView,
  type SpeakerCard,
} from './types'

const NEAR_BOTTOM_PX = 96
const PERCENT = 100
const MEMORY_RULE = 'presence.remembered_exchanges'

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

export function SessionBadges({
  session,
}: {
  session: PresenceSessionSummary
}) {
  const guise = GUISE_LOOK[session.guise]
  const record = RECORD_LOOK[session.record]
  const GuiseIcon = guise.icon
  const RecordIcon = record.icon
  return (
    <>
      <Badge size='sm' variant='secondary'>
        <GuiseIcon />
        {`As ${guise.label}`}
      </Badge>
      <Badge
        size='sm'
        variant={session.record === 'on_record' ? 'default' : 'outline'}
      >
        <RecordIcon />
        {record.label}
      </Badge>
    </>
  )
}

function MemoryMeter({
  view,
  name,
}: {
  view: PresenceSessionView
  name: string
}) {
  const limit = view.remembered_exchanges
  const kept = view.exchanges.filter(
    (exchange) =>
      exchange.ordinal >= view.memory_boundary && exchange.status === 'done'
  ).length
  const shown = Math.min(kept, limit)
  return (
    <div
      data-domain='presence-memory-meter'
      className='flex min-w-0 items-center gap-1.5'
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            tabIndex={0}
            aria-label={`${String(shown)} of ${String(limit)} exchanges in mind`}
            className='flex min-w-0 flex-1 flex-col gap-1 rounded-md surface-well px-2 py-1'
          >
            <div className='flex min-w-0 items-center gap-1.5'>
              <Brain
                aria-hidden='true'
                className='size-icon-xs shrink-0 text-primary'
              />
              <Text
                as='span'
                variant='caption'
                weight='medium'
                className='tabular-nums'
              >
                {`${String(shown)} / ${String(limit)}`}
              </Text>
              <Muted as='span' variant='caption' truncate>
                exchanges in mind
              </Muted>
            </div>
            <Progress
              size='sm'
              value={limit > 0 ? (shown / limit) * PERCENT : 0}
              aria-hidden='true'
            />
          </div>
        </TooltipTrigger>
        <TooltipContent className='max-w-xs'>
          {`${name} keeps the last finished exchanges of this audience in mind, up to the world rule. Older ones stay on this page above the line but no longer reach its thoughts.`}
        </TooltipContent>
      </Tooltip>
      <RuleInfo
        rule={MEMORY_RULE}
        label='How many exchanges it keeps in mind'
      />
    </div>
  )
}

function Opening({
  speaker,
  session,
}: {
  speaker: SpeakerCard
  session: PresenceSessionSummary
}) {
  const guise = GUISE_LOOK[session.guise]
  return (
    <div
      data-domain='presence-opening'
      className='flex min-w-0 flex-col items-center gap-3 py-4 text-center'
    >
      <Medallion icon={guise.icon} tone={guise.tone} />
      <div className='flex max-w-md min-w-0 flex-col gap-1'>
        <Text weight='semibold' className='text-gilded font-display'>
          {`${speaker.name} is before you`}
        </Text>
        <Muted>{`${guise.heard} ${RECORD_LOOK[session.record].line} Say the first word.`}</Muted>
      </div>
    </div>
  )
}

export function AudiencePanel({
  speaker,
  session,
  modelEnabled,
}: {
  speaker: SpeakerCard
  session: PresenceSessionSummary
  modelEnabled: boolean
}) {
  const pending = usePresence((state) => state.live)
  const endLive = usePresence((state) => state.endLive)
  const view = useSession(session.id)
  const exchanges = useMemo(() => view.data?.exchanges ?? [], [view.data])
  const runningId = view.data?.running_exchange_id ?? null
  const running =
    exchanges.find(
      (exchange) => exchange.id === runningId || exchange.status === 'running'
    ) ?? null
  useEffect(() => {
    for (const exchange of exchanges)
      if (exchange.status !== 'running' && pending[exchange.id])
        endLive(exchange.id)
  }, [exchanges, pending, endLive])
  const liveSize = Object.values(pending).reduce(
    (sum, item) => sum + item.text.length + item.calls.length,
    0
  )
  const scroller = useStickToBottom(
    `${String(exchanges.length)}:${String(liveSize)}:${String(exchanges.at(-1)?.events.length ?? 0)}`
  )
  return (
    <Section
      id='presence-audience'
      title={`Audience with ${speaker.name}`}
      icon={MessagesSquare}
      actions={
        <>
          <SessionBadges session={session} />
          {session.dead_when_summoned && (
            <DeadSeal size='sm' death={deathText(speaker)} />
          )}
          <BeginAnewButton
            session={session}
            name={speaker.name}
            busy={running !== null}
          />
        </>
      }
    >
      {view.data && <MemoryMeter view={view.data} name={speaker.name} />}
      <div
        ref={scroller}
        role='log'
        aria-label={`Exchanges with ${speaker.name}`}
        aria-busy={running !== null}
        className='flex max-h-160 min-h-0 min-w-0 flex-col gap-5 overflow-y-auto'
      >
        {view.isPending ? (
          <LoadingBlock label='Opening the audience' />
        ) : view.isError ? (
          <EmptyState
            size='compact'
            icon={CircleAlert}
            title='The audience could not be opened'
            description={view.error.message}
            action={
              <Button
                variant='outline'
                size='sm'
                onClick={() => void view.refetch()}
              >
                <RefreshCw />
                Try again
              </Button>
            }
          />
        ) : exchanges.length === 0 ? (
          <Opening speaker={speaker} session={session} />
        ) : (
          <ExchangeList
            exchanges={exchanges}
            boundary={view.data.memory_boundary}
            speaker={audienceSpeaker(speaker)}
            session={view.data.session}
          />
        )}
      </div>
      <PresenceComposer
        sessionId={session.id}
        nodeId={speaker.node_id}
        name={speaker.name}
        runningId={running?.id ?? null}
        modelEnabled={modelEnabled}
      />
    </Section>
  )
}
