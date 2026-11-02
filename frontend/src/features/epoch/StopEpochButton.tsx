import { useState } from 'react'
import { LoaderCircle, Square } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/domain'
import { useWorldState } from '@/features/overview/api'
import { useStopEpoch } from './api'
import { useEpochRun } from './runStore'

type StopEpochButtonProps = {
  size?: 'sm' | 'default'
}

export function StopEpochButton({ size = 'default' }: StopEpochButtonProps) {
  const state = useWorldState()
  const stop = useStopEpoch()
  const active = useEpochRun((run) => run.active)
  const stopRequested = useEpochRun((run) => run.stopRequested)
  const [open, setOpen] = useState(false)
  const running = Boolean(state.data?.epoch_running) || active
  if (!running) return null
  if (stopRequested || stop.isSuccess)
    return (
      <Button
        size={size}
        variant='outline'
        disabled
        disabledReason='The epoch stops at the next safe point'
      >
        <LoaderCircle className='animate-spin' />
        Stopping
      </Button>
    )
  return (
    <>
      <Button size={size} variant='destructive' onClick={() => setOpen(true)}>
        <Square />
        Stop
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title='Stop the epoch?'
        desc='The epoch halts at the next safe point. Completing the epoch later resumes it from where it stopped.'
        confirmText='Stop at a safe point'
        destructive
        isLoading={stop.isPending}
        handleConfirm={() =>
          stop.mutate(undefined, {
            onSuccess: (result) => {
              setOpen(false)
              toast.success(
                result.message ?? 'The epoch stops at the next safe point'
              )
            },
            onError: (error) => {
              setOpen(false)
              toast.error(error.message)
            },
          })
        }
      />
    </>
  )
}
