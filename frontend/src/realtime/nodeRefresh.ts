import { type Query, type QueryClient } from '@tanstack/react-query'
import { queryKeys } from '@/api/queryKeys'
import { whenIdle } from './idleGate'

const WORLD = queryKeys.world.all[0]
const ALWAYS_SHOWN = new Set<unknown>(['state', 'opportunities'])

function isIdField(field: string): boolean {
  return field === 'id' || field.endsWith('_id')
}

function listsNode(field: string, value: unknown, nodeId: number): boolean {
  return (
    field.endsWith('_ids') && Array.isArray(value) && value.includes(nodeId)
  )
}

export function mentionsNode(data: unknown, nodeId: number): boolean {
  const pending: unknown[] = [data]
  const seen = new Set<object>()
  while (pending.length > 0) {
    const value = pending.pop()
    if (value === null || typeof value !== 'object' || seen.has(value)) continue
    seen.add(value)
    if (Array.isArray(value)) {
      pending.push(...(value as unknown[]))
      continue
    }
    for (const [field, item] of Object.entries(value)) {
      if (item === nodeId && isIdField(field)) return true
      if (listsNode(field, item, nodeId)) return true
      if (item !== null && typeof item === 'object') pending.push(item)
    }
  }
  return false
}

export function showsNode(query: Query, nodeId: number): boolean {
  const key = query.queryKey
  if (key[0] !== WORLD) return false
  if (ALWAYS_SHOWN.has(key[1])) return true
  if (key.includes(nodeId)) return true
  return mentionsNode(query.state.data, nodeId)
}

type PendingViews = { key: string; nodes: Set<number> }

const pendingByClient = new WeakMap<QueryClient, PendingViews>()
const clientCount = { value: 0 }

function pendingFor(queryClient: QueryClient): PendingViews {
  const known = pendingByClient.get(queryClient)
  if (known) return known
  clientCount.value += 1
  const created = {
    key: `node-views:${clientCount.value}`,
    nodes: new Set<number>(),
  }
  pendingByClient.set(queryClient, created)
  return created
}

export function refreshNodeViews(queryClient: QueryClient, nodeId: number) {
  const pending = pendingFor(queryClient)
  pending.nodes.add(nodeId)
  whenIdle(pending.key, () => {
    const nodes = [...pending.nodes]
    pending.nodes.clear()
    if (nodes.length === 0) return
    void queryClient.invalidateQueries({
      predicate: (query) => nodes.some((nodeId) => showsNode(query, nodeId)),
    })
  })
}
