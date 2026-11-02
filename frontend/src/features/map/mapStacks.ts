import {
  type StackItem,
  type StackPopup,
  type StackSection,
} from './MapStackOverlay'
import { type MapView } from './api'
import { type PositionedPoint, TIER_LABEL, isDead, tierOf } from './mapModel'
import { type HitTarget, type Thresholds } from './mapScene'
import { EVENT_KIND_LABEL, typeName } from './mapText'

const SAME_PLACE = 1

function grouped(
  items: readonly { section: string; item: StackItem }[],
  first?: string
): StackSection[] {
  const sections = new Map<string, StackItem[]>()
  for (const { section, item } of items) {
    const list = sections.get(section)
    if (list) list.push(item)
    else sections.set(section, [item])
  }
  return [...sections.entries()]
    .sort(
      (left, right) =>
        Number(right[0] === first) - Number(left[0] === first) ||
        right[1].length - left[1].length ||
        left[0].localeCompare(right[0])
    )
    .map(([title, list]) => ({ title, items: list }))
}

function summaryOf(sections: readonly StackSection[]): string {
  return sections
    .map(
      (section) =>
        `${section.title} ${section.items.length.toLocaleString('en-US')}`
    )
    .join(' · ')
}

function epochs(start: number, end: number | null | undefined): string {
  return end && end !== start ? `Epochs ${start}–${end}` : `Epoch ${start}`
}

export function entityStack(
  hit: HitTarget,
  view: MapView,
  pointById: ReadonlyMap<number, PositionedPoint>,
  labels: ReadonlyMap<string, string>,
  thresholds: Thresholds,
  screen: { x: number; y: number }
): StackPopup | null {
  const members = (hit.members ?? [])
    .map((id) => pointById.get(id))
    .filter((point): point is PositionedPoint => Boolean(point))
  const lead = members[0]
  if (!lead) return null
  const entries = members.map((point) => {
    const kind =
      point.type === 'settlement'
        ? TIER_LABEL[tierOf(view, point.id, thresholds)]
        : typeName(point.type, labels)
    return {
      section: typeName(point.type, labels),
      item: {
        id: point.id,
        name: point.name,
        detail: point.subtype ? `${kind} · ${point.subtype}` : kind,
        dead: isDead(point.status),
      },
    }
  })
  const sections = grouped(entries, typeName(lead.type, labels))
  const spread = members.some(
    (point) => Math.hypot(point.x - lead.x, point.y - lead.y) > SAME_PLACE
  )
  const count = members.length - 1
  return {
    x: screen.x,
    y: screen.y,
    title: `${lead.name} and ${count.toLocaleString('en-US')} more`,
    summary: spread
      ? `${summaryOf(sections)} · close together; zoom in to part them`
      : `${summaryOf(sections)} · all in one place`,
    sections,
    centre: spread
      ? {
          x: members.reduce((sum, point) => sum + point.x, 0) / members.length,
          y: members.reduce((sum, point) => sum + point.y, 0) / members.length,
        }
      : null,
  }
}

export function warStack(
  hit: HitTarget,
  view: MapView,
  pointById: ReadonlyMap<number, PositionedPoint>,
  screen: { x: number; y: number }
): StackPopup | null {
  const members = new Set(hit.members ?? [])
  const wars = view.wars.filter((war) => members.has(war.id))
  const battles = view.markers.filter((marker) => members.has(marker.id))
  if (wars.length === 0) return null
  const sections: StackSection[] = [
    {
      title: 'Wars',
      items: [...wars]
        .sort((left, right) => left.started_epoch - right.started_epoch)
        .map((war) => ({
          id: war.id,
          name: war.name,
          detail: `${epochs(war.started_epoch, war.ended_epoch)} · ${war.ongoing ? 'ongoing' : 'ended'}`,
          dead: false,
        })),
    },
  ]
  if (battles.length > 0)
    sections.push({
      title: 'Battles',
      items: [...battles]
        .sort((left, right) => left.epoch - right.epoch)
        .map((battle) => ({
          id: battle.id,
          name: battle.name,
          detail: [`Epoch ${battle.epoch}`, battle.subtype]
            .filter(Boolean)
            .join(' · '),
          dead: false,
        })),
    })
  const place = pointById.get(wars[0].location_id ?? -1)?.name
  return {
    x: screen.x,
    y: screen.y,
    title: place ? `Wars at ${place}` : 'Wars here',
    summary: summaryOf(sections),
    sections,
    centre: null,
  }
}

export function eventStack(
  hit: HitTarget,
  view: MapView,
  pointById: ReadonlyMap<number, PositionedPoint>,
  screen: { x: number; y: number }
): StackPopup | null {
  const members = new Set(hit.members ?? [])
  const markers = view.markers
    .filter((marker) => members.has(marker.id))
    .sort((left, right) => left.epoch - right.epoch)
  if (markers.length === 0) return null
  const sections = grouped(
    markers.map((marker) => ({
      section: EVENT_KIND_LABEL[marker.kind] ?? marker.kind,
      item: {
        id: marker.id,
        name: marker.name,
        detail: [`Epoch ${marker.epoch}`, marker.subtype]
          .filter(Boolean)
          .join(' · '),
        dead: false,
      },
    }))
  )
  const place = pointById.get(markers[0].location_id ?? -1)?.name
  return {
    x: screen.x,
    y: screen.y,
    title: place ? `Events at ${place}` : 'Events here',
    summary: summaryOf(sections),
    sections,
    centre: null,
  }
}
