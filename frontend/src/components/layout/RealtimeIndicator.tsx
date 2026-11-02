import { type StreamStatus, useRealtimeStatus } from '@/realtime'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DOT_CLASS,
  STATUS_LABEL,
  STATUS_SHORT,
  STATUS_TEXT_CLASS,
} from './realtimeStatus'

export function StatusDot({ status }: { status: StreamStatus }) {
  const pulsing = status === 'open' || status === 'reconnecting'
  return (
    <span aria-hidden='true' className='relative flex size-2 shrink-0'>
      {pulsing && (
        <span
          className={cn(
            'absolute inline-flex size-full animate-ping rounded-full opacity-60 motion-reduce:animate-none',
            DOT_CLASS[status]
          )}
        />
      )}
      <span
        className={cn(
          'relative inline-flex size-2 rounded-full',
          DOT_CLASS[status]
        )}
      />
    </span>
  )
}

export function RealtimeIndicator() {
  const status = useRealtimeStatus()
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant='ghost'
          size='sm'
          data-realtime-status={status}
          aria-label={STATUS_LABEL[status]}
          className={cn('gap-2 px-2', STATUS_TEXT_CLASS[status])}
        >
          <StatusDot status={status} />
          <span className='hidden text-overline tracking-wider uppercase @7xl/topbar:inline'>
            {STATUS_SHORT[status]}
          </span>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{STATUS_LABEL[status]}</TooltipContent>
    </Tooltip>
  )
}
