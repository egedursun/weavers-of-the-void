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

export const floraKeys = {
  crops: (id: number) => [...loreKeys.entity(id), 'crops'] as const,
  life: (id: number) => [...loreKeys.state, 'world-life', id] as const,
}

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

export type UseKind = components['schemas']['UseKindView']
export type TotemView = components['schemas']['TotemView']
export type RangeMap = components['schemas']['SpeciesRangeMap']

export type WildAction =
  | 'species:create'
  | 'species:prey'
  | 'species:host'
  | 'species:custom_use'
  | 'use_kind:create'
  | 'use_kind:edit'
  | 'use_kind:drop'
  | 'herd:drop'
  | 'people:totem'
  | 'beast:create'
  | 'beast:slay'
  | 'beast:treasure'
  | 'plant:edit'
  | 'crop:set'
  | 'crop:drop'
  | 'crop_pest:set'
  | 'world:life'

export function runWild(name: WildAction, body: Record<string, unknown>) {
  return unwrap(
    api.POST(`/api/actions/${name}` as '/api/actions/species:prey', {
      body: body as never,
    })
  )
}

export function useWildAction<T>(
  name: WildAction,
  toBody: (vars: T) => Record<string, unknown>,
  onDone?: () => void
) {
  return useGodAction<T>({
    run: (vars) => runWild(name, toBody(vars)),
    onDone: () => onDone?.(),
  })
}

export const wildExtraKeys = {
  useKinds: () => [...loreKeys.state, 'use-kinds'] as const,
  totem: (id: number) => [...loreKeys.entity(id), 'totem'] as const,
  range: (id: number) => [...loreKeys.state, 'range-map', id] as const,
}

export function useUseKinds() {
  return useQuery({
    queryKey: wildExtraKeys.useKinds(),
    queryFn: () => unwrap(api.GET('/api/use-kinds')),
  })
}

export function useTotem(id: number) {
  return useQuery({
    queryKey: wildExtraKeys.totem(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/totem', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useRangeMap(id: number | null) {
  return useQuery({
    queryKey: wildExtraKeys.range(id ?? 0),
    enabled: id !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/species/{species_id}/range-map', {
          params: { path: { species_id: id ?? 0 } },
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
