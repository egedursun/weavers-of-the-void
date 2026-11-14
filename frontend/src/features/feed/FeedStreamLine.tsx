import { ChevronDown, ChevronUp, Eye } from 'lucide-react'
import { plural } from '@/lib/units'
import { STREAM_COLLAPSE_CHARS } from '@/constants/ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { TimelineItem } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { FEED_SYMBOL_ICON } from './feedLabels'
import { type FeedLine } from './feedModel'
import { isOpenStream } from './feedStream'
import { toolIcon, toolLabel } from './feedToolIcons'

type StreamLineViewProps = {
  line: FeedLine
  open: boolean
  last: boolean
  stamp: string
  onToggle: (key: string) => void
}

function Collapsible({
  line,
  open,
  body,
  tone,
  onToggle,
}: {
  line: FeedLine
  open: boolean
  body: string
  tone: 'muted' | 'destructive'
  onToggle: (key: string) => void
}) {
  const long = body.length > STREAM_COLLAPSE_CHARS
  return (
    <div className='flex min-w-0 flex-col items-start gap-1'>
      <Muted
        truncate={long && !open ? 3 : undefined}
        className={
          tone === 'destructive'
            ? 'text-destructive'
            : 'border-l-2 border-primary/40 pl-3 italic'
        }
      >
        {body}
      </Muted>
      {long && (
        <Button
          variant='ghost'
          size='sm'
          aria-expanded={open}
          onClick={() => onToggle(`line-${line.id}`)}
        >
          {open ? <ChevronUp /> : <ChevronDown />}
          {open ? 'Show less' : 'Show more'}
        </Button>
      )}
    </div>
  )
}

function toolStatus(line: FeedLine): string {
  const stream = line.stream
  if (!stream) return ''
  switch (stream.phase) {
    case 'preparing':
      return 'Preparing the call'
    case 'writing':
      return `Writing the call · ${plural(stream.chars, 'character', 'characters')}`
    case 'called':
      return stream.readOnly ? 'Reading' : 'Called, waiting for the result'
    case 'result':
      return 'Done'
    case 'failed':
      return 'Failed'
    default:
      return ''
  }
}

export function StreamLineView({
  line,
  open,
  last,
  stamp,
  onToggle,
}: StreamLineViewProps) {
  const stream = line.stream
  if (!stream) return null
  const live = isOpenStream(stream)
  const isTool = stream.key.startsWith('tool:')
  const isWrite = stream.key.startsWith('write:')
  const Icon = isTool ? toolIcon(stream.tool) : FEED_SYMBOL_ICON[line.symbol]
  const title = isTool
    ? `${stream.actorName} · ${toolLabel(stream.tool)}`
    : isWrite
      ? stream.phase === 'finished'
        ? `${stream.actorName} finished writing`
        : stream.phase === 'failed'
          ? `${stream.actorName} could not finish writing`
          : `${stream.actorName} is writing`
      : stream.phase === 'streaming'
        ? `${stream.actorName} is thinking`
        : `${stream.actorName} thought`
  return (
    <TimelineItem
      icon={Icon}
      tone={line.tone}
      title={title}
      timestamp={stamp}
      last={last}
      framed
    >
      <div
        className='flex min-w-0 flex-col gap-1'
        aria-busy={live || undefined}
      >
        {isTool && (
          <Badge
            size='sm'
            variant={
              stream.phase === 'failed'
                ? 'destructive'
                : stream.phase === 'result'
                  ? 'success'
                  : 'info'
            }
          >
            {toolStatus(line)}
          </Badge>
        )}
        {isWrite && (
          <>
            <Label>{`${plural(stream.chars, 'character', 'characters')}`}</Label>
            {stream.phase === 'writing' && (
              <Progress size='sm' indeterminate aria-label='Writing' />
            )}
          </>
        )}
        {stream.text !== '' && (
          <Collapsible
            line={line}
            open={open}
            body={stream.text}
            tone={stream.phase === 'failed' ? 'destructive' : 'muted'}
            onToggle={onToggle}
          />
        )}
      </div>
    </TimelineItem>
  )
}

export function ReadingGroupView({
  lines,
  open,
  groupKey,
  last,
  stamp,
  onToggle,
}: {
  lines: FeedLine[]
  open: boolean
  groupKey: string
  last: boolean
  stamp: string
  onToggle: (key: string) => void
}) {
  const actor = lines[0].stream?.actorName ?? 'Someone'
  return (
    <TimelineItem
      icon={Eye}
      title={`${actor} reads ×${lines.length}`}
      timestamp={stamp}
      last={last}
      framed
    >
      <div className='flex min-w-0 flex-col items-start gap-1'>
        {open ? (
          <ul className='flex min-w-0 flex-col gap-1'>
            {lines.map((line) => (
              <li key={line.id}>
                <Text as='span' variant='caption' tone='muted'>
                  {toolLabel(line.stream?.tool ?? null)}
                </Text>
              </li>
            ))}
          </ul>
        ) : (
          <Muted truncate>
            {[
              ...new Set(
                lines.map((line) => toolLabel(line.stream?.tool ?? null))
              ),
            ].join(', ')}
          </Muted>
        )}
        <Button
          variant='ghost'
          size='sm'
          aria-expanded={open}
          onClick={() => onToggle(groupKey)}
        >
          {open ? <ChevronUp /> : <ChevronDown />}
          {open ? 'Collapse' : 'Show each call'}
        </Button>
      </div>
    </TimelineItem>
  )
}
