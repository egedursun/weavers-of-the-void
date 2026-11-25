import { useCallback, useMemo } from 'react'
import { type components } from '@/api/generated/schema'
import { type Permission, refusalIn, useTeamGate } from '@/api/teamGate'
import { formatInteger } from '@/lib/format'
import { TERMINAL_JOB_STATUSES, isJobStatus } from '@/constants/jobs'
import {
  useActionCatalogue,
  useActiveJobs,
  useRules,
  useWorldState,
} from './api'

type Job = components['schemas']['JobResponse']

export const BUSY_REASON = 'An epoch is running; this opens when it ends.'
export const READ_ONLY_REASON = 'A guest world is open read-only.'
export const NO_LLM_REASON =
  'The language model is not connected; this needs it.'

export function essenceReason(cost: number, essence: number): string {
  return `${formatInteger(cost)} essence needed; you have ${formatInteger(essence)}.`
}

export function useRuleLookup() {
  const rules = useRules()
  const table = useMemo(() => {
    const map = new Map<string, number>()
    for (const rule of rules.data ?? []) {
      map.set(`${rule.namespace}.${rule.key}`, rule.value)
    }
    return map
  }, [rules.data])
  return useCallback((path: string) => table.get(path), [table])
}

export function useCostText() {
  const catalogue = useActionCatalogue()
  const table = useMemo(
    () => new Map((catalogue.data ?? []).map((item) => [item.id, item])),
    [catalogue.data]
  )
  return useCallback((actionId: string) => table.get(actionId), [table])
}

type GateNeeds = {
  cost?: number
  world?: boolean
  llm?: boolean
  permission?: Permission | null
}

export function useGodGate() {
  const state = useWorldState()
  const essence = state.data?.creator?.essence ?? 0
  const busy = state.data?.epoch_running ?? false
  const readOnly = state.data?.read_only ?? false
  const llm = state.data?.llm_enabled ?? true
  const team = useTeamGate()
  const reason = useCallback(
    (needs: GateNeeds = {}): string | null => {
      if (readOnly) return READ_ONLY_REASON
      const refusal = refusalIn(team, needs.permission ?? null)
      if (refusal !== null) return refusal
      if (needs.llm && !llm) return NO_LLM_REASON
      if (needs.world && busy) return BUSY_REASON
      if (needs.cost !== undefined && needs.cost > essence)
        return essenceReason(needs.cost, essence)
      return null
    },
    [busy, essence, llm, readOnly, team]
  )
  return { essence, busy, readOnly, llm, reason, state }
}

export function isActiveJob(job: Job): boolean {
  return isJobStatus(job.status) && !TERMINAL_JOB_STATUSES.has(job.status)
}

export function useRunningJob(matches: (job: Job) => boolean): Job | undefined {
  const jobs = useActiveJobs()
  return (jobs.data ?? []).find((job) => isActiveJob(job) && matches(job))
}

export function paramEquals(job: Job, key: string, value: unknown): boolean {
  return job.params[key] === value
}
