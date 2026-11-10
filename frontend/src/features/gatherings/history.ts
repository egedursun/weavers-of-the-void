import { useState } from 'react'
import { type CollectionView } from './api'

const WORKING = 'Working on it.'

export function why(blocked: string | null, ...pending: boolean[]) {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

export function spanOf(collection: CollectionView): string {
  if (collection.end_epoch === null)
    return `since epoch ${collection.start_epoch}, still unfolding`
  if (collection.end_epoch === collection.start_epoch)
    return `in epoch ${collection.start_epoch}`
  return `epochs ${collection.start_epoch} to ${collection.end_epoch}`
}

export function useOpenHistory() {
  const [open, setOpen] = useState<number | null>(null)
  return {
    open,
    toggle: (id: number) => setOpen((current) => (current === id ? null : id)),
    show: (id: number) => setOpen(id),
    close: () => setOpen(null),
  }
}
