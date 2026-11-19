import { type ThemeColors } from '@/components/domain/useThemeColors'
import { shapePath } from '@/features/graph/families'
import {
  EVENT_ICON,
  SETTLEMENT_ICON,
  WAR_ICON,
  drawIcon,
  typeIcon,
} from './iconPaths'
import { type SettlementTier, TIER_RADIUS } from './mapModel'

export const ICON_SHARE = 1.25
export const DEAD_ALPHA = 0.55
export const EVENT_RADIUS = 8.5
export const NOTE_PIN = 9
export const OUTSIDER_HALO = 14
export const RING_GAP = 2.2
export const RING_WIDTH = 2.6
export const PORTRAIT_GAIN = 1.45
const HALO_WIDTH = 3.2
const MAJOR_TIERS: ReadonlySet<SettlementTier> = new Set<SettlementTier>([
  'great_city',
  'megacity',
  'conurbation',
  'capital',
])
const BADGE_HEIGHT = 13
const BADGE_PAD = 4
const BADGE_FONT = 9
const CROWN_SIZE = 11
const DASH = [2, 2]
const TAU = Math.PI * 2

export type Slice = { color: string; value: number }

export function font(
  size: number,
  family: string,
  weight = 400,
  italic = false
): string {
  return `${italic ? 'italic ' : ''}${weight} ${size}px ${family}`
}

export function haloText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  fill: string,
  halo: string,
  width = HALO_WIDTH
): void {
  context.lineJoin = 'round'
  context.miterLimit = 2
  context.lineWidth = width
  context.strokeStyle = halo
  const alpha = context.globalAlpha
  context.globalAlpha = alpha * 0.75
  context.strokeText(text, x, y)
  context.globalAlpha = alpha
  context.fillStyle = fill
  context.fillText(text, x, y)
}

function disc(
  context: CanvasRenderingContext2D,
  radius: number,
  fill: string,
  halo: string,
  dead: boolean
): void {
  context.beginPath()
  context.arc(0, 0, radius, 0, TAU)
  context.fillStyle = fill
  context.fill()
  context.setLineDash(dead ? DASH : [])
  context.lineWidth = 1.4
  context.strokeStyle = halo
  context.stroke()
  context.setLineDash([])
}

export function settlementGlyph(
  context: CanvasRenderingContext2D,
  tier: SettlementTier,
  dead: boolean,
  tokens: ThemeColors,
  halo: string
): void {
  const radius = TIER_RADIUS[tier]
  const gold = tokens['brand-gold']
  const alpha = context.globalAlpha
  context.globalAlpha = alpha * (dead ? DEAD_ALPHA : 1)
  disc(context, radius, gold, halo, dead)
  const major = MAJOR_TIERS.has(tier)
  if (major) {
    context.beginPath()
    context.arc(0, 0, radius + 2.2, 0, TAU)
    context.strokeStyle = gold
    context.lineWidth = 1.4
    context.stroke()
  }
  drawIcon(context, SETTLEMENT_ICON[tier], radius * ICON_SHARE, halo)
  if (major) {
    context.save()
    context.translate(0, -radius - 5)
    context.fillStyle = tier === 'capital' ? tokens.primary : gold
    context.fill(shapePath('star', 2.8))
    context.restore()
  }
  context.globalAlpha = alpha
}

export function trendGlyph(
  context: CanvasRenderingContext2D,
  trend: 'up' | 'down',
  radius: number,
  tokens: ThemeColors,
  halo: string
): void {
  context.save()
  context.translate(radius * 0.85, -radius * 0.85)
  context.beginPath()
  if (trend === 'up') {
    context.moveTo(0, -4.5)
    context.lineTo(4, 2.5)
    context.lineTo(-4, 2.5)
  } else {
    context.moveTo(0, 4.5)
    context.lineTo(4, -2.5)
    context.lineTo(-4, -2.5)
  }
  context.closePath()
  context.lineWidth = 1.2
  context.strokeStyle = halo
  context.stroke()
  context.fillStyle = trend === 'up' ? tokens.success : tokens.destructive
  context.fill()
  context.restore()
}

export function entityGlyph(
  context: CanvasRenderingContext2D,
  type: string,
  radius: number,
  color: string,
  dead: boolean,
  tokens: ThemeColors,
  halo: string
): void {
  const alpha = context.globalAlpha
  if (type === 'outer_being') {
    context.globalAlpha = alpha * 0.45
    context.fillStyle = tokens['rarity-epic']
    context.beginPath()
    context.arc(0, 0, OUTSIDER_HALO, 0, TAU)
    context.fill()
  }
  context.globalAlpha = alpha * (dead ? DEAD_ALPHA : 1)
  disc(context, radius, color, halo, dead)
  drawIcon(context, typeIcon(type), radius * ICON_SHARE, halo)
  context.globalAlpha = alpha
}

export function portraitGlyph(
  context: CanvasRenderingContext2D,
  image: HTMLImageElement,
  radius: number,
  ring: string,
  dead: boolean,
  halo: string
): void {
  const alpha = context.globalAlpha
  context.globalAlpha = alpha * (dead ? DEAD_ALPHA : 1)
  context.save()
  context.beginPath()
  context.arc(0, 0, radius, 0, TAU)
  context.clip()
  const side = Math.min(image.naturalWidth, image.naturalHeight)
  context.drawImage(
    image,
    (image.naturalWidth - side) / 2,
    (image.naturalHeight - side) / 2,
    side,
    side,
    -radius,
    -radius,
    radius * 2,
    radius * 2
  )
  if (dead) {
    context.fillStyle = halo
    context.globalAlpha = alpha * 0.35
    context.fillRect(-radius, -radius, radius * 2, radius * 2)
  }
  context.restore()
  context.globalAlpha = alpha * (dead ? DEAD_ALPHA : 1)
  context.beginPath()
  context.arc(0, 0, radius, 0, TAU)
  context.setLineDash(dead ? DASH : [])
  context.lineWidth = 3.4
  context.strokeStyle = halo
  context.stroke()
  context.lineWidth = 2
  context.strokeStyle = ring
  context.stroke()
  context.setLineDash([])
  context.globalAlpha = alpha
}

export function stackGlyph(
  context: CanvasRenderingContext2D,
  color: string,
  icon: Parameters<typeof drawIcon>[1],
  halo: string
): void {
  disc(context, EVENT_RADIUS, color, halo, false)
  drawIcon(context, icon, EVENT_RADIUS * ICON_SHARE, halo)
}

export function eventIcon(kind: string) {
  return EVENT_ICON[kind] ?? EVENT_ICON.event
}

export function warIcon() {
  return WAR_ICON
}

export function donutRing(
  context: CanvasRenderingContext2D,
  radius: number,
  slices: readonly Slice[],
  halo: string
): void {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0)
  if (total <= 0) return
  const reach = radius + RING_GAP + RING_WIDTH / 2
  context.beginPath()
  context.arc(0, 0, reach, 0, TAU)
  context.lineWidth = RING_WIDTH + 2
  context.strokeStyle = halo
  context.stroke()
  let start = -Math.PI / 2
  context.lineWidth = RING_WIDTH
  context.lineCap = 'butt'
  for (const slice of slices) {
    const sweep = (slice.value / total) * TAU
    context.beginPath()
    context.arc(0, 0, reach, start, start + sweep)
    context.strokeStyle = slice.color
    context.stroke()
    start += sweep
  }
}

export function countBadge(
  context: CanvasRenderingContext2D,
  count: number,
  radius: number,
  fill: string,
  text: string,
  family: string
): void {
  const label = count.toLocaleString('en-US')
  context.font = font(BADGE_FONT, family, 700)
  const width = Math.max(
    BADGE_HEIGHT,
    context.measureText(label).width + BADGE_PAD * 2
  )
  const x = radius * 0.7
  const y = -radius - BADGE_HEIGHT / 2 + 3
  context.beginPath()
  context.roundRect(x - 2, y, width, BADGE_HEIGHT, BADGE_HEIGHT / 2)
  context.fillStyle = fill
  context.fill()
  context.lineWidth = 1.2
  context.strokeStyle = text
  context.globalAlpha *= 0.6
  context.stroke()
  context.globalAlpha /= 0.6
  context.fillStyle = text
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillText(label, x - 2 + width / 2, y + BADGE_HEIGHT / 2 + 0.5)
}

export function crownGlyph(
  context: CanvasRenderingContext2D,
  radius: number,
  color: string,
  halo: string
): void {
  context.save()
  context.translate(0, -radius - CROWN_SIZE * 0.75)
  context.beginPath()
  context.arc(0, 0, CROWN_SIZE * 0.62, 0, TAU)
  context.fillStyle = halo
  context.fill()
  drawIcon(context, typeIcon('son'), CROWN_SIZE, color, 2.6)
  context.restore()
}

export function pinGlyph(
  context: CanvasRenderingContext2D,
  color: string,
  halo: string
): void {
  context.beginPath()
  context.moveTo(0, 0)
  context.bezierCurveTo(
    -NOTE_PIN,
    -NOTE_PIN,
    -NOTE_PIN * 0.7,
    -NOTE_PIN * 2,
    0,
    -NOTE_PIN * 2
  )
  context.bezierCurveTo(
    NOTE_PIN * 0.7,
    -NOTE_PIN * 2,
    NOTE_PIN,
    -NOTE_PIN,
    0,
    0
  )
  context.fillStyle = color
  context.fill()
  context.lineWidth = 1.2
  context.strokeStyle = halo
  context.stroke()
  context.beginPath()
  context.arc(0, -NOTE_PIN * 1.35, 2.2, 0, TAU)
  context.fillStyle = halo
  context.fill()
}
