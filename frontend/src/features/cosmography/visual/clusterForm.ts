import type { components } from '@/api/generated/schema'
import { seededRandom } from '@/lib/hash'
import { type Palette, type Rgb } from './galaxyForm'

export type ClusterKind = components['schemas']['ClusterKind']

export type ClusterMember = { x: number; y: number; z: number; size: number }

export type ClusterLook = {
  body: string
  glow: string
  edge: string
  accents: readonly string[]
  light: number
  haze: number
}

const CORE = '--galaxy-core'
const HALO = '--galaxy-halo'

export const CLUSTER_LOOK: Record<ClusterKind, ClusterLook> = {
  galaxy_group: {
    body: '--galaxy-young',
    glow: CORE,
    edge: HALO,
    accents: ['--galaxy-nursery', '--galaxy-leak', '--galaxy-hollow'],
    light: 0.42,
    haze: 0.07,
  },
  local_group: {
    body: '--galaxy-young',
    glow: CORE,
    edge: HALO,
    accents: ['--galaxy-nursery', '--galaxy-leak', '--galaxy-hollow'],
    light: 0.42,
    haze: 0.07,
  },
  poor_cluster: {
    body: '--galaxy-disc',
    glow: CORE,
    edge: HALO,
    accents: ['--galaxy-leak', '--galaxy-young', '--galaxy-nursery'],
    light: 0.38,
    haze: 0.06,
  },
  rich_cluster: {
    body: '--galaxy-old',
    glow: CORE,
    edge: '--galaxy-bulge',
    accents: ['--galaxy-nursery', '--galaxy-leak', '--structure-emission'],
    light: 0.5,
    haze: 0.1,
  },
  supercluster: {
    body: '--galaxy-disc',
    glow: CORE,
    edge: HALO,
    accents: ['--galaxy-hollow', '--galaxy-leak', '--galaxy-nursery'],
    light: 0.42,
    haze: 0.07,
  },
  filament: {
    body: '--galaxy-young',
    glow: CORE,
    edge: HALO,
    accents: ['--galaxy-hollow', '--structure-planetary', '--galaxy-leak'],
    light: 0.48,
    haze: 0.06,
  },
  wall: {
    body: '--galaxy-disc',
    glow: CORE,
    edge: HALO,
    accents: ['--structure-reflection', '--galaxy-leak', '--galaxy-nursery'],
    light: 0.42,
    haze: 0.07,
  },
  void: {
    body: HALO,
    glow: '--galaxy-hollow',
    edge: '--galaxy-veiled',
    accents: ['--galaxy-leak', '--galaxy-hollow', '--structure-reflection'],
    light: 0.5,
    haze: 0.1,
  },
  crown_cluster: {
    body: '--galaxy-crowned',
    glow: CORE,
    edge: '--galaxy-bulge',
    accents: ['--galaxy-old', '--structure-emission', '--galaxy-forged'],
    light: 0.48,
    haze: 0.08,
  },
  drowned_cluster: {
    body: '--structure-reflection',
    glow: '--galaxy-hollow',
    edge: '--galaxy-veiled',
    accents: ['--structure-planetary', '--galaxy-hollow', '--galaxy-leak'],
    light: 0.42,
    haze: 0.09,
  },
  forge_cluster: {
    body: '--galaxy-forged',
    glow: CORE,
    edge: '--galaxy-ember',
    accents: ['--galaxy-ember', '--structure-emission', '--galaxy-crowned'],
    light: 0.5,
    haze: 0.09,
  },
  dream_cluster: {
    body: '--galaxy-dreaming',
    glow: CORE,
    edge: '--galaxy-leak',
    accents: ['--galaxy-nursery', '--structure-bubble', '--galaxy-hollow'],
    light: 0.46,
    haze: 0.08,
  },
  mirror_cluster: {
    body: '--galaxy-mirror',
    glow: '--galaxy-quasar',
    edge: '--galaxy-young',
    accents: ['--galaxy-hollow', '--galaxy-leak', '--galaxy-young'],
    light: 0.42,
    haze: 0.06,
  },
}

export type ClusterVeil = 'cloud' | 'shell'

export type ClusterFrame = {
  centre: [number, number, number]
  angle: number
  major: number
  minor: number
  ring: number
}

export type ClusterCloud = ClusterFrame & {
  count: number
  positions: Float32Array
  colors: Float32Array
  sizes: Float32Array
  seeds: Float32Array
  veil: ClusterVeil
}

type Context = {
  random: () => number
  put: (
    x: number,
    y: number,
    z: number,
    color: Rgb,
    size: number,
    light: number
  ) => void
  local: (u: number, v: number, h: number) => [number, number, number]
  members: readonly ClusterMember[]
  frame: ClusterFrame
  size: number
  body: Rgb
  glow: Rgb
  edge: Rgb
}

type Generator = (context: Context, budget: number) => void

const MIN_SPAN = 0.25
const VEIL_SPAN = 0.35
const CLUMP_LIMIT = 4
const RIPPLES = 4
const OUTLINE_SEGMENTS = 96
const RIBBON_SHARE = 0.35

function ribbons(context: Context, links: readonly Link[], budget: number) {
  const { random, put, body, glow } = context
  const total = links.reduce((sum, [from, to]) => sum + distanceOf(from, to), 0)
  if (total <= 0) return
  for (const [from, to] of links) {
    const span = distanceOf(from, to)
    const share = Math.round((budget * span) / total)
    const width = span * 0.035 + Math.min(from.size, to.size) * 0.12
    for (let index = 0; index < share; index += 1) {
      const t = random()
      const sag = Math.sin(t * Math.PI)
      const spread = width * (0.6 + 0.6 * sag)
      put(
        from.x + (to.x - from.x) * t + gaussian(random) * spread,
        from.y + (to.y - from.y) * t + gaussian(random) * spread * 0.3,
        from.z + (to.z - from.z) * t + gaussian(random) * spread,
        mix(glow, body, 0.25 + sag * 0.5),
        1.6 + random() * 2.4,
        0.45 * (1 - sag * 0.35)
      )
    }
  }
}
const CLOUD_LIGHT = 1.15
const ACCENT_SHARE = 0.6
const ACCENT_MIX = 0.75

function gaussian(random: () => number): number {
  const u = Math.max(random(), 1e-6)
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * random())
}

function mix(a: Rgb, b: Rgb, t: number): Rgb {
  const k = Math.min(Math.max(t, 0), 1)
  return [
    a[0] + (b[0] - a[0]) * k,
    a[1] + (b[1] - a[1]) * k,
    a[2] + (b[2] - a[2]) * k,
  ]
}

function at<T>(items: readonly T[], index: number, fallback: T): T {
  return items[index] ?? fallback
}

function distanceOf(a: ClusterMember, b: ClusterMember): number {
  return Math.hypot(a.x - b.x, a.z - b.z)
}

export function clusterFrame(
  members: readonly ClusterMember[],
  size: number
): ClusterFrame {
  if (members.length === 0)
    return {
      centre: [0, 0, 0],
      angle: 0,
      major: size * 0.6,
      minor: size * 0.6,
      ring: size * 0.6,
    }
  const cy = members.reduce((sum, row) => sum + row.y, 0) / members.length
  let xx = 0
  let zz = 0
  let xz = 0
  for (const row of members) {
    xx += row.x ** 2
    zz += row.z ** 2
    xz += row.x * row.z
  }
  const angle = 0.5 * Math.atan2(2 * xz, xx - zz)
  const ux = Math.cos(angle)
  const uz = Math.sin(angle)
  let major = 0
  let minor = 0
  for (const row of members) {
    major = Math.max(major, Math.abs(row.x * ux + row.z * uz) + row.size)
    minor = Math.max(minor, Math.abs(-row.x * uz + row.z * ux) + row.size)
  }
  const reaches = members
    .map((row) => Math.hypot(row.x, row.z))
    .sort((a, b) => a - b)
  const floor = size * MIN_SPAN
  return {
    centre: [0, cy, 0],
    angle,
    major: Math.max(major, floor),
    minor: Math.max(minor, floor),
    ring: Math.max(at(reaches, Math.floor(reaches.length / 2), floor), floor),
  }
}

function heartOf(members: readonly ClusterMember[]): ClusterMember | null {
  return [...members].sort((a, b) => b.size - a.size)[0] ?? null
}

function halos(context: Context, budget: number, light = 0.5) {
  const { random, put, members, body, glow } = context
  if (members.length === 0) return
  const total = members.reduce((sum, row) => sum + row.size, 0)
  for (let index = 0; index < budget; index += 1) {
    let pick = random() * total
    let member = at(members, 0, members[0])
    for (const row of members) {
      pick -= row.size
      member = row
      if (pick <= 0) break
    }
    if (!member) return
    const spread = member.size * 0.8
    const dx = gaussian(random) * spread
    const dz = gaussian(random) * spread
    const distance = Math.hypot(dx, dz) / spread
    put(
      member.x + dx,
      member.y + gaussian(random) * member.size * 0.16,
      member.z + dz,
      mix(glow, body, 0.35 + distance * 0.4),
      1.6 + random() * 2,
      light * Math.exp(-distance * 1.1)
    )
  }
}

function envelope(
  context: Context,
  budget: number,
  stretch = 0.6,
  lift = 0.05,
  light = 0.22
) {
  const { random, put, local, frame, size, body, edge } = context
  for (let index = 0; index < budget; index += 1) {
    const u = gaussian(random) * frame.major * stretch
    const v = gaussian(random) * (frame.minor * stretch + size * 0.06)
    const reach = Math.hypot(
      u / Math.max(frame.major, 1),
      v / Math.max(frame.minor, 1)
    )
    put(
      ...local(u, v, gaussian(random) * size * lift),
      mix(body, edge, 0.3 + reach * 0.6),
      2 + random() * 2.4,
      light * Math.max(1 - reach * 0.6, 0.05)
    )
  }
}

function strand(
  context: Context,
  from: ClusterMember,
  to: ClusterMember,
  budget: number,
  light = 0.32
) {
  const { random, put, body, edge } = context
  const span = distanceOf(from, to)
  const width = Math.max(Math.min(from.size, to.size) * 0.16, span * 0.018)
  for (let index = 0; index < budget; index += 1) {
    const t = random()
    const sag = Math.sin(t * Math.PI)
    put(
      from.x + (to.x - from.x) * t + gaussian(random) * width,
      from.y + (to.y - from.y) * t + gaussian(random) * width * 0.35,
      from.z + (to.z - from.z) * t + gaussian(random) * width,
      mix(body, edge, sag * 0.6),
      1.4 + random() * 1.4,
      light * (1 - sag * 0.6)
    )
  }
}

type Link = [ClusterMember, ClusterMember]

function nearestPairs(members: readonly ClusterMember[]): Link[] {
  const links: Link[] = []
  const seen = new Set<string>()
  members.forEach((member, index) => {
    let best = -1
    members.forEach((other, position) => {
      if (position === index) return
      if (
        best < 0 ||
        distanceOf(member, other) <
          distanceOf(member, at(members, best, member))
      )
        best = position
    })
    if (best < 0) return
    const key = index < best ? `${index}-${best}` : `${best}-${index}`
    if (seen.has(key)) return
    seen.add(key)
    links.push([member, at(members, best, member)])
  })
  return links
}

function nearestStrands(context: Context, budget: number, light = 0.28) {
  const links = nearestPairs(context.members)
  const share = Math.max(Math.floor(budget / Math.max(links.length, 1)), 1)
  for (const [from, to] of links) strand(context, from, to, share, light)
}

function hotCore(
  context: Context,
  budget: number,
  core: number,
  flatten: number,
  anchor: ClusterMember | null
) {
  const { random, put, local, frame, body, glow, edge } = context
  const ratio = Math.max(frame.minor / Math.max(frame.major, 1), 0.7)
  const [ox, oy, oz] = anchor
    ? [
        anchor.x - frame.centre[0],
        anchor.y - frame.centre[1],
        anchor.z - frame.centre[2],
      ]
    : [0, 0, 0]
  for (let index = 0; index < budget; index += 1) {
    const u = Math.min(random(), 0.985)
    const reach = Math.min(core * Math.sqrt(u / (1 - u)), frame.major * 1.1)
    const angle = random() * Math.PI * 2
    const tilt = Math.asin(random() * 2 - 1)
    const level = 1 / (1 + (reach / core) ** 2)
    const [x, y, z] = local(
      Math.cos(angle) * Math.cos(tilt) * reach,
      Math.sin(angle) * Math.cos(tilt) * reach * ratio,
      Math.sin(tilt) * reach * flatten
    )
    put(
      x + ox,
      y + oy,
      z + oz,
      reach < core * 1.4
        ? mix(glow, body, reach / (core * 1.4))
        : mix(body, edge, reach / frame.major),
      1.6 + level * 2.2 + random(),
      0.07 + level * 0.36
    )
  }
}

function groupCloud(context: Context, budget: number) {
  halos(context, Math.round(budget * 0.35))
  envelope(context, Math.round(budget * 0.4))
  nearestStrands(context, Math.round(budget * 0.25))
}

function localGroup(context: Context, budget: number) {
  const hosts = [...context.members].sort((a, b) => b.size - a.size)
  halos(context, Math.round(budget * 0.35))
  const first = hosts[0]
  const second = hosts[1]
  if (first && second)
    strand(context, first, second, Math.round(budget * 0.2), 0.4)
  envelope(context, Math.round(budget * 0.3), 0.55)
  nearestStrands(context, Math.round(budget * 0.15), 0.22)
}

function richCluster(context: Context, budget: number) {
  hotCore(
    context,
    Math.round(budget * 0.45),
    context.frame.major * 0.16,
    0.5,
    heartOf(context.members)
  )
  halos(context, Math.round(budget * 0.3))
  envelope(context, Math.round(budget * 0.25), 0.7, 0.1, 0.16)
}

function clumpsOf(
  members: readonly ClusterMember[],
  frame: ClusterFrame
): ClusterMember[][] {
  const [cx, , cz] = frame.centre
  const count = Math.min(CLUMP_LIMIT, Math.max(members.length, 1))
  const sorted = [...members].sort(
    (a, b) => Math.atan2(a.z - cz, a.x - cx) - Math.atan2(b.z - cz, b.x - cx)
  )
  const groups: ClusterMember[][] = Array.from({ length: count }, () => [])
  sorted.forEach((member, index) => {
    at(groups, Math.floor((index * count) / sorted.length), []).push(member)
  })
  return groups.filter((group) => group.length > 0)
}

function centreOf(group: readonly ClusterMember[]): ClusterMember {
  return {
    x: group.reduce((sum, row) => sum + row.x, 0) / group.length,
    y: group.reduce((sum, row) => sum + row.y, 0) / group.length,
    z: group.reduce((sum, row) => sum + row.z, 0) / group.length,
    size: Math.max(...group.map((row) => row.size)),
  }
}

function supercluster(context: Context, budget: number) {
  const { random, put, body, glow } = context
  const groups = clumpsOf(context.members, context.frame)
  const centres = groups.map(centreOf)
  const clumpShare = Math.round((budget * 0.35) / Math.max(groups.length, 1))
  groups.forEach((group, index) => {
    const centre = at(centres, index, centreOf(group))
    const reach =
      Math.max(...group.map((row) => distanceOf(row, centre) + row.size)) * 0.5
    for (let step = 0; step < clumpShare; step += 1) {
      const dx = gaussian(random) * reach
      const dz = gaussian(random) * reach
      const distance = Math.hypot(dx, dz) / Math.max(reach, 1)
      put(
        centre.x + dx,
        centre.y + gaussian(random) * reach * 0.1,
        centre.z + dz,
        mix(glow, body, 0.3 + distance * 0.5),
        1.8 + random() * 2,
        0.36 * Math.exp(-distance * 0.8)
      )
    }
  })
  const strandShare = Math.round((budget * 0.25) / Math.max(centres.length, 1))
  centres.forEach((centre, index) => {
    const next = at(centres, (index + 1) % centres.length, centre)
    if (next !== centre) strand(context, centre, next, strandShare, 0.22)
  })
  halos(context, Math.round(budget * 0.25))
  envelope(context, Math.round(budget * 0.15), 0.9, 0.06, 0.1)
}

function filament(context: Context, budget: number) {
  const { random, put, local, frame, members, size, body, glow } = context
  const [cx, , cz] = frame.centre
  const ux = Math.cos(frame.angle)
  const uz = Math.sin(frame.angle)
  const along = members.map((row) => ({
    u: (row.x - cx) * ux + (row.z - cz) * uz,
    v: -(row.x - cx) * uz + (row.z - cz) * ux,
    size: row.size,
  }))
  const low =
    Math.min(...along.map((row) => row.u), -frame.major * 0.5) -
    frame.major * 0.25
  const high =
    Math.max(...along.map((row) => row.u), frame.major * 0.5) +
    frame.major * 0.25
  const spine = Math.round(budget * 0.6)
  const fade = frame.major * 0.3
  for (let index = 0; index < spine; index += 1) {
    const u = low + (high - low) * random()
    let knot = 0
    let bend = 0
    let weight = 0
    for (const row of along) {
      knot = Math.max(knot, Math.exp(-(((u - row.u) / (row.size * 1.4)) ** 2)))
      const pull = Math.exp(-(((u - row.u) / (frame.major * 0.35)) ** 2))
      bend += row.v * pull
      weight += pull
    }
    const centreLine = weight > 0 ? bend / weight : 0
    const taper = Math.min((u - low) / fade, (high - u) / fade, 1)
    const width = frame.major * 0.03 * (0.5 + 1.2 * knot) + size * 0.008
    put(
      ...local(
        u,
        centreLine + gaussian(random) * width,
        gaussian(random) * width * 0.6
      ),
      mix(body, glow, knot * 0.7),
      1.4 + knot * 2.2 + random(),
      (0.2 + 0.5 * knot) * Math.max(taper, 0.04)
    )
  }
  halos(context, Math.round(budget * 0.28))
  envelope(context, Math.round(budget * 0.12), 0.8, 0.04, 0.1)
}

function wall(context: Context, budget: number) {
  const { random, put, local, frame, size, body, glow } = context
  const across = Math.max(frame.minor * 1.4, frame.major * 0.35)
  const reach = frame.major * 1.15
  const blobs = Array.from({ length: 14 }, () => {
    const angle = random() * Math.PI * 2
    const distance = Math.sqrt(random()) * 0.85
    return [Math.cos(angle) * distance, Math.sin(angle) * distance] as const
  })
  const sheet = Math.round(budget * 0.55)
  let drawn = 0
  let tries = 0
  while (drawn < sheet && tries < sheet * 6) {
    tries += 1
    const angle = random() * Math.PI * 2
    const distance = Math.sqrt(random())
    const p = Math.cos(angle) * distance
    const q = Math.sin(angle) * distance
    const blob = Math.max(
      ...blobs.map(([bx, by]) =>
        Math.exp(-(((p - bx) ** 2 + (q - by) ** 2) / 0.05))
      )
    )
    if (random() > 0.25 + 0.75 * blob) continue
    drawn += 1
    put(
      ...local(p * reach, q * across, gaussian(random) * size * 0.015),
      mix(body, glow, blob * 0.6),
      1.4 + blob * 2 + random(),
      (0.14 + 0.36 * blob) * (1 - distance * 0.45)
    )
  }
  halos(context, Math.round(budget * 0.28))
  envelope(context, Math.round(budget * 0.17), 0.75, 0.02, 0.12)
}

function voidShell(context: Context, budget: number) {
  const { random, put, local, frame, members, body, glow, edge } = context
  const [cx, , cz] = frame.centre
  const angles = members.map((row) => Math.atan2(row.z - cz, row.x - cx))
  const shell = Math.round(budget * 0.55)
  for (let index = 0; index < shell; index += 1) {
    const angle = random() * Math.PI * 2
    const radius = frame.ring + gaussian(random) * frame.ring * 0.08
    const near = angles.reduce((best, towards) => {
      const gap = Math.atan2(
        Math.sin(angle - towards),
        Math.cos(angle - towards)
      )
      return Math.max(best, Math.exp(-((gap / 0.25) ** 2)))
    }, 0)
    put(
      ...local(
        Math.cos(angle - frame.angle) * radius,
        Math.sin(angle - frame.angle) * radius,
        gaussian(random) * frame.ring * 0.04
      ),
      mix(body, glow, near * 0.8),
      1.4 + near * 2 + random(),
      0.18 + 0.32 * near
    )
  }
  const specks = Math.round(budget * 0.05)
  for (let index = 0; index < specks; index += 1) {
    const angle = random() * Math.PI * 2
    const radius = Math.sqrt(random()) * frame.ring * 0.7
    put(
      ...local(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        gaussian(random) * frame.ring * 0.03
      ),
      edge,
      1.2 + random(),
      0.05
    )
  }
  const rim = Math.round(budget * 0.1)
  for (let index = 0; index < rim; index += 1) {
    const angle = random() * Math.PI * 2
    const radius = frame.ring * (1.15 + Math.abs(gaussian(random)) * 0.3)
    put(
      ...local(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        gaussian(random) * frame.ring * 0.05
      ),
      mix(body, edge, 0.6),
      1.8 + random() * 1.6,
      0.08
    )
  }
  halos(context, Math.round(budget * 0.3))
}

function spokes(
  context: Context,
  heart: ClusterMember,
  ends: readonly ClusterMember[],
  budget: number,
  light: number
) {
  const { random, put, body, glow } = context
  const share = Math.max(Math.round(budget / Math.max(ends.length, 1)), 1)
  for (const end of ends) {
    const width = Math.min(heart.size, end.size) * 0.08
    for (let index = 0; index < share; index += 1) {
      const t = random() ** 0.8
      put(
        heart.x + (end.x - heart.x) * t + gaussian(random) * width,
        heart.y + (end.y - heart.y) * t + gaussian(random) * width * 0.4,
        heart.z + (end.z - heart.z) * t + gaussian(random) * width,
        mix(glow, body, t),
        1.2 + (1 - t) * 1.6,
        light * (1 - t * 0.65)
      )
    }
  }
}

function crown(context: Context, budget: number) {
  const { random, put, members, body, glow } = context
  const heart = heartOf(members)
  if (!heart) return groupCloud(context, budget)
  hotCore(
    context,
    Math.round(budget * 0.2),
    context.frame.major * 0.1,
    0.5,
    heart
  )
  const jewels = members.filter((row) => row !== heart)
  const radius =
    jewels.reduce((sum, row) => sum + distanceOf(row, heart), 0) /
    Math.max(jewels.length, 1)
  const angles = jewels.map((row) =>
    Math.atan2(row.z - heart.z, row.x - heart.x)
  )
  const low = Math.min(...angles, 0) - 0.15
  const high = Math.max(...angles, 0) + 0.15
  const arc = Math.round(budget * 0.25)
  for (let index = 0; index < arc; index += 1) {
    const angle = low + (high - low) * random()
    const reach = radius + gaussian(random) * radius * 0.03
    put(
      heart.x + Math.cos(angle) * reach,
      heart.y + gaussian(random) * radius * 0.02,
      heart.z + Math.sin(angle) * reach,
      mix(body, glow, random() * 0.4),
      1.4 + random() * 1.6,
      0.34
    )
  }
  spokes(context, heart, jewels, Math.round(budget * 0.2), 0.3)
  halos(context, Math.round(budget * 0.25))
  envelope(context, Math.round(budget * 0.1), 0.6, 0.04, 0.1)
}

function drowned(context: Context, budget: number) {
  const { random, put, local, frame, members, size, body, edge } = context
  const haze = Math.round(budget * 0.45)
  for (let index = 0; index < haze; index += 1) {
    const u = gaussian(random) * frame.major * 0.75
    const v = gaussian(random) * (frame.minor * 0.75 + size * 0.06)
    const depth = Math.abs(gaussian(random))
    const reach = Math.hypot(
      u / Math.max(frame.major, 1),
      v / Math.max(frame.minor, 1)
    )
    put(
      ...local(u, v, -depth * frame.major * 0.2 - size * 0.02),
      mix(body, edge, depth * 0.5 + reach * 0.3),
      2 + random() * 2.4,
      0.18 * Math.max(1 - reach * 0.5, 0.05) * (1 - Math.min(depth, 1) * 0.4)
    )
  }
  const surface = frame.major * 0.28
  const rippleShare = Math.round((budget * 0.12) / RIPPLES)
  for (let ripple = 1; ripple <= RIPPLES; ripple += 1) {
    const a = frame.major * 0.28 * ripple
    const b = frame.minor * 0.28 * ripple + size * 0.02
    for (let index = 0; index < rippleShare; index += 1) {
      const angle = random() * Math.PI * 2
      put(
        ...local(
          Math.cos(angle) * a,
          Math.sin(angle) * b,
          surface + gaussian(random) * size * 0.004
        ),
        mix(body, edge, ripple / RIPPLES),
        1.2 + random(),
        0.3 - ripple * 0.05
      )
    }
  }
  const tendrils = Math.round((budget * 0.13) / Math.max(members.length, 1))
  for (const member of members) {
    for (let index = 0; index < tendrils; index += 1) {
      const t = random()
      put(
        member.x + gaussian(random) * member.size * 0.1,
        member.y + t * surface,
        member.z + gaussian(random) * member.size * 0.1,
        mix(body, edge, t),
        1.2 + random() * 1.2,
        0.22 * (1 - t)
      )
    }
  }
  halos(context, Math.round(budget * 0.3))
}

function forge(context: Context, budget: number) {
  const { random, put, members, body, edge } = context
  const heart = heartOf(members)
  if (!heart) return groupCloud(context, budget)
  hotCore(
    context,
    Math.round(budget * 0.3),
    context.frame.major * 0.12,
    0.45,
    heart
  )
  const anvils = members.filter((row) => row !== heart)
  spokes(context, heart, anvils, Math.round(budget * 0.25), 0.42)
  const sparks = Math.round(budget * 0.15)
  for (let index = 0; index < sparks; index += 1) {
    const angle = random() * Math.PI * 2
    const reach = context.frame.major * (0.2 + random() * 0.9)
    const rise = gaussian(random) * 0.12
    put(
      heart.x + Math.cos(angle) * reach,
      heart.y + rise * reach,
      heart.z + Math.sin(angle) * reach,
      mix(body, edge, reach / context.frame.major),
      1 + random() * 1.2,
      0.24 * (1 - reach / (context.frame.major * 1.2))
    )
  }
  halos(context, Math.round(budget * 0.22))
  envelope(context, Math.round(budget * 0.08), 0.6, 0.05, 0.1)
}

function dream(context: Context, budget: number) {
  const { random, put, members, frame, body, glow } = context
  const [cx, cy, cz] = frame.centre
  const heart = heartOf(members)
  const origin: ClusterMember = heart ?? { x: cx, y: cy, z: cz, size: 1 }
  const path = [...members].sort(
    (a, b) => distanceOf(a, origin) - distanceOf(b, origin)
  )
  if (path.length >= 2) {
    const strandBudget = Math.round(budget * 0.5)
    for (let index = 0; index < strandBudget; index += 1) {
      const t = random() * (path.length - 1)
      const piece = Math.min(Math.floor(t), path.length - 2)
      const phase = t - piece
      const a = at(path, Math.max(piece - 1, 0), origin)
      const b = at(path, piece, origin)
      const c = at(path, piece + 1, origin)
      const d = at(path, Math.min(piece + 2, path.length - 1), c)
      const curve = (p0: number, p1: number, p2: number, p3: number) =>
        0.5 *
        (2 * p1 +
          (-p0 + p2) * phase +
          (2 * p0 - 5 * p1 + 4 * p2 - p3) * phase ** 2 +
          (-p0 + 3 * p1 - 3 * p2 + p3) * phase ** 3)
      const share = t / Math.max(path.length - 1, 1)
      const width = frame.major * 0.035 * (0.5 + share)
      put(
        curve(a.x, b.x, c.x, d.x) + gaussian(random) * width,
        curve(a.y, b.y, c.y, d.y) + gaussian(random) * width * 0.35,
        curve(a.z, b.z, c.z, d.z) + gaussian(random) * width,
        mix(glow, body, 0.3 + share * 0.7),
        1.4 + random() * 2,
        0.36 * (1 - share * 0.5)
      )
    }
  }
  halos(context, Math.round(budget * 0.3))
  envelope(context, Math.round(budget * 0.2), 0.7, 0.05, 0.12)
}

function mirrorCluster(context: Context, budget: number) {
  const { random, put, frame, size, glow } = context
  const [cx, cy, cz] = frame.centre
  const half = Math.round(budget * 0.45)
  const mirrored: Context = {
    ...context,
    members: context.members.filter((row) => row.x <= cx),
    put: (x, y, z, color, point, light) => {
      put(x, y, z, color, point, light)
      put(2 * cx - x, y, z, color, point, light)
    },
  }
  halos(mirrored, Math.round(half * 0.45))
  envelope(mirrored, Math.round(half * 0.35), 0.5)
  nearestStrands(mirrored, Math.round(half * 0.2))
  const seam = Math.round(budget * 0.1)
  const reach = Math.max(frame.major, frame.minor) * 1.05
  for (let index = 0; index < seam; index += 1) {
    const w = (random() * 2 - 1) * reach
    put(
      cx + gaussian(random) * size * 0.004,
      cy + gaussian(random) * size * 0.008,
      cz + w,
      glow,
      1.2 + random(),
      0.4 * (1 - Math.abs(w) / (reach * 1.05))
    )
  }
}

const GENERATORS: Record<ClusterKind, Generator> = {
  galaxy_group: groupCloud,
  local_group: localGroup,
  poor_cluster: groupCloud,
  rich_cluster: richCluster,
  supercluster,
  filament,
  wall,
  void: voidShell,
  crown_cluster: crown,
  drowned_cluster: drowned,
  forge_cluster: forge,
  dream_cluster: dream,
  mirror_cluster: mirrorCluster,
}

export function clusterCloud(
  kind: ClusterKind,
  members: readonly ClusterMember[],
  size: number,
  seed: number,
  palette: Palette,
  count: number
): ClusterCloud {
  const look = CLUSTER_LOOK[kind]
  const frame = clusterFrame(members, size)
  const random = seededRandom(seed * 104729 + 7)
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const seeds = new Float32Array(count)
  const ux = Math.cos(frame.angle)
  const uz = Math.sin(frame.angle)
  let written = 0
  const accents = look.accents.map(palette)
  const put: Context['put'] = (x, y, z, base, point, light) => {
    if (written >= count) return
    const accent = accents[Math.floor(random() * accents.length)]
    const color =
      accent && random() < ACCENT_SHARE
        ? mix(base, accent, random() * ACCENT_MIX)
        : base
    const glow = Math.max(light, 0) * look.light * CLOUD_LIGHT
    positions.set([x, y, z], written * 3)
    colors.set([color[0] * glow, color[1] * glow, color[2] * glow], written * 3)
    sizes[written] = point
    seeds[written] = random()
    written += 1
  }
  const local: Context['local'] = (u, v, h) => [
    frame.centre[0] + u * ux - v * uz,
    frame.centre[1] + h,
    frame.centre[2] + u * uz + v * ux,
  ]
  const context: Context = {
    random,
    put,
    local,
    members,
    frame,
    size,
    body: palette(look.body),
    glow: palette(look.glow),
    edge: palette(look.edge),
  }
  const links = SKELETONS[kind](members, frame)
  const ribbon = links.length > 0 ? Math.round(count * RIBBON_SHARE) : 0
  ribbons(context, links, ribbon)
  GENERATORS[kind](context, count - ribbon)
  return {
    ...frame,
    count: written,
    positions,
    colors,
    sizes,
    seeds,
    veil: kind === 'void' ? 'shell' : 'cloud',
  }
}

export function veilSpan(
  frame: ClusterFrame,
  veil: ClusterVeil
): [number, number] {
  if (veil === 'shell') return [frame.ring * 2.8, frame.ring * 2.8]
  return [
    frame.major * 2.6,
    Math.max(frame.minor, frame.major * VEIL_SPAN) * 2.6,
  ]
}

export function clusterOutline(
  frame: ClusterFrame,
  kind: ClusterKind
): [number, number, number][] {
  const ux = Math.cos(frame.angle)
  const uz = Math.sin(frame.angle)
  const [cx, cy, cz] = frame.centre
  const place = (u: number, v: number): [number, number, number] => [
    cx + u * ux - v * uz,
    cy,
    cz + u * uz + v * ux,
  ]
  if (kind === 'filament')
    return [place(-frame.major * 1.1, 0), place(frame.major * 1.1, 0)]
  const [a, b] =
    kind === 'void'
      ? [frame.ring * 1.12, frame.ring * 1.12]
      : kind === 'wall'
        ? [frame.major * 1.15, Math.max(frame.minor * 1.4, frame.major * 0.35)]
        : [frame.major * 1.1, Math.max(frame.minor, frame.major * 0.6) * 1.1]
  return Array.from({ length: OUTLINE_SEGMENTS + 1 }, (_, index) => {
    const angle = (index / OUTLINE_SEGMENTS) * Math.PI * 2
    return place(Math.cos(angle) * a, Math.sin(angle) * b)
  })
}

type Skeleton = (
  members: readonly ClusterMember[],
  frame: ClusterFrame
) => Link[]

function chained(members: readonly ClusterMember[], closed: boolean): Link[] {
  const links: Link[] = members
    .slice(1)
    .map((member, index) => [at(members, index, member), member])
  const first = members[0]
  const last = members[members.length - 1]
  if (closed && first && last && members.length > 2) links.push([last, first])
  return links
}

function byAngle(
  members: readonly ClusterMember[],
  centre: ClusterMember
): ClusterMember[] {
  return [...members].sort(
    (a, b) =>
      Math.atan2(a.z - centre.z, a.x - centre.x) -
      Math.atan2(b.z - centre.z, b.x - centre.x)
  )
}

function spokesOf(
  heart: ClusterMember,
  ends: readonly ClusterMember[]
): Link[] {
  return ends.map((end) => [heart, end])
}

function originOf(frame: ClusterFrame): ClusterMember {
  return {
    x: frame.centre[0],
    y: frame.centre[1],
    z: frame.centre[2],
    size: 0,
  }
}

const hearted =
  (ring: boolean): Skeleton =>
  (members) => {
    const heart = heartOf(members)
    if (!heart) return []
    const rest = members.filter((row) => row !== heart)
    const links = spokesOf(heart, rest)
    return ring ? [...links, ...chained(byAngle(rest, heart), true)] : links
  }

const SKELETONS: Record<ClusterKind, Skeleton> = {
  galaxy_group: (members) => nearestPairs(members),
  local_group: (members) => {
    const hosts = [...members].sort((a, b) => b.size - a.size)
    const first = hosts[0]
    const second = hosts[1]
    return [
      ...(first && second ? [[first, second] as Link] : []),
      ...nearestPairs(members),
    ]
  },
  poor_cluster: (members) => nearestPairs(members),
  rich_cluster: hearted(false),
  supercluster: (members, frame) => {
    const groups = clumpsOf(members, frame)
    const centres = groups.map(centreOf)
    return [
      ...chained(centres, true),
      ...groups.flatMap((group, index) =>
        spokesOf(at(centres, index, centreOf(group)), group)
      ),
    ]
  },
  filament: (members, frame) => {
    const ux = Math.cos(frame.angle)
    const uz = Math.sin(frame.angle)
    return chained(
      [...members].sort((a, b) => a.x * ux + a.z * uz - (b.x * ux + b.z * uz)),
      false
    )
  },
  wall: (members) => nearestPairs(members),
  void: (members, frame) => chained(byAngle(members, originOf(frame)), true),
  crown_cluster: (members) => {
    const heart = heartOf(members)
    if (!heart) return []
    const jewels = members.filter((row) => row !== heart)
    return [
      ...spokesOf(heart, jewels),
      ...chained(byAngle(jewels, heart), false),
    ]
  },
  drowned_cluster: (members) => nearestPairs(members),
  forge_cluster: hearted(true),
  dream_cluster: (members) => {
    const heart = heartOf(members)
    if (!heart) return []
    return chained(
      [...members].sort((a, b) => distanceOf(a, heart) - distanceOf(b, heart)),
      false
    )
  },
  mirror_cluster: (members, frame) => {
    const reach = Math.max(frame.major, frame.minor)
    const [cx, cy, cz] = frame.centre
    return [
      ...nearestPairs(members),
      [
        { x: cx, y: cy, z: cz - reach, size: 0 },
        { x: cx, y: cy, z: cz + reach, size: 0 },
      ],
    ]
  },
}

export function clusterSkeleton(
  kind: ClusterKind,
  members: readonly ClusterMember[],
  frame: ClusterFrame
): [number, number, number][] {
  return SKELETONS[kind](members, frame).flatMap(([from, to]) => [
    [from.x, from.y, from.z] as [number, number, number],
    [to.x, to.y, to.z] as [number, number, number],
  ])
}
