import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type CyclesView = Schema['CyclesView']
export type CosmosCyclesView = Schema['CosmosCyclesView']
export type ReadingView = Schema['ReadingView']
export type PlanView = Schema['PlanView']
export type GiftView = Schema['GiftRecordView']
export type CircuitView = Schema['CircuitView']
export type ConfederationView = Schema['ConfederationView']

export const cycleKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'cycles-of', nodeId] as const,
  cosmos: () => [...queryKeys.world.all, 'cycles-cosmos'] as const,
}

export function useNodeCycles(nodeId: number) {
  return useQuery({
    queryKey: cycleKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/cycles/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useCosmosCycles() {
  return useQuery({
    queryKey: cycleKeys.cosmos(),
    queryFn: () => unwrap(api.GET('/api/cycles/cosmos')),
  })
}

export type CycleAction =
  | 'union:set'
  | 'union:edit'
  | 'union:delete'
  | 'stress:set'
  | 'stress:edit'
  | 'stress:delete'
  | 'stress_reading:set'
  | 'stress_reading:edit'
  | 'stress_reading:delete'
  | 'asabiyya:set'
  | 'asabiyya:edit'
  | 'asabiyya:delete'
  | 'challenge:strike'
  | 'challenge:edit'
  | 'challenge:delete'
  | 'plan:create'
  | 'plan:edit'
  | 'plan:advance'
  | 'plan:expose'
  | 'plan:delete'
  | 'gift:give'
  | 'gift:return'
  | 'gift:refuse'
  | 'gift:edit'
  | 'gift:delete'
  | 'circuit:create'
  | 'circuit:edit'
  | 'circuit:route'
  | 'circuit:pass'
  | 'circuit:delete'
  | 'debt:set'
  | 'debt:edit'
  | 'debt:delete'
  | 'kinship:set'
  | 'kinship:edit'
  | 'kinship:delete'
  | 'alliance:set'
  | 'alliance:edit'
  | 'alliance:delete'
  | 'reproduction:set'
  | 'reproduction:edit'
  | 'reproduction:delete'
  | 'caste:set'
  | 'caste:edit'
  | 'caste:delete'
  | 'camp:set'
  | 'camp:edit'
  | 'camp:route'
  | 'camp:move'
  | 'camp:delete'
  | 'confederation:create'
  | 'confederation:edit'
  | 'confederation:members'
  | 'confederation:dissolve'
  | 'confederation:delete'
  | 'legacy:set'
  | 'legacy:edit'
  | 'legacy:delete'
  | 'indenture:create'
  | 'indenture:edit'
  | 'indenture:release'
  | 'indenture:delete'
  | 'slave_market:set'
  | 'slave_market:edit'
  | 'slave_market:delete'
  | 'manumission:free'
  | 'manumission:edit'
  | 'manumission:delete'

export function useCycleAction<Name extends CycleAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
