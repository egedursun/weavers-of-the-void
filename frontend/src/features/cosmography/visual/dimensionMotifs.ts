import { type DimensionKind } from './galaxyForm'
import { cssColor } from './palette'

export type Motif = {
  context: CanvasRenderingContext2D
  x: number
  y: number
  r: number
  token: string
  random: () => number
  veil: number
  magic: number
  stability: number
}

const TAU = Math.PI * 2

function glow(m: Motif, x: number, y: number, radius: number, alpha: number) {
  const gradient = m.context.createRadialGradient(x, y, 0, x, y, radius)
  gradient.addColorStop(0, cssColor('--galaxy-core', alpha))
  gradient.addColorStop(0.35, cssColor(m.token, alpha * 0.6))
  gradient.addColorStop(1, cssColor(m.token, 0))
  m.context.fillStyle = gradient
  m.context.beginPath()
  m.context.arc(x, y, radius, 0, TAU)
  m.context.fill()
}

function stroke(m: Motif, alpha: number, width = 1.4) {
  m.context.strokeStyle = cssColor(m.token, alpha)
  m.context.lineWidth = width
  m.context.setLineDash(m.stability < 40 ? [3, 4] : [])
}

function ellipse(
  m: Motif,
  x: number,
  y: number,
  rx: number,
  ry: number,
  turn = 0
) {
  m.context.beginPath()
  m.context.ellipse(x, y, Math.max(rx, 0.5), Math.max(ry, 0.5), turn, 0, TAU)
  m.context.stroke()
}

function dust(m: Motif, count: number, spread: number, squash = 1) {
  for (let index = 0; index < count; index += 1) {
    const angle = m.random() * TAU
    const distance = Math.sqrt(m.random()) * spread
    m.context.fillStyle = cssColor(m.token, 0.3 + m.random() * 0.6)
    m.context.fillRect(
      m.x + Math.cos(angle) * distance,
      m.y + Math.sin(angle) * distance * squash,
      1.4,
      1.4
    )
  }
}

function polyline(m: Motif, points: readonly [number, number][]) {
  m.context.beginPath()
  points.forEach(([px, py], index) =>
    index === 0 ? m.context.moveTo(px, py) : m.context.lineTo(px, py)
  )
  m.context.stroke()
}

function curve(m: Motif, steps: number, at: (t: number) => [number, number]) {
  polyline(
    m,
    Array.from({ length: steps + 1 }, (_, index) => at(index / steps))
  )
}

const prime = (m: Motif) => {
  glow(m, m.x, m.y, m.r * 1.05, 0.5)
  for (let ring = 1; ring <= 4; ring += 1) {
    stroke(m, 0.2 + ring * 0.12, ring === 4 ? 2 : 1)
    ellipse(m, m.x, m.y, (m.r * ring) / 4, (m.r * ring * 0.42) / 4)
  }
  dust(m, 90, m.r, 0.42)
}

const parallel = (m: Motif) => {
  for (let layer = -1; layer <= 1; layer += 1) {
    const y = m.y + layer * m.r * 0.42
    glow(m, m.x, y, m.r * 0.5, 0.35)
    stroke(m, 0.75, 1.6)
    ellipse(m, m.x, y, m.r * 0.92, m.r * 0.2)
  }
  stroke(m, 0.35, 1)
  polyline(m, [
    [m.x - m.r * 0.92, m.y - m.r * 0.42],
    [m.x - m.r * 0.92, m.y + m.r * 0.42],
  ])
  polyline(m, [
    [m.x + m.r * 0.92, m.y - m.r * 0.42],
    [m.x + m.r * 0.92, m.y + m.r * 0.42],
  ])
}

const mirror = (m: Motif) => {
  stroke(m, 0.9, 2)
  polyline(m, [
    [m.x - m.r, m.y],
    [m.x + m.r, m.y],
  ])
  for (const side of [-1, 1]) {
    glow(m, m.x, m.y + side * m.r * 0.45, m.r * 0.45, side < 0 ? 0.6 : 0.3)
    stroke(m, side < 0 ? 0.8 : 0.4, 1.4)
    ellipse(m, m.x, m.y + side * m.r * 0.45, m.r * 0.6, m.r * 0.22)
    ellipse(m, m.x, m.y + side * m.r * 0.45, m.r * 0.32, m.r * 0.12)
  }
}

const pocket = (m: Motif) => {
  stroke(m, 0.35, 1)
  ellipse(m, m.x, m.y, m.r, m.r)
  stroke(m, 0.9, 2)
  ellipse(m, m.x + m.r * 0.35, m.y + m.r * 0.3, m.r * 0.32, m.r * 0.32)
  glow(m, m.x + m.r * 0.35, m.y + m.r * 0.3, m.r * 0.4, 0.8)
  curve(m, 40, (t) => [
    m.x - m.r + t * m.r * 1.4,
    m.y - m.r * 0.2 + Math.sin(t * Math.PI) * m.r * 0.35,
  ])
}

const bubble = (m: Motif) => {
  const bubbles: [number, number, number][] = [
    [0, 0, 0.42],
    [-0.55, -0.35, 0.28],
    [0.55, -0.3, 0.32],
    [-0.45, 0.5, 0.22],
    [0.48, 0.52, 0.26],
    [0.02, -0.72, 0.18],
  ]
  for (const [dx, dy, size] of bubbles) {
    glow(m, m.x + dx * m.r, m.y + dy * m.r, size * m.r, 0.35)
    stroke(m, 0.8, 1.4)
    ellipse(m, m.x + dx * m.r, m.y + dy * m.r, size * m.r, size * m.r)
  }
}

const brane = (m: Motif) => {
  for (let line = 0; line < 9; line += 1) {
    const offset = (line / 8 - 0.5) * m.r * 1.6
    stroke(m, 0.3 + (1 - Math.abs(line / 8 - 0.5)) * 0.5, 1.2)
    curve(m, 60, (t) => [
      m.x - m.r + t * m.r * 2,
      m.y + offset * 0.55 + Math.sin(t * TAU * 1.5 + line * 0.4) * m.r * 0.16,
    ])
  }
  glow(m, m.x, m.y, m.r * 0.35, 0.5)
}

const higher = (m: Motif) => {
  const outer = m.r * 0.85
  const inner = m.r * 0.42
  const square = (half: number, turn: number): [number, number][] =>
    [0, 1, 2, 3, 0].map((corner) => [
      m.x + Math.cos(turn + (corner * TAU) / 4) * half,
      m.y + Math.sin(turn + (corner * TAU) / 4) * half,
    ])
  const big = square(outer, Math.PI / 4)
  const small = square(inner, Math.PI / 4 + 0.35)
  stroke(m, 0.85, 1.8)
  polyline(m, big)
  polyline(m, small)
  stroke(m, 0.45, 1)
  for (let corner = 0; corner < 4; corner += 1)
    polyline(m, [big[corner], small[corner]])
  glow(m, m.x, m.y, m.r * 0.3, 0.6)
}

const antimatter = (m: Motif) => {
  for (let ring = 0; ring < 6; ring += 1) {
    stroke(m, 0.9 - ring * 0.12, 2.4 - ring * 0.3)
    ellipse(m, m.x, m.y, m.r * (0.4 + ring * 0.11), m.r * (0.4 + ring * 0.11))
  }
  m.context.globalCompositeOperation = 'source-over'
  m.context.fillStyle = cssColor('--cosmos-void', 1)
  m.context.beginPath()
  m.context.arc(m.x, m.y, m.r * 0.36, 0, TAU)
  m.context.fill()
  m.context.globalCompositeOperation = 'lighter'
}

const quantum = (m: Motif) => {
  const grow = (
    x: number,
    y: number,
    angle: number,
    length: number,
    depth: number
  ) => {
    if (depth === 0) {
      glow(m, x, y, m.r * 0.06, 0.8)
      return
    }
    const nx = x + Math.cos(angle) * length
    const ny = y + Math.sin(angle) * length
    stroke(m, 0.35 + depth * 0.12, depth * 0.5 + 0.6)
    polyline(m, [
      [x, y],
      [nx, ny],
    ])
    grow(nx, ny, angle - 0.45, length * 0.68, depth - 1)
    grow(nx, ny, angle + 0.45, length * 0.68, depth - 1)
  }
  grow(m.x, m.y + m.r * 0.9, -Math.PI / 2, m.r * 0.55, 5)
}

const timeReversed = (m: Motif) => {
  stroke(m, 0.85, 1.6)
  curve(m, 120, (t) => {
    const angle = t * TAU * 2.6
    const distance = m.r * (1 - t * 0.92)
    return [
      m.x + Math.cos(-angle) * distance,
      m.y + Math.sin(-angle) * distance,
    ]
  })
  for (let arrow = 0; arrow < 4; arrow += 1) {
    const angle = (arrow * TAU) / 4
    const x = m.x + Math.cos(angle) * m.r
    const y = m.y + Math.sin(angle) * m.r
    polyline(m, [
      [
        x + Math.cos(angle + 2.5) * m.r * 0.14,
        y + Math.sin(angle + 2.5) * m.r * 0.14,
      ],
      [x, y],
      [
        x + Math.cos(angle - 2.5) * m.r * 0.14,
        y + Math.sin(angle - 2.5) * m.r * 0.14,
      ],
    ])
  }
  glow(m, m.x, m.y, m.r * 0.18, 0.4)
}

const compactified = (m: Motif) => {
  stroke(m, 0.6, 1.2)
  polyline(m, [
    [m.x - m.r, m.y],
    [m.x + m.r, m.y],
  ])
  for (let coil = 0; coil < 9; coil += 1) {
    const cx = m.x - m.r * 0.85 + (coil / 8) * m.r * 1.7
    const size = m.r * (0.08 + 0.07 * Math.sin((coil / 8) * Math.PI))
    stroke(m, 0.9, 1.4)
    ellipse(m, cx, m.y, size, size * 1.6)
    glow(m, cx, m.y, size * 1.4, 0.35)
  }
}

const astral = (m: Motif) => {
  const points = Array.from({ length: 9 }, () => {
    const angle = m.random() * TAU
    const distance = (0.25 + m.random() * 0.75) * m.r
    return [
      m.x + Math.cos(angle) * distance,
      m.y + Math.sin(angle) * distance,
    ] as [number, number]
  })
  stroke(m, 0.5, 1)
  for (let index = 1; index < points.length; index += 1)
    polyline(m, [points[index - 1], points[index]])
  for (const [px, py] of points) glow(m, px, py, m.r * 0.09, 0.9)
  dust(m, 60, m.r)
}

const ethereal = (m: Motif) => {
  for (let veil = 0; veil < 5; veil += 1) {
    const offset = (veil - 2) * m.r * 0.28
    const gradient = m.context.createLinearGradient(m.x - m.r, 0, m.x + m.r, 0)
    gradient.addColorStop(0, cssColor(m.token, 0))
    gradient.addColorStop(0.5, cssColor(m.token, 0.28))
    gradient.addColorStop(1, cssColor(m.token, 0))
    m.context.fillStyle = gradient
    m.context.beginPath()
    m.context.ellipse(m.x, m.y + offset, m.r, m.r * 0.08, -0.25, 0, TAU)
    m.context.fill()
  }
  dust(m, 40, m.r * 0.9)
}

const dream = (m: Motif) => {
  stroke(m, 0.75, 1.4)
  for (let loop = 0; loop < 3; loop += 1)
    curve(m, 160, (t) => [
      m.x + Math.sin(t * TAU * 3 + loop) * m.r * (0.9 - loop * 0.2),
      m.y + Math.sin(t * TAU * 2) * m.r * (0.6 - loop * 0.12),
    ])
  glow(m, m.x, m.y, m.r * 0.4, 0.35)
}

const shadow = (m: Motif) => {
  glow(m, m.x, m.y, m.r * 1.05, 0.55)
  m.context.globalCompositeOperation = 'source-over'
  m.context.fillStyle = cssColor('--cosmos-void', 1)
  m.context.beginPath()
  m.context.arc(m.x + m.r * 0.08, m.y - m.r * 0.04, m.r * 0.72, 0, TAU)
  m.context.fill()
  m.context.globalCompositeOperation = 'lighter'
  stroke(m, 0.9, 1.6)
  m.context.beginPath()
  m.context.arc(m.x + m.r * 0.08, m.y - m.r * 0.04, m.r * 0.74, 2.2, 4.4)
  m.context.stroke()
}

const spirit = (m: Motif) => {
  for (let wisp = 0; wisp < 5; wisp += 1) {
    const base = m.x - m.r * 0.7 + wisp * m.r * 0.35
    stroke(m, 0.45 + wisp * 0.08, 1.4)
    curve(m, 50, (t) => [
      base + Math.sin(t * TAU * 1.2 + wisp) * m.r * 0.15,
      m.y + m.r * 0.8 - t * m.r * 1.6,
    ])
    glow(
      m,
      base + Math.sin(TAU * 1.2 + wisp) * m.r * 0.15,
      m.y - m.r * 0.8,
      m.r * 0.1,
      0.7
    )
  }
}

const fey = (m: Motif) => {
  stroke(m, 0.85, 1.4)
  curve(m, 240, (t) => {
    const angle = t * TAU
    const distance = m.r * Math.cos(5 * angle)
    return [m.x + Math.cos(angle) * distance, m.y + Math.sin(angle) * distance]
  })
  glow(m, m.x, m.y, m.r * 0.2, 0.7)
}

const elemental = (m: Motif) => {
  stroke(m, 0.45, 1)
  ellipse(m, m.x, m.y, m.r * 0.62, m.r * 0.62)
  for (let element = 0; element < 4; element += 1) {
    const angle = (element * TAU) / 4 - Math.PI / 4
    const x = m.x + Math.cos(angle) * m.r * 0.62
    const y = m.y + Math.sin(angle) * m.r * 0.62
    glow(m, x, y, m.r * 0.26, 0.75)
    stroke(m, 0.85, 1.4)
    ellipse(m, x, y, m.r * 0.16, m.r * 0.16)
  }
}

const celestial = (m: Motif) => {
  for (let ray = 0; ray < 16; ray += 1) {
    const angle = (ray * TAU) / 16
    stroke(m, ray % 2 === 0 ? 0.85 : 0.4, ray % 2 === 0 ? 1.8 : 1)
    polyline(m, [
      [m.x + Math.cos(angle) * m.r * 0.28, m.y + Math.sin(angle) * m.r * 0.28],
      [
        m.x + Math.cos(angle) * m.r * (ray % 2 === 0 ? 1 : 0.7),
        m.y + Math.sin(angle) * m.r * (ray % 2 === 0 ? 1 : 0.7),
      ],
    ])
  }
  glow(m, m.x, m.y, m.r * 0.45, 0.9)
}

const infernal = (m: Motif) => {
  stroke(m, 0.9, 1.8)
  const teeth = 14
  polyline(
    m,
    Array.from({ length: teeth * 2 + 1 }, (_, index) => {
      const angle = (index * TAU) / (teeth * 2)
      const distance = m.r * (index % 2 === 0 ? 0.95 : 0.62)
      return [
        m.x + Math.cos(angle) * distance,
        m.y + Math.sin(angle) * distance,
      ]
    })
  )
  glow(m, m.x, m.y, m.r * 0.6, 0.7)
}

const abyssal = (m: Motif) => {
  for (let ring = 0; ring < 8; ring += 1) {
    const t = ring / 7
    stroke(m, 0.85 - t * 0.6, 1.8 - t)
    ellipse(
      m,
      m.x,
      m.y - m.r * 0.5 + t * m.r * 0.95,
      m.r * (1 - t * 0.85),
      m.r * (0.3 - t * 0.24)
    )
  }
  glow(m, m.x, m.y + m.r * 0.5, m.r * 0.12, 0.4)
}

const limbo = (m: Motif) => {
  const band = m.context.createLinearGradient(0, m.y - m.r, 0, m.y + m.r)
  band.addColorStop(0, cssColor(m.token, 0))
  band.addColorStop(0.55, cssColor(m.token, 0.35))
  band.addColorStop(0.6, cssColor('--galaxy-core', 0.5))
  band.addColorStop(0.68, cssColor(m.token, 0.2))
  band.addColorStop(1, cssColor(m.token, 0))
  m.context.fillStyle = band
  m.context.fillRect(m.x - m.r * 1.2, m.y - m.r, m.r * 2.4, m.r * 2)
  for (let index = 0; index < 30; index += 1) {
    const x = m.x - m.r + m.random() * m.r * 2
    const y = m.y + m.r * 0.2 - m.random() * m.r * 0.9
    m.context.fillStyle = cssColor(m.token, 0.3 + m.random() * 0.4)
    m.context.fillRect(x, y, 2, 2)
  }
}

const farRealm = (m: Motif) => {
  stroke(m, 0.8, 1.3)
  curve(m, 300, (t) => {
    const angle = t * TAU
    const distance =
      m.r * (0.55 + 0.3 * Math.sin(angle * 7) * Math.cos(angle * 3))
    return [
      m.x + Math.cos(angle * 2) * distance,
      m.y + Math.sin(angle * 3) * distance,
    ]
  })
  glow(m, m.x - m.r * 0.2, m.y + m.r * 0.15, m.r * 0.22, 0.6)
}

const clockwork = (m: Motif) => {
  const gear = (
    x: number,
    y: number,
    size: number,
    teeth: number,
    turn: number
  ) => {
    stroke(m, 0.85, 1.4)
    polyline(
      m,
      Array.from({ length: teeth * 4 + 1 }, (_, index) => {
        const angle = turn + (index * TAU) / (teeth * 4)
        const distance = size * (Math.floor(index / 2) % 2 === 0 ? 1 : 0.8)
        return [x + Math.cos(angle) * distance, y + Math.sin(angle) * distance]
      })
    )
    ellipse(m, x, y, size * 0.3, size * 0.3)
  }
  gear(m.x - m.r * 0.3, m.y - m.r * 0.2, m.r * 0.55, 10, 0)
  gear(m.x + m.r * 0.5, m.y + m.r * 0.42, m.r * 0.36, 7, 0.3)
  glow(m, m.x - m.r * 0.3, m.y - m.r * 0.2, m.r * 0.25, 0.5)
}

const chaos = (m: Motif) => {
  for (let scribble = 0; scribble < 7; scribble += 1) {
    stroke(m, 0.4 + m.random() * 0.5, 1 + m.random() * 1.4)
    polyline(
      m,
      Array.from({ length: 7 }, () => [
        m.x + (m.random() - 0.5) * m.r * 1.9,
        m.y + (m.random() - 0.5) * m.r * 1.9,
      ])
    )
  }
  for (let spark = 0; spark < 6; spark += 1)
    glow(
      m,
      m.x + (m.random() - 0.5) * m.r * 1.6,
      m.y + (m.random() - 0.5) * m.r * 1.6,
      m.r * 0.12,
      0.8
    )
}

const underworld = (m: Motif) => {
  for (let tier = 0; tier < 4; tier += 1) {
    stroke(m, 0.85 - tier * 0.15, 1.6)
    ellipse(
      m,
      m.x,
      m.y + tier * m.r * 0.28,
      m.r * (0.95 - tier * 0.2),
      m.r * 0.16
    )
  }
  stroke(m, 0.95, 2)
  m.context.beginPath()
  m.context.moveTo(m.x - m.r * 0.22, m.y + m.r * 0.15)
  m.context.lineTo(m.x - m.r * 0.22, m.y - m.r * 0.45)
  m.context.arc(m.x, m.y - m.r * 0.45, m.r * 0.22, Math.PI, 0)
  m.context.lineTo(m.x + m.r * 0.22, m.y + m.r * 0.15)
  m.context.stroke()
  glow(m, m.x, m.y - m.r * 0.25, m.r * 0.2, 0.6)
}

const divine = (m: Motif) => {
  stroke(m, 0.9, 2)
  polyline(m, [
    [m.x, m.y - m.r * 0.85],
    [m.x + m.r * 0.75, m.y + m.r * 0.55],
    [m.x - m.r * 0.75, m.y + m.r * 0.55],
    [m.x, m.y - m.r * 0.85],
  ])
  stroke(m, 0.6, 1.2)
  ellipse(m, m.x, m.y - m.r * 0.85, m.r * 0.32, m.r * 0.1)
  glow(m, m.x, m.y + m.r * 0.05, m.r * 0.5, 0.75)
}

const voidBetween = (m: Motif) => {
  stroke(m, 0.8, 2.2)
  m.context.setLineDash([3, 7])
  ellipse(m, m.x, m.y, m.r, m.r)
  ellipse(m, m.x, m.y, m.r * 0.55, m.r * 0.55)
  m.context.setLineDash([])
  stroke(m, 0.5, 1)
  polyline(m, [
    [m.x - m.r * 0.15, m.y],
    [m.x + m.r * 0.15, m.y],
  ])
  polyline(m, [
    [m.x, m.y - m.r * 0.15],
    [m.x, m.y + m.r * 0.15],
  ])
}

export const DIMENSION_MOTIF: Record<DimensionKind, (m: Motif) => void> = {
  prime,
  parallel,
  mirror,
  pocket,
  bubble_universe: bubble,
  brane,
  higher_dimensional: higher,
  antimatter,
  quantum_branch: quantum,
  time_reversed: timeReversed,
  compactified,
  astral,
  ethereal,
  dream,
  shadow,
  spirit,
  fey,
  elemental,
  celestial,
  infernal,
  abyssal,
  limbo,
  far_realm: farRealm,
  clockwork,
  chaos,
  underworld,
  divine_domain: divine,
  void_between: voidBetween,
}
