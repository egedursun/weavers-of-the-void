import { type DimensionRecord } from '../api'
import { type DimensionState } from './dimensionMaterial'

export function stateOf(dimension: DimensionRecord): DimensionState {
  return {
    id: dimension.id,
    kind: dimension.dimension_kind,
    veil: dimension.veil,
    stability: dimension.stability,
    magic: dimension.magic,
    time_factor: dimension.time_factor,
  }
}
