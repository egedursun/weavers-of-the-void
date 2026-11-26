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
  WAITS_FOR_AGE,
  WRITE_PERMISSIONS,
  type WriteRule,
} from './writePermissions'

export type WriteTarget = PlainWrite | { lever: string }

const CHECKING = 'Checking what you may do…'
const AGE_RUNNING_REASON =
  'An epoch is running; rules can be changed again when it ends.'
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

function waitsForAge(target: WriteTarget): boolean {
  return !('lever' in target) && WAITS_FOR_AGE.has(target.path)
}

export function useAgeRefusal(writes: readonly WriteTarget[]): string | null {
  const bound = writes.some(waitsForAge)
  const state = useQuery({
    queryKey: godKeys.state,
    queryFn: () => unwrap(api.GET('/api/state')),
    enabled: bound,
  })
  return bound && state.data?.epoch_running ? AGE_RUNNING_REASON : null
}

export function useWriteRefusal(
  writes: readonly WriteTarget[],
  chosen?: Permission | null
): string | null {
  const gate = useTeamGate()
  const levers = useLeverPermissions(gate !== null && needsCatalogue(writes))
  const age = useAgeRefusal(writes)
  const known = levers.data ?? null
  if (chosen === null) return age
  if (writes.length === 0)
    return chosen === undefined ? null : refusalIn(gate, chosen)
  let first: string | null = null
  for (const target of writes) {
    const refusal = refusalOfRule(gate, ruleOf(target), known, chosen)
    if (refusal === null) return age
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
