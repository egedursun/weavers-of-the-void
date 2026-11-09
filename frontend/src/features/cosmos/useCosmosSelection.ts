import { useCallback } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { useEvent } from '@/realtime'
import { toast } from 'sonner'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import {
  type CommandSection,
  type CosmosPanel,
  type CosmosSearch,
} from './cosmosSearch'

export type CosmosSelection = {
  galaxyId: number | undefined
  worldId: number | undefined
  starId: number | undefined
  panel: CosmosPanel
  section: CommandSection | undefined
  selectWorld: (worldId: number) => void
  selectGalaxy: (galaxyId: number) => void
  selectStar: (starId: number) => void
  openPanel: (panel: CosmosPanel, section?: CommandSection) => void
}

export function useCosmosSelection(): CosmosSelection {
  const search = useSearch({ from: '/_app/cosmos' })
  const globalWorld = useGlobalWorld()
  const navigate = useNavigate({ from: '/cosmos' })

  const update = useCallback(
    (patch: (previous: CosmosSearch) => CosmosSearch) =>
      navigate({
        search: (previous) => ({ ...previous, ...patch(previous) }),
        replace: true,
      }),
    [navigate]
  )

  const selectWorld = useCallback(
    (worldId: number) =>
      void update((previous) => ({
        world: worldId,
        star: undefined,
        panel: previous.panel === 'star' ? 'world' : previous.panel,
      })),
    [update]
  )

  const selectGalaxy = useCallback(
    (galaxyId: number) =>
      void update(() => ({
        galaxy: galaxyId,
        world: undefined,
        star: undefined,
      })),
    [update]
  )

  const selectStar = useCallback(
    (starId: number) => void update(() => ({ star: starId, panel: 'star' })),
    [update]
  )

  const openPanel = useCallback(
    (panel: CosmosPanel, section?: CommandSection) =>
      void update(() => ({ panel, section })),
    [update]
  )

  useEvent('world.born', (event) => {
    selectWorld(event.payload.world_id)
    if (event.payload.name) toast.success(`${event.payload.name} was born`)
  })

  return {
    galaxyId: search.galaxy,
    worldId: search.world ?? globalWorld ?? undefined,
    starId: search.star,
    panel: search.panel ?? (search.star !== undefined ? 'star' : 'world'),
    section: search.section,
    selectWorld,
    selectGalaxy,
    selectStar,
    openPanel,
  }
}
