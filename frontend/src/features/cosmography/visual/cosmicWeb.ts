import { seededRandom, unitHash } from '@/lib/hash'
import { type Palette } from './galaxyForm'
import { type UniverseLayout, type Vec3 } from './universeLayout'

export type WebStrand = {
  key: string
  from: Vec3
  to: Vec3
  fromToken: string
  toToken: string
}

export type WebCloud = {
  positions: Float32Array
  colors: Float32Array
  sizes: Float32Array
  seeds: Float32Array
  count: number
}

export const DIMENSION_ACCENTS = [
  '--cosmos-violet',
  '--cosmos-teal',
  '--cosmos-nebula-3',
  '--cosmos-nebula-4',
] as const

const NEIGHBOURS = 2
const DENSITY = 0.16
const STRAND_MIN = 90
const STRAND_MAX = 520
const BEND = 0.45
const LIFT = 0.1
const WIDTH = 0.05
const FLAT = 0.45
const SEED_SPAN = 1_000_000_007
const DIM = 0.22
const SPARK = 1.1

function distance(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

function planeOf(layout: UniverseLayout, y: number): number {
  let best = 0
  let gap = Infinity
  for (const plane of layout.dimensions.values()) {
    const away = Math.abs(plane.y - y)
    if (away < gap) {
      gap = away
      best = plane.id
    }
  }
  return best
}

export function webStrands(
  layout: UniverseLayout,
  tokenOf: (clusterId: number) => string,
  neighbours = NEIGHBOURS
): WebStrand[] {
  const clusters = [...layout.clusters.values()]
  const strands = new Map<string, WebStrand>()
  for (const cluster of clusters) {
    const plane = planeOf(layout, cluster.position[1])
    const nearest = clusters
      .filter(
        (other) =>
          other.id !== cluster.id &&
          planeOf(layout, other.position[1]) === plane &&
          distance(other.position, cluster.position) >
            Math.max(other.size, cluster.size)
      )
      .sort(
        (a, b) =>
          distance(a.position, cluster.position) -
          distance(b.position, cluster.position)
      )
      .slice(0, neighbours)
    for (const other of nearest) {
      const [low, high] =
        cluster.id < other.id ? [cluster, other] : [other, cluster]
      const key = `${low.id}-${high.id}`
      if (strands.has(key)) continue
      strands.set(key, {
        key,
        from: low.position,
        to: high.position,
        fromToken: tokenOf(low.id),
        toToken: tokenOf(high.id),
      })
    }
  }
  return [...strands.values()]
}

function spread(random: () => number): number {
  return random() + random() + random() - 1.5
}

export function webCloud(
  strands: readonly WebStrand[],
  palette: Palette
): WebCloud {
  const counts = strands.map((strand) =>
    Math.min(
      Math.max(
        Math.round(distance(strand.from, strand.to) * DENSITY),
        STRAND_MIN
      ),
      STRAND_MAX
    )
  )
  const total = counts.reduce((sum, count) => sum + count, 0)
  const positions = new Float32Array(total * 3)
  const colors = new Float32Array(total * 3)
  const sizes = new Float32Array(total)
  const seeds = new Float32Array(total)
  let index = 0
  strands.forEach((strand, slot) => {
    const random = seededRandom(
      Math.floor(unitHash(`web-${strand.key}`) * SEED_SPAN) + 1
    )
    const [ax, ay, az] = strand.from
    const [bx, by, bz] = strand.to
    const length = distance(strand.from, strand.to)
    const across = Math.hypot(bx - ax, bz - az) || 1
    const bend = (random() - 0.5) * BEND * length
    const control: Vec3 = [
      (ax + bx) / 2 + (-(bz - az) / across) * bend,
      (ay + by) / 2 + (random() - 0.5) * LIFT * length,
      (az + bz) / 2 + ((bx - ax) / across) * bend,
    ]
    const start = palette(strand.fromToken)
    const end = palette(strand.toToken)
    const width = length * WIDTH
    for (let step = 0; step < (counts[slot] ?? 0); step += 1) {
      const t = random()
      const u = 1 - t
      const thick = width * (0.35 + Math.sin(Math.PI * t))
      positions.set(
        [
          u * u * ax +
            2 * u * t * control[0] +
            t * t * bx +
            spread(random) * thick,
          u * u * ay +
            2 * u * t * control[1] +
            t * t * by +
            spread(random) * thick * FLAT,
          u * u * az +
            2 * u * t * control[2] +
            t * t * bz +
            spread(random) * thick,
        ],
        index * 3
      )
      const light = DIM + Math.pow(random(), 4) * SPARK
      colors.set(
        [0, 1, 2].map(
          (channel) =>
            ((start[channel] ?? 1) * u + (end[channel] ?? 1) * t) * light
        ),
        index * 3
      )
      sizes[index] = 1.4 + Math.pow(random(), 5) * 3.4
      seeds[index] = random()
      index += 1
    }
  })
  return { positions, colors, sizes, seeds, count: index }
}
