import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'

export type SpeciesCard = components['schemas']['SpeciesCard']
export type BeastCard = components['schemas']['BeastCard']
export type FoodWeb = components['schemas']['FoodWeb']
export type HerdView = components['schemas']['HerdView']

export const wildKeys = {
  species: (id: number) => [...loreKeys.entity(id), 'ecology'] as const,
  beast: (id: number) => [...loreKeys.entity(id), 'beast'] as const,
  web: (id: number) => [...loreKeys.entity(id), 'food-web'] as const,
  herds: (id: number) => [...loreKeys.entity(id), 'herds'] as const,
}

export function useSpecies(id: number) {
  return useQuery({
    queryKey: wildKeys.species(id),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/ecology', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useBeast(id: number) {
  return useQuery({
    queryKey: wildKeys.beast(id),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/beast', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useFoodWeb(id: number) {
  return useQuery({
    queryKey: wildKeys.web(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/food-web', {
          params: { path: { region_id: id } },
        })
      ),
  })
}

export function useHerds(id: number) {
  return useQuery({
    queryKey: wildKeys.herds(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/herds', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

type Edit = { values: Record<string, unknown>; release?: string[] }

export function useSpeciesEdit(id: number) {
  return useGodAction<Edit>({
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/species:edit', {
          body: {
            species_id: id,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
}

export function useBeastEdit(id: number) {
  return useGodAction<Edit>({
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/beast:edit', {
          body: {
            beast_id: id,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
}
