import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NodeArcanaView = Schema['NodeArcanaView']
export type NodeMythicView = Schema['NodeMythicView']
export type GrammarView = Schema['GrammarView']
export type LabTextView = Schema['LabTextView']
export type VisView = Schema['VisView']
export type WarpingView = Schema['WarpingView']
export type LongevityView = Schema['LongevityView']
export type ChargeView = Schema['ChargeView']
export type UpkeepView = Schema['UpkeepView']
export type HeroquestView = Schema['HeroquestView']
export type MantlingView = Schema['MantlingView']
export type ServitorView = Schema['ServitorView']
export type GeasView = Schema['GeasView']
export type OfficeView = Schema['CosmicOfficeView']
export type SpellForm = Schema['SpellForm']
export type CosmicOffice = Schema['CosmicOffice']

export const arcanaKeys = {
  arcana: (nodeId: number) =>
    [...queryKeys.world.all, 'arcana-of', nodeId] as const,
  mythic: (nodeId: number) =>
    [...queryKeys.world.all, 'mythic-of', nodeId] as const,
  offices: () => [...queryKeys.world.all, 'cosmic-offices'] as const,
}

export function useNodeArcana(nodeId: number) {
  return useQuery({
    queryKey: arcanaKeys.arcana(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/arcana/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeMythic(nodeId: number) {
  return useQuery({
    queryKey: arcanaKeys.mythic(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/mythic/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useCosmicOffices() {
  return useQuery({
    queryKey: arcanaKeys.offices(),
    queryFn: () => unwrap(api.GET('/api/mythic/offices')),
  })
}

export type ArcanaAction =
  | 'rite_grammar:edit'
  | 'rite_grammar:delete'
  | 'lab_text:write'
  | 'lab_text:edit'
  | 'lab_text:delete'
  | 'vis:set'
  | 'vis:delete'
  | 'warping:edit'
  | 'warping:delete'
  | 'longevity:begin'
  | 'longevity:edit'
  | 'longevity:end'
  | 'enchantment:lay'
  | 'law_upkeep:edit'
  | 'law_upkeep:delete'
  | 'enchantment:dispel'
  | 'item_charge:edit'
  | 'heroquest:begin'
  | 'heroquest:edit'
  | 'heroquest:party'
  | 'heroquest:advance'
  | 'heroquest:delete'
  | 'mantling:edit'
  | 'mantling:delete'
  | 'servitor:make'
  | 'servitor:edit'
  | 'servitor:release'
  | 'geas:lay'
  | 'geas:edit'
  | 'geas:break'
  | 'geas:delete'
  | 'cosmic_office:appoint'
  | 'cosmic_office:edit'
  | 'cosmic_office:vacate'

export function useArcanaAction<Name extends ArcanaAction, T>(
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
