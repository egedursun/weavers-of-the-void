import { type ChronicleLine } from '@/features/entity/api/types'
import { DEFAULT_HIDDEN_KINDS } from './chronicleKinds'

export type LineFilter = {
  q: string
  kinds: ReadonlySet<string> | null
  world: number | null
}

export function keepsLine(line: ChronicleLine, filter: LineFilter): boolean {
  if (
    filter.kinds
      ? !filter.kinds.has(line.kind)
      : DEFAULT_HIDDEN_KINDS.has(line.kind)
  )
    return false
  if (
    filter.world !== null &&
    line.world_id !== null &&
    line.world_id !== filter.world
  )
    return false
  const needle = filter.q.trim().toLowerCase()
  return !needle || line.text.toLowerCase().includes(needle)
}

export function filterLines(
  lines: ChronicleLine[],
  filter: LineFilter
): ChronicleLine[] {
  return lines.filter((line) => keepsLine(line, filter))
}
