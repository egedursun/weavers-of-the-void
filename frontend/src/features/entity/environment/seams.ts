import { useWorldMaterials } from '../economy/api'
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

export function seamLabel(
  key: string,
  worldNames: Record<string, string>
): string {
  if (key.startsWith(WORLD_SEAM))
    return worldNames[key.slice(WORLD_SEAM.length)] ?? 'A strange stone'
  return plain(MINERALS, key)
}

export function useSeamNames(worldId: number | null): Record<string, string> {
  const materials = useWorldMaterials(worldId)
  return Object.fromEntries(
    (materials.data?.materials ?? [])
      .filter((item) => item.world_material_id != null)
      .map((item) => [String(item.world_material_id), item.label])
  )
}
