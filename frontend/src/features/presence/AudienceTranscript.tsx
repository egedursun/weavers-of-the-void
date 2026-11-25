import { Fragment, useState } from 'react'
import {
  Brain,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  CircleSlash,
  Infinity as Boundless,
  Loader2,
} from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  CopyButton,
  KeyValueList,
  Medallion,
  Portrait,
  ToolIcon,
  toolTitle,
} from '@/components/domain'
import { TOOL_FALLBACK_ICON, toolIdIcon } from '@/components/domain/toolIcons'
import { Label, Muted, Text } from '@/components/typography'
import {
  ErrorCard,
  RetryCard,
  ThoughtGroup,
} from '@/features/divine-will/TraceCards'
import { WillMarkdown } from '@/features/divine-will/WillMarkdown'
import { argumentRows, argumentSummary } from '@/features/divine-will/toolLook'
import { useNameOf } from '@/features/divine-will/useNameOf'
import { mediaUrl } from '@/features/pantheon/media'
import { DeadSeal } from './DeadSeal'
import { EXCHANGE_STATUS_LABEL, GUISE_LOOK } from './looks'
import { type LiveCall, type LiveExchange, usePresence } from './presenceStore'
import {
  type CallTrace,
  type PresenceTraceItem,
  shortTool,
  traceOfExchange,
} from './presenceTrace'
import {
  type AudienceSpeaker,
  type PresenceExchange,
  type PresenceGuise,
  type PresenceSessionSummary,
} from './types'

const LIVE_PHASE_LABEL: Record<LiveCall['phase'], string> = {
  preparing: 'Choosing its words',
  writing: 'Writing the request',
  called: 'At work',
  result: 'Done',
}

function CallCard({ trace }: { trace: CallTrace }) {
  const [open, setOpen] = useState(false)
  const nameOf = useNameOf()
  const Icon = toolIdIcon(trace.tool) ?? TOOL_FALLBACK_ICON
  const summary = argumentSummary(trace.input, nameOf)
  return (
    <article
      data-domain='presence-tool-call'
      data-tool={trace.tool}
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-md surface-sheen px-3 py-2.5',
        trace.failed && 'border-destructive/50'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={Icon}
          tone={trace.failed ? 'danger' : trace.done ? 'gold' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {toolTitle(trace.tool)}
          </Text>
          {summary && (
            <Muted as='span' variant='caption' truncate={2}>
              {summary}
            </Muted>
          )}
        </div>
        {!trace.done ? (
          <Badge size='sm' variant='outline'>
            <Loader2 className='animate-spin' />
            Working
          </Badge>
        ) : trace.failed ? (
          <Badge size='sm' variant='destructive'>
            <CircleAlert />
            Refused
          </Badge>
        ) : (
          <Badge size='sm' variant='success'>
            <CircleCheck />
            Done
          </Badge>
        )}
      </div>
      {trace.outcome && <Text variant='caption'>{trace.outcome}</Text>}
      <Button
        variant='ghost'
        size='sm'
        className='w-fit'
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown /> : <ChevronRight />}
        {open ? 'Hide the details' : 'Details'}
      </Button>
      {open && (
        <div className='flex min-w-0 flex-col gap-3 rounded-md surface-well px-3 py-2.5'>
          <Label variant='overline'>What it was given</Label>
          {Object.keys(trace.input).length > 0 ? (
            <KeyValueList
              layout='stacked'
              items={argumentRows(trace.input).map((row) => ({
                key: row.key,
                label: row.label,
                value: (
                  <span className='font-mono whitespace-pre-wrap'>
                    {row.value}
                  </span>
                ),
              }))}
            />
          ) : (
            <Muted variant='caption'>Nothing; it needed no input.</Muted>
          )}
          <div className='flex min-w-0 items-center justify-between gap-2'>
            <Label variant='overline'>What came back</Label>
            <CopyButton text={trace.result} label='Copy what came back' />
          </div>
          {trace.result ? (
            <div className='min-w-0 rounded-md surface-well px-3 py-2'>
              <WillMarkdown text={trace.result} />
            </div>
          ) : (
            <Muted variant='caption'>
              {trace.done ? 'No text came back.' : 'The result is on its way.'}
            </Muted>
          )}
        </div>
      )}
    </article>
  )
}

function LiveCallCard({ call }: { call: LiveCall }) {
  return (
    <div
      role='status'
      data-domain='presence-live-tool'
      className='flex min-w-0 items-center gap-2.5 rounded-md px-3 py-2 sealed-well'
    >
      <ToolIcon tool={shortTool(call.tool)} className='text-primary' />
      <Text as='span' weight='medium' truncate className='flex-1'>
        {call.tool ? toolTitle(shortTool(call.tool)) : 'A tool'}
      </Text>
      <Badge size='sm' variant='outline'>
        <Loader2 className='animate-spin' />
        {LIVE_PHASE_LABEL[call.phase]}
      </Badge>
    </div>
  )
}

function TraceView({ item }: { item: PresenceTraceItem }) {
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
    case 'call':
      return <CallCard trace={item.trace} />
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
    case 'live-call':
      return <LiveCallCard call={item.call} />
    case 'streaming':
      return (
        <div
          aria-live='polite'
          aria-atomic='false'
          data-domain='presence-streaming'
        >
          <WillMarkdown text={item.text} />
          <span aria-hidden='true' className='will-caret' />
        </div>
      )
  }
}

function PlayerTurn({
  exchange,
  guise,
}: {
  exchange: PresenceExchange
  guise: PresenceGuise
}) {
  const look = GUISE_LOOK[guise]
  const Icon = look.icon
  return (
    <div className='flex min-w-0 justify-end ps-8'>
      <div
        data-domain='presence-player'
        className='flex min-w-0 flex-col gap-1.5 rounded-lg rounded-br-sm surface-framed px-3 py-2'
      >
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='outline'>
            <Icon />
            {`You, as ${look.label}`}
          </Badge>
          <Muted as='span' variant='caption'>
            {`Epoch ${String(exchange.epoch)} · ${formatDateTime(exchange.started_at)}`}
          </Muted>
          <span aria-hidden='true' className='flex-1' />
          <CopyButton text={exchange.player_text} label='Copy your words' />
        </div>
        <Text className='whitespace-pre-wrap'>{exchange.player_text}</Text>
      </div>
    </div>
  )
}

function ExchangeFooter({ exchange }: { exchange: PresenceExchange }) {
  const tokens = exchange.input_tokens + exchange.output_tokens
  const parts = [
    exchange.model,
    exchange.steps > 0 ? plural(exchange.steps, 'step') : '',
    tokens > 0 ? plural(tokens, 'token') : '',
    exchange.finished_at
      ? `answered ${formatDateTime(exchange.finished_at)}`
      : '',
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
        {`${plural(exchange.input_tokens, 'token')} read, ${plural(exchange.output_tokens, 'token')} written`}
      </TooltipContent>
    </Tooltip>
  )
}

function ExchangeBlock({
  exchange,
  live,
  remembered,
  speaker,
  session,
}: {
  exchange: PresenceExchange
  live: LiveExchange | null
  remembered: boolean
  speaker: AudienceSpeaker
  session: PresenceSessionSummary
}) {
  const items = traceOfExchange(exchange, live)
  const running = exchange.status === 'running'
  const waiting =
    running && live === null && items.length === 0 && !exchange.reply_text
  const dead = session.dead_when_summoned
  return (
    <article
      data-domain='presence-exchange'
      data-status={exchange.status}
      data-remembered={remembered ? true : undefined}
      aria-label={`Exchange ${String(exchange.ordinal)}, ${EXCHANGE_STATUS_LABEL[exchange.status]}`}
      className={cn('flex min-w-0 flex-col gap-3', !remembered && 'opacity-80')}
    >
      <PlayerTurn exchange={exchange} guise={session.guise} />
      <div className='flex min-w-0 items-start gap-2.5'>
        <Portrait name={speaker.name} src={mediaUrl(speaker.cover)} size='md' />
        <div className='flex min-w-0 flex-1 flex-col gap-2.5'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Text
              as='span'
              weight='semibold'
              className='text-gilded font-display'
            >
              {speaker.name}
            </Text>
            {dead && <DeadSeal size='sm' death={speaker.deathLine} />}
          </div>
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
                {`${speaker.name} gathers its thoughts…`}
              </Muted>
            </div>
          )}
          {exchange.reply_text && (
            <div
              data-domain='presence-reply'
              className='flex min-w-0 items-start gap-2 rounded-lg rounded-tl-sm surface-sheen px-3.5 py-3'
            >
              <div className='flex min-w-0 flex-1 flex-col gap-2'>
                <WillMarkdown text={exchange.reply_text} />
              </div>
              <CopyButton text={exchange.reply_text} label='Copy the answer' />
            </div>
          )}
          {exchange.remember_text && (
            <div
              data-domain='presence-remembered'
              className='flex min-w-0 items-start gap-2 rounded-md surface-well px-3 py-2'
            >
              <Brain
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Label variant='overline'>It will remember</Label>
                <Text variant='caption'>{exchange.remember_text}</Text>
              </div>
              <CopyButton
                text={exchange.remember_text}
                label='Copy what it will remember'
              />
            </div>
          )}
          {exchange.status === 'failed' && exchange.error && (
            <ErrorCard text={exchange.error} />
          )}
          {exchange.status === 'cancelled' && (
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
          {!running && <ExchangeFooter exchange={exchange} />}
        </div>
      </div>
    </article>
  )
}

function MemoryBoundary({
  forgotten,
  name,
}: {
  forgotten: number
  name: string
}) {
  return (
    <div
      role='separator'
      aria-label='Beyond memory'
      data-domain='presence-memory-boundary'
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
        {`${name} no longer keeps the ${forgotten === 1 ? 'exchange' : plural(forgotten, 'exchange')} above in mind this audience. ${forgotten === 1 ? 'It stays' : 'They stay'} on this page.`}
      </Muted>
    </div>
  )
}

export function ExchangeList({
  exchanges,
  boundary,
  speaker,
  session,
}: {
  exchanges: PresenceExchange[]
  boundary: number
  speaker: AudienceSpeaker
  session: PresenceSessionSummary
}) {
  const live = usePresence((state) => state.live)
  const firstRemembered = exchanges.findIndex(
    (exchange) => exchange.ordinal >= boundary
  )
  const forgotten = firstRemembered === -1 ? exchanges.length : firstRemembered
  const showLine = boundary > 0 && forgotten > 0
  return (
    <>
      {exchanges.map((exchange, index) => (
        <Fragment key={exchange.id}>
          {showLine && index === forgotten && (
            <MemoryBoundary forgotten={forgotten} name={speaker.name} />
          )}
          <ExchangeBlock
            exchange={exchange}
            live={live[exchange.id] ?? null}
            remembered={exchange.ordinal >= boundary}
            speaker={speaker}
            session={session}
          />
        </Fragment>
      ))}
      {showLine && forgotten === exchanges.length && (
        <MemoryBoundary forgotten={forgotten} name={speaker.name} />
      )}
    </>
  )
}
