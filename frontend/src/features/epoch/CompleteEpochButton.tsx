import { Hourglass, LoaderCircle, Play } from 'lucide-react'
import { toast } from 'sonner'
import { agree, formatDuration, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useWorldState } from '@/features/overview/api'
import { useCompleteEpoch, useEpochEstimate } from './api'
import { epochScopeText } from './epochText'
import { useEpochRun } from './runStore'

type CompleteEpochButtonProps = {
  size?: 'sm' | 'default'
}

export function CompleteEpochButton({
  size = 'default',
}: CompleteEpochButtonProps) {
  const state = useWorldState()
  const estimate = useEpochEstimate()
  const complete = useCompleteEpoch()
  const last = useEpochRun((run) => run.last)
  const world = state.data?.world ?? null
  const running = Boolean(state.data?.epoch_running) || complete.isPending
  const half = state.data?.half_epoch ?? null
  const waiting = state.data?.pending_son_ids.length ?? 0

  if (!world)
    return (
      <Button
        size={size}
        disabled
        disabledReason={
          state.isPending
            ? 'Reading the state of the world'
            : 'Create a world before completing an epoch'
        }
      >
        <Hourglass />
        Complete the epoch
      </Button>
    )

  if (running)
    return (
      <Button
        size={size}
        disabled
        disabledReason='An epoch is running; follow it in the live feed and the progress strip'
      >
        <LoaderCircle className='animate-spin' />
        Running
      </Button>
    )

  const label = half
    ? `Resume epoch ${half.epoch} from phase ${half.phase}`
    : 'Complete the epoch'
  const averageSeconds = estimate.data?.average_epoch_seconds ?? null
  const lines = [
    half
      ? `Epoch ${half.epoch} was interrupted; everything after phase ${plural(half.phase, 'resume', 'resumes')} where it stopped.`
      : waiting > 0
        ? `${plural(waiting, 'son', 'sons')} ${agree(waiting, 'is', 'are')} waiting to act.`
        : 'Every son has acted this epoch.',
    epochScopeText(waiting, world.mortal_agents_per_epoch),
    averageSeconds !== null
      ? `Estimated time ${formatDuration(averageSeconds)} (average of the last ${plural(estimate.data?.samples ?? 0, 'epoch', 'epochs')}).`
      : 'No epoch has been measured yet, so there is no time estimate.',
    last
      ? `The last epoch took ${formatDuration(last.durationSeconds)}.`
      : null,
    'While it runs, Stop halts it at a safe point; completing again resumes it.',
  ].filter((line) => line !== null)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          act={complete}
          size={size}
          aria-description={lines.join(' ')}
          onClick={() =>
            complete.mutate(undefined, {
              onSuccess: () =>
                toast.success(half ? 'The epoch resumes' : 'The epoch begins'),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          {half ? <Play /> : <Hourglass />}
          {label}
          {!half && waiting > 0 && (
            <Badge size='sm' variant='secondary'>
              {waiting}
            </Badge>
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent className='flex max-w-xs flex-col gap-1'>
        {lines.map((line) => (
          <span key={line}>{line}</span>
        ))}
      </TooltipContent>
    </Tooltip>
  )
}
