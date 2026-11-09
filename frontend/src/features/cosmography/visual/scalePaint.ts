import type { components } from '@/api/generated/schema'
import { seededRandom } from '@/lib/hash'
import { DIMENSION_MOTIF } from './dimensionMotifs'
import { DIMENSION_TOKEN, type DimensionKind } from './galaxyForm'
import { cssColor } from './palette'

type ClusterKind = components['schemas']['ClusterKind']

function prepare(canvas: HTMLCanvasElement) {
  const ratio = window.devicePixelRatio || 1
  const width = Math.max(canvas.clientWidth, 1)
  const height = Math.max(canvas.clientHeight, 1)
  canvas.width = Math.round(width * ratio)
  canvas.height = Math.round(height * ratio)
  const context = canvas.getContext('2d')
  if (!context) return null
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  const background = context.createRadialGradient(
    width / 2,
    height / 2,
    0,
    width / 2,
    height / 2,
    Math.max(width, height) * 0.75
  )
  background.addColorStop(0, cssColor('--cosmos-void-edge'))
  background.addColorStop(1, cssColor('--cosmos-void'))
  context.fillStyle = background
  context.fillRect(0, 0, width, height)
  return { context, width, height }
}

export type SigilInput = {
  id: number
  kind: DimensionKind
  veil: number
  stability: number
  magic: number
}

export function paintSigil(canvas: HTMLCanvasElement, input: SigilInput) {
  const prepared = prepare(canvas)
  if (!prepared) return
  const { context, width, height } = prepared
  context.globalCompositeOperation = 'lighter'
  DIMENSION_MOTIF[input.kind]({
    context,
    x: width / 2,
    y: height / 2,
    r: Math.min(width, height) * 0.4,
    token: DIMENSION_TOKEN[input.kind],
    random: seededRandom(input.id * 131 + 7),
    veil: input.veil,
    magic: input.magic,
    stability: input.stability,
  })
  context.setLineDash([])
  context.globalCompositeOperation = 'source-over'
}

export type ClusterInput = {
  id: number
  kind: ClusterKind
  galaxies: number
  heat: number
}

type Blob = { x: number; y: number; size: number; major: boolean }

type Arrange = (random: () => number, count: number) => Blob[]

const around = (
  random: () => number,
  x: number,
  y: number,
  spread: number,
  count: number,
  size: number
): Blob[] =>
  Array.from({ length: count }, () => {
    const angle = random() * Math.PI * 2
    const distance = Math.pow(random(), 0.8) * spread
    return {
      x: x + Math.cos(angle) * distance,
      y: y + Math.sin(angle) * distance,
      size: size * (0.6 + random() * 0.5),
      major: false,
    }
  })

const major = (x: number, y: number, size: number): Blob => ({
  x,
  y,
  size,
  major: true,
})

const CLUSTER_ARRANGE: Record<ClusterKind, Arrange> = {
  galaxy_group: (random) => [
    major(-0.18, -0.1, 0.1),
    major(0.2, 0.05, 0.08),
    major(-0.02, 0.24, 0.07),
    ...around(random, 0, 0, 0.32, 5, 0.025),
  ],
  local_group: (random) => [
    major(-0.24, -0.06, 0.12),
    major(0.26, 0.1, 0.1),
    ...around(random, -0.24, -0.06, 0.16, 6, 0.02),
    ...around(random, 0.26, 0.1, 0.14, 5, 0.02),
  ],
  poor_cluster: (random) =>
    [
      [-0.3, -0.25],
      [0.28, -0.3],
      [0.32, 0.22],
      [-0.25, 0.3],
      [0, 0],
    ].flatMap(([x, y], index) => [
      major(x, y, index === 4 ? 0.09 : 0.07),
      ...around(random, x, y, 0.08, 2, 0.02),
    ]),
  rich_cluster: (random) => [
    major(0, 0, 0.15),
    ...around(random, 0, 0, 0.3, 34, 0.035),
  ],
  supercluster: (random) =>
    [
      [-0.3, -0.22],
      [0.28, -0.18],
      [-0.05, 0.28],
      [0.34, 0.3],
    ].flatMap(([x, y]) => [
      major(x, y, 0.06),
      ...around(random, x, y, 0.1, 7, 0.02),
    ]),
  filament: (random) =>
    Array.from({ length: 16 }, (_, index) => {
      const t = index / 15
      return {
        x: (t - 0.5) * 0.9,
        y: Math.sin(t * Math.PI * 1.5) * 0.18 + (random() - 0.5) * 0.04,
        size: index % 4 === 0 ? 0.06 : 0.025,
        major: index % 4 === 0,
      }
    }),
  wall: (random) =>
    Array.from({ length: 26 }, () => ({
      x: (random() - 0.5) * 0.9,
      y: (random() - 0.5) * 0.14 + (random() - 0.5) * 0.9 * 0.18,
      size: 0.02 + random() * 0.035,
      major: random() < 0.25,
    })),
  void: (random) =>
    Array.from({ length: 14 }, (_, index) => {
      const angle = (index / 14) * Math.PI * 2 + random() * 0.2
      const distance = 0.4 + random() * 0.06
      return {
        x: Math.cos(angle) * distance,
        y: Math.sin(angle) * distance,
        size: 0.025 + random() * 0.02,
        major: index % 5 === 0,
      }
    }),
  crown_cluster: () => [
    major(0, 0, 0.12),
    ...Array.from({ length: 7 }, (_, index) => {
      const angle = -Math.PI / 2 + ((index - 3) / 3) * 1.1
      return major(Math.cos(angle) * 0.34, Math.sin(angle) * 0.34, 0.05)
    }),
  ],
  drowned_cluster: (random) => [
    ...around(random, 0, 0.12, 0.32, 14, 0.04),
    major(-0.1, 0.18, 0.08),
  ],
  forge_cluster: (random) => [
    major(0, 0, 0.09),
    ...Array.from({ length: 6 }, (_, index) => {
      const angle = (index / 6) * Math.PI * 2
      return major(Math.cos(angle) * 0.18, Math.sin(angle) * 0.18, 0.05)
    }),
    ...around(random, 0, 0, 0.12, 8, 0.02),
  ],
  dream_cluster: (random) =>
    Array.from({ length: 18 }, (_, index) => {
      const t = index / 17
      const angle = t * Math.PI * 3
      const distance = 0.06 + t * 0.34
      return {
        x: Math.cos(angle) * distance,
        y: Math.sin(angle) * distance,
        size: 0.025 + (1 - t) * 0.04 + random() * 0.01,
        major: index % 6 === 0,
      }
    }),
  mirror_cluster: (random) => {
    const half = around(random, -0.22, 0, 0.18, 8, 0.04).map((blob, index) => ({
      ...blob,
      x: Math.min(blob.x, -0.04),
      major: index < 2,
    }))
    return [...half, ...half.map((blob) => ({ ...blob, x: -blob.x }))]
  },
}

const CLUSTER_TOKEN: Record<ClusterKind, string> = {
  galaxy_group: '--galaxy-young',
  local_group: '--galaxy-young',
  poor_cluster: '--galaxy-disc',
  rich_cluster: '--galaxy-old',
  supercluster: '--galaxy-disc',
  filament: '--galaxy-young',
  wall: '--galaxy-disc',
  void: '--galaxy-halo',
  crown_cluster: '--galaxy-crowned',
  drowned_cluster: '--structure-reflection',
  forge_cluster: '--galaxy-forged',
  dream_cluster: '--galaxy-dreaming',
  mirror_cluster: '--galaxy-mirror',
}

export function paintCluster(canvas: HTMLCanvasElement, input: ClusterInput) {
  const prepared = prepare(canvas)
  if (!prepared) return
  const { context, width, height } = prepared
  const random = seededRandom(input.id * 977 + 3)
  const token = CLUSTER_TOKEN[input.kind]
  const size = Math.min(width, height)
  const centreX = width / 2
  const centreY = height / 2
  context.globalCompositeOperation = 'lighter'
  const medium = context.createRadialGradient(
    centreX,
    centreY,
    0,
    centreX,
    centreY,
    size * 0.48
  )
  medium.addColorStop(
    0,
    cssColor('--structure-emission', (input.heat / 100) * 0.25)
  )
  medium.addColorStop(1, cssColor('--structure-emission', 0))
  context.fillStyle = medium
  context.fillRect(0, 0, width, height)
  const blobs = CLUSTER_ARRANGE[input.kind](random, input.galaxies)
  if (input.kind === 'filament' || input.kind === 'mirror_cluster') {
    context.strokeStyle = cssColor(token, 0.35)
    context.lineWidth = 1
    context.beginPath()
    if (input.kind === 'mirror_cluster') {
      context.lineWidth = 2.5
      context.strokeStyle = cssColor(token, 0.8)
      context.moveTo(centreX, centreY - size * 0.45)
      context.lineTo(centreX, centreY + size * 0.45)
    } else
      blobs.forEach((blob, index) =>
        index === 0
          ? context.moveTo(centreX + blob.x * size, centreY + blob.y * size)
          : context.lineTo(centreX + blob.x * size, centreY + blob.y * size)
      )
    context.stroke()
  }
  if (input.kind === 'drowned_cluster')
    for (let ripple = 1; ripple <= 4; ripple += 1) {
      context.strokeStyle = cssColor(token, 0.32 - ripple * 0.05)
      context.lineWidth = 1
      context.beginPath()
      context.ellipse(
        centreX,
        centreY - size * 0.18,
        size * 0.12 * ripple,
        size * 0.035 * ripple,
        0,
        0,
        Math.PI * 2
      )
      context.stroke()
    }
  if (input.kind === 'forge_cluster')
    for (let ray = 0; ray < 6; ray += 1) {
      const angle = (ray / 6) * Math.PI * 2
      context.strokeStyle = cssColor(token, 0.45)
      context.lineWidth = 1.2
      context.beginPath()
      context.moveTo(centreX, centreY)
      context.lineTo(
        centreX + Math.cos(angle) * size * 0.18,
        centreY + Math.sin(angle) * size * 0.18
      )
      context.stroke()
    }
  if (input.kind === 'void') {
    const rim = context.createRadialGradient(
      centreX,
      centreY,
      size * 0.3,
      centreX,
      centreY,
      size * 0.48
    )
    rim.addColorStop(0, cssColor(token, 0))
    rim.addColorStop(0.5, cssColor(token, 0.4))
    rim.addColorStop(1, cssColor(token, 0))
    context.fillStyle = rim
    context.fillRect(0, 0, width, height)
  }
  for (const blob of blobs) {
    const x = centreX + blob.x * size
    const y = centreY + blob.y * size
    const radius = blob.size * size
    const gradient = context.createRadialGradient(x, y, 0, x, y, radius)
    gradient.addColorStop(
      0,
      cssColor('--galaxy-core', blob.major ? 0.95 : 0.55)
    )
    gradient.addColorStop(0.4, cssColor(token, blob.major ? 0.6 : 0.32))
    gradient.addColorStop(1, cssColor(token, 0))
    context.fillStyle = gradient
    context.beginPath()
    context.ellipse(
      x,
      y,
      radius,
      radius * (0.5 + random() * 0.4),
      random() * Math.PI,
      0,
      Math.PI * 2
    )
    context.fill()
  }
  context.globalCompositeOperation = 'source-over'
}
