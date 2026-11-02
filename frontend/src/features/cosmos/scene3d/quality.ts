import { type CosmosQuality } from '../useCosmosViewSettings'

export type QualityPreset = {
  pixelRatio: number
  samples: number
  dust: number
  bloom: boolean
  widthSegments: number
  heightSegments: number
}

export const QUALITY_PRESETS: Record<CosmosQuality, QualityPreset> = {
  low: {
    pixelRatio: 1,
    samples: 0,
    dust: 0.3,
    bloom: false,
    widthSegments: 40,
    heightSegments: 24,
  },
  medium: {
    pixelRatio: 1.5,
    samples: 2,
    dust: 0.65,
    bloom: true,
    widthSegments: 72,
    heightSegments: 48,
  },
  high: {
    pixelRatio: 2,
    samples: 4,
    dust: 1,
    bloom: true,
    widthSegments: 96,
    heightSegments: 64,
  },
}
