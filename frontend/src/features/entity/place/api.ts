import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components, paths } from '@/api/generated/schema'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'

export type PlaceProfile = components['schemas']['PlaceProfileView']
export type PlaceSecret = components['schemas']['PlaceSecretView']

type PlaceAction =
  | 'place:create'
  | 'place:edit'
  | 'place:release'
  | 'place:secret'
  | 'place:secret_edit'
  | 'place:reveal'
  | 'place:secret_delete'
  | 'pilgrimage:clear'
  | 'pilgrimage:declare'

export type ActionBody<Action extends PlaceAction> = NonNullable<
  paths[`/api/actions/${Action}`]['post']['requestBody']
>['content']['application/json']

export const placeKeys = {
  profile: (id: number) => [...loreKeys.entity(id), 'place-profile'] as const,
}

export function usePlaceProfile(id: number) {
  return useQuery({
    queryKey: placeKeys.profile(id),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/places/{place_id}/profile', {
          params: { path: { place_id: id } },
        })
      ),
  })
}

export function usePlaceAction<Action extends PlaceAction>(
  action: Action,
  success?: string
) {
  return useGodAction<ActionBody<Action>>({
    success,
    run: (body) =>
      unwrap(
        api.POST(`/api/actions/${action}` as '/api/actions/place:edit', {
          body: body as ActionBody<'place:edit'>,
        })
      ),
  })
}
