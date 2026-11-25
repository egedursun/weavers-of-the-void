import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type GodDominionView = Schema['GodDominionView']
export type PlaceDominionView = Schema['PlaceDominionView']
export type WorldDominionView = Schema['WorldDominionView']
export type ClaimView = Schema['DominionClaimView']
export type ScaleView = Schema['ScaleView']
export type GodDesignView = Schema['GodDesignView']
export type ImageView = Schema['ImageView']
export type MiracleView = Schema['MiracleView']
export type CreatureView = Schema['CreatureView']
export type ThroneView = Schema['ThroneView']
export type MagicSiteView = Schema['MagicSiteView']
export type RuleView = Schema['RegionRuleView']
export type DivineScale = Schema['DivineScale']
export type CreatureDeed = Schema['CreatureDeed']
export type CreatureLesson = Schema['CreatureLesson']
export type MagicSiteKind = Schema['MagicSiteKind']
export type MagicSchool = Schema['MagicSchool']

export const dominionKeys = {
  god: (nodeId: number) =>
    [...queryKeys.world.all, 'dominion-of', nodeId] as const,
  place: (placeId: number) =>
    [...queryKeys.world.all, 'dominion-place', placeId] as const,
  world: (worldId: number) =>
    [...queryKeys.world.all, 'dominion-world', worldId] as const,
}

export function useGodDominion(nodeId: number) {
  return useQuery({
    queryKey: dominionKeys.god(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/dominion/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function usePlaceDominion(placeId: number, enabled = true) {
  return useQuery({
    queryKey: dominionKeys.place(placeId),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/dominion/place/{place_id}', {
          params: { path: { place_id: placeId } },
        })
      ),
  })
}

export function useWorldDominion(worldId: number, enabled = true) {
  return useQuery({
    queryKey: dominionKeys.world(worldId),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/dominion/world/{world_id}', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export type DominionAction =
  | 'dominion:set'
  | 'dominion:delete'
  | 'god_scale:set'
  | 'god_scale:delete'
  | 'god_design:edit'
  | 'god_design:delete'
  | 'god_image:edit'
  | 'god_image:delete'
  | 'miracle_record:edit'
  | 'miracle_record:delete'
  | 'magic_site:create'
  | 'magic_site:edit'
  | 'magic_site:reveal'
  | 'magic_site:delete'
  | 'throne:create'
  | 'throne:edit'
  | 'throne:delete'
  | 'divine_creature:raise'
  | 'divine_creature:edit'
  | 'divine_creature:teach'
  | 'divine_creature:weight'
  | 'divine_creature:release'

export function useDominionAction<Name extends DominionAction, T>(
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
