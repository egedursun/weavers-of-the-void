import { type components } from '@/api/generated/schema'
import { type ThemeColorName } from '@/components/domain/useThemeColors'
import { type MapStratum } from './api'

export type PassageState = components['schemas']['DeepPassageState']
export type PassageKind = components['schemas']['DeepPassageKind']

export type DeepPattern =
  | 'frost'
  | 'ripples'
  | 'abyss'
  | 'sheen'
  | 'drips'
  | 'columns'
  | 'roots'
  | 'cracks'
  | 'radiance'
  | 'embers'
  | 'mist'

export type HollowSurface = 'floor' | 'water' | 'molten'

export type StratumLook = {
  fill: ThemeColorName
  glow: ThemeColorName
  pattern: DeepPattern
  shade: number
  surface: HollowSurface
}

export const STRATUM_LOOK: Record<MapStratum, StratumLook> = {
  permafrost_layer: {
    fill: 'rarity-common',
    glow: 'rarity-rare',
    pattern: 'frost',
    shade: 0.15,
    surface: 'floor',
  },
  aquifer: {
    fill: 'rarity-rare',
    glow: 'chart-3',
    pattern: 'ripples',
    shade: 0.3,
    surface: 'water',
  },
  under_ocean: {
    fill: 'chart-3',
    glow: 'brand-verdigris',
    pattern: 'abyss',
    shade: 0.2,
    surface: 'water',
  },
  reservoir: {
    fill: 'warning',
    glow: 'rarity-legendary',
    pattern: 'sheen',
    shade: 0.6,
    surface: 'floor',
  },
  cavern_upper: {
    fill: 'rarity-legendary',
    glow: 'brand-gold',
    pattern: 'drips',
    shade: 0.35,
    surface: 'floor',
  },
  cavern_middle: {
    fill: 'rarity-uncommon',
    glow: 'success',
    pattern: 'columns',
    shade: 0.42,
    surface: 'floor',
  },
  fault_zone: {
    fill: 'muted-foreground',
    glow: 'destructive',
    pattern: 'cracks',
    shade: 0.25,
    surface: 'floor',
  },
  cavern_lower: {
    fill: 'rarity-epic',
    glow: 'rarity-uncommon',
    pattern: 'roots',
    shade: 0.2,
    surface: 'floor',
  },
  hollow_interior: {
    fill: 'success',
    glow: 'brand-gold',
    pattern: 'radiance',
    shade: 0.05,
    surface: 'floor',
  },
  magma_sea: {
    fill: 'destructive',
    glow: 'warning',
    pattern: 'embers',
    shade: 0.1,
    surface: 'molten',
  },
  deep_underworld: {
    fill: 'rarity-mythic',
    glow: 'foreground',
    pattern: 'mist',
    shade: 0.22,
    surface: 'floor',
  },
}

export type PassageLook = {
  token: ThemeColorName
  width: number
  dash: readonly number[]
  casing: boolean
}

export const PASSAGE_LOOK: Record<PassageState, PassageLook> = {
  open: { token: 'brand-gold', width: 2.2, dash: [], casing: true },
  digging: { token: 'warning', width: 1.6, dash: [5, 3], casing: false },
  flooded: {
    token: 'rarity-rare',
    width: 2.4,
    dash: [9, 3, 2, 3],
    casing: true,
  },
  collapsed: { token: 'destructive', width: 1.4, dash: [2, 5], casing: false },
  sealed: { token: 'rarity-epic', width: 1.8, dash: [1, 3], casing: true },
}

export type ShaftGlyph = 'trail' | 'shaft' | 'mouth'

export const PASSAGE_GLYPH: Record<PassageKind, ShaftGlyph> = {
  level: 'trail',
  vertical: 'shaft',
  opening: 'mouth',
}

export const ROCK_TOKEN: ThemeColorName = 'brand-ink'
export const ROCK_GRAIN_TOKEN: ThemeColorName = 'rarity-common'
export const ROCK_SEAM_TOKEN: ThemeColorName = 'muted-foreground'
export const SEABED_TOKEN: ThemeColorName = 'chart-3'
