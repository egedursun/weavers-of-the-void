import { describe, expect, it } from 'vitest'
import { type ThemeColors } from '@/components/domain/useThemeColors'
import { type MapView } from './api'
import {
  CREATOR_KEY,
  SERIES_TOKENS,
  buildLayerPalette,
} from './useLayerPalette'

const TOKENS = new Proxy({} as ThemeColors, {
  get: (_, key) => `token-${String(key)}`,
})

const region = (id: number, top = id) => ({ id, top_level_id: top })

const VIEW = {
  points: [],
  geometry: { regions: [region(1), region(2), region(3), region(4, 1)] },
  region_creators: { '1': null, '2': 7, '3': 7, '4': 8 },
  dominance: {
    '1': { son_id: 7, language_id: null },
    '2': { son_id: 8, language_id: 3 },
  },
  political: {
    '1': {
      ruler_id: 9,
      ruler_name: 'Kethrani',
      ruler_type: 'people',
      share: 100,
      contested: false,
    },
  },
} as unknown as MapView

const NAMES = {
  sons: new Map([
    [7, 'Ithren'],
    [8, 'Vaskor'],
  ]),
  languages: new Map([[3, 'Old Tongue']]),
  creatorName: 'The Creator',
}

describe('layer palette', () => {
  it('orders categories by region count and keeps the creator gold', () => {
    const palette = buildLayerPalette(VIEW, 'creators', NAMES, TOKENS)
    expect(palette.categories.map((item) => item.key)).toEqual([
      'son:7',
      CREATOR_KEY,
      'son:8',
    ])
    expect(palette.categories[0].token).toBe(SERIES_TOKENS[0])
    expect(palette.categories[1].token).toBe('brand-gold')
    expect(palette.categories[1].label).toContain('the Creator in person')
    expect(palette.colorOf('son:7')).toBe(`token-${SERIES_TOKENS[0]}`)
  })

  it('tints sub-regions by their top region for faith and language', () => {
    const faith = buildLayerPalette(VIEW, 'religions', NAMES, TOKENS)
    expect(faith.tints.get(4)?.key).toBe('son:7')
    const language = buildLayerPalette(VIEW, 'languages', NAMES, TOKENS)
    expect(language.categories.map((item) => item.label)).toEqual([
      'Old Tongue',
    ])
  })

  it('weights political tint by share and is empty on terrain', () => {
    const political = buildLayerPalette(VIEW, 'political', NAMES, TOKENS)
    expect(political.tints.get(1)?.alpha).toBeCloseTo(0.4)
    expect(political.categories[0].label).toBe('Kethrani')
    expect(buildLayerPalette(VIEW, 'terrain', NAMES, TOKENS).tints.size).toBe(0)
  })
})
