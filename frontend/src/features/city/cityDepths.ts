import { Color } from 'three'
import { type components } from '@/api/generated/schema'
import { type ThemeColorName } from '@/components/domain/useThemeColors'
import { tokenHex } from '@/features/cosmography/visual/palette'
import { STRATUM_LOOK } from '@/features/map/deepLooks'
import { type DepthSet } from './models'

type UndergroundStratum = components['schemas']['UndergroundStratum']
type SceneTone = ThemeColorName | 'cosmos-void-edge' | 'cosmos-bone'

type DepthLook = {
  set: DepthSet
  lit: SceneTone
  floor: SceneTone
  hue: number
  ice: boolean
  textured: boolean
  walls: boolean
  stones: boolean
  haze: SceneTone
  hazeShare: number
  sky: SceneTone
  ambient: number
  near: number
  far: number
}

const CAVE: Omit<DepthLook, 'floor' | 'hue' | 'set' | 'lit'> = {
  ice: false,
  textured: false,
  walls: true,
  stones: true,
  haze: 'cosmos-void-edge',
  hazeShare: 0,
  sky: 'cosmos-bone',
  ambient: 0.25,
  near: 1,
  far: 2.8,
}

export const DEPTH_LOOK: Record<UndergroundStratum, DepthLook> = {
  permafrost_layer: {
    ...CAVE,
    set: 'ice',
    lit: 'chart-3',
    floor: 'cosmos-bone',
    hue: 0.35,
    ice: true,
    haze: 'chart-3',
    hazeShare: 0.12,
    ambient: 0.45,
  },
  aquifer: {
    ...CAVE,
    set: 'stalagmites',
    lit: 'chart-3',
    floor: 'chart-3',
    hue: 0.3,
    haze: 'chart-3',
    hazeShare: 0.15,
  },
  under_ocean: {
    ...CAVE,
    set: 'kelp',
    lit: 'cosmos-bone',
    floor: 'chart-3',
    hue: 0.42,
    ice: true,
    haze: 'chart-3',
    hazeShare: 0.2,
    ambient: 0.4,
    far: 2.6,
  },
  reservoir: {
    ...CAVE,
    set: 'stalagmites',
    lit: 'warning',
    floor: 'warning',
    hue: 0.16,
  },
  cavern_upper: {
    ...CAVE,
    set: 'stalagmites',
    lit: 'brand-gold',
    floor: 'rarity-legendary',
    hue: 0.1,
  },
  cavern_middle: {
    ...CAVE,
    set: 'fungi',
    lit: 'success',
    floor: 'rarity-uncommon',
    hue: 0.12,
  },
  fault_zone: {
    ...CAVE,
    set: 'cinders',
    lit: 'destructive',
    floor: 'destructive',
    hue: 0.1,
    haze: 'destructive',
    hazeShare: 0.06,
  },
  cavern_lower: {
    ...CAVE,
    set: 'crystals',
    lit: 'rarity-epic',
    floor: 'rarity-epic',
    hue: 0.14,
  },
  hollow_interior: {
    ...CAVE,
    set: 'meadow',
    lit: 'brand-gold',
    floor: 'success',
    hue: 0.5,
    textured: true,

    haze: 'brand-gold',
    hazeShare: 0.28,
    sky: 'brand-gold',
    ambient: 0.9,
    near: 1.5,
    far: 3.8,
  },
  magma_sea: {
    ...CAVE,
    set: 'cinders',
    lit: 'warning',
    floor: 'destructive',
    hue: 0.28,
    haze: 'destructive',
    hazeShare: 0.18,
    sky: 'warning',
    ambient: 0.3,
  },
  deep_underworld: {
    ...CAVE,
    set: 'cairns',
    lit: 'cosmos-bone',
    floor: 'rarity-mythic',
    hue: 0.16,
    haze: 'rarity-mythic',
    hazeShare: 0.05,
    sky: 'foreground',
    ambient: 0.3,
  },
}

const ICE_SHARE = 0.55
const STONE = 0.5
const LIT_CALM = 0.5
const PLAIN = 0.42
const PLAIN_RIM = 0.26
const PAVING_SHARE = 0.22

function hex(color: Color): string {
  return `#${color.getHexString()}`
}

export function depthColors(stratum: UndergroundStratum) {
  const look = DEPTH_LOOK[stratum]
  const floor = new Color(tokenHex('--cosmos-bone'))
    .multiplyScalar(STONE)
    .lerp(new Color(tokenHex(`--${look.floor}`)), look.hue)
  const bone = new Color(tokenHex('--cosmos-bone'))
  return {
    look,
    floor: hex(floor),
    plain: hex(floor.clone().multiplyScalar(PLAIN)),
    plainRim: hex(
      (look.ice
        ? floor.clone().lerp(bone, ICE_SHARE)
        : floor.clone()
      ).multiplyScalar(PLAIN_RIM)
    ),
    wall: hex(look.ice ? floor.clone().lerp(bone, ICE_SHARE) : floor),
    paving: hex(floor.clone().lerp(bone, PAVING_SHARE)),
    haze: hex(
      new Color(tokenHex('--cosmos-void')).lerp(
        new Color(tokenHex(`--${look.haze}`)),
        look.hazeShare
      )
    ),
    sky: tokenHex(`--${look.sky}`),
    lit: hex(new Color(tokenHex(`--${look.lit}`)).lerp(floor, LIT_CALM)),
    glow: tokenHex(`--${STRATUM_LOOK[stratum].glow}`),
  }
}
