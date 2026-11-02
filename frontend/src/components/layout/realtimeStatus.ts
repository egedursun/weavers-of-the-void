import { type StreamStatus } from '@/realtime'

export const STATUS_LABEL: Record<StreamStatus, string> = {
  connecting: 'Connecting to live updates',
  open: 'Live updates connected',
  reconnecting: 'Reconnecting to live updates',
  closed: 'Live updates stopped',
}

export const STATUS_SHORT: Record<StreamStatus, string> = {
  connecting: 'Linking',
  open: 'Live',
  reconnecting: 'Relinking',
  closed: 'Offline',
}

export const DOT_CLASS: Record<StreamStatus, string> = {
  connecting: 'bg-muted-foreground',
  open: 'bg-success',
  reconnecting: 'bg-warning',
  closed: 'bg-destructive',
}

export const STATUS_TEXT_CLASS: Record<StreamStatus, string> = {
  connecting: 'text-muted-foreground',
  open: 'text-success',
  reconnecting: 'text-warning',
  closed: 'text-destructive',
}
