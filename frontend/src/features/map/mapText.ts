import { formatNumber } from '@/lib/format'
import { typeLabel } from '@/features/graph/families'
import { type MapView } from './api'
import { type LineKind } from './mapLines'
import {
  type PositionedPoint,
  TIER_LABEL,
  leagues,
  percentChange,
  tierOf,
} from './mapModel'
import { type Thresholds, type HitTarget } from './mapScene'
import { type PaletteNames } from './useLayerPalette'

export const EVENT_KIND_LABEL: Record<string, string> = {
  battle: 'Battle',
  disaster: 'Disaster',
  ruin: 'Ruin',
  remnant: 'Relic',
  event: 'Event',
}

const ELEVATION_LABEL: Record<string, string> = {
  mountainous: 'mountainous',
  hilly: 'hilly',
  plain: 'plains',
  water: 'water',
}

export type HoverText = { title: string; lines: string[] }

export const LINE_LABEL: Record<LineKind, string> = {
  road: 'Road',
  trade_road: 'Trade road',
  trade: 'Distant trade',
  hostility: 'Hostility',
  rule: 'Rule',
  hunt: 'Hunt',
  route: 'Trade route',
  route_busy: 'Busy trade route',
  route_blocked: 'Blockaded trade route',
  outbreak: 'Spreading sickness',
  front: 'Front',
  supply: 'Army and supply line',
}

const DIRECTED: ReadonlySet<LineKind> = new Set(['rule', 'hunt', 'outbreak'])
const LIST_HINT = 'Click to list everything here'

function plural(count: number, noun: string): string {
  return `${count.toLocaleString('en-US')} ${noun}${count === 1 ? '' : 's'}`
}

function breakdown(
  ids: readonly number[],
  pointById: ReadonlyMap<number, PositionedPoint>,
  labels: ReadonlyMap<string, string>
): string {
  const counts = new Map<string, number>()
  for (const id of ids) {
    const point = pointById.get(id)
    if (!point) continue
    const name = typeName(point.type, labels)
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .map(([name, count]) => `${name} ${count.toLocaleString('en-US')}`)
    .join(' · ')
}

function siteName(
  pointById: ReadonlyMap<number, PositionedPoint>,
  id: number | null | undefined
): string {
  if (id === null || id === undefined) return 'an unknown place'
  return pointById.get(id)?.name ?? 'an unknown place'
}

export function typeName(
  type: string,
  labels: ReadonlyMap<string, string>
): string {
  return typeLabel(type, labels)
}

function populationLine(view: MapView, id: number): string | null {
  const population = view.population[String(id)]
  if (population === undefined) return null
  const previous = view.settlements[String(id)]?.previous_population
  const souls = `${formatNumber(population)} souls`
  if (!previous) return souls
  const change = percentChange(population, previous)
  const sign = change > 0 ? '+' : ''
  return `${souls} (previous epoch ${formatNumber(previous)}, ${sign}${change}%)`
}

export function hoverText(
  hit: HitTarget,
  view: MapView,
  pointById: ReadonlyMap<number, PositionedPoint>,
  labels: ReadonlyMap<string, string>,
  thresholds: Thresholds,
  palette?: PaletteNames
): HoverText | null {
  if (hit.kind === 'entity') {
    const point = pointById.get(hit.id)
    if (!point) return null
    const kind =
      point.type === 'settlement'
        ? TIER_LABEL[tierOf(view, point.id, thresholds)]
        : typeName(point.type, labels)
    const lines = [point.subtype ? `${kind} · ${point.subtype}` : kind]
    const population = populationLine(view, point.id)
    if (population) lines.push(population)
    const others = (hit.members ?? []).filter((id) => id !== point.id)
    if (others.length > 0) {
      lines.push(
        `Here with ${plural(others.length, 'more record')}: ${breakdown(others, pointById, labels)}`
      )
      lines.push(LIST_HINT)
    }
    return { title: point.name, lines }
  }
  if (hit.kind === 'region') {
    const region = view.geometry.regions.find((item) => item.id === hit.id)
    const point = pointById.get(hit.id)
    if (!region || !point) return null
    const names = (ids: readonly number[]) =>
      ids
        .map((id) => pointById.get(id)?.name)
        .filter((name): name is string => Boolean(name))
    const terrain = [
      ELEVATION_LABEL[region.elevation_class] ?? region.elevation_class,
      region.coastal ? 'coastal' : null,
    ]
      .filter(Boolean)
      .join(', ')
    const climate = region.climate
      .slice(0, 3)
      .map((share) => `${share.name} ${share.share_pct}%`)
      .join(', ')
    const lines = [[point.subtype, terrain].filter(Boolean).join(' · ')]
    if (climate) lines.push(climate)
    const neighbours = names(region.neighbours)
    if (neighbours.length) lines.push(`Neighbours: ${neighbours.join(', ')}`)
    const control =
      view.political[String(region.id)] ??
      view.political[String(region.top_level_id)]
    if (control)
      lines.push(
        `Ruler: ${control.ruler_name} ${Math.round(control.share)}%${control.contested ? ' · contested' : ''}`
      )
    const dominance = palette
      ? view.dominance[String(region.top_level_id ?? region.id)]
      : undefined
    if (palette && dominance?.son_id)
      lines.push(
        `Faith: ${palette.sons.get(dominance.son_id) ?? `Son ${dominance.son_id}`}`
      )
    if (palette && dominance?.language_id)
      lines.push(
        `Tongue: ${palette.languages.get(dominance.language_id) ?? `Language ${dominance.language_id}`}`
      )
    const creatorKey = String(region.id)
    if (palette && view.region_creators[creatorKey] !== undefined) {
      const son = view.region_creators[creatorKey]
      lines.push(
        `Shaped by ${son === null ? palette.creatorName : (palette.sons.get(son) ?? `Son ${son}`)}`
      )
    }
    return { title: point.name, lines }
  }
  if (hit.kind === 'war') {
    const members = new Set(hit.members ?? [hit.id])
    const wars = view.wars.filter((item) => members.has(item.id))
    const battles = view.markers.filter((item) => members.has(item.id))
    const first = wars[0]
    if (!first) return null
    const ongoing = wars.filter((item) => item.ongoing).length
    const lines: string[] = []
    if (wars.length === 1)
      lines.push(
        `Epoch ${first.started_epoch}${first.ended_epoch ? `–${first.ended_epoch}` : ''} · ${first.ongoing ? 'ongoing' : 'ended'}`
      )
    else {
      const starts = wars.map((item) => item.started_epoch)
      lines.push(
        `Epochs ${Math.min(...starts)}–${Math.max(...wars.map((item) => item.ended_epoch ?? item.started_epoch))} · ${ongoing} ongoing · ${wars.length - ongoing} ended`
      )
    }
    if (battles.length > 0) lines.push(plural(battles.length, 'battle'))
    if (members.size > 1) lines.push(LIST_HINT)
    return {
      title:
        wars.length === 1
          ? first.name
          : `${plural(wars.length, 'war')} at ${siteName(pointById, first.location_id)}`,
      lines,
    }
  }
  if (hit.kind === 'event') {
    const members = new Set(hit.members ?? [hit.id])
    const markers = view.markers.filter((item) => members.has(item.id))
    const marker = markers[0]
    if (!marker) return null
    if (markers.length === 1) {
      const kind = EVENT_KIND_LABEL[marker.kind] ?? marker.kind
      return {
        title: marker.name,
        lines: [
          `${marker.subtype ? `${kind} · ${marker.subtype}` : kind} · Epoch ${marker.epoch}`,
        ],
      }
    }
    const kinds = new Map<string, number>()
    for (const item of markers)
      kinds.set(item.kind, (kinds.get(item.kind) ?? 0) + 1)
    const epochs = markers.map((item) => item.epoch)
    return {
      title: `${plural(markers.length, 'event')} at ${siteName(pointById, marker.location_id)}`,
      lines: [
        [...kinds.entries()]
          .sort((left, right) => right[1] - left[1])
          .map(([kind, count]) => `${count} ${EVENT_KIND_LABEL[kind] ?? kind}`)
          .join(' · '),
        `Epochs ${Math.min(...epochs)}–${Math.max(...epochs)}`,
        LIST_HINT,
      ],
    }
  }
  if (hit.kind === 'line' && hit.line) {
    const line = hit.line
    const from = pointById.get(line.source)?.name ?? 'Unknown'
    const to = pointById.get(line.target)?.name ?? 'Unknown'
    const lines = [`${from} ${DIRECTED.has(line.kind) ? '→' : '–'} ${to}`]
    if (line.length !== null) lines.push(`${leagues(line.length)} leagues`)
    if (line.description) lines.push(line.description)
    return { title: LINE_LABEL[line.kind], lines }
  }
  const note = view.notes.find((item) => item.id === hit.id)
  return note ? { title: 'Your note', lines: [note.text] } : null
}
