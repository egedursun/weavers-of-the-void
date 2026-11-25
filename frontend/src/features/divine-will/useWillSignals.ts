import { useWillSession } from './api'

export function useWillSignals() {
  const session = useWillSession()
  const head = session.data?.pages[0] ?? null
  const recent = head?.cycles ?? []
  const running =
    head?.running_cycle_id != null ||
    recent.some((cycle) => cycle.status === 'running')
  const awaiting = recent.some(
    (cycle) => cycle.status === 'awaiting_confirmation'
  )
  const total = head?.session?.cycle_count ?? 0
  const completed = Math.max(
    0,
    total -
      recent.filter(
        (cycle) =>
          cycle.status === 'running' || cycle.status === 'awaiting_confirmation'
      ).length
  )
  return {
    session: head?.session ?? null,
    ready: head !== null,
    running,
    awaiting,
    total,
    remembered: Math.min(completed, head?.remembered_cycles ?? 0),
    limit: head?.remembered_cycles ?? 0,
  }
}
