import type { components } from '@/api/generated/schema'
import { seededRandom } from '@/lib/hash'

type Schema = components['schemas']
export type GalaxyType = Schema['GalaxyType']
export type GalaxyShape = Schema['GalaxyShapeRecord']
export type StructureKind = Schema['GalacticStructureKind']
export type DimensionKind = Schema['DimensionKind']

export type GalaxyFamily =
  | 'spiral'
  | 'barred'
  | 'grand'
  | 'flocculent'
  | 'lenticular'
  | 'elliptical'
  | 'spheroidal'
  | 'irregular'
  | 'ring'
  | 'hollow'
  | 'mirror'
  | 'shattered'

export type GalaxyLook = {
  family: GalaxyFamily
  inner: string
  outer: string
  arms: string
  brightness: number
  flatten: number
  clumps: number
  nurseries: number
  jets: boolean
  crown: boolean
  dust: number
  wind: number
  span: number
  bulge: number
  bar: number
  extent: number
  axis: number
  globulars: number
  view: number | null
}

const look = (
  family: GalaxyFamily,
  inner: string,
  outer: string,
  arms: string,
  extra: Partial<Omit<GalaxyLook, 'family' | 'inner' | 'outer' | 'arms'>> = {}
): GalaxyLook => ({
  family,
  inner,
  outer,
  arms,
  brightness: extra.brightness ?? 1,
  flatten: extra.flatten ?? 0.08,
  clumps: extra.clumps ?? 0,
  nurseries: extra.nurseries ?? 0.06,
  jets: extra.jets ?? false,
  crown: extra.crown ?? false,
  dust: extra.dust ?? 0.25,
  wind: extra.wind ?? 1,
  span: extra.span ?? 1,
  bulge: extra.bulge ?? 1,
  bar: extra.bar ?? 1,
  extent: extra.extent ?? 1,
  axis: extra.axis ?? 1,
  globulars: extra.globulars ?? 0,
  view: extra.view ?? null,
})

const BULGE = '--galaxy-bulge'
const YOUNG = '--galaxy-young'
const OLD = '--galaxy-old'
const DISC = '--galaxy-disc'

export const GALAXY_LOOK: Record<GalaxyType, GalaxyLook> = {
  spiral: look('spiral', BULGE, DISC, YOUNG),
  barred_spiral: look('barred', BULGE, DISC, YOUNG, {
    bar: 1.6,
    wind: 0.7,
    bulge: 0.7,
    view: 0.25,
  }),
  grand_design_spiral: look('grand', BULGE, DISC, YOUNG, {
    brightness: 1.15,
    nurseries: 0.12,
    wind: 1.8,
    span: 0.45,
    view: 0.2,
  }),
  flocculent_spiral: look('flocculent', BULGE, DISC, YOUNG, {
    dust: 0.35,
    wind: 1.3,
    span: 1.6,
    nurseries: 0.12,
    bulge: 0.6,
    view: 0.3,
  }),
  lenticular: look('lenticular', BULGE, OLD, DISC, {
    nurseries: 0.01,
    dust: 0.4,
    bulge: 2.4,
    flatten: 0.05,
    view: 1.3,
  }),
  elliptical: look('elliptical', BULGE, OLD, OLD, {
    flatten: 0.62,
    nurseries: 0,
    dust: 0,
    axis: 0.55,
    globulars: 5,
  }),
  giant_elliptical: look('elliptical', '--galaxy-core', OLD, OLD, {
    flatten: 0.78,
    brightness: 1.3,
    nurseries: 0,
    dust: 0,
    axis: 0.92,
    extent: 1.15,
    bulge: 1.6,
    globulars: 22,
  }),
  dwarf_elliptical: look('elliptical', BULGE, OLD, OLD, {
    flatten: 0.55,
    brightness: 0.6,
    nurseries: 0,
    dust: 0,
    axis: 0.72,
    extent: 0.45,
  }),
  dwarf_spheroidal: look('spheroidal', OLD, '--galaxy-halo', OLD, {
    flatten: 0.8,
    brightness: 0.45,
    nurseries: 0,
    dust: 0,
    extent: 0.6,
    bulge: 0.2,
  }),
  irregular: look('irregular', YOUNG, DISC, YOUNG, {
    clumps: 6,
    nurseries: 0.14,
    flatten: 0.2,
  }),
  dwarf_irregular: look('irregular', YOUNG, DISC, YOUNG, {
    clumps: 3,
    brightness: 0.6,
    nurseries: 0.12,
    flatten: 0.2,
    extent: 0.5,
  }),
  ring: look('ring', BULGE, YOUNG, YOUNG, { nurseries: 0.16, view: 0.3 }),
  peculiar: look('shattered', BULGE, DISC, YOUNG, {
    clumps: 4,
    nurseries: 0.12,
    flatten: 0.18,
  }),
  starburst: look('irregular', '--galaxy-nursery', YOUNG, '--galaxy-nursery', {
    clumps: 7,
    brightness: 1.25,
    nurseries: 0.34,
    flatten: 0.22,
    bulge: 1.4,
  }),
  active: look('spiral', '--galaxy-quasar', DISC, YOUNG, {
    jets: true,
    brightness: 1.1,
    bulge: 1.3,
    view: 1.05,
  }),
  quasar_host: look('elliptical', '--galaxy-quasar', OLD, OLD, {
    jets: true,
    flatten: 0.68,
    brightness: 1.35,
    nurseries: 0,
    dust: 0,
    axis: 0.8,
    view: 1.1,
  }),
  low_surface_brightness: look('spiral', DISC, '--galaxy-halo', YOUNG, {
    brightness: 0.45,
    nurseries: 0.03,
    wind: 0.55,
    span: 1.7,
    bulge: 0.25,
    extent: 1.15,
  }),
  ultra_diffuse: look('spheroidal', '--galaxy-halo', '--galaxy-halo', DISC, {
    brightness: 0.32,
    flatten: 0.7,
    nurseries: 0,
    dust: 0,
    extent: 1.2,
    bulge: 0,
  }),
  living: look('spiral', '--galaxy-living', DISC, '--galaxy-living', {
    nurseries: 0.24,
    wind: 1.35,
    span: 0.8,
  }),
  dead: look('elliptical', '--galaxy-dead', '--galaxy-dead', '--galaxy-dead', {
    flatten: 0.5,
    brightness: 0.5,
    nurseries: 0,
    dust: 0,
    axis: 0.45,
    bulge: 0.5,
  }),
  shattered: look(
    'shattered',
    '--galaxy-shattered',
    DISC,
    '--galaxy-shattered',
    {
      clumps: 5,
      flatten: 0.14,
    }
  ),
  forged: look('barred', '--galaxy-forged', '--galaxy-forged', BULGE, {
    brightness: 1.15,
    nurseries: 0.04,
    bar: 2.1,
    wind: 0.35,
    span: 0.5,
  }),
  dreaming: look('flocculent', '--galaxy-dreaming', DISC, '--galaxy-dreaming', {
    nurseries: 0.08,
    dust: 0.1,
    wind: 2.2,
    span: 1.2,
  }),
  mirror: look('mirror', '--galaxy-mirror', DISC, '--galaxy-mirror'),
  crowned: look('grand', '--galaxy-crowned', DISC, YOUNG, {
    crown: true,
    brightness: 1.15,
    wind: 1.4,
    span: 0.6,
  }),
  hollow: look('hollow', '--galaxy-hollow', YOUNG, '--galaxy-hollow', {
    nurseries: 0.1,
  }),
  ember: look('spiral', '--galaxy-ember', OLD, '--galaxy-ember', {
    brightness: 0.8,
    nurseries: 0.03,
    wind: 1.1,
    bulge: 1.5,
  }),
  veiled: look('spiral', '--galaxy-veiled', DISC, '--galaxy-veiled', {
    dust: 0.95,
    brightness: 0.75,
    view: 1.15,
  }),
}

export type StructureLook = {
  token: string
  form: 'cloud' | 'cluster' | 'dark' | 'stream' | 'shell' | 'mark'
  scale: number
}

const structure = (
  token: string,
  form: StructureLook['form'],
  scale = 1
): StructureLook => ({ token, form, scale })

export const STRUCTURE_LOOK: Record<StructureKind, StructureLook> = {
  spiral_arm: structure(YOUNG, 'mark'),
  bar: structure(BULGE, 'mark'),
  bulge: structure(BULGE, 'mark'),
  core: structure('--galaxy-core', 'mark'),
  halo: structure('--galaxy-halo', 'mark'),
  emission_nebula: structure('--structure-emission', 'cloud'),
  reflection_nebula: structure('--structure-reflection', 'cloud'),
  dark_nebula: structure('--structure-dark', 'dark'),
  planetary_nebula: structure('--structure-planetary', 'shell', 0.7),
  supernova_remnant: structure('--structure-remnant', 'shell'),
  stellar_nursery: structure('--structure-nursery', 'cloud', 1.1),
  open_cluster: structure('--structure-open-cluster', 'cluster', 0.8),
  globular_cluster: structure('--structure-globular', 'cluster', 0.7),
  stellar_stream: structure('--structure-stream', 'stream'),
  dust_lane: structure('--structure-dark', 'dark', 1.2),
  superbubble: structure('--structure-bubble', 'shell', 1.2),
  star_graveyard: structure('--structure-graveyard', 'cluster'),
  ley_spiral: structure('--structure-ley', 'stream'),
  sealed_vault: structure('--structure-vault', 'shell', 0.6),
  gods_forge: structure('--structure-forge', 'cloud', 0.9),
  dead_light_drift: structure('--structure-dead-light', 'cloud', 1.1),
  singing_nebula: structure('--structure-singing', 'cloud'),
  rift_scar: structure('--structure-rift', 'stream', 0.8),
}

export const LAYOUT_STRUCTURES: ReadonlySet<StructureKind> = new Set([
  'spiral_arm',
  'bar',
  'bulge',
  'core',
  'halo',
])

export const DIMENSION_TOKEN: Record<DimensionKind, string> = {
  prime: '--dimension-prime',
  parallel: '--dimension-material',
  mirror: '--dimension-mirror',
  pocket: '--dimension-material',
  made: '--dimension-material',
  bubble_universe: '--dimension-material',
  brane: '--dimension-material',
  higher_dimensional: '--dimension-astral',
  antimatter: '--dimension-chaos',
  quantum_branch: '--dimension-material',
  time_reversed: '--dimension-mirror',
  compactified: '--dimension-limbo',
  astral: '--dimension-astral',
  ethereal: '--dimension-spirit',
  dream: '--dimension-dream',
  shadow: '--dimension-shadow',
  spirit: '--dimension-spirit',
  fey: '--dimension-fey',
  elemental: '--dimension-elemental',
  celestial: '--dimension-celestial',
  infernal: '--dimension-infernal',
  abyssal: '--dimension-abyssal',
  limbo: '--dimension-limbo',
  far_realm: '--dimension-far',
  clockwork: '--dimension-clockwork',
  chaos: '--dimension-chaos',
  underworld: '--dimension-underworld',
  divine_domain: '--dimension-divine',
  void_between: '--dimension-void',
}

export type FormInput = {
  id: number
  galaxy_type: GalaxyType
  radius: number
  arm_count: number
  nucleus: Schema['GalacticNucleus']
  star_formation: number
  metallicity: number
  age_stage: Schema['GalaxyAge']
  leak: number
  merge_progress: number
}

export type Rgb = [number, number, number]
export type Palette = (token: string) => Rgb

export type GalaxyPoints = {
  count: number
  positions: Float32Array
  colors: Float32Array
  sizes: Float32Array
  seeds: Float32Array
  dark: { positions: Float32Array; sizes: Float32Array; count: number }
}

const AGE_WARMTH: Record<Schema['GalaxyAge'], number> = {
  forming: -0.25,
  young: -0.12,
  mature: 0,
  old: 0.25,
  dying: 0.45,
  dead: 0.7,
}

const AGE_LIGHT: Record<Schema['GalaxyAge'], number> = {
  forming: 0.95,
  young: 1.05,
  mature: 1,
  old: 0.85,
  dying: 0.65,
  dead: 0.4,
}

const CORE_LIGHT: Record<Schema['GalacticNucleus'], number> = {
  none: 0.5,
  dormant: 1,
  active: 1.5,
  quasar: 2.2,
  devoured: 0.15,
}

const PERCENT = 100
const DEGREE = Math.PI / 180

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

export function familyOf(type: GalaxyType): GalaxyFamily {
  return GALAXY_LOOK[type].family
}

export function armsOf(galaxy: FormInput): number {
  const family = familyOf(galaxy.galaxy_type)
  if (family === 'grand' || family === 'mirror')
    return Math.max(2, galaxy.arm_count)
  if (family === 'flocculent') return Math.max(5, galaxy.arm_count * 3)
  return Math.max(galaxy.arm_count, 0)
}

export function galaxyPoints(
  galaxy: FormInput,
  shape: GalaxyShape,
  count: number,
  palette: Palette
): GalaxyPoints {
  const random = seededRandom(galaxy.id * 7919 + 17)
  const style = GALAXY_LOOK[galaxy.galaxy_type]
  const radius = Math.max(galaxy.radius, 1) * style.extent
  const reach = (pct: number) => (pct / PERCENT) * radius
  const core = palette('--galaxy-core')
  const inner = palette(style.inner)
  const outer = palette(style.outer)
  const arms = palette(style.arms)
  const young = palette(YOUNG)
  const old = palette(OLD)
  const nursery = palette('--galaxy-nursery')
  const leak = palette('--galaxy-leak')
  const jet = palette('--galaxy-jet')
  const crownColor = palette('--galaxy-crowned')
  const warmth = AGE_WARMTH[galaxy.age_stage]
  const light = AGE_LIGHT[galaxy.age_stage] * style.brightness
  const coreLight = CORE_LIGHT[galaxy.nucleus]
  const nurseryShare =
    style.nurseries * (0.4 + (galaxy.star_formation / PERCENT) * 1.6)
  const leakShare = (galaxy.leak / PERCENT) * 0.25
  const spiral = shape.spiral_types.includes(galaxy.galaxy_type)
  const barred = shape.barred_types.includes(galaxy.galaxy_type)
  const armCount = spiral ? armsOf(galaxy) : 0
  const wind = shape.arm_wind_deg * DEGREE * style.wind
  const armWidth = shape.arm_width_deg * DEGREE
  const family = style.family
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const seeds = new Float32Array(count)
  const clumpCentres = Array.from({ length: Math.max(style.clumps, 1) }, () => {
    const angle = random() * Math.PI * 2
    const distance = (0.15 + random() * 0.7) * radius
    return [
      Math.cos(angle) * distance,
      Math.sin(angle) * distance,
      0.12 + random() * 0.22,
    ] as const
  })
  const fragments = Array.from(
    { length: Math.max(armCount, 1) },
    () => (random() - 0.5) * 1.4
  )
  const tidal = galaxy.merge_progress / PERCENT
  const bulgeReach = reach(shape.bulge_reach_pct)
  const discReach = reach(shape.disc_reach_pct)
  const haloReach = reach(shape.halo_reach_pct)
  const barReach = reach(shape.bar_reach_pct) * style.bar
  const thickness = radius * style.flatten
  let written = 0
  const put = (
    x: number,
    y: number,
    z: number,
    color: Rgb,
    size: number,
    brightness: number
  ) => {
    if (written >= count) return
    const tinted = random() < leakShare ? mix(color, leak, 0.7) : color
    const warmed =
      warmth > 0 ? mix(tinted, old, warmth) : mix(tinted, young, -warmth)
    const glow = brightness * light
    positions.set([x, y, z], written * 3)
    colors.set(
      [warmed[0] * glow, warmed[1] * glow, warmed[2] * glow],
      written * 3
    )
    sizes[written] = size
    seeds[written] = random()
    written += 1
  }
  const radial = (distance: number) => mix(inner, outer, distance / discReach)
  const bulgeCount = Math.round(
    count *
      Math.min(
        (family === 'elliptical' || family === 'spheroidal'
          ? 0.55
          : family === 'hollow'
            ? 0
            : 0.16) * style.bulge,
        0.7
      )
  )
  for (let index = 0; index < bulgeCount; index += 1) {
    const spread =
      family === 'elliptical' || family === 'spheroidal'
        ? radius * 0.42
        : bulgeReach * 0.55 * Math.sqrt(Math.max(style.bulge, 0.2))
    const x = gaussian(random) * spread
    const z =
      gaussian(random) *
      spread *
      (family === 'elliptical' || family === 'spheroidal' ? style.axis : 1)
    const y =
      gaussian(random) *
      spread *
      (family === 'elliptical' || family === 'spheroidal'
        ? style.flatten
        : 0.45)
    const distance = Math.hypot(x, z) / Math.max(spread * 2.5, 1)
    put(
      x,
      y,
      z,
      mix(core, inner, distance),
      1 + random() * 1.4,
      (1.25 - distance) * coreLight * 0.9
    )
  }
  if (barred) {
    const barCount = Math.round(count * 0.1)
    for (let index = 0; index < barCount; index += 1) {
      const along = (random() * 2 - 1) * barReach
      put(
        along,
        gaussian(random) * thickness * 0.4,
        gaussian(random) * barReach * 0.12,
        mix(core, inner, Math.abs(along) / barReach),
        1.2,
        1.1
      )
    }
  }
  const armRoot = barred ? barReach : bulgeReach * 0.6
  while (written < count * 0.9) {
    if (family === 'elliptical' || family === 'spheroidal') {
      const spread =
        radius *
          (family === 'spheroidal' ? 0.5 : 0.36) *
          Math.pow(random(), family === 'spheroidal' ? 0.6 : 1.1) +
        radius * 0.04
      const theta = random() * Math.PI * 2
      const cosPhi = random() * 2 - 1
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi)
      const x = Math.cos(theta) * sinPhi * spread * 1.6
      const z = Math.sin(theta) * sinPhi * spread * 1.6 * style.axis
      const y = cosPhi * spread * 1.6 * style.flatten
      const distance = Math.min(Math.hypot(x, z) / radius, 1)
      put(
        x,
        y,
        z,
        radial(distance * discReach),
        0.7 + random() * 0.6,
        0.75 - distance * 0.55
      )
      continue
    }
    if (family === 'irregular' || family === 'shattered') {
      const centre = clumpCentres[Math.floor(random() * clumpCentres.length)]
      const spread = radius * centre[2] * (family === 'shattered' ? 0.45 : 0.55)
      const x = centre[0] + gaussian(random) * spread
      const z = centre[1] + gaussian(random) * spread
      const knot = random() < nurseryShare
      put(
        x,
        gaussian(random) * thickness,
        z,
        knot ? nursery : radial(Math.hypot(x, z)),
        knot ? 2.2 : 1 + random(),
        knot ? 1.3 : 0.75
      )
      continue
    }
    if (family === 'ring' || family === 'hollow') {
      const ringRadius = radius * (family === 'hollow' ? 0.82 : 0.68)
      const angle = random() * Math.PI * 2
      const distance = ringRadius + gaussian(random) * radius * 0.07
      const knot = random() < nurseryShare
      put(
        Math.cos(angle) * distance,
        gaussian(random) * thickness * 0.5,
        Math.sin(angle) * distance,
        knot ? nursery : arms,
        knot ? 2.2 : 1.1 + random(),
        knot ? 1.3 : 0.9
      )
      continue
    }
    let distance = armRoot + Math.pow(random(), 1.25) * (discReach - armRoot)
    let angle = random() * Math.PI * 2
    const onArm =
      family !== 'lenticular' &&
      armCount > 0 &&
      random() < (family === 'flocculent' ? 0.8 : 0.72)
    if (onArm) {
      const arm = Math.floor(random() * armCount)
      const spacing = (Math.PI * 2) / armCount
      const jitter = family === 'flocculent' ? fragments[arm] : 0
      const span =
        (family === 'flocculent' ? 0.18 : family === 'grand' ? 0.22 : 0.32) *
        style.span
      if (family === 'flocculent')
        distance = Math.min(
          Math.max(
            armRoot +
              (0.5 + fragments[arm] * 0.6) * (discReach - armRoot) +
              gaussian(random) * radius * 0.1,
            armRoot
          ),
          discReach
        )
      angle =
        arm * spacing +
        jitter +
        (distance / radius) * wind +
        gaussian(random) * armWidth * span
      if (family === 'mirror' && arm % 2 === 1) angle = -(angle - Math.PI)
    }
    const knot = onArm && random() < nurseryShare
    const x = Math.cos(angle) * distance
    const z = Math.sin(angle) * distance
    const tail = tidal > 0 && random() < tidal * 0.25 ? 1 + random() * tidal : 1
    const color = knot
      ? nursery
      : onArm
        ? mix(arms, radial(distance), 0.35)
        : radial(distance)
    put(
      x * tail,
      gaussian(random) *
        thickness *
        (1 - ((distance - armRoot) / Math.max(discReach - armRoot, 1)) * 0.5),
      z * tail,
      color,
      knot ? 2.4 : onArm ? 1.2 + random() : 0.9 + random() * 0.6,
      knot ? 1.35 : onArm ? 0.95 : 0.45
    )
  }
  if (style.jets) {
    const jetCount = Math.round(count * 0.03)
    for (let index = 0; index < jetCount; index += 1) {
      const height =
        Math.pow(random(), 0.7) * radius * 0.9 * (random() < 0.5 ? -1 : 1)
      const spread = Math.abs(height) * 0.05
      put(
        gaussian(random) * spread,
        height,
        gaussian(random) * spread,
        jet,
        1.6,
        1.3 * coreLight * (1 - Math.abs(height) / radius)
      )
    }
  }
  if (style.crown) {
    const crownCount = Math.round(count * 0.03)
    for (let index = 0; index < crownCount; index += 1) {
      const angle = (index / crownCount) * Math.PI * 2
      const distance = radius * 1.04 + gaussian(random) * radius * 0.01
      put(
        Math.cos(angle) * distance,
        gaussian(random) * thickness * 0.2,
        Math.sin(angle) * distance,
        crownColor,
        1.8,
        1.2
      )
    }
  }
  for (let globular = 0; globular < style.globulars; globular += 1) {
    const angle = random() * Math.PI * 2
    const distance = radius * (0.45 + random() * 0.75)
    const centre = [
      Math.cos(angle) * distance,
      gaussian(random) * radius * 0.25,
      Math.sin(angle) * distance,
    ] as const
    for (let dot = 0; dot < 10; dot += 1)
      put(
        centre[0] + gaussian(random) * radius * 0.012,
        centre[1] + gaussian(random) * radius * 0.012,
        centre[2] + gaussian(random) * radius * 0.012,
        old,
        1.4,
        1.1
      )
  }
  while (written < count) {
    const angle = random() * Math.PI * 2
    const cos = random() * 2 - 1
    const sin = Math.sqrt(1 - cos * cos)
    const distance = Math.pow(random(), 0.6) * haloReach
    put(
      Math.cos(angle) * sin * distance,
      cos * distance * 0.6,
      Math.sin(angle) * sin * distance,
      palette('--galaxy-halo'),
      0.8 + random() * 0.5,
      0.25
    )
  }
  const darkCount =
    family === 'elliptical' || family === 'spheroidal'
      ? 0
      : Math.round(
          count * 0.12 * (style.dust + galaxy.metallicity / PERCENT / 2)
        )
  const darkPositions = new Float32Array(darkCount * 3)
  const darkSizes = new Float32Array(darkCount)
  for (let index = 0; index < darkCount; index += 1) {
    const distance = armRoot + random() * (discReach * 0.85 - armRoot)
    const arm = armCount > 0 ? Math.floor(random() * armCount) : 0
    const spacing = armCount > 0 ? (Math.PI * 2) / armCount : Math.PI * 2
    const angle =
      armCount > 0
        ? arm * spacing +
          (distance / radius) * wind -
          armWidth * 0.28 +
          gaussian(random) * armWidth * 0.12
        : random() * Math.PI * 2
    darkPositions.set(
      [
        Math.cos(angle) * distance,
        gaussian(random) * thickness * 0.2,
        Math.sin(angle) * distance,
      ],
      index * 3
    )
    darkSizes[index] = 3 + random() * 4
  }
  return {
    count: written,
    positions,
    colors,
    sizes,
    seeds,
    dark: { positions: darkPositions, sizes: darkSizes, count: darkCount },
  }
}

export function coreGlow(galaxy: FormInput): number {
  return (
    CORE_LIGHT[galaxy.nucleus] *
    AGE_LIGHT[galaxy.age_stage] *
    GALAXY_LOOK[galaxy.galaxy_type].brightness
  )
}

export function zoneRings(shape: GalaxyShape, radius: number) {
  return [
    {
      key: 'core',
      label: 'Core',
      radius: (shape.core_reach_pct / PERCENT) * radius,
    },
    {
      key: 'bulge',
      label: 'Bulge',
      radius: (shape.bulge_reach_pct / PERCENT) * radius,
    },
    {
      key: 'inner',
      label: 'Inner disc',
      radius: (shape.inner_reach_pct / PERCENT) * radius,
    },
    {
      key: 'disc',
      label: 'Disc',
      radius: (shape.disc_reach_pct / PERCENT) * radius,
    },
    {
      key: 'halo',
      label: 'Halo',
      radius: (shape.halo_reach_pct / PERCENT) * radius,
    },
  ]
}
