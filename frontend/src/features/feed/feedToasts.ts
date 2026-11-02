import { type ServerEvent } from '@/realtime'
import { toast } from 'sonner'

const STREAM_CLOSING_KINDS: ReadonlySet<ServerEvent['kind']> = new Set([
  'stream.hello',
  'epoch.finished',
  'epoch.stopped',
])

export function closesStreams(event: ServerEvent): boolean {
  return STREAM_CLOSING_KINDS.has(event.kind)
}

export function isLiveEvent(event: ServerEvent, since: number): boolean {
  const at = Date.parse(event.at)
  return Number.isNaN(at) || at >= since
}

export function feedToast(event: ServerEvent, since: number): void {
  if (!isLiveEvent(event, since)) return
  switch (event.kind) {
    case 'epoch.finished':
      toast.success(`Epoch ${event.payload.new_epoch} began`)
      return
    case 'system.error':
      toast.error(event.payload.text)
      return
    case 'council.held':
      toast(`Council: ${event.payload.topic}`, {
        description: event.payload.passed
          ? 'The motion passed.'
          : 'The motion failed.',
      })
      return
    default:
      return
  }
}
