import { useState } from 'react'
import { Brain, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { ConfirmDialog, RuleInfo } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useResetSession } from './api'

const PERCENT = 100
const MEMORY_RULE = 'divine_will.remembered_cycles'

export function MemoryMeter({
  remembered,
  limit,
}: {
  remembered: number
  limit: number
}) {
  const shown = Math.min(remembered, limit)
  return (
    <div
      data-domain='will-memory-meter'
      className='flex min-w-0 flex-1 items-center gap-1.5'
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            tabIndex={0}
            aria-label={`${String(shown)} of ${String(limit)} exchanges remembered`}
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
                exchanges remembered
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
          The Divine Will keeps the last completed exchanges of this session in
          mind, up to the world rule. Older ones stay in the chat above the
          line, in Past sessions, the lore book and the Codex, but no longer
          enter its thoughts.
        </TooltipContent>
      </Tooltip>
      <RuleInfo rule={MEMORY_RULE} label='How many exchanges it remembers' />
    </div>
  )
}

export function ResetSessionButton({
  busy,
  empty,
}: {
  busy: boolean
  empty: boolean
}) {
  const [open, setOpen] = useState(false)
  const reset = useResetSession()
  const reason = isReadOnly()
    ? READ_ONLY_MESSAGE
    : busy
      ? 'Wait until the Divine Will has answered, or stop it first.'
      : empty
        ? 'This session has no exchange yet.'
        : reset.isPending
          ? 'Beginning a new session.'
          : null
  return (
    <>
      {reason === null ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              act={reset}
              variant='ghost'
              size='icon-sm'
              aria-label='Begin a new session'
              onClick={() => setOpen(true)}
            >
              <RotateCcw />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Begin a new session</TooltipContent>
        </Tooltip>
      ) : (
        <Button
          variant='ghost'
          size='icon-sm'
          aria-label='Begin a new session'
          disabled
          disabledReason={reason}
        >
          <RotateCcw />
        </Button>
      )}
      <ConfirmDialog
        act={reset}
        open={open}
        onOpenChange={setOpen}
        title='Begin a new session?'
        desc={
          <div className='flex flex-col gap-2'>
            <span>
              The Divine Will closes this session and starts the next one with
              an empty memory: it will not recall what was said here.
            </span>
            <span>
              Nothing is lost. The closed session, with every exchange, act,
              plan, forecast and writing, stays in Past sessions, the lore book
              and the Codex.
            </span>
          </div>
        }
        confirmText='Begin anew'
        isLoading={reset.isPending}
        handleConfirm={() =>
          reset.mutate(undefined, {
            onSuccess: () => {
              setOpen(false)
              toast.success(
                'A new session begins. The last one is kept in the record.'
              )
            },
            onError: (error) => toast.error(error.message),
          })
        }
      />
    </>
  )
}
