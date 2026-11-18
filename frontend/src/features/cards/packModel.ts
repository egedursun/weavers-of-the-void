import { type CardMaterial } from './cardModel'

export type PackPhase = 'sealed' | 'tearing' | 'opening' | 'revealed'

export type Staging = {
  pulses: number
  spin: number
  burst: number
  rays: number
  shake: number
  gather: number
}

export const STAGING: Record<CardMaterial, Staging> = {
  common: { pulses: 0, spin: 180, burst: 40, rays: 0.18, shake: 0, gather: 0 },
  uncommon: {
    pulses: 1,
    spin: 180,
    burst: 60,
    rays: 0.28,
    shake: 0,
    gather: 0,
  },
  rare: { pulses: 1, spin: 540, burst: 95, rays: 0.45, shake: 0, gather: 30 },
  epic: { pulses: 2, spin: 540, burst: 140, rays: 0.6, shake: 3, gather: 60 },
  legendary: {
    pulses: 3,
    spin: 900,
    burst: 200,
    rays: 0.8,
    shake: 5,
    gather: 100,
  },
  mythic: {
    pulses: 3,
    spin: 900,
    burst: 250,
    rays: 0.9,
    shake: 6,
    gather: 130,
  },
  sovereign: {
    pulses: 3,
    spin: 900,
    burst: 260,
    rays: 0.95,
    shake: 6,
    gather: 140,
  },
  obsidian: {
    pulses: 3,
    spin: 540,
    burst: 180,
    rays: 0.7,
    shake: 5,
    gather: 90,
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
