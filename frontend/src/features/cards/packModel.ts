import { type CardMaterial } from './cardModel'

export type PackPhase = 'sealed' | 'tearing' | 'opening' | 'revealed'

export type Staging = {
  pulses: number
  spin: number
  burst: number
  rays: number
  shake: number
  gather: number
  embers: number
}

export const STAGING: Record<CardMaterial, Staging> = {
  common: {
    pulses: 0,
    spin: 180,
    burst: 36,
    rays: 0.22,
    shake: 0,
    gather: 0,
    embers: 0,
  },
  uncommon: {
    pulses: 1,
    spin: 180,
    burst: 54,
    rays: 0.32,
    shake: 0,
    gather: 0,
    embers: 0,
  },
  rare: {
    pulses: 1,
    spin: 540,
    burst: 80,
    rays: 0.5,
    shake: 0,
    gather: 26,
    embers: 10,
  },
  epic: {
    pulses: 2,
    spin: 540,
    burst: 110,
    rays: 0.65,
    shake: 2,
    gather: 44,
    embers: 16,
  },
  legendary: {
    pulses: 3,
    spin: 900,
    burst: 150,
    rays: 0.82,
    shake: 4,
    gather: 64,
    embers: 24,
  },
  mythic: {
    pulses: 3,
    spin: 900,
    burst: 180,
    rays: 0.9,
    shake: 4,
    gather: 80,
    embers: 30,
  },
  sovereign: {
    pulses: 3,
    spin: 900,
    burst: 190,
    rays: 0.95,
    shake: 5,
    gather: 84,
    embers: 32,
  },
  obsidian: {
    pulses: 3,
    spin: 540,
    burst: 140,
    rays: 0.72,
    shake: 4,
    gather: 60,
    embers: 22,
  },
}

export const REVEAL_TOKEN: Record<CardMaterial, string> = {
  common: '--rarity-common',
  uncommon: '--rarity-uncommon',
  rare: '--rarity-rare',
  epic: '--rarity-epic',
  legendary: '--rarity-legendary',
  mythic: '--rarity-mythic',
  sovereign: '--gild-hi',
  obsidian: '--brand-azure',
}

export const PRISM_TOKENS = [
  '--rarity-mythic',
  '--rarity-rare',
  '--rarity-legendary',
  '--rarity-epic',
  '--rarity-uncommon',
] as const

export const SPIN_TIME: Record<number, number> = {
  180: 760,
  540: 1350,
  900: 1850,
}

export const PACK_RATIO = 1.72
export const PACK_TOP = 0.57
export const CARD_TOP = 0.116
export const CARD_SPAN = 0.86
export const CARD_RATIO = 5 / 3
export const REVEAL_Y = 0.44

export const BEAM_TOKENS = [
  '--beam-strong',
  '--beam-mid',
  '--beam-soft',
] as const
export const PRISM_BEAM_TOKENS = [
  '--prism-1',
  '--prism-2',
  '--prism-3',
  '--prism-4',
  '--prism-5',
] as const

export function beamsOf(
  random: () => number,
  count: number,
  [narrow, wide]: [number, number],
  tokens: readonly string[]
): string {
  const slot = 360 / count
  const stops = ['transparent 0deg']
  for (let index = 0; index < count; index += 1) {
    const half = narrow + random() * (wide - narrow)
    const room = Math.max(0, slot / 2 - half)
    const center = index * slot + slot / 2 + (random() - 0.5) * 2 * room
    const token = tokens[Math.floor(random() * tokens.length)]
    stops.push(
      `transparent ${(center - half).toFixed(2)}deg`,
      `var(${token}) ${center.toFixed(2)}deg`,
      `transparent ${(center + half).toFixed(2)}deg`
    )
  }
  stops.push('transparent 360deg')
  return `conic-gradient(from 0deg, ${stops.join(', ')})`
}

export type Landing = {
  rise: number
  dy: number
  scale: number
  width: number
  height: number
}

export function landingOf(
  stageWidth: number,
  stageHeight: number,
  packWidth: number
): Landing {
  const packHeight = packWidth * PACK_RATIO
  const width = packWidth * CARD_SPAN
  const height = width * CARD_RATIO
  const center =
    stageHeight * PACK_TOP - packHeight / 2 + packHeight * CARD_TOP + height / 2
  return {
    rise: height * 0.6,
    dy: stageHeight * REVEAL_Y - center,
    scale: Math.min((stageHeight * 0.7) / height, (stageWidth * 0.84) / width),
    width,
    height,
  }
}
export const TEAR_AT = 0.104
export const TEAR_FINISH = 0.42
export const STRIP_ZONE = 0.26

export type Point = [number, number]

export function serration(
  width: number,
  y: number,
  depth: number,
  downward: boolean
): Point[] {
  const teeth = Math.max(16, Math.round(width / 6.5))
  const points: Point[] = []
  for (let index = 0; index <= teeth * 2; index += 1) {
    const x = (index * width) / (teeth * 2)
    const tip = index % 2 === 1
    const base = downward ? y - depth : y + depth
    points.push([x, tip ? y : base])
  }
  return points
}

export function jagged(
  width: number,
  y: number,
  random: () => number = Math.random
): Point[] {
  const points: Point[] = [[0, y]]
  let drift = 0
  const steps = Math.max(8, Math.round(width / 5))
  for (let index = 1; index < steps; index += 1) {
    drift = Math.max(-3.2, Math.min(3.2, drift + (random() - 0.5) * 2.4))
    const spike = random() < 0.12 ? (random() - 0.5) * 3.4 : 0
    points.push([
      (index * width) / steps + (random() - 0.5) * 1.6,
      y + drift + spike,
    ])
  }
  points.push([width, y + drift * 0.5])
  return points
}

export function polygonOf(points: Point[]): string {
  return `polygon(${points.map(([x, y]) => `${x.toFixed(2)}px ${y.toFixed(2)}px`).join(',')})`
}

export function pathOf(points: Point[], shift = 0): string {
  return `M${points.map(([x, y]) => `${x.toFixed(2)} ${(y + shift).toFixed(2)}`).join('L')}`
}

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b)
}

export type LaceSpec = {
  outer: number
  roller: number
  pen: number
  radius: number
  turn?: number
}

export function lacePath({
  outer,
  roller,
  pen,
  radius,
  turn = 0,
}: LaceSpec): string {
  const shared = gcd(outer, roller)
  const span = (2 * Math.PI * roller) / shared
  const steps = Math.max(360, (outer / shared) * 64)
  const scale = radius / (outer - roller + pen)
  const ratio = (outer - roller) / roller
  const points: string[] = []
  for (let step = 0; step <= steps; step += 1) {
    const angle = (step / steps) * span
    const x = (outer - roller) * Math.cos(angle) + pen * Math.cos(ratio * angle)
    const y = (outer - roller) * Math.sin(angle) - pen * Math.sin(ratio * angle)
    const rx = x * Math.cos(turn) - y * Math.sin(turn)
    const ry = x * Math.sin(turn) + y * Math.cos(turn)
    points.push(
      `${(50 + rx * scale).toFixed(2)} ${(50 + ry * scale).toFixed(2)}`
    )
  }
  return `M${points.join('L')}Z`
}

export function ticksPath(count: number, inner: number, outer: number): string {
  const parts: string[] = []
  for (let index = 0; index < count; index += 1) {
    const angle = (index / count) * Math.PI * 2
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    parts.push(
      `M${(50 + cos * inner).toFixed(2)} ${(50 + sin * inner).toFixed(2)}L${(50 + cos * outer).toFixed(2)} ${(50 + sin * outer).toFixed(2)}`
    )
  }
  return parts.join('')
}
