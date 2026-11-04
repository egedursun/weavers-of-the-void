import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'
import { MINERALS, plain } from './labels'

export const WORLD_SEAM = 'world:'

export const BIOMES: string[] = [
  'Shallow water',
  'Deep water',
  'Shore',
  'Dry lowland',
  'Lowland',
  'Wet lowland',
  'Dry hills',
  'Wet hills',
  'Mountains',
  'Peaks',
]

export function useWorldMaterials(worldId: number) {
  return useQuery({
    queryKey: [...loreKeys.cosmos, 'materials', worldId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/materials', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function seamLabel(
  key: string,
  worldNames: Record<string, string>
): string {
  if (key.startsWith(WORLD_SEAM))
    return worldNames[key.slice(WORLD_SEAM.length)] ?? 'A strange stone'
  return plain(MINERALS, key)
}

export function useSeamNames(worldId: number): Record<string, string> {
  const materials = useWorldMaterials(worldId)
  return Object.fromEntries(
    (materials.data?.materials ?? [])
      .filter((item) => item.world_material_id != null)
      .map((item) => [String(item.world_material_id), item.label])
  )
}
