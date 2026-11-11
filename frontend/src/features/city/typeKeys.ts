import { Home, type LucideIcon } from 'lucide-react'
import type { components } from '@/api/generated/schema'

type Schema = components['schemas']

export const DWELLING_ICON: LucideIcon = Home
const BUILDING = 'building-type'
const DWELLING = 'dwelling-type'

export function buildingTypeKey(
  worldId: number,
  kind: Schema['StructureKind']
): string {
  return `${BUILDING}:${worldId}:${kind}`
}

export function dwellingTypeKey(
  worldId: number,
  housing: Schema['HousingLevel']
): string {
  return `${DWELLING}:${worldId}:${housing}`
}

export type TypeSelection =
  | { kind: 'building'; worldId: number; type: Schema['StructureKind'] }
  | { kind: 'dwelling'; worldId: number; type: Schema['HousingLevel'] }

export function parseTypeKey(key: string | null): TypeSelection | null {
  if (!key) return null
  const [prefix, world, type] = key.split(':')
  const worldId = Number(world)
  if (!type || !Number.isInteger(worldId) || worldId <= 0) return null
  if (prefix === BUILDING)
    return { kind: 'building', worldId, type: type as Schema['StructureKind'] }
  if (prefix === DWELLING)
    return { kind: 'dwelling', worldId, type: type as Schema['HousingLevel'] }
  return null
}
