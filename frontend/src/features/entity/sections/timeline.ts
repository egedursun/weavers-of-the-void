import { strongestKind } from '@/features/chronicle/chronicleKinds'
import { type ChronicleLine } from '../api/types'

export type Column = { epoch: number; count: number; kind: string | null }

export function timelineColumns(
  lines: ChronicleLine[],
  birthEpoch: number,
  currentEpoch: number
): Column[] {
  const first = Math.min(birthEpoch, ...lines.map((line) => line.epoch))
  const last = Math.max(currentEpoch, ...lines.map((line) => line.epoch))
  const columns: Column[] = []
  for (let epoch = Math.max(1, first); epoch <= last; epoch += 1) {
    const here = lines.filter((line) => line.epoch === epoch)
    columns.push({
      epoch,
      count: here.length,
      kind: here.length ? strongestKind(here.map((line) => line.kind)) : null,
    })
  }
  return columns
}
