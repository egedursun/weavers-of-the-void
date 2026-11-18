type ParticleKind = 'spark' | 'star' | 'ember' | 'flake'

type Particle = {
  kind: ParticleKind
  x: number
  y: number
  vx: number
  vy: number
  age: number
  life: number
  size: number
  color: string
  spin: number
  spinRate: number
  gravity: number
  drag: number
  trail: number
  target: { x: number; y: number; pull: number } | null
}

type Range = [number, number]

export type Emission = {
  count: number
  colors: readonly string[]
  kinds?: readonly ParticleKind[]
  angle?: number
  spread?: number
  speed?: Range
  size?: Range
  life?: Range
  gravity?: number
  drag?: number
  trail?: Range
}

export type Frame = { x: number; y: number; width: number; height: number }

const SPRITE = 128
const CENTER = SPRITE / 2
const TINT_ALPHA = 0.7
const MAX_RATIO = 2
const FADE_IN = 0.08

function between([low, high]: Range): number {
  return low + Math.random() * (high - low)
}

function pick<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)]
}

function sprite(
  draw: (context: CanvasRenderingContext2D) => void
): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = SPRITE
  canvas.height = SPRITE
  const context = canvas.getContext('2d')
  if (context) draw(context)
  return canvas
}

function softDisc(
  context: CanvasRenderingContext2D,
  radius: number,
  core: number
) {
  const gradient = context.createRadialGradient(
    CENTER,
    CENTER,
    0,
    CENTER,
    CENTER,
    radius
  )
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(core, 'rgba(255,255,255,0.55)')
  gradient.addColorStop(0.55, 'rgba(255,255,255,0.12)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, SPRITE, SPRITE)
}

function flare(
  context: CanvasRenderingContext2D,
  length: number,
  thickness: number,
  angle: number
) {
  context.save()
  context.translate(CENTER, CENTER)
  context.rotate(angle)
  const gradient = context.createLinearGradient(-length, 0, length, 0)
  gradient.addColorStop(0, 'rgba(255,255,255,0)')
  gradient.addColorStop(0.42, 'rgba(255,255,255,0.35)')
  gradient.addColorStop(0.5, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.58, 'rgba(255,255,255,0.35)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  context.fillStyle = gradient
  context.beginPath()
  context.moveTo(-length, 0)
  context.quadraticCurveTo(0, -thickness, length, 0)
  context.quadraticCurveTo(0, thickness, -length, 0)
  context.fill()
  context.restore()
}

let sprites: { glow: HTMLCanvasElement; star: HTMLCanvasElement } | null = null

function spritesOf() {
  if (sprites) return sprites
  sprites = {
    glow: sprite((context) => softDisc(context, CENTER, 0.12)),
    star: sprite((context) => {
      softDisc(context, CENTER * 0.42, 0.18)
      flare(context, CENTER - 2, 3.2, 0)
      flare(context, CENTER - 2, 3.2, Math.PI / 2)
      flare(context, CENTER * 0.45, 1.6, Math.PI / 4)
      flare(context, CENTER * 0.45, 1.6, -Math.PI / 4)
    }),
  }
  return sprites
}

const tinted = new Map<string, HTMLCanvasElement>()

function tint(
  base: HTMLCanvasElement,
  color: string,
  key: string
): HTMLCanvasElement {
  const cacheKey = `${key}:${color}`
  const cached = tinted.get(cacheKey)
  if (cached) return cached
  const canvas = sprite((context) => {
    context.drawImage(base, 0, 0)
    context.globalCompositeOperation = 'source-atop'
    context.globalAlpha = TINT_ALPHA
    context.fillStyle = color
    context.fillRect(0, 0, SPRITE, SPRITE)
    context.globalCompositeOperation = 'lighter'
    context.globalAlpha = 0.5
    const core = context.createRadialGradient(
      CENTER,
      CENTER,
      0,
      CENTER,
      CENTER,
      CENTER * 0.14
    )
    core.addColorStop(0, 'rgba(255,255,255,1)')
    core.addColorStop(1, 'rgba(255,255,255,0)')
    context.fillStyle = core
    context.fillRect(0, 0, SPRITE, SPRITE)
  })
  tinted.set(cacheKey, canvas)
  return canvas
}

export function tokenColor(
  name: string,
  scope: Element = document.documentElement
): string {
  return getComputedStyle(scope).getPropertyValue(name).trim() || 'white'
}

function edgePoint(frame: Frame): { x: number; y: number } {
  const perimeter = 2 * (frame.width + frame.height)
  let along = Math.random() * perimeter
  const left = frame.x - frame.width / 2
  const top = frame.y - frame.height / 2
  if (along < frame.width) return { x: left + along, y: top }
  along -= frame.width
  if (along < frame.height) return { x: left + frame.width, y: top + along }
  along -= frame.height
  if (along < frame.width)
    return { x: left + frame.width - along, y: top + frame.height }
  along -= frame.width
  return { x: left, y: top + frame.height - along }
}

export class ParticleField {
  private canvas: HTMLCanvasElement
  private context: CanvasRenderingContext2D | null
  private particles: Particle[] = []
  private frame = 0
  private ratio = 1

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas
    this.context = canvas.getContext('2d')
    this.resize()
  }

  resize() {
    const box = this.canvas.getBoundingClientRect()
    this.ratio = Math.min(MAX_RATIO, window.devicePixelRatio || 1)
    this.canvas.width = Math.max(1, Math.round(box.width * this.ratio))
    this.canvas.height = Math.max(1, Math.round(box.height * this.ratio))
  }

  dispose() {
    cancelAnimationFrame(this.frame)
    this.frame = 0
    this.particles = []
  }

  emit(x: number, y: number, emission: Emission) {
    for (let index = 0; index < emission.count; index += 1) {
      const angle =
        (emission.angle ?? 0) +
        (Math.random() - 0.5) * 2 * (emission.spread ?? Math.PI)
      this.spawn(x, y, angle, emission, null)
    }
    this.wake()
  }

  burst(frame: Frame, emission: Emission) {
    for (let index = 0; index < emission.count; index += 1) {
      const point = edgePoint(frame)
      const outward = Math.atan2(point.y - frame.y, point.x - frame.x)
      const angle =
        outward + (Math.random() - 0.5) * 2 * (emission.spread ?? 0.35)
      this.spawn(point.x, point.y, angle, emission, null)
    }
    this.wake()
  }

  gather(
    x: number,
    y: number,
    emission: Emission & {
      distance: number
    }
  ) {
    for (let index = 0; index < emission.count; index += 1) {
      const around = Math.random() * Math.PI * 2
      const distance = emission.distance * (0.55 + Math.random() * 0.6)
      this.spawn(
        x + Math.cos(around) * distance,
        y + Math.sin(around) * distance,
        around + Math.PI / 2,
        { ...emission, speed: emission.speed ?? [0.6, 1.6] },
        { x, y, pull: 0.0016 + Math.random() * 0.001 }
      )
    }
    this.wake()
  }

  private spawn(
    x: number,
    y: number,
    angle: number,
    emission: Emission,
    target: Particle['target']
  ) {
    const speed = between(emission.speed ?? [1, 6])
    this.particles.push({
      kind: pick(emission.kinds ?? ['spark', 'star']),
      x,
      y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      age: 0,
      life: between(emission.life ?? [40, 90]),
      size: between(emission.size ?? [1.5, 4]),
      color: pick(emission.colors),
      spin: Math.random() * Math.PI * 2,
      spinRate: (Math.random() - 0.5) * 0.12,
      gravity: emission.gravity ?? 0.03,
      drag: emission.drag ?? 0.96,
      trail: between(emission.trail ?? [3, 6]),
      target,
    })
  }

  private wake() {
    if (this.frame === 0) this.frame = requestAnimationFrame(this.tick)
  }

  private tick = () => {
    const context = this.context
    if (!context) {
      this.frame = 0
      return
    }
    context.setTransform(1, 0, 0, 1, 0, 0)
    context.clearRect(0, 0, this.canvas.width, this.canvas.height)
    if (this.particles.length === 0) {
      this.frame = 0
      return
    }
    context.setTransform(this.ratio, 0, 0, this.ratio, 0, 0)
    context.globalCompositeOperation = 'lighter'
    const alive: Particle[] = []
    for (const particle of this.particles) {
      this.step(particle)
      if (particle.age >= particle.life) continue
      alive.push(particle)
      this.draw(context, particle)
    }
    this.particles = alive
    context.globalAlpha = 1
    this.frame = requestAnimationFrame(this.tick)
  }

  private step(particle: Particle) {
    particle.age += 1
    if (particle.target) {
      const dx = particle.target.x - particle.x
      const dy = particle.target.y - particle.y
      particle.vx += dx * particle.target.pull
      particle.vy += dy * particle.target.pull
      if (dx * dx + dy * dy < 400) particle.age = particle.life
    }
    particle.vx *= particle.drag
    particle.vy = particle.vy * particle.drag + particle.gravity
    if (particle.kind === 'flake') particle.vx += Math.sin(particle.spin) * 0.05
    if (particle.kind === 'ember')
      particle.vx += Math.sin(particle.age * 0.08 + particle.spin) * 0.02
    particle.x += particle.vx
    particle.y += particle.vy
    particle.spin += particle.spinRate
  }

  private alpha(particle: Particle): number {
    const t = particle.age / particle.life
    const rise = Math.min(1, t / FADE_IN)
    return rise * (1 - t) ** 1.4
  }

  private draw(context: CanvasRenderingContext2D, particle: Particle) {
    const alpha = this.alpha(particle)
    if (alpha <= 0.002) return
    const { glow, star } = spritesOf()
    if (particle.kind === 'spark') {
      const tailX = particle.x - particle.vx * particle.trail
      const tailY = particle.y - particle.vy * particle.trail
      const streak = context.createLinearGradient(
        tailX,
        tailY,
        particle.x,
        particle.y
      )
      streak.addColorStop(0, 'rgba(255,255,255,0)')
      streak.addColorStop(1, particle.color)
      context.globalAlpha = alpha
      context.strokeStyle = streak
      context.lineCap = 'round'
      context.lineWidth = particle.size * 0.7
      context.beginPath()
      context.moveTo(tailX, tailY)
      context.lineTo(particle.x, particle.y)
      context.stroke()
      const head = particle.size * 4
      context.drawImage(
        tint(glow, particle.color, 'glow'),
        particle.x - head / 2,
        particle.y - head / 2,
        head,
        head
      )
      return
    }
    if (particle.kind === 'flake') {
      const glint = 0.35 + Math.abs(Math.cos(particle.spin * 2.3)) * 0.65
      context.globalAlpha = alpha * glint
      context.save()
      context.translate(particle.x, particle.y)
      context.rotate(particle.spin)
      context.scale(Math.cos(particle.spin * 2.3), 1)
      context.fillStyle = particle.color
      context.fillRect(
        -particle.size * 0.8,
        -particle.size * 0.35,
        particle.size * 1.6,
        particle.size * 0.7
      )
      context.restore()
      return
    }
    if (particle.kind === 'ember') {
      const flicker = 0.7 + Math.sin(particle.age * 0.3 + particle.spin) * 0.3
      context.globalAlpha = alpha * flicker
      const size = particle.size * 4
      context.drawImage(
        tint(glow, particle.color, 'glow'),
        particle.x - size / 2,
        particle.y - size / 2,
        size,
        size
      )
      return
    }
    const twinkle = 0.65 + Math.sin(particle.age * 0.22 + particle.spin) * 0.35
    context.globalAlpha = alpha
    const size = particle.size * 9 * twinkle
    context.save()
    context.translate(particle.x, particle.y)
    context.rotate(particle.spin * 0.25)
    context.drawImage(
      tint(star, particle.color, 'star'),
      -size / 2,
      -size / 2,
      size,
      size
    )
    context.restore()
  }
}
