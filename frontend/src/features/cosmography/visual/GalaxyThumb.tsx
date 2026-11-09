import { useEffect, useRef } from 'react'
import { unitHash } from '@/lib/hash'
import { cn } from '@/lib/utils'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import {
  type FormInput,
  type GalaxyShape,
  coreGlow,
  galaxyPoints,
} from './galaxyForm'
import { cssColor, mixColor, screenPalette } from './palette'

const THUMB_POINTS = 5200
const MIN_TILT = 0.35
const TILT_RANGE = 0.5
const MARGIN = 1.12
const BRIGHT_DOT = 1.6
const DOT_SCALE = 0.55
const DUST_MIN_WIDTH = 240

export type ThumbStar = { id: number; x: number; y: number }

type GalaxyThumbProps = {
  galaxy: FormInput
  shape: GalaxyShape
  label: string
  stars?: readonly ThumbStar[]
  tilt?: number
  points?: number
  className?: string
}

function draw(
  canvas: HTMLCanvasElement,
  galaxy: FormInput,
  shape: GalaxyShape,
  stars: readonly ThumbStar[],
  tilt: number,
  count: number
) {
  const ratio = window.devicePixelRatio || 1
  const width = Math.max(canvas.clientWidth, 1)
  const height = Math.max(canvas.clientHeight, 1)
  canvas.width = Math.round(width * ratio)
  canvas.height = Math.round(height * ratio)
  const context = canvas.getContext('2d')
  const layer = document.createElement('canvas')
  layer.width = canvas.width
  layer.height = canvas.height
  const light = layer.getContext('2d')
  if (!context || !light) return
  light.setTransform(ratio, 0, 0, ratio, 0, 0)
  const centreX = width / 2
  const centreY = height / 2
  const scale =
    Math.min(width, height) /
    2 /
    (((galaxy.radius * shape.disc_reach_pct) / 100) * MARGIN + 1)
  const spin = unitHash(`galaxy-spin-${galaxy.id}`) * Math.PI * 2
  const cos = Math.cos(spin)
  const sin = Math.sin(spin)
  const squash = Math.cos(tilt)
  const lift = Math.sin(tilt)
  const project = (x: number, y: number, z: number): [number, number] => {
    const rx = x * cos - z * sin
    const rz = x * sin + z * cos
    return [centreX + rx * scale, centreY + (rz * squash - y * lift) * scale]
  }
  const points = galaxyPoints(galaxy, shape, count, screenPalette)
  light.globalCompositeOperation = 'lighter'
  for (let index = 0; index < points.count; index += 1) {
    const [px, py] = project(
      points.positions[index * 3],
      points.positions[index * 3 + 1],
      points.positions[index * 3 + 2]
    )
    const r = points.colors[index * 3]
    const g = points.colors[index * 3 + 1]
    const b = points.colors[index * 3 + 2]
    const peak = Math.max(r, g, b, 0.001)
    const size = points.sizes[index] * DOT_SCALE
    light.fillStyle = mixColor(
      r / peak,
      g / peak,
      b / peak,
      Math.min(0.12 + peak * 0.42, 0.85)
    )
    if (size > BRIGHT_DOT) {
      light.beginPath()
      light.arc(px, py, size, 0, Math.PI * 2)
      light.fill()
    } else light.fillRect(px, py, size + 0.6, size + 0.6)
  }
  const glow = coreGlow(galaxy)
  const coreRadius =
    ((galaxy.radius * shape.bulge_reach_pct) / 100) * scale * 0.9
  const core = light.createRadialGradient(
    centreX,
    centreY,
    0,
    centreX,
    centreY,
    Math.max(coreRadius, 2)
  )
  core.addColorStop(0, cssColor('--galaxy-core', Math.min(0.85 * glow, 1)))
  core.addColorStop(0.35, cssColor('--galaxy-bulge', Math.min(0.3 * glow, 1)))
  core.addColorStop(1, cssColor('--galaxy-bulge', 0))
  light.fillStyle = core
  light.beginPath()
  light.arc(centreX, centreY, Math.max(coreRadius, 2), 0, Math.PI * 2)
  light.fill()
  for (const star of stars) {
    const [px, py] = project(star.x, 0, star.y)
    const halo = light.createRadialGradient(px, py, 0, px, py, 6)
    halo.addColorStop(0, cssColor('--cosmos-copper', 1))
    halo.addColorStop(1, cssColor('--cosmos-copper', 0))
    light.fillStyle = halo
    light.beginPath()
    light.arc(px, py, 6, 0, Math.PI * 2)
    light.fill()
  }
  context.setTransform(1, 0, 0, 1, 0, 0)
  const background = context.createRadialGradient(
    canvas.width / 2,
    canvas.height / 2,
    0,
    canvas.width / 2,
    canvas.height / 2,
    Math.max(canvas.width, canvas.height) * 0.75
  )
  background.addColorStop(0, cssColor('--cosmos-void-edge'))
  background.addColorStop(1, cssColor('--cosmos-void'))
  context.fillStyle = background
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.globalCompositeOperation = 'lighter'
  context.filter = `blur(${Math.round(10 * ratio)}px)`
  context.globalAlpha = 0.55
  context.drawImage(layer, 0, 0)
  context.filter = `blur(${Math.round(3 * ratio)}px)`
  context.globalAlpha = 0.6
  context.drawImage(layer, 0, 0)
  context.filter = 'none'
  context.globalAlpha = 1
  context.drawImage(layer, 0, 0)
  context.globalCompositeOperation = 'source-over'
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  if (width < DUST_MIN_WIDTH) return
  context.fillStyle = cssColor('--galaxy-dust', 0.1)
  context.filter = `blur(${Math.round(2 * ratio)}px)`
  for (let index = 0; index < points.dark.count; index += 1) {
    const [px, py] = project(
      points.dark.positions[index * 3],
      points.dark.positions[index * 3 + 1],
      points.dark.positions[index * 3 + 2]
    )
    context.beginPath()
    context.arc(px, py, points.dark.sizes[index] * DOT_SCALE, 0, Math.PI * 2)
    context.fill()
  }
  context.filter = 'none'
}

export function GalaxyThumb({
  galaxy,
  shape,
  label,
  stars = [],
  tilt,
  points = THUMB_POINTS,
  className,
}: GalaxyThumbProps) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const angle =
    tilt ?? MIN_TILT + unitHash(`galaxy-tilt-${galaxy.id}`) * TILT_RANGE
  const signature = JSON.stringify([galaxy, stars, angle, shape, points])
  const latest = useLatest({ galaxy, shape, stars, angle, points })
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const render = () => {
      const now = latest.current
      draw(element, now.galaxy, now.shape, now.stars, now.angle, now.points)
    }
    render()
    const observer = new ResizeObserver(render)
    observer.observe(element)
    return () => observer.disconnect()
  }, [signature, latest])
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}
