import {
  type Atmosphere,
  type StarType,
  type TravelMethod,
  type WorldType,
} from '../api'

export type MethodLook = {
  token: string
  dash: readonly number[]
  width: number
  curve: number
  lift: number
  style: number
  ribbon: number
  glow: number
  endRings: boolean
  opacity: number
}

const method = (
  token: string,
  dash: readonly number[],
  width: number,
  curve: number,
  lift: number,
  style: number,
  ribbon: number,
  glow: number,
  extra: Partial<Pick<MethodLook, 'endRings' | 'opacity'>> = {}
): MethodLook => ({
  token,
  dash,
  width,
  curve,
  lift,
  style,
  ribbon,
  glow,
  endRings: extra.endRings ?? false,
  opacity: extra.opacity ?? 0.9,
})

export const METHOD_LOOK: Record<TravelMethod, MethodLook> = {
  ancient_gate: method(
    '--cosmos-route-ancient-gate',
    [1, 5],
    1.4,
    0,
    0.35,
    5,
    2.6,
    1,
    {
      endRings: true,
    }
  ),
  space_fold: method(
    '--cosmos-route-space-fold',
    [10, 3, 2, 3],
    1.6,
    0,
    0.6,
    4,
    3.2,
    1.3
  ),
  light_sail: method(
    '--cosmos-route-light-sail',
    [7, 5],
    1.4,
    0.12,
    1,
    1,
    3,
    1
  ),
  cosmic_mount: method(
    '--cosmos-route-cosmic-mount',
    [4, 4],
    1.6,
    0.18,
    1.25,
    6,
    3.2,
    1
  ),
  dream_journey: method(
    '--cosmos-route-dream-journey',
    [0.1, 6],
    2.4,
    0.22,
    1.15,
    2,
    3.8,
    1.3
  ),
  river_of_dead: method(
    '--cosmos-route-river-of-dead',
    [2, 3],
    1.8,
    -0.25,
    -0.7,
    3,
    5.2,
    0.9
  ),
  divine_bridge: method(
    '--cosmos-route-divine-bridge',
    [],
    2.4,
    0.32,
    1,
    0,
    3.3,
    1.05
  ),
  slingshot_orbit: method(
    '--cosmos-route-slingshot-orbit',
    [1, 7],
    1.8,
    0.4,
    1.5,
    7,
    3.4,
    1.1
  ),
  swallowed: method('--cosmos-route-swallowed', [], 3.2, -0.1, 0.5, 8, 6, 1, {
    opacity: 0.55,
  }),
}

export const CLOSED_ROUTE_DASH: readonly number[] = [2, 6]
export const CLOSED_ROUTE_OPACITY = 0.3
export const HIDDEN_ROUTE_OPACITY = 0.4
export const LEGEND_LINE_MAX_WIDTH = 2.4

export type StarKind =
  'normal' | 'dead' | 'black' | 'broken' | 'pulse' | 'remnant' | 'reborn'

export type StarLook = {
  token: string
  edgeToken: string
  lightToken: string
  size: number
  kind: StarKind
  rays: number
  spike: number
  twin: boolean
}

const star = (
  type: StarType,
  size: number,
  kind: StarKind,
  rays: number,
  spike: number,
  twin = false
): StarLook => {
  const name = type.replace(/_/g, '-')
  return {
    token: `--cosmos-star-${name}`,
    edgeToken: `--cosmos-star-${name}-edge`,
    lightToken: `--cosmos-star-${name}-light`,
    size,
    kind,
    rays,
    spike,
    twin,
  }
}

export const STAR_LOOK: Record<StarType, StarLook> = {
  yellow_dwarf: star('yellow_dwarf', 1, 'normal', 0.75, 0.22),
  red_giant: star('red_giant', 1.75, 'normal', 0.95, 0.08),
  blue_giant: star('blue_giant', 1.4, 'normal', 0.85, 0.5),
  white_dwarf: star('white_dwarf', 0.5, 'normal', 0.4, 0.65),
  binary: star('binary', 0.74, 'normal', 0.6, 0.2, true),
  dead_star: star('dead_star', 0.85, 'dead', 0.05, 0),
  black_sun: star('black_sun', 1, 'black', 0, 0),
  broken_star: star('broken_star', 1.05, 'broken', 1.5, 0.3),
  pulsar: star('pulsar', 0.6, 'pulse', 0.5, 0.7),
  star_remnant: star('star_remnant', 0.38, 'remnant', 0.2, 0.35),
  reborn_star: star('reborn_star', 0.95, 'reborn', 0.9, 0.4),
}

export const TWIN_STAR_TOKEN = '--cosmos-star-blue-giant'

export const STAR_KIND_CODE: Record<StarKind, number> = {
  normal: 0,
  dead: 1,
  black: 2,
  broken: 3,
  pulse: 4,
  remnant: 5,
  reborn: 6,
}

export type SurfaceCode =
  | 'rocky'
  | 'ocean'
  | 'sand'
  | 'ice'
  | 'lava'
  | 'crystal'
  | 'living'
  | 'dead'
  | 'dream'
  | 'gas'
  | 'mirror'
  | 'locked'
  | 'void'
  | 'palace'
  | 'ship'
  | 'corpse'
  | 'belt'

export const SURFACE_CODE: Record<SurfaceCode, number> = {
  rocky: 0,
  ocean: 1,
  sand: 2,
  ice: 3,
  lava: 4,
  crystal: 5,
  living: 6,
  dead: 7,
  dream: 8,
  gas: 9,
  mirror: 10,
  locked: 11,
  void: 12,
  palace: 13,
  ship: 14,
  corpse: 15,
  belt: 16,
}

export type WorldBodyLook = {
  surface: SurfaceCode
  ring: boolean
  gas: boolean
  breath: boolean
  cities: boolean
  cloudy: boolean
}

const body = (
  surface: SurfaceCode,
  extra: Partial<Omit<WorldBodyLook, 'surface'>> = {}
): WorldBodyLook => ({
  surface,
  ring: extra.ring ?? false,
  gas: extra.gas ?? false,
  breath: extra.breath ?? false,
  cities: extra.cities ?? true,
  cloudy: extra.cloudy ?? true,
})

export const WORLD_BODY: Record<WorldType, WorldBodyLook> = {
  ordinary: body('rocky'),
  ocean: body('ocean'),
  sand: body('sand'),
  ice: body('ice'),
  lava: body('lava', { cloudy: false }),
  crystal: body('crystal', { cloudy: false }),
  living: body('living', { breath: true }),
  dead: body('dead', { cities: false }),
  dream: body('dream'),
  mirror: body('mirror', { cloudy: false }),
  gas: body('gas', { ring: true, gas: true, cities: false, cloudy: false }),
  ringed: body('rocky', { ring: true }),
  asteroid_belt: body('belt', { cities: false, cloudy: false }),
  tidally_locked: body('locked'),
  void_pocket: body('void', { cities: false, cloudy: false }),
  gods_palace: body('palace', { cloudy: false }),
  generation_ship: body('ship', { cloudy: false }),
  corpse_world: body('corpse', { breath: true, cloudy: false }),
}

export type AtmosphereLook = {
  intensity: number
  shell: number
  clouds: number
  toxic: boolean
}

export const ATMOSPHERE_LOOK: Record<Atmosphere, AtmosphereLook | null> = {
  none: null,
  thin: { intensity: 0.55, shell: 1.07, clouds: 0.2, toxic: false },
  normal: { intensity: 1, shell: 1.11, clouds: 0.4, toxic: false },
  dense: { intensity: 1.5, shell: 1.16, clouds: 0.68, toxic: false },
  toxic: { intensity: 1.25, shell: 1.13, clouds: 0.5, toxic: true },
}

export const GAS_ATMOSPHERE: AtmosphereLook = {
  intensity: 0.8,
  shell: 1.08,
  clouds: 0,
  toxic: false,
}

export const NEBULA_TOKENS = [
  '--cosmos-nebula-1',
  '--cosmos-nebula-2',
  '--cosmos-nebula-3',
  '--cosmos-nebula-4',
  '--cosmos-nebula-5',
  '--cosmos-nebula-6',
  '--cosmos-nebula-7',
] as const

export const DUST_TOKENS = [
  '--cosmos-dust-1',
  '--cosmos-dust-2',
  '--cosmos-dust-3',
  '--cosmos-dust-4',
  '--cosmos-dust-5',
] as const

export function cssVar(token: string): string {
  return `var(${token})`
}
