type ParticleKind = 'spark' | 'star' | 'mote' | 'flake'

type Particle = {
  kind: ParticleKind
  x: number
  y: number
  px: number
  py: number
  vx: number
  vy: number
  life: number
  decay: number
  size: number
  color: string
  spin: number
  spinRate: number
  gravity: number
  drag: number
  target: { x: number; y: number; pull: number } | null
}

export type Emission = {
  count: number
  colors: readonly string[]
  kinds?: readonly ParticleKind[]
  angle?: number
  spread?: number
  speed?: [number, number]
  size?: [number, number]
  life?: [number, number]
  gravity?: number
  drag?: number
  radius?: number
}

const SPRITE = 64
const CENTER = SPRITE / 2
const GLOW_RINGS = 16
const GLOW_RING_ALPHA = 0.09
const STAR_POINTS = 8
const TINT_ALPHA = 0.62
const MAX_RATIO = 2

function between([low, high]: [number, number]): number {
  return low + Math.random() * (high - low)
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

function glow(context: CanvasRenderingContext2D, radius: number) {
  context.fillStyle = 'white'
  for (let ring = GLOW_RINGS; ring >= 1; ring -= 1) {
    context.globalAlpha = GLOW_RING_ALPHA
    context.beginPath()
    context.arc(CENTER, CENTER, (radius * ring) / GLOW_RINGS, 0, Math.PI * 2)
    context.fill()
  }
  context.globalAlpha = 1
  context.beginPath()
  context.arc(CENTER, CENTER, radius / 10, 0, Math.PI * 2)
  context.fill()
}

let sprites: { glow: HTMLCanvasElement; star: HTMLCanvasElement } | null = null

function spritesOf() {
  if (sprites) return sprites
  sprites = {
    glow: sprite((context) => glow(context, CENTER)),
    star: sprite((context) => {
      context.fillStyle = 'white'
      context.beginPath()
      for (let point = 0; point < STAR_POINTS; point += 1) {
        const radius = point % 2 === 0 ? CENTER - 1 : 3.5
        const angle = (point * Math.PI) / (STAR_POINTS / 2) - Math.PI / 2
        context.lineTo(
          CENTER + Math.cos(angle) * radius,
          CENTER + Math.sin(angle) * radius
        )
      }
      context.closePath()
      context.fill()
      glow(context, CENTER / 2)
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
    const kinds = emission.kinds ?? ['spark', 'star']
    for (let index = 0; index < emission.count; index += 1) {
      const angle =
        (emission.angle ?? 0) +
        (Math.random() - 0.5) * 2 * (emission.spread ?? Math.PI)
      const speed = between(emission.speed ?? [1, 6])
      const reach = emission.radius ? Math.random() * emission.radius : 0
      const around = Math.random() * Math.PI * 2
      const startX = x + Math.cos(around) * reach
      const startY = y + Math.sin(around) * reach
      this.particles.push({
        kind: kinds[Math.floor(Math.random() * kinds.length)],
        x: startX,
        y: startY,
        px: startX,
        py: startY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        decay: 1 / between(emission.life ?? [40, 90]),
        size: between(emission.size ?? [1.5, 4]),
        color:
          emission.colors[Math.floor(Math.random() * emission.colors.length)],
        spin: Math.random() * Math.PI * 2,
        spinRate: (Math.random() - 0.5) * 0.3,
        gravity: emission.gravity ?? 0.04,
        drag: emission.drag ?? 0.975,
        target: null,
      })
    }
    this.wake()
  }

  gather(
    x: number,
    y: number,
    emission: Pick<Emission, 'count' | 'colors' | 'size' | 'life'> & {
      distance: number
    }
  ) {
    for (let index = 0; index < emission.count; index += 1) {
      const angle = Math.random() * Math.PI * 2
      const distance = emission.distance * (0.6 + Math.random() * 0.6)
      const startX = x + Math.cos(angle) * distance
      const startY = y + Math.sin(angle) * distance
      this.particles.push({
        kind: Math.random() < 0.3 ? 'star' : 'mote',
        x: startX,
        y: startY,
        px: startX,
        py: startY,
        vx: Math.sin(angle) * 1.6,
        vy: -Math.cos(angle) * 1.6,
        life: 1,
        decay: 1 / between(emission.life ?? [50, 80]),
        size: between(emission.size ?? [1.5, 3.5]),
        color:
          emission.colors[Math.floor(Math.random() * emission.colors.length)],
        spin: 0,
        spinRate: 0.05,
        gravity: 0,
        drag: 0.9,
        target: { x, y, pull: 0.06 + Math.random() * 0.05 },
      })
    }
    this.wake()
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
      if (particle.life <= 0) continue
      alive.push(particle)
      this.draw(context, particle)
    }
    this.particles = alive
    context.globalAlpha = 1
    this.frame = requestAnimationFrame(this.tick)
  }

  private step(particle: Particle) {
    particle.px = particle.x
    particle.py = particle.y
    if (particle.target) {
      particle.vx += (particle.target.x - particle.x) * particle.target.pull
      particle.vy += (particle.target.y - particle.y) * particle.target.pull
    }
    particle.vx *= particle.drag
    particle.vy = particle.vy * particle.drag + particle.gravity
    if (particle.kind === 'flake') particle.vx += Math.sin(particle.spin) * 0.08
    particle.x += particle.vx
    particle.y += particle.vy
    particle.spin += particle.spinRate
    particle.life -= particle.decay
  }

  private draw(context: CanvasRenderingContext2D, particle: Particle) {
    const fade = Math.min(1, particle.life * 1.6)
    const { glow: glowSprite, star } = spritesOf()
    if (particle.kind === 'spark') {
      context.globalAlpha = fade
      context.strokeStyle = particle.color
      context.lineWidth = particle.size * 0.55
      context.lineCap = 'round'
      context.beginPath()
      context.moveTo(
        particle.px - particle.vx * 1.8,
        particle.py - particle.vy * 1.8
      )
      context.lineTo(particle.x, particle.y)
      context.stroke()
      const size = particle.size * 3
      context.drawImage(
        tint(glowSprite, particle.color, 'glow'),
        particle.x - size / 2,
        particle.y - size / 2,
        size,
        size
      )
      return
    }
    if (particle.kind === 'flake') {
      context.globalAlpha = fade * 0.9
      context.save()
      context.translate(particle.x, particle.y)
      context.rotate(particle.spin)
      context.scale(Math.cos(particle.spin * 2.3), 1)
      context.fillStyle = particle.color
      context.fillRect(
        -particle.size,
        -particle.size * 0.45,
        particle.size * 2,
        particle.size * 0.9
      )
      context.restore()
      return
    }
    const twinkle =
      particle.kind === 'star' ? 0.7 + Math.sin(particle.spin * 6) * 0.3 : 1
    context.globalAlpha = fade * twinkle
    const base = particle.kind === 'star' ? star : glowSprite
    const size = particle.size * (particle.kind === 'star' ? 7 : 5)
    context.drawImage(
      tint(base, particle.color, particle.kind),
      particle.x - size / 2,
      particle.y - size / 2,
      size,
      size
    )
  }
}
