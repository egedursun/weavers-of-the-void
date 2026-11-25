import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'

export type EnginePhase = components['schemas']['EnginePhaseView']
export type PhaseStage = EnginePhase['stage']
export type ActionResponse = components['schemas']['ActionResponse']
export type IntegrityTask = components['schemas']['IntegrityTaskView']
export type IntegrityResult = components['schemas']['IntegrityResult']

export type EngineSeed = components['schemas']['EngineSeed']

export const engineKeys = {
  phases: [...queryKeys.rules.all, 'engine', 'phases'] as const,
  seed: [...queryKeys.world.all, 'engine', 'seed'] as const,
  integrity: [...queryKeys.rules.all, 'engine', 'integrity'] as const,
}

export function useEnginePhases() {
  return useQuery({
    queryKey: engineKeys.phases,
    queryFn: () => unwrap(api.GET('/api/engine/phases')),
  })
}

export function useEngineSeed() {
  return useQuery({
    queryKey: engineKeys.seed,
    queryFn: () => unwrap(api.GET('/api/engine/seed')),
  })
}

export function useRunPhase() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ lever: 'engine:run_phase' }],
    mutationFn: (phase: string) =>
      unwrap(
        api.POST('/api/actions/engine:run_phase', {
          body: { phase, replay: false },
        })
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.ledger.all })
    },
  })
}

export function useSetPhaseSwitch() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'PUT', path: '/api/rules/{namespace}/{key}' }],
    mutationFn: (change: { rule: string; on: boolean }) =>
      unwrap(
        api.PUT('/api/rules/{namespace}/{key}', {
          params: { path: { namespace: 'engine_phases', key: change.rule } },
          body: { value: change.on ? 1 : 0 },
        })
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rules.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
  })
}

export function useIntegrityTasks() {
  return useQuery({
    queryKey: engineKeys.integrity,
    queryFn: () => unwrap(api.GET('/api/integrity/tasks')),
  })
}

export function useRunIntegrity() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/integrity/{task}' }],
    mutationFn: (task: IntegrityTask['task']) =>
      unwrap(api.POST('/api/integrity/{task}', { params: { path: { task } } })),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
  })
}

export type IntegrityFinding = components['schemas']['IntegrityFindingView']

export function useIntegrityFindings() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'integrity', 'findings'] as const,
    queryFn: () => unwrap(api.GET('/api/integrity/findings')),
  })
}

export function useResolveFinding() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/integrity/findings/resolve' }],
    mutationFn: (finding: IntegrityFinding) =>
      unwrap(
        api.POST('/api/integrity/findings/resolve', {
          body: {
            check: finding.check,
            invariant: finding.invariant,
            table: finding.table,
            column: finding.column,
            key: finding.key,
          },
        })
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
  })
}
