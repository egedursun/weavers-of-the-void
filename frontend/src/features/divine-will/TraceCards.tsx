import { useState } from 'react'
import {
  ArrowRight,
  ArrowRightLeft,
  Brain,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  EyeOff,
  Info,
  Loader2,
  RotateCw,
  Sparkles,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { formatDuration, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  CopyButton,
  KeyValueList,
  Medallion,
  RuleInfo,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { UndoButton } from './UndoButton'
import { WillMarkdown } from './WillMarkdown'
import { MODE_LOOK } from './modes'
import { parsedResult } from './resultModel'
import { argumentRows, argumentSummary, toolLook } from './toolLook'
import { type ToolTrace, textField } from './traceModel'
import { type DivineWillMode } from './types'
import { useActionTitle } from './useActionTitle'
import { useNameOf } from './useNameOf'
import { type LiveTool, useWill } from './willStore'

const ACTING_TOOLS: ReadonlySet<string> = new Set([
  'perform_action',
  'set_rule',
  'reset_rule',
  'undo_action',
])

export function ThoughtGroup({ texts }: { texts: string[] }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button
          variant='ghost'
          size='sm'
          aria-expanded={open}
          className='w-fit text-muted-foreground'
        >
          {open ? <ChevronDown /> : <ChevronRight />}
          <Brain />
          {texts.length === 1 ? 'A thought' : plural(texts.length, 'thought')}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-2 border-l-2 border-gild/30 ps-3'>
        {texts.map((text, index) => (
          <Muted key={index} as='div' className='italic'>
            <WillMarkdown text={text} />
          </Muted>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function ToolCallCard({ trace }: { trace: ToolTrace }) {
  const [open, setOpen] = useState(false)
  const look = toolLook(trace.tool)
  const actionTitle = useActionTitle(trace.actionId)
  const Icon = look.icon
  const title =
    trace.tool === 'perform_action' && actionTitle ? actionTitle : look.label
  const nameOf = useNameOf()
  const summary = argumentSummary(trace.input, nameOf)
  const acted = ACTING_TOOLS.has(trace.tool) && trace.done && !trace.failed
  const rule = textField(trace.details, 'rule')
  return (
    <article
      data-domain='will-tool-call'
      data-tool={trace.tool}
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-md surface-sheen px-3 py-2.5',
        acted && 'will-act-flash',
        trace.failed && 'border-destructive/50'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={Icon}
          tone={trace.failed ? 'danger' : acted ? 'gold' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {title}
          </Text>
          {summary && (
            <Muted as='span' variant='caption' truncate={2}>
              {summary}
            </Muted>
          )}
        </div>
        <div className='flex shrink-0 flex-wrap items-center justify-end gap-1'>
          {trace.essence > 0 && (
            <Badge size='sm' variant='default'>
              <Sparkles />
              {formatInteger(trace.essence)}
            </Badge>
          )}
          {!trace.done ? (
            <Badge size='sm' variant='outline'>
              <Loader2 className='animate-spin' />
              Working
            </Badge>
          ) : trace.failed ? (
            <Badge size='sm' variant='destructive'>
              <CircleAlert />
              Failed
            </Badge>
          ) : (
            <Badge size='sm' variant='success'>
              <CircleCheck />
              Done
            </Badge>
          )}
        </div>
      </div>
      {trace.outcome && <Text variant='caption'>{trace.outcome}</Text>}
      {rule && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-md surface-well px-2.5 py-1.5'>
          <Text
            as='span'
            variant='caption'
            weight='medium'
            className='font-mono'
          >
            {rule}
          </Text>
          <Muted as='span' variant='caption' className='line-through'>
            {textField(trace.details, 'before')}
          </Muted>
          <ArrowRight
            aria-hidden='true'
            className='size-icon-xs text-muted-foreground'
          />
          <Text as='span' variant='caption' weight='semibold'>
            {textField(trace.details, 'after')}
          </Text>
          <Muted as='span' variant='caption' className='flex-1'>
            {`default ${textField(trace.details, 'default')}`}
          </Muted>
          <RuleInfo rule={rule} label='This rule' />
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Button
          variant='ghost'
          size='sm'
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <ChevronDown /> : <ChevronRight />}
          {open ? 'Hide the details' : 'Details'}
        </Button>
        {trace.ledgerEntryId !== null && (
          <UndoButton entryId={trace.ledgerEntryId} />
        )}
      </div>
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
          <Label variant='overline'>What came back</Label>
          {trace.detail ? (
            <ResultBody text={trace.detail} />
          ) : (
            <Muted variant='caption'>
              {trace.done ? 'No text came back.' : 'The result is on its way.'}
            </Muted>
          )}
          {trace.handle && (
            <Muted variant='caption'>
              {`Kept under the handle ${trace.handle}; the Divine Will can read further pages of it while this exchange stays in mind.`}
            </Muted>
          )}
        </div>
      )}
    </article>
  )
}

function ResultBody({ text }: { text: string }) {
  const { envelope, lines } = parsedResult(text)
  const shown = useShowMore(lines, RESULT_LINES)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        {envelope && (
          <>
            <Badge size='sm' variant='secondary'>
              {envelope.shown === envelope.total
                ? plural(envelope.total, 'item')
                : `${formatInteger(envelope.shown)} of ${formatInteger(envelope.total)}`}
            </Badge>
            <Badge size='sm' variant='outline'>
              {`Page ${String(envelope.page)}`}
            </Badge>
            <Badge size='sm' variant={envelope.next ? 'info' : 'outline'}>
              {envelope.next ? 'More pages to read' : 'Complete'}
            </Badge>
          </>
        )}
        <span aria-hidden='true' className='flex-1' />
        <CopyButton text={lines.join('\n')} label='Copy what came back' />
      </div>
      <div className='min-w-0 rounded-md surface-well px-3 py-2'>
        <WillMarkdown text={shown.visible.join('\n')} />
      </div>
      <ShowMore state={shown} noun={['line', 'lines']} />
    </div>
  )
}

const RESULT_LINES = 12

const LIVE_PHASE_LABEL: Record<LiveTool['phase'], string> = {
  preparing: 'Choosing its words',
  writing: 'Writing the request',
  called: 'At work',
  result: 'Done',
}

export function LiveToolCard({ tool }: { tool: LiveTool }) {
  const look = toolLook(tool.tool)
  const Icon = look.icon
  return (
    <div
      role='status'
      data-domain='will-live-tool'
      className='flex min-w-0 items-center gap-2.5 rounded-md px-3 py-2 sealed-well'
    >
      <Icon aria-hidden='true' className='size-icon-sm shrink-0 text-primary' />
      <Text as='span' weight='medium' truncate className='flex-1'>
        {look.label}
      </Text>
      <Badge size='sm' variant='outline'>
        <Loader2 className='animate-spin' />
        {LIVE_PHASE_LABEL[tool.phase]}
      </Badge>
    </div>
  )
}

export function SuggestModeCard({
  mode,
  reason,
}: {
  mode: DivineWillMode
  reason: string
}) {
  const current = useWill((state) => state.mode)
  const setMode = useWill((state) => state.setMode)
  const look = MODE_LOOK[mode]
  const Icon = look.icon
  const already = current === mode
  return (
    <div
      data-domain='will-suggest-mode'
      className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-sheen border-info/40 px-3 py-2.5'
    >
      <ArrowRightLeft
        aria-hidden='true'
        className='size-icon-md shrink-0 text-info'
      />
      <div className='flex min-w-0 flex-1 basis-48 flex-col'>
        <Text as='span' weight='semibold'>
          {`This is better done in ${look.label}`}
        </Text>
        {reason && (
          <Muted as='span' variant='caption'>
            {reason}
          </Muted>
        )}
      </div>
      <Button
        variant='outline'
        size='sm'
        disabled={already}
        disabledReason={`${look.label} is already the chosen mode.`}
        onClick={() => setMode(mode)}
      >
        <Icon />
        {`Switch to ${look.label}`}
      </Button>
    </div>
  )
}

export function NoticeCard({
  text,
  vision,
}: {
  text: string
  vision: boolean
}) {
  return (
    <div
      data-domain='will-notice'
      data-notice={vision ? 'vision' : undefined}
      className={cn(
        'flex min-w-0 items-start gap-2.5 rounded-md surface-well px-3 py-2',
        vision && 'border-warning/40'
      )}
    >
      {vision ? (
        <EyeOff
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-warning'
        />
      ) : (
        <Info aria-hidden='true' className='size-icon-sm shrink-0 text-info' />
      )}
      <div className='flex min-w-0 flex-col'>
        {vision && (
          <Text as='span' variant='caption' weight='medium'>
            The model could not see your image
          </Text>
        )}
        <Text variant='caption'>{text}</Text>
      </div>
    </div>
  )
}

export function RetryCard({
  attempt,
  total,
  reason,
  waitSeconds,
}: {
  attempt: number
  total: number
  reason: string
  waitSeconds: number
}) {
  return (
    <div
      data-domain='will-retry'
      className='flex min-w-0 items-start gap-2.5 rounded-md surface-well border-warning/40 px-3 py-2'
    >
      <RotateCw
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-warning'
      />
      <div className='flex min-w-0 flex-col'>
        <Text as='span' variant='caption' weight='medium'>
          {`Trying again, attempt ${String(attempt)} of ${String(total)}`}
        </Text>
        <Muted as='span' variant='caption'>
          {[
            reason,
            waitSeconds > 0 ? `after ${formatDuration(waitSeconds)}` : '',
          ]
            .filter(Boolean)
            .join(' · ') ||
            'The model did not answer; the Divine Will asks again.'}
        </Muted>
      </div>
    </div>
  )
}

export function ErrorCard({ text }: { text: string }) {
  return (
    <div
      role='alert'
      data-domain='will-error'
      className='flex min-w-0 items-start gap-2.5 rounded-md surface-well border-destructive/50 px-3 py-2'
    >
      <CircleAlert
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-destructive'
      />
      <Text variant='caption' tone='destructive'>
        {text || 'Something went wrong in this exchange.'}
      </Text>
    </div>
  )
}
