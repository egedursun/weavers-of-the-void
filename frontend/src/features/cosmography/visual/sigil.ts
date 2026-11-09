import { type DimensionRecord } from '../api'

export function sigilOf(dimension: DimensionRecord) {
  return {
    id: dimension.id,
    kind: dimension.dimension_kind,
    veil: dimension.veil,
    stability: dimension.stability,
    magic: dimension.magic,
  }
}
