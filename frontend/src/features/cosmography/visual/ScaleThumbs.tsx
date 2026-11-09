import { useEffect, useRef } from 'react'
import type { components } from '@/api/generated/schema'
import { seededRandom, unitHash } from '@/lib/hash'
import { cn } from '@/lib/utils'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
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

function useCanvas<T>(
  value: T,
  paint: (canvas: HTMLCanvasElement, value: T) => void
) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const latest = useLatest(value)
  const signature = JSON.stringify(value)
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const render = () => paint(element, latest.current)
    render()
    const observer = new ResizeObserver(render)
    observer.observe(element)
    return () => observer.disconnect()
  }, [signature, latest, paint])
  return canvas
}

type SigilInput = {
  id: number
  kind: DimensionKind
  veil: number
  stability: number
  magic: number
}

function paintSigil(canvas: HTMLCanvasElement, input: SigilInput) {
  const prepared = prepare(canvas)
  if (!prepared) return
  const { context, width, height } = prepared
  const token = DIMENSION_TOKEN[input.kind]
  const centreX = width / 2
  const centreY = height / 2
  const radius = Math.min(width, height) * 0.42
  const random = seededRandom(input.id * 131 + 7)
  context.globalCompositeOperation = 'lighter'
  const glow = context.createRadialGradient(
    centreX,
    centreY,
    0,
    centreX,
    centreY,
    radius * 1.1
  )
  glow.addColorStop(0, cssColor(token, 0.55))
  glow.addColorStop(0.55, cssColor(token, 0.16))
  glow.addColorStop(1, cssColor(token, 0))
  context.fillStyle = glow
  context.beginPath()
  context.arc(centreX, centreY, radius * 1.1, 0, Math.PI * 2)
  context.fill()
  const rings = 3 + Math.round(input.magic / 25)
  for (let ring = 1; ring <= rings; ring += 1) {
    const distance = (radius * ring) / rings
    context.strokeStyle = cssColor(
      token,
      0.15 + (input.veil / 100) * 0.5 * (ring / rings)
    )
    context.lineWidth = ring === rings ? 2 : 1
    context.setLineDash(input.stability < 40 ? [3, 4] : [])
    context.beginPath()
    context.ellipse(
      centreX,
      centreY,
      distance,
      distance * 0.42,
      unitHash(`dimension-${input.id}`) * 0.6,
      0,
      Math.PI * 2
    )
    context.stroke()
  }
  context.setLineDash([])
  for (let index = 0; index < 90; index += 1) {
    const angle = random() * Math.PI * 2
    const distance = Math.sqrt(random()) * radius
    context.fillStyle = cssColor(token, 0.3 + random() * 0.6)
    context.fillRect(
      centreX + Math.cos(angle) * distance,
      centreY + Math.sin(angle) * distance * 0.42,
      1.4,
      1.4
    )
  }
  const core = context.createRadialGradient(
    centreX,
    centreY,
    0,
    centreX,
    centreY,
    radius * 0.22
  )
  core.addColorStop(0, cssColor('--galaxy-core', 0.95))
  core.addColorStop(1, cssColor(token, 0))
  context.fillStyle = core
  context.beginPath()
  context.arc(centreX, centreY, radius * 0.22, 0, Math.PI * 2)
  context.fill()
  context.globalCompositeOperation = 'source-over'
}

export function DimensionSigil({
  dimension,
  label,
  className,
}: {
  dimension: SigilInput
  label: string
  className?: string
}) {
  const canvas = useCanvas(dimension, paintSigil)
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}

type ClusterInput = {
  id: number
  kind: ClusterKind
  galaxies: number
  heat: number
}

const CLUSTER_SPREAD: Record<
  ClusterKind,
  'ball' | 'line' | 'band' | 'ring' | 'crown'
> = {
  galaxy_group: 'ball',
  local_group: 'ball',
  poor_cluster: 'ball',
  rich_cluster: 'ball',
  supercluster: 'band',
  filament: 'line',
  wall: 'band',
  void: 'ring',
  crown_cluster: 'crown',
  drowned_cluster: 'ball',
  forge_cluster: 'ball',
  dream_cluster: 'ball',
  mirror_cluster: 'line',
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

function paintCluster(canvas: HTMLCanvasElement, input: ClusterInput) {
  const prepared = prepare(canvas)
  if (!prepared) return
  const { context, width, height } = prepared
  const random = seededRandom(input.id * 977 + 3)
  const spread = CLUSTER_SPREAD[input.kind]
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
  const blobs = Math.max(input.galaxies, 3) + 6
  for (let index = 0; index < blobs; index += 1) {
    const t = random()
    const angle = random() * Math.PI * 2
    let x = centreX
    let y = centreY
    if (spread === 'ball') {
      const distance = Math.pow(random(), 0.7) * size * 0.36
      x += Math.cos(angle) * distance
      y += Math.sin(angle) * distance
    } else if (spread === 'line') {
      x += (t - 0.5) * size * 0.8
      y +=
        Math.sin(t * Math.PI * 2) * size * 0.12 + (random() - 0.5) * size * 0.08
    } else if (spread === 'band') {
      x += (t - 0.5) * size * 0.85
      y += (random() - 0.5) * size * 0.3
    } else {
      const distance =
        size * (spread === 'crown' ? 0.32 : 0.36) +
        (random() - 0.5) * size * 0.06
      x += Math.cos(angle) * distance
      y += Math.sin(angle) * distance
    }
    const major = index < input.galaxies
    const radius = (major ? 0.07 : 0.03) * size * (0.6 + random() * 0.6)
    const blob = context.createRadialGradient(x, y, 0, x, y, radius)
    blob.addColorStop(0, cssColor('--galaxy-core', major ? 0.95 : 0.5))
    blob.addColorStop(0.4, cssColor(token, major ? 0.55 : 0.3))
    blob.addColorStop(1, cssColor(token, 0))
    context.fillStyle = blob
    context.beginPath()
    context.ellipse(
      x,
      y,
      radius,
      radius * (0.45 + random() * 0.4),
      random() * Math.PI,
      0,
      Math.PI * 2
    )
    context.fill()
  }
  context.globalCompositeOperation = 'source-over'
}

export function ClusterThumb({
  cluster,
  label,
  className,
}: {
  cluster: ClusterInput
  label: string
  className?: string
}) {
  const canvas = useCanvas(cluster, paintCluster)
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}
