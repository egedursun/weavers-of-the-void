import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Bone,
  BrickWall,
  Building,
  Building2,
  Castle,
  CircleHelp,
  CloudLightning,
  Crown,
  Ghost,
  Globe2,
  Home,
  Landmark,
  type LucideIcon,
  Sun,
  Swords,
  Zap,
} from 'lucide-react'
import { flushSync } from 'react-dom'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { type SettlementTier } from './mapModel'

export const ICON_GRID = 24

export const SETTLEMENT_ICON: Record<SettlementTier, LucideIcon> = {
  village: Home,
  town: Building,
  city: Building2,
  great_city: Landmark,
  capital: Castle,
}

export const EVENT_ICON: Record<string, LucideIcon> = {
  battle: Swords,
  disaster: CloudLightning,
  ruin: BrickWall,
  remnant: Bone,
  event: Zap,
}

export const WAR_ICON: LucideIcon = Swords

const KIND_ICON: Record<string, LucideIcon> = {
  son: Crown,
  creator: Sun,
  foreign_god: Ghost,
  world: Globe2,
}

function number(element: Element, name: string): number {
  return Number(element.getAttribute(name) ?? 0)
}

function ellipsePath(cx: number, cy: number, rx: number, ry: number): string {
  return `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${rx * 2} 0a${rx} ${ry} 0 1 0 ${-rx * 2} 0`
}

function rectPath(element: Element): string {
  const x = number(element, 'x')
  const y = number(element, 'y')
  const width = number(element, 'width')
  const height = number(element, 'height')
  const radius = Math.min(number(element, 'rx'), width / 2, height / 2)
  if (radius <= 0) return `M${x} ${y}h${width}v${height}h${-width}Z`
  return [
    `M${x + radius} ${y}`,
    `h${width - radius * 2}`,
    `a${radius} ${radius} 0 0 1 ${radius} ${radius}`,
    `v${height - radius * 2}`,
    `a${radius} ${radius} 0 0 1 ${-radius} ${radius}`,
    `h${-(width - radius * 2)}`,
    `a${radius} ${radius} 0 0 1 ${-radius} ${-radius}`,
    `v${-(height - radius * 2)}`,
    `a${radius} ${radius} 0 0 1 ${radius} ${-radius}`,
    'Z',
  ].join('')
}

function pointsPath(element: Element, closed: boolean): string {
  const values = (element.getAttribute('points') ?? '')
    .trim()
    .split(/[\s,]+/)
    .map(Number)
  const pairs: string[] = []
  for (let index = 0; index + 1 < values.length; index += 2)
    pairs.push(
      `${index === 0 ? 'M' : 'L'}${values[index]} ${values[index + 1]}`
    )
  return pairs.join('') + (closed ? 'Z' : '')
}

function elementPath(element: Element): string | null {
  switch (element.tagName.toLowerCase()) {
    case 'path':
      return element.getAttribute('d')
    case 'circle':
      return ellipsePath(
        number(element, 'cx'),
        number(element, 'cy'),
        number(element, 'r'),
        number(element, 'r')
      )
    case 'ellipse':
      return ellipsePath(
        number(element, 'cx'),
        number(element, 'cy'),
        number(element, 'rx'),
        number(element, 'ry')
      )
    case 'rect':
      return rectPath(element)
    case 'line':
      return `M${number(element, 'x1')} ${number(element, 'y1')}L${number(element, 'x2')} ${number(element, 'y2')}`
    case 'polyline':
      return pointsPath(element, false)
    case 'polygon':
      return pointsPath(element, true)
    default:
      return null
  }
}

function buildPath(icon: LucideIcon): Path2D {
  const path = new Path2D()
  if (typeof document === 'undefined') return path
  const host = document.createElement('div')
  const root = createRoot(host)
  flushSync(() => root.render(createElement(icon)))
  for (const element of Array.from(host.querySelector('svg')?.children ?? [])) {
    const data = elementPath(element)
    if (data) path.addPath(new Path2D(data))
  }
  root.unmount()
  return path
}

const ICONS: readonly LucideIcon[] = [
  ...new Set([
    ...Object.values(ENTITY_TYPE_ICON),
    ...Object.values(SETTLEMENT_ICON),
    ...Object.values(KIND_ICON),
    ...Object.values(EVENT_ICON),
    CircleHelp,
  ]),
]

const PATHS = new Map(ICONS.map((icon) => [icon, buildPath(icon)]))

export function iconPath(icon: LucideIcon): Path2D {
  return PATHS.get(icon) ?? PATHS.get(CircleHelp) ?? new Path2D()
}

export function typeIcon(type: string): LucideIcon {
  if (type in ENTITY_TYPE_ICON)
    return ENTITY_TYPE_ICON[type as keyof typeof ENTITY_TYPE_ICON]
  return KIND_ICON[type] ?? CircleHelp
}

export function drawIcon(
  context: CanvasRenderingContext2D,
  icon: LucideIcon,
  size: number,
  color: string,
  weight = 2.4
) {
  const scale = size / ICON_GRID
  context.save()
  context.scale(scale, scale)
  context.translate(-ICON_GRID / 2, -ICON_GRID / 2)
  context.lineWidth = weight
  context.lineCap = 'round'
  context.lineJoin = 'round'
  context.strokeStyle = color
  context.stroke(iconPath(icon))
  context.restore()
}
