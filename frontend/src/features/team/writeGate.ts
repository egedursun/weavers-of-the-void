import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type ActGate, everyRefused } from '@/api/mutation'
import {
  type Permission,
  type TeamGate,
  refusalIn,
  useTeamGate,
} from '@/api/teamGate'
import { godKeys } from '@/features/pantheon/api'
import {
  type PlainWrite,
  WRITE_PERMISSIONS,
  type WriteRule,
} from './writePermissions'

export type WriteTarget = PlainWrite | { lever: string }

const CHECKING = 'Checking what you may do…'
const UNKNOWN_LEVER: Permission = 'edit_world'

function ruleOf(target: WriteTarget): WriteRule {
  if ('lever' in target) return target
  const methods: Partial<Record<string, WriteRule>> =
    WRITE_PERMISSIONS[target.path]
  return methods[target.method] ?? 'none'
}

export function needsCatalogue(writes: readonly WriteTarget[]): boolean {
  return writes.some((target) => typeof ruleOf(target) === 'object')
}

export function refusalOfRule(
  gate: TeamGate | null,
  rule: WriteRule,
  levers: ReadonlyMap<string, Permission> | null,
  chosen: Permission | null | undefined
): string | null {
  if (gate === null) return null
  if (typeof rule === 'object') {
    if (levers === null) return CHECKING
    return refusalIn(gate, levers.get(rule.lever) ?? UNKNOWN_LEVER)
  }
  switch (rule) {
    case 'none':
    case 'account':
    case 'author':
    case 'workspace_admin':
      return null
    case 'admin':
    case 'universe_admin':
      return gate.adminRefusal
    case 'undo':
    case 'divine_will_mode':
    case 'presence_record':
      return chosen === undefined ? null : refusalIn(gate, chosen)
    default:
      return refusalIn(gate, rule)
  }
}

export function useLeverPermissions(enabled: boolean) {
  return useQuery({
    queryKey: godKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    staleTime: Infinity,
    enabled,
    select: (items) =>
      new Map(items.map((item) => [item.id, item.permission] as const)),
  })
}

export function useHoldFields(enabled: boolean) {
  return useQuery({
    queryKey: godKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    staleTime: Infinity,
    enabled,
    select: (items) =>
      new Map(
        items
          .filter((item) => item.hold_fields.length > 0)
          .map((item) => [item.path, item.hold_fields] as const)
      ),
  })
}

export function useWriteRefusal(
  writes: readonly WriteTarget[],
  chosen?: Permission | null
): string | null {
  const gate = useTeamGate()
  const levers = useLeverPermissions(gate !== null && needsCatalogue(writes))
  const known = levers.data ?? null
  if (chosen === null) return null
  if (writes.length === 0)
    return chosen === undefined ? null : refusalIn(gate, chosen)
  let first: string | null = null
  for (const target of writes) {
    const refusal = refusalOfRule(gate, ruleOf(target), known, chosen)
    if (refusal === null) return null
    first ??= refusal
  }
  return first
}

export type AdjustGate =
  | { acts: readonly [ActGate, ...ActGate[]]; writes?: never }
  | { writes: readonly [WriteTarget, ...WriteTarget[]]; acts?: never }

export function useAdjustGate(
  acts: readonly ActGate[] | undefined,
  writes: readonly WriteTarget[] | undefined
): ActGate {
  const refused = useWriteRefusal(writes ?? [])
  return writes ? { blockedReason: refused } : everyRefused(acts ?? [])
}
