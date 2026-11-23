import { useMemo } from 'react'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import {
  type ThemeColorName,
  type ThemeColors,
} from '@/components/domain/useThemeColors'
import { REMNANT_KIND } from '@/features/arsenal/labels'
import { GROUP_FORM } from '@/features/creatureGroups/labels'
import { MONEY_FORM } from '@/features/entity/economy/labels'
import { DANGER_SOURCE } from '@/features/entity/environment/regionLabels'
import { PROTECTION_BASIS } from '@/features/protectedNature/labels'
import { WAVE_ORIGIN } from '@/features/seaWaves/labels'
import { type MapView } from './api'
import { type CellKey } from './mapEdges'
import { type LayerMode } from './mapModel'
import {
  type RangeShade,
  rangeAlpha,
  rangeBand,
  rangeLabel,
} from './speciesRange'

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

type Schemas = components['schemas']
type KindConcept = Schemas['KindConcept']

const CONCEPT_NOUN: Partial<Record<KindConcept, string>> = {
  cuisine: 'Cuisine',
  garment: 'Garment',
  organisation: 'Organisation',
}

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
  de_jure: 0.12,
  regions: 0.3,
  creators: 0.3,
  religions: 0.42,
  dominion: 0.3,
  languages: 0.42,
  ground: 0.45,
  soil: 0.45,
  climate: 0.4,
  land_use: 0.42,
  rainfall: 0.42,
  danger: 0.45,
  scars: 0.45,
  sacred: 0.45,
  ley: 0.5,
  population: 0.45,
  followers: 0.45,
  soldiers: 0.45,
  wildlife: 0.45,
  species_range: 0.3,
  desirability: 0.45,
  coverage: 0.45,
  niches: 0.45,
  solidarity: 0.45,
  rings: 0.45,
  centrality: 0.45,
  nutrients: 0.45,
  networks: 0.45,
  hidden: 0.45,
  works: 0.45,
  cuisines: 0.42,
  dress: 0.42,
  organisations: 0.42,
  money: 0.42,
  remnants: 0.5,
  waves: 0.5,
  groups: 0.45,
  protected: 0.45,
}

const KIND_LAYERS: Partial<Record<LayerMode, KindConcept>> = {
  cuisines: 'cuisine',
  dress: 'garment',
  organisations: 'organisation',
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
  low: 'Low',
  middling: 'Middling',
  high: 'High',
  few_ways: 'Few ways of life filled',
  many_ways: 'Many ways of life filled',
  crowded_ways: 'Crowded with ways of life',
  soft: 'Gone soft',
  steady: 'Holding together',
  forged: 'Forged as one',
  net_one: 'Reached by one network',
  net_few: 'Reached by a few networks',
  net_many: 'Reached by many networks',
  hid_one: 'One thing hidden here',
  hid_few: 'A few things hidden here',
  hid_many: 'Much hidden here',
  works_one: 'One work under way',
  works_few: 'A few works under way',
  works_many: 'Many works under way',
  frontier_soft: 'A frontier gone soft',
  frontier_steady: 'A frontier holding together',
  frontier_forged: 'A frontier forged as one',
  gardens: 'Gardens and dairy',
  forestry: 'Fuel wood',
  grain: 'Grain',
  ranching: 'Herds',
  wilds: 'Beyond the markets',
  daily: 'Daily needs',
  weekly: 'Weekly market',
  rare: 'Rare goods',
  poor: 'Poor soil',
  fair: 'Fair soil',
  rich: 'Rich soil',
  salted: 'Saline fields',
}

export const RAIN_BANDS = [
  { key: 'arid', below: 20 },
  { key: 'dry', below: 40 },
  { key: 'moderate', below: 60 },
  { key: 'wet', below: 80 },
  { key: 'drenched', below: Number.POSITIVE_INFINITY },
] as const

const HOLY_FROM = 40

const LAND_LABEL: Record<string, string> = {
  arid: 'Arid',
  dry: 'Dry',
  moderate: 'Moderate rain',
  wet: 'Wet',
  drenched: 'Drenched',
  holy: 'Holy ground that draws pilgrims',
  hallowed: 'Hallowed ground',
}

export function rainBand(value: number): string {
  return RAIN_BANDS.find((band) => value < band.below)?.key ?? 'drenched'
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

export const SHARE_BANDS = [
  { key: 'low', below: 34 },
  { key: 'middling', below: 67 },
  { key: 'high', below: Number.POSITIVE_INFINITY },
] as const

export function shareBand(value: number): string | null {
  if (value <= 0) return null
  return SHARE_BANDS.find((band) => value < band.below)?.key ?? null
}

export const NICHE_BANDS = [
  { key: 'few_ways', below: 3 },
  { key: 'many_ways', below: 6 },
  { key: 'crowded_ways', below: Number.POSITIVE_INFINITY },
] as const

export const NETWORK_BANDS = [
  { key: 'net_one', below: 2 },
  { key: 'net_few', below: 4 },
  { key: 'net_many', below: Number.POSITIVE_INFINITY },
] as const

export const HIDDEN_BANDS = [
  { key: 'hid_one', below: 2 },
  { key: 'hid_few', below: 4 },
  { key: 'hid_many', below: Number.POSITIVE_INFINITY },
] as const

export const WORKS_BANDS = [
  { key: 'works_one', below: 2 },
  { key: 'works_few', below: 4 },
  { key: 'works_many', below: Number.POSITIVE_INFINITY },
] as const

export function worksBand(value: number): string | null {
  if (value <= 0) return null
  return WORKS_BANDS.find((band) => value < band.below)?.key ?? null
}

export function hiddenBand(value: number): string | null {
  if (value <= 0) return null
  return HIDDEN_BANDS.find((band) => value < band.below)?.key ?? null
}

export function networkBand(value: number): string | null {
  if (value <= 0) return null
  return NETWORK_BANDS.find((band) => value < band.below)?.key ?? null
}

export function nicheBand(value: number): string | null {
  if (value <= 0) return null
  return NICHE_BANDS.find((band) => value < band.below)?.key ?? null
}

export const SOLIDARITY_BANDS = [
  { key: 'soft', below: 34 },
  { key: 'steady', below: 67 },
  { key: 'forged', below: Number.POSITIVE_INFINITY },
] as const

export function solidarityBand(value: number, frontier: number): string | null {
  if (value <= 0) return null
  const band = SOLIDARITY_BANDS.find((item) => value < item.below)?.key ?? null
  return band && frontier > 0 ? `frontier_${band}` : band
}

export const RING_BANDS = [
  'gardens',
  'forestry',
  'grain',
  'ranching',
  'wilds',
] as const
export const RANK_BANDS = ['daily', 'weekly', 'rare'] as const
const SALTED_FROM = 40
export const SOIL_BANDS = [
  { key: 'poor', below: 34 },
  { key: 'fair', below: 67 },
  { key: 'rich', below: Number.POSITIVE_INFINITY },
] as const

export function ringBand(value: number): string | null {
  return value > 0 ? (RING_BANDS[value - 1] ?? null) : null
}

export function rankBand(value: number): string | null {
  return value > 0 ? (RANK_BANDS[value - 1] ?? null) : null
}

export function soilBand(soil: number, salt: number): string | null {
  if (salt >= SALTED_FROM) return 'salted'
  if (soil <= 0) return null
  return SOIL_BANDS.find((band) => soil < band.below)?.key ?? null
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
    case 'dominion': {
      const rule =
        view.dominion?.[String(regionId)] ?? view.dominion?.[String(topId)]
      if (!rule) return null
      return {
        key: `god:${rule.god_id}`,
        alpha:
          alpha +
          Math.min(POLITICAL_ALPHA_GAIN, rule.share / POLITICAL_SHARE_DIVISOR),
      }
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
    case 'rainfall':
    case 'danger':
    case 'scars':
    case 'sacred': {
      const ground = view.ground[String(regionId)] ?? view.ground[String(topId)]
      if (!ground) return null
      if (mode === 'rainfall')
        return { key: `rainfall:${rainBand(ground.rainfall ?? 0)}`, alpha }
      if (mode === 'danger')
        return ground.danger_source
          ? { key: `danger:${ground.danger_source}`, alpha }
          : null
      if (mode === 'scars')
        return ground.scar && (ground.scar_depth ?? 0) > 0
          ? { key: `scars:${ground.scar}`, alpha }
          : null
      const sacred = ground.sacredness ?? 0
      if (sacred <= 0) return null
      return {
        key: `sacred:${sacred >= HOLY_FROM ? 'holy' : 'hallowed'}`,
        alpha,
      }
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
    case 'desirability':
    case 'coverage': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? shareBand(stocks[mode] ?? 0) : null
      return band ? { key: `${mode}:${band}`, alpha } : null
    }
    case 'networks': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? networkBand(stocks.networks ?? 0) : null
      return band ? { key: `networks:${band}`, alpha } : null
    }
    case 'hidden': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? hiddenBand(stocks.hidden ?? 0) : null
      return band ? { key: `hidden:${band}`, alpha } : null
    }
    case 'works': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? worksBand(stocks.works ?? 0) : null
      return band ? { key: `works:${band}`, alpha } : null
    }
    case 'niches': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? nicheBand(stocks.niches ?? 0) : null
      return band ? { key: `niches:${band}`, alpha } : null
    }
    case 'solidarity': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks
        ? solidarityBand(stocks.solidarity ?? 0, stocks.frontier ?? 0)
        : null
      return band ? { key: `solidarity:${band}`, alpha } : null
    }
    case 'rings': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? ringBand(stocks.ring ?? 0) : null
      return band ? { key: `rings:${band}`, alpha } : null
    }
    case 'centrality': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? rankBand(stocks.market ?? 0) : null
      return band ? { key: `centrality:${band}`, alpha } : null
    }
    case 'nutrients': {
      const stocks = view.stocks[String(regionId)] ?? view.stocks[String(topId)]
      const band = stocks ? soilBand(stocks.soil ?? 0, stocks.salt ?? 0) : null
      return band ? { key: `nutrients:${band}`, alpha } : null
    }
    case 'cuisines':
    case 'dress':
    case 'organisations': {
      const concept = KIND_LAYERS[mode]
      const ways =
        view.kinds?.[String(regionId)] ?? view.kinds?.[String(topId)] ?? []
      const top = ways.find((item) => item.concept === concept)
      return top ? { key: `${mode}:${top.kind_id}`, alpha } : null
    }
    case 'money': {
      const money =
        view.money?.[String(regionId)] ?? view.money?.[String(topId)]
      return money ? { key: `money:${money.form}`, alpha } : null
    }
    case 'protected': {
      const area =
        view.protected?.[String(regionId)] ?? view.protected?.[String(topId)]
      return area
        ? {
            key: `protected:${area.basis}`,
            alpha: (alpha * Math.max(area.strength, 20)) / 100,
          }
        : null
    }
    case 'groups': {
      const group =
        view.groups?.[String(regionId)] ?? view.groups?.[String(topId)]
      return group
        ? {
            key: `groups:${group.form}`,
            alpha: (alpha * Math.min(100, Math.max(group.size / 50, 20))) / 100,
          }
        : null
    }
    case 'waves': {
      const wave = view.waves?.[String(regionId)] ?? view.waves?.[String(topId)]
      return wave
        ? {
            key: `waves:${wave.origin}`,
            alpha: (alpha * Math.max(wave.height, 20)) / 100,
          }
        : null
    }
    case 'remnants': {
      const remnant =
        view.remnants?.[String(regionId)] ?? view.remnants?.[String(topId)]
      return remnant
        ? {
            key: `remnants:${remnant.kind}`,
            alpha: (alpha * Math.max(remnant.density, 20)) / 100,
          }
        : null
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
    case 'de_jure': {
      const right =
        view.de_jure?.[String(regionId)] ?? view.de_jure?.[String(topId)]
      if (!right) return null
      return {
        key: `dejure:${right.title_id}`,
        alpha: right.held_by_right ? alpha : alpha + POLITICAL_ALPHA_GAIN,
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
  if (kind === 'danger') return dangerLabel(raw)
  if (kind === 'rainfall' || kind === 'sacred')
    return LAND_LABEL[raw] ?? words(raw)
  if (kind === 'scars') return words(raw)
  if (
    kind === 'population' ||
    kind === 'followers' ||
    kind === 'soldiers' ||
    kind === 'wildlife' ||
    kind === 'desirability' ||
    kind === 'coverage' ||
    kind === 'niches' ||
    kind === 'networks' ||
    kind === 'hidden' ||
    kind === 'works' ||
    kind === 'solidarity' ||
    kind === 'rings' ||
    kind === 'centrality' ||
    kind === 'nutrients'
  )
    return BAND_LABEL[raw] ?? words(raw)
  if (
    kind === 'ground' ||
    kind === 'soil' ||
    kind === 'climate' ||
    kind === 'land_use'
  )
    return words(raw)
  if (kind === 'range') return rangeLabel(raw)
  if (kind === 'money')
    return MONEY_FORM[raw as Schemas['MoneyForm']]?.label ?? words(raw)
  if (kind === 'protected')
    return (
      PROTECTION_BASIS[raw as Schemas['ProtectionBasis']]?.label ?? words(raw)
    )
  if (kind === 'remnants')
    return REMNANT_KIND[raw as Schemas['RemnantKind']]?.label ?? words(raw)
  if (kind === 'groups')
    return GROUP_FORM[raw as Schemas['GroupForm']]?.label ?? words(raw)
  if (kind === 'waves')
    return WAVE_ORIGIN[raw as Schemas['WaveOrigin']]?.label ?? words(raw)
  const concept = KIND_LAYERS[kind as LayerMode]
  if (concept) {
    const named = Object.values(view.kinds ?? {})
      .flat()
      .find((item) => item.concept === concept && item.kind_id === id)
    return named?.name ?? `${CONCEPT_NOUN[concept]} ${id}`
  }
  if (kind === 'god') {
    const rule = Object.values(view.dominion ?? {}).find(
      (item) => item.god_id === id
    )
    return rule
      ? `${rule.name}${rule.rivals > 0 ? `, against ${plural(rule.rivals, 'rival', 'rivals')}` : ''}`
      : `God ${id}`
  }
  if (kind === 'realm') {
    const held = Object.values(view.realms ?? {}).find(
      (item) => item.polity_id === id
    )
    return held?.name ?? `Realm ${id}`
  }
  if (kind === 'dejure') {
    const right = Object.values(view.de_jure ?? {}).find(
      (item) => item.title_id === id
    )
    return right?.name ?? `Title ${id}`
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

const RANGE_TOKEN: ThemeColorName = 'success'

function rangeTint(
  range: RangeShade | null,
  regionId: number
): RegionTint | null {
  if (!range) return null
  const band = rangeBand(range.cells.get(regionId) ?? 0, range.peak)
  return band ? { key: `range:${band}`, alpha: rangeAlpha(band) } : null
}

export function buildLayerPalette(
  view: MapView,
  mode: LayerMode,
  names: PaletteNames,
  tokens: ThemeColors,
  range: RangeShade | null = null
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
      const tint =
        mode === 'species_range'
          ? rangeTint(range, region.id)
          : regionKey(view, mode, region.id, region.top_level_id)
      if (!tint) continue
      tints.set(region.id, tint)
      counts.set(tint.key, (counts.get(tint.key) ?? 0) + 1)
      if (mode === 'dominion') {
        const rule =
          view.dominion?.[String(region.id)] ??
          view.dominion?.[String(region.top_level_id)]
        if (rule && rule.rivals > 0) contested.add(region.id)
        continue
      }
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
    else if (key.startsWith('range:')) token = RANGE_TOKEN
    else if (regionTokens) token = regionTokens.get(key) ?? SERIES_TOKENS[0]
    else if (series < SERIES_TOKENS.length) token = SERIES_TOKENS[series++]
    else token = EXTRA_TOKENS[extra++ % EXTRA_TOKENS.length]
    const color = tokens[token]
    colorByKey.set(key, color)
    const label = labelFor(view, key, names, regionNames)
    return {
      key,
      label: key === CREATOR_KEY ? `${label} (the Creator in person)` : label,
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
  tokens: ThemeColors,
  range: RangeShade | null = null
): LayerPalette | null {
  return useMemo(
    () => (view ? buildLayerPalette(view, mode, names, tokens, range) : null),
    [view, mode, names, tokens, range]
  )
}

function dangerLabel(raw: string): string {
  return raw in DANGER_SOURCE
    ? DANGER_SOURCE[raw as keyof typeof DANGER_SOURCE].label
    : words(raw)
}
