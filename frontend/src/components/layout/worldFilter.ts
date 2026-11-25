import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { followUniverse, universePersisted } from '@/lib/universeStorage'

export const WORLD_FILTER_ROUTES = [
  '/map',
  '/network',
  '/chronicle',
  '/cosmos',
  '/atlas',
] as const

export type WorldFilterRoute = (typeof WORLD_FILTER_ROUTES)[number]

const DEPENDENT_SEARCH: Record<WorldFilterRoute, readonly string[]> = {
  '/map': ['epoch', 'focus'],
  '/network': ['focus', 'from', 'to'],
  '/chronicle': ['epoch', 'line'],
  '/cosmos': ['star'],
  '/atlas': ['select', 'page'],
}

type WorldFilterStore = {
  worldId: number | null
  setWorldId: (worldId: number | null) => void
}

export const useWorldFilter = create<WorldFilterStore>()(
  persist(
    (set) => ({
      worldId: null,
      setWorldId: (worldId) => set({ worldId }),
    }),
    universePersisted<WorldFilterStore>('aerona.world-filter')
  )
)

followUniverse(useWorldFilter)

export function useGlobalWorld(): number | null {
  return useWorldFilter((state) => state.worldId)
}

export function filteredRoute(pathname: string): WorldFilterRoute | null {
  return WORLD_FILTER_ROUTES.find((route) => pathname === route) ?? null
}

export function worldSearch(
  route: WorldFilterRoute,
  previous: Record<string, unknown>,
  worldId: number | null
): Record<string, unknown> {
  const next: Record<string, unknown> = {
    ...previous,
    world: worldId ?? undefined,
  }
  for (const key of DEPENDENT_SEARCH[route]) delete next[key]
  for (const key of Object.keys(next))
    if (next[key] === undefined) delete next[key]
  return next
}
