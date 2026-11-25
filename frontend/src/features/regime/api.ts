import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type RegimeNodeView = Schema['RegimeNodeView']
export type CosmosRegimeView = Schema['CosmosRegimeView']
export type SchoolView = Schema['SchoolView']
export type PowerBaseView = Schema['PowerBaseView']
export type AcademicFreedomView = Schema['AcademicFreedomView']
export type ExamSittingView = Schema['ExamSittingView']

export const regimeKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'regime-of', nodeId] as const,
  cosmos: () => [...queryKeys.world.all, 'regime-cosmos'] as const,
}

export function useNodeRegime(nodeId: number) {
  return useQuery({
    queryKey: regimeKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/regime/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useCosmosRegime() {
  return useQuery({
    queryKey: regimeKeys.cosmos(),
    queryFn: () => unwrap(api.GET('/api/regime/cosmos')),
  })
}

export type RegimeAction =
  | 'regime:set'
  | 'regime:edit'
  | 'regime:delete'
  | 'coalition:enrol'
  | 'coalition:edit'
  | 'coalition:purge'
  | 'coalition:delete'
  | 'patronage:bind'
  | 'patronage:edit'
  | 'patronage:delete'
  | 'venal_office:sell'
  | 'venal_office:sinecure'
  | 'venal_office:edit'
  | 'venal_office:delete'
  | 'power_base:measure'
  | 'power_base:set'
  | 'power_base:edit'
  | 'power_base:delete'
  | 'kin_segment:set'
  | 'kin_segment:edit'
  | 'kin_segment:delete'
  | 'breeding:create'
  | 'breeding:edit'
  | 'breeding:delete'
  | 'examination:set'
  | 'examination:sit'
  | 'examination:edit'
  | 'examination:delete'
  | 'exam_sitting:edit'
  | 'exam_sitting:delete'
  | 'credential:grant'
  | 'credential:edit'
  | 'credential:delete'
  | 'academic_freedom:set'
  | 'academic_freedom:edit'
  | 'academic_freedom:delete'
  | 'school:found'
  | 'school:edit'
  | 'school:delete'
  | 'disciple:admit'
  | 'disciple:edit'
  | 'disciple:delete'

export function useRegimeAction<Name extends RegimeAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
