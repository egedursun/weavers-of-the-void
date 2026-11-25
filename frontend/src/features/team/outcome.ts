import { toast } from 'sonner'
import { openTeamView } from './teamSignals'

type Waiting = {
  queued?: { title: string } | null
  proposal?: { title: string } | null
}

export type Outcome = 'done' | 'queued' | 'proposed'

function waitingPart(result: unknown): Waiting {
  return result !== null && typeof result === 'object' ? result : {}
}

export function announceWaiting(result: unknown): Outcome {
  const waiting = waitingPart(result)
  if (waiting.queued) {
    toast.info('Waiting for the age to end — it runs right after', {
      description: waiting.queued.title,
      action: { label: 'See the queue', onClick: () => openTeamView('queue') },
    })
    return 'queued'
  }
  if (waiting.proposal) {
    toast.info('Sent for canon review', {
      description: `${waiting.proposal.title} waits for an administrator.`,
      action: {
        label: 'Open the Team panel',
        onClick: () => openTeamView('team'),
      },
    })
    return 'proposed'
  }
  return 'done'
}

export function toastDone(
  result: unknown,
  message: string,
  options?: Parameters<typeof toast.success>[1]
): void {
  if (announceWaiting(result) === 'done') toast.success(message, options)
}
