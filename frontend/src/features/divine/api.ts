import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '@/features/entity/api/keys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type GodDivinity = Schema['GodDivinity']
export type GoalView = Schema['GodGoalView']
export type WoundView = Schema['DivineWoundView']
export type AvatarView = Schema['GodAvatarView']
export type StandingView = Schema['DivineStandingView']
export type CreatorDivinity = Schema['CreatorDivinity']
export type WorldDivinity = Schema['WorldDivinity']
export type RulingView = Schema['CouncilRulingView']
export type LawProfileView = Schema['NaturalLawProfileView']
export type OuterProfileView = Schema['OuterBeingProfileView']

export const divineKeys = {
  god: (id: number) => [...loreKeys.entity(id), 'divinity'] as const,
  regard: (id: number) => [...loreKeys.entity(id), 'regard'] as const,
  creator: [...loreKeys.state, 'creator-divinity'] as const,
  world: (id: number) => [...loreKeys.state, 'world-divinity', id] as const,
  rulings: [...loreKeys.state, 'council-rulings'] as const,
  law: (id: number) => [...loreKeys.entity(id), 'law-profile'] as const,
  outer: (id: number) => [...loreKeys.entity(id), 'outer-profile'] as const,
}

export function useGodDivinity(godId: number) {
  return useQuery({
    queryKey: divineKeys.god(godId),
    queryFn: () =>
      unwrap(
        api.GET('/api/gods/{god_id}/divinity', {
          params: { path: { god_id: godId } },
        })
      ),
  })
}

export function useRegard(communityId: number) {
  return useQuery({
    queryKey: divineKeys.regard(communityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/regard', {
          params: { path: { entity_id: communityId } },
        })
      ),
  })
}

export function useCreatorDivinity() {
  return useQuery({
    queryKey: divineKeys.creator,
    queryFn: () => unwrap(api.GET('/api/creator/divinity')),
  })
}

export function useWorldDivinity(worldId: number) {
  return useQuery({
    queryKey: divineKeys.world(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/divinity', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function useRulings() {
  return useQuery({
    queryKey: divineKeys.rulings,
    queryFn: () => unwrap(api.GET('/api/council/rulings')),
  })
}

export function useLawProfile(lawId: number) {
  return useQuery({
    queryKey: divineKeys.law(lawId),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/law-profile', {
          params: { path: { entity_id: lawId } },
        })
      ),
  })
}

export function useOuterProfile(beingId: number) {
  return useQuery({
    queryKey: divineKeys.outer(beingId),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/outer-profile', {
          params: { path: { entity_id: beingId } },
        })
      ),
  })
}

export type DivineAction =
  | 'domain_hook:set'
  | 'domain_hook:clear'
  | 'god_goal:set'
  | 'god_goal:edit'
  | 'god_goal:drop'
  | 'divine_standing:set'
  | 'divine_standing:clear'
  | 'divine_wound:inflict'
  | 'divine_wound:edit'
  | 'divine_wound:remove'
  | 'avatar:manifest'
  | 'avatar:edit'
  | 'avatar:withdraw'
  | 'taboo:set'
  | 'taboo:remove'
  | 'attention:set'
  | 'attention:clear'
  | 'divine_pact:seal'
  | 'ruling:decree'
  | 'ruling:edit'
  | 'ruling:revoke'
  | 'law_profile:edit'
  | 'outer_profile:edit'
  | 'breach:open'
  | 'breach:edit'
  | 'breach:close'

export function runDivine(name: DivineAction, body: Record<string, unknown>) {
  return unwrap(
    api.POST(`/api/actions/${name}` as '/api/actions/taboo:set', {
      body: body as never,
    })
  )
}

export function useDivineAction<T>(
  name: DivineAction,
  toBody: (vars: T) => Record<string, unknown>,
  onDone?: () => void
) {
  return useGodAction<T>({
    run: (vars) => runDivine(name, toBody(vars)),
    onDone: () => onDone?.(),
  })
}
