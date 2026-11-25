import { Fragment } from 'react'
import {
  CircleSlash,
  Hourglass,
  Infinity as Boundless,
  Loader2,
} from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { CopyButton, ShowMore, useShowMore } from '@/components/domain'
import { DivineCrest } from '@/components/layout/divine-will/DivineCrest'
import { Muted, Text } from '@/components/typography'
import { ArtifactLink, AttachmentChip } from './AttachmentView'
import { ConfirmationCard } from './ConfirmationCard'
import { ForecastCard } from './ForecastCard'
import { PlanCard } from './PlanCard'
import {
  ErrorCard,
  LiveToolCard,
  NoticeCard,
  RetryCard,
  SuggestModeCard,
  ThoughtGroup,
  ToolCallCard,
} from './TraceCards'
import { WillMarkdown } from './WillMarkdown'
import { MODE_LOOK } from './modes'
import { type TraceItem, isActive, traceOf } from './traceModel'
import { type WillCycle } from './types'
import { type LiveCycle, useWill } from './willStore'

function TraceView({ item }: { item: TraceItem }) {
  switch (item.type) {
    case 'thoughts':
      return <ThoughtGroup texts={item.texts} />
    case 'text':
      return (
        <div className='flex min-w-0 items-start gap-2'>
          <div className='flex min-w-0 flex-1 flex-col'>
            <WillMarkdown text={item.text} />
          </div>
          <CopyButton text={item.text} label='Copy these words' />
        </div>
      )
    case 'tool':
      return <ToolCallCard trace={item.trace} />
    case 'confirmation':
      return (
        <ConfirmationCard confirmation={item.confirmation} reply={item.reply} />
      )
    case 'plan':
      return <PlanCard planId={item.planId} />
    case 'forecast':
      return <ForecastCard forecastId={item.forecastId} />
    case 'artifact':
      return (
        <ArtifactLink artifactId={item.artifactId} version={item.version} />
      )
    case 'suggest':
      return <SuggestModeCard mode={item.mode} reason={item.reason} />
    case 'notice':
      return <NoticeCard text={item.text} vision={item.vision} />
    case 'retry':
      return (
        <RetryCard
          attempt={item.attempt}
          total={item.total}
          reason={item.reason}
          waitSeconds={item.waitSeconds}
        />
      )
    case 'error':
      return <ErrorCard text={item.text} />
    case 'live-tool':
      return <LiveToolCard tool={item.tool} />
    case 'streaming':
      return (
        <div
          aria-live='polite'
          aria-atomic='false'
          data-domain='will-streaming'
        >
          <WillMarkdown text={item.text} />
          <span aria-hidden='true' className='will-caret' />
        </div>
      )
  }
}

function PlayerTurn({ cycle }: { cycle: WillCycle }) {
  const look = MODE_LOOK[cycle.mode]
  const Icon = look.icon
  return (
    <div className='flex min-w-0 justify-end ps-8'>
      <div
        data-domain='will-player'
        className='flex min-w-0 flex-col gap-1.5 rounded-lg rounded-br-sm surface-framed px-3 py-2'
      >
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='outline'>
            <Icon />
            {look.label}
          </Badge>
          <Muted as='span' variant='caption'>
            {`Epoch ${String(cycle.epoch)} · ${formatDateTime(cycle.started_at)}`}
          </Muted>
          <span aria-hidden='true' className='flex-1' />
          <CopyButton text={cycle.player_text} label='Copy your words' />
        </div>
        <Text className='whitespace-pre-wrap'>{cycle.player_text}</Text>
        {cycle.attachments.length > 0 && (
          <AttachmentChips attachments={cycle.attachments} />
        )}
      </div>
    </div>
  )
}

function CycleFooter({ cycle }: { cycle: WillCycle }) {
  const tokens = cycle.input_tokens + cycle.output_tokens
  const parts = [
    cycle.model,
    cycle.steps > 0 ? plural(cycle.steps, 'step') : '',
    tokens > 0 ? plural(tokens, 'token') : '',
    cycle.finished_at ? `answered ${formatDateTime(cycle.finished_at)}` : '',
  ].filter(Boolean)
  if (parts.length === 0) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Muted as='span' variant='caption' tabIndex={0} className='w-fit'>
          {parts.join(' · ')}
        </Muted>
      </TooltipTrigger>
      <TooltipContent>
        {`${plural(cycle.input_tokens, 'token')} read, ${plural(cycle.output_tokens, 'token')} written`}
      </TooltipContent>
    </Tooltip>
  )
}

export function CycleBlock({
  cycle,
  live,
  remembered,
}: {
  cycle: WillCycle
  live: LiveCycle | null
  remembered: boolean
}) {
  const items = traceOf(cycle, live)
  const active = isActive(cycle)
  const waiting =
    active && live === null && items.length === 0 && !cycle.final_text
  return (
    <article
      data-domain='will-cycle'
      data-status={cycle.status}
      data-remembered={remembered ? true : undefined}
      aria-label={`Exchange ${String(cycle.ordinal)}`}
      className={cn('flex min-w-0 flex-col gap-3', !remembered && 'opacity-80')}
    >
      <PlayerTurn cycle={cycle} />
      <div className='flex min-w-0 items-start gap-2.5'>
        <DivineCrest
          size='sm'
          tone={cycle.status === 'failed' ? 'danger' : 'gold'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2.5'>
          {items.map((item) => (
            <TraceView key={item.key} item={item} />
          ))}
          {waiting && (
            <div role='status' className='flex items-center gap-2'>
              <Loader2
                aria-hidden='true'
                className='size-icon-sm animate-spin text-primary'
              />
              <Muted as='span' variant='caption'>
                The Divine Will gathers its thoughts…
              </Muted>
            </div>
          )}
          {cycle.status === 'awaiting_confirmation' && (
            <div role='status' className='flex items-center gap-2'>
              <Hourglass
                aria-hidden='true'
                className='size-icon-sm text-warning'
              />
              <Muted as='span' variant='caption'>
                The Divine Will waits for your word before it goes on.
              </Muted>
            </div>
          )}
          {cycle.final_text && (
            <div
              data-domain='will-answer'
              className='relative flex min-w-0 flex-col gap-2 rounded-lg rounded-tl-sm surface-sheen px-3.5 py-3'
            >
              <div className='flex min-w-0 items-start gap-2'>
                <div className='flex min-w-0 flex-1 flex-col gap-2'>
                  <WillMarkdown text={cycle.final_text} />
                </div>
                <CopyButton text={cycle.final_text} label='Copy the answer' />
              </div>
            </div>
          )}
          {cycle.status === 'failed' && cycle.error && (
            <ErrorCard text={cycle.error} />
          )}
          {cycle.status === 'cancelled' && (
            <div className='flex items-center gap-2'>
              <CircleSlash
                aria-hidden='true'
                className='size-icon-sm text-muted-foreground'
              />
              <Muted as='span' variant='caption'>
                You stopped this exchange.
              </Muted>
            </div>
          )}
          {!active && <CycleFooter cycle={cycle} />}
        </div>
      </div>
    </article>
  )
}

export function MemoryBoundary({ forgotten }: { forgotten: number }) {
  return (
    <div
      role='separator'
      aria-label='Beyond memory'
      data-domain='will-memory-boundary'
      className='flex min-w-0 flex-col items-center gap-1.5 py-2 text-center'
    >
      <div className='flex w-full min-w-0 items-center gap-3'>
        <span
          aria-hidden='true'
          className='h-px flex-1 bg-linear-to-r from-transparent to-gild/60'
        />
        <Badge variant='outline'>
          <Boundless />
          Beyond memory
        </Badge>
        <span
          aria-hidden='true'
          className='h-px flex-1 bg-linear-to-l from-transparent to-gild/60'
        />
      </div>
      <Muted variant='caption' className='max-w-sm'>
        {`The Divine Will no longer keeps the ${forgotten === 1 ? 'exchange' : plural(forgotten, 'exchange')} above in mind. ${forgotten === 1 ? 'It stays' : 'They stay'} here, in Past sessions, the lore book and the Codex.`}
      </Muted>
    </div>
  )
}

export function CycleList({
  cycles,
  boundary,
}: {
  cycles: WillCycle[]
  boundary: number
}) {
  const live = useWill((state) => state.live)
  const firstRemembered = cycles.findIndex((cycle) => cycle.ordinal >= boundary)
  const forgotten = firstRemembered === -1 ? cycles.length : firstRemembered
  const showLine = boundary > 0 && forgotten > 0
  return (
    <>
      {cycles.map((cycle, index) => (
        <Fragment key={cycle.id}>
          {showLine && index === forgotten && (
            <MemoryBoundary
              forgotten={
                cycles.filter((item) => item.ordinal < boundary).length
              }
            />
          )}
          <CycleBlock
            cycle={cycle}
            live={live[cycle.id] ?? null}
            remembered={cycle.ordinal >= boundary}
          />
        </Fragment>
      ))}
      {showLine && forgotten === cycles.length && (
        <MemoryBoundary forgotten={forgotten} />
      )}
    </>
  )
}

const SHOWN_ATTACHMENTS = 6

function AttachmentChips({
  attachments,
}: {
  attachments: WillCycle['attachments']
}) {
  const shown = useShowMore(attachments, SHOWN_ATTACHMENTS)
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {shown.visible.map((attachment) => (
          <AttachmentChip key={attachment.id} attachment={attachment} />
        ))}
      </div>
      <ShowMore state={shown} />
    </div>
  )
}
