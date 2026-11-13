export type MadeKind = 'vehicle' | 'unit' | 'equipment' | 'dish' | 'building'

export type KindSelection = { kind: MadeKind; worldId: number; id: number }

const PREFIX = 'made'
const KINDS: readonly MadeKind[] = [
  'vehicle',
  'unit',
  'equipment',
  'dish',
  'building',
]

export function kindKey(kind: MadeKind, worldId: number, id: number): string {
  return `${PREFIX}:${kind}:${worldId}:${id}`
}

export function parseKindKey(key: string | null): KindSelection | null {
  if (!key) return null
  const [prefix, kind, world, id] = key.split(':')
  const worldId = Number(world)
  const rowId = Number(id)
  if (prefix !== PREFIX || !KINDS.includes(kind as MadeKind)) return null
  if (
    !Number.isInteger(worldId) ||
    worldId <= 0 ||
    !Number.isInteger(rowId) ||
    rowId <= 0
  )
    return null
  return { kind: kind as MadeKind, worldId, id: rowId }
}
