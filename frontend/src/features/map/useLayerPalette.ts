import { useMemo } from 'react'
import {
  type ThemeColorName,
  type ThemeColors,
} from '@/components/domain/useThemeColors'
import { type MapView } from './api'
import { type CellKey } from './mapEdges'
import { type LayerMode } from './mapModel'

export const SERIES_TOKENS: readonly ThemeColorName[] = [
  'chart-2',
  'chart-5',
  'chart-3',
  'warning',
  'rarity-mythic',
  'rarity-uncommon',
  'rarity-epic',
  'destructive',
]
export const CREATOR_TOKEN: ThemeColorName = 'brand-gold'
export const CREATOR_KEY = 'creator'

const EXTRA_TOKENS: readonly ThemeColorName[] = [
  'chart-1',
  'chart-4',
  'rarity-rare',
  'rarity-legendary',
  'brand-verdigris',
  'success',
  'primary',
  'rarity-common',
]
const UNKNOWN = 0

export type LayerCategory = {
  key: string
  label: string
  mapLabel: string
  count: number
  token: ThemeColorName
  color: string
}

export type RegionTint = { key: string; alpha: number }

export type LayerPalette = {
  mode: LayerMode
  tints: Map<number, RegionTint>
  categories: LayerCategory[]
  contested: Set<number>
  rulers: Set<number>
  colorOf: (key: string) => string
  cellKey: CellKey
}

const ALPHA: Record<LayerMode, number> = {
  terrain: 0,
  political: 0.2,
  realms: 0.15,
  regions: 0.3,
  creators: 0.3,
  religions: 0.42,
  languages: 0.42,
  ground: 0.45,
  soil: 0.45,
  climate: 0.4,
  land_use: 0.42,
  ley: 0.5,
  population: 0.45,
  followers: 0.45,
  soldiers: 0.45,
  wildlife: 0.45,
}

export const STOCK_BANDS = [
  { key: 'few', below: 1000 },
  { key: 'many', below: 10000 },
  { key: 'multitude', below: Number.POSITIVE_INFINITY },
] as const

const BAND_LABEL: Record<string, string> = {
  few: 'Fewer than a thousand',
  many: 'Thousands',
  multitude: 'Tens of thousands or more',
  sparse: 'Few wild herds',
  teeming: 'Many wild herds',
  wild: 'A land of beasts',
}

export const WILD_BANDS = [
  { key: 'sparse', below: 100 },
  { key: 'teeming', below: 300 },
  { key: 'wild', below: Number.POSITIVE_INFINITY },
] as const

export function wildBand(value: number): string | null {
  if (value <= 0) return null
  return WILD_BANDS.find((band) => value < band.below)?.key ?? null
}

export function stockBand(value: number): string | null {
  if (value <= 0) return null
  return STOCK_BANDS.find((band) => value < band.below)?.key ?? null
}

function words(value: string): string {
  const text = value.replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

const POLITICAL_ALPHA_GAIN = 0.2
const POLITICAL_SHARE_DIVISOR = 500

export type PaletteNames = {
  sons: ReadonlyMap<number, string>
  languages: ReadonlyMap<number, string>
  creatorName: string
}

function controlOf(view: MapView, regionId: number, topId: number) {
  return view.political[String(regionId)] ?? view.political[String(topId)]
}

function regionKey(
  view: MapView,
  mode: LayerMode,
  regionId: number,
  topId: number
): RegionTint | null {
  const alpha = ALPHA[mode]
  switch (mode) {
    case 'regions':
      return { key: String(regionId), alpha }
    case 'creators': {
      if (!(String(regionId) in view.region_creators)) return null
      const son = view.region_creators[String(regionId)]
      return { key: son === null ? CREATOR_KEY : `son:${son}`, alpha }
    }
    case 'religions': {
      const son = view.dominance[String(topId)]?.son_id
      return son ? { key: `son:${son}`, alpha } : null
    }
    case 'languages': {
      const language = view.dominance[String(topId)]?.language_id
      return language ? { key: `language:${language}`, alpha } : null
    }
    case 'ground':
    case 'soil':
    case 'climate':
    case 'land_use':
    case 'ley': {
      const ground = view.ground[String(regionId)] ?? view.ground[String(topId)]
      if (!ground) return null
      if (mode === 'ley') {
        if (ground.nexus) return { key: 'ley:nexus', alpha }
        return ground.ley_lines > 0 ? { key: 'ley:line', alpha } : null
      }
      const value =
        mode === 'ground'
          ? ground.terrain
          : mode === 'soil'
            ? ground.soil
            : mode === 'climate'
              ? ground.climate
              : ground.land_use
      return { key: `${mode}:${value}`, alpha }
    }
    case 'population':
    case 'followers':
    case 'soldiers': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? stockBand(stocks[mode]) : null
      return band ? { key: `${mode}:${band}`, alpha } : null
    }
    case 'wildlife': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? wildBand(stocks.wildlife ?? 0) : null
      return band ? { key: `wildlife:${band}`, alpha } : null
    }
    case 'realms': {
      const held =
        view.realms?.[String(regionId)] ?? view.realms?.[String(topId)]
      if (!held) return null
      return {
        key: `realm:${held.polity_id}`,
        alpha:
          alpha +
          Math.min(
            POLITICAL_ALPHA_GAIN,
            held.control / POLITICAL_SHARE_DIVISOR
          ),
      }
    }
    case 'political': {
      const control = controlOf(view, regionId, topId)
      if (!control) return null
      return {
        key: `ruler:${control.ruler_id}`,
        alpha:
          alpha +
          Math.min(
            POLITICAL_ALPHA_GAIN,
            control.share / POLITICAL_SHARE_DIVISOR
          ),
      }
    }
    default:
      return null
  }
}

function labelFor(
  view: MapView,
  key: string,
  names: PaletteNames,
  regionNames: ReadonlyMap<number, string>
): string {
  if (key === CREATOR_KEY) return names.creatorName
  const [kind, raw] = key.includes(':') ? key.split(':') : ['region', key]
  const id = Number(raw)
  if (kind === 'son') return names.sons.get(id) ?? `Son ${id}`
  if (kind === 'language') return names.languages.get(id) ?? `Language ${id}`
  if (kind === 'ley')
    return raw === 'nexus' ? 'Nexus of ley lines' : 'On a ley line'
  if (
    kind === 'population' ||
    kind === 'followers' ||
    kind === 'soldiers' ||
    kind === 'wildlife'
  )
    return BAND_LABEL[raw] ?? words(raw)
  if (
    kind === 'ground' ||
    kind === 'soil' ||
    kind === 'climate' ||
    kind === 'land_use'
  )
    return words(raw)
  if (kind === 'realm') {
    const held = Object.values(view.realms ?? {}).find(
      (item) => item.polity_id === id
    )
    return held?.name ?? `Realm ${id}`
  }
  if (kind === 'ruler') {
    const control = Object.values(view.political).find(
      (item) => item.ruler_id === id
    )
    return control?.ruler_name ?? `Ruler ${id}`
  }
  return regionNames.get(id) ?? `Region ${id}`
}

function neighbourTokens(view: MapView): Map<string, ThemeColorName> {
  const regions = [...view.geometry.regions].sort(
    (left, right) => right.size - left.size || left.id - right.id
  )
  const chosen = new Map<number, number>()
  for (const region of regions) {
    const taken = new Set(
      [...region.neighbours, ...region.bordering, region.parent_id ?? -1]
        .map((id) => chosen.get(id))
        .filter((slot): slot is number => slot !== undefined)
    )
    let slot = 0
    while (taken.has(slot) && slot < SERIES_TOKENS.length - 1) slot += 1
    chosen.set(region.id, slot)
  }
  return new Map(
    [...chosen].map(([id, slot]) => [String(id), SERIES_TOKENS[slot]])
  )
}

export function buildLayerPalette(
  view: MapView,
  mode: LayerMode,
  names: PaletteNames,
  tokens: ThemeColors
): LayerPalette {
  const tints = new Map<number, RegionTint>()
  const counts = new Map<string, number>()
  const contested = new Set<number>()
  const rulers = new Set<number>()
  const regionNames = new Map(
    view.points
      .filter((point) => point.entity.entity_type === 'region')
      .map((point) => [point.entity.id, point.entity.name])
  )
  if (mode !== 'terrain') {
    for (const region of view.geometry.regions) {
      const tint = regionKey(view, mode, region.id, region.top_level_id)
      if (!tint) continue
      tints.set(region.id, tint)
      counts.set(tint.key, (counts.get(tint.key) ?? 0) + 1)
      if (mode !== 'political') continue
      const control = controlOf(view, region.id, region.top_level_id)
      if (!control) continue
      rulers.add(control.ruler_id)
      if (control.contested) contested.add(region.id)
    }
  }
  const sorted = [...counts.entries()].sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0])
  )
  const regionTokens = mode === 'regions' ? neighbourTokens(view) : null
  const colorByKey = new Map<string, string>()
  let series = 0
  let extra = 0
  const categories = sorted.map(([key, count]): LayerCategory => {
    let token: ThemeColorName
    if (key === CREATOR_KEY) token = CREATOR_TOKEN
    else if (regionTokens) token = regionTokens.get(key) ?? SERIES_TOKENS[0]
    else if (series < SERIES_TOKENS.length) token = SERIES_TOKENS[series++]
    else token = EXTRA_TOKENS[extra++ % EXTRA_TOKENS.length]
    const color = tokens[token]
    colorByKey.set(key, color)
    const label = labelFor(view, key, names, regionNames)
    return {
      key,
      label: key === CREATOR_KEY ? `${label} (the god himself)` : label,
      mapLabel: label,
      count,
      token,
      color,
    }
  })
  const cells = view.geometry.cells
  const waterRegions = new Set(
    view.geometry.regions
      .filter((region) => region.is_water)
      .map((region) => region.id)
  )
  const cellKey: CellKey = (cell) => {
    if (cells.known[cell] === UNKNOWN) return null
    const region = cells.region[cell]
    if (region === null || region === undefined) return null
    if (cells.water[cell] && !waterRegions.has(region)) return null
    return tints.get(region)?.key ?? null
  }
  return {
    mode,
    tints,
    categories,
    contested,
    rulers,
    colorOf: (key) => colorByKey.get(key) ?? tokens['muted-foreground'],
    cellKey,
  }
}

export function useLayerPalette(
  view: MapView | undefined,
  mode: LayerMode,
  names: PaletteNames,
  tokens: ThemeColors
): LayerPalette | null {
  return useMemo(
    () => (view ? buildLayerPalette(view, mode, names, tokens) : null),
    [view, mode, names, tokens]
  )
}
