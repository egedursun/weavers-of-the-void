import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NodeLawView = Schema['NodeLawView']
export type PrecedentView = Schema['PrecedentView']
export type AppealView = Schema['AppealView']
export type OracleCaseView = Schema['OracleCaseView']
export type RegistryView = Schema['RegistryView']
export type JurisdictionView = Schema['JurisdictionView']
export type PardonView = Schema['PardonView']
export type OutlawView = Schema['OutlawView']
export type PrisonView = Schema['PrisonView']
export type PrisonerView = Schema['PrisonerView']
export type AgentMotiveView = Schema['AgentMotiveView']
export type CellView = Schema['CellView']
export type MoleHuntView = Schema['MoleHuntView']
export type DefectionView = Schema['DefectionView']
export type KillingView = Schema['KillingView']

export const lawKeys = {
  of: (nodeId: number) => [...queryKeys.world.all, 'law-of', nodeId] as const,
}

export function useNodeLaw(nodeId: number) {
  return useQuery({
    queryKey: lawKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/law/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type LawAction =
  | 'legal_system:set'
  | 'legal_system:edit'
  | 'legal_system:delete'
  | 'precedent:add'
  | 'precedent:edit'
  | 'precedent:delete'
  | 'appeal:file'
  | 'appeal:edit'
  | 'appeal:hear'
  | 'appeal:delete'
  | 'oracle:answer'
  | 'registry:add'
  | 'registry:edit'
  | 'registry:delete'
  | 'jurisdiction:set'
  | 'jurisdiction:edit'
  | 'jurisdiction:delete'
  | 'pardon:grant'
  | 'amnesty:declare'
  | 'pardon:delete'
  | 'outlaw:declare'
  | 'outlaw:edit'
  | 'outlaw:delete'
  | 'prison:set'
  | 'prison:edit'
  | 'prison:delete'
  | 'prisoner:jail'
  | 'prisoner:edit'
  | 'prisoner:free'
  | 'spy_cell:add'
  | 'spy_cell:edit'
  | 'spy_cell:delete'
  | 'mole_hunt:order'
  | 'mole_hunt:delete'
  | 'defection:make'
  | 'defection:edit'
  | 'defection:delete'
  | 'killing:add'
  | 'killing:edit'
  | 'killing:delete'

export function useLawAction<Name extends LawAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
