import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NodeEvolutionView = Schema['NodeEvolutionView']
export type TraitView = Schema['StockTraitView']
export type LineageMarkView = Schema['LineageMarkView']
export type ServiceView = Schema['ServiceView']
export type CarrierView = Schema['CarrierView']
export type PlagueResponseView = Schema['PlagueResponseView']
export type CureResearchView = Schema['CureResearchView']
export type HerdRef = Schema['HerdRef']
export type EvolvedTrait = Schema['EvolvedTrait']
export type KeystoneRole = Schema['KeystoneRole']
export type PlagueResponse = Schema['PlagueResponse']
export type LandAct = Schema['LandAct']

export const evolutionKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'evolution-of', nodeId] as const,
}

export function useNodeEvolution(nodeId: number) {
  return useQuery({
    queryKey: evolutionKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/evolution/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type EvolutionAction =
  | 'species_trait:set'
  | 'species_trait:edit'
  | 'species_trait:delete'
  | 'lineage:mark'
  | 'lineage:edit'
  | 'lineage:delete'
  | 'species_ecology:edit'
  | 'ecosystem_service:set'
  | 'ecosystem_service:edit'
  | 'ecosystem_service:delete'
  | 'herd:release'
  | 'carrier:add'
  | 'carrier:edit'
  | 'carrier:delete'
  | 'plague_response:set'
  | 'plague_response:edit'
  | 'plague_response:delete'
  | 'cure_research:start'
  | 'cure_research:edit'
  | 'cure_research:delete'
  | 'world_cycle:edit'
  | 'world_cycle:reset'
  | 'land:reshape'
  | 'disease:edit'
  | 'environment:set'
  | 'environment:unlock'

export function useEvolutionAction<Name extends EvolutionAction, T>(
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
