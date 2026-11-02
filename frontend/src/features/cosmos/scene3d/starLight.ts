import { Color } from 'three'
import { type StarRecord } from '../api'
import { STAR_LOOK } from '../model/looks'
import { tokenColor } from './sceneColors'

const DIM_LIGHT = 0.42
const BLACK_LIGHT = 0.6
const LIGHT_BASE = 0.78
const LIGHT_BRIGHTNESS = 0.42
const PERCENT = 100

export function isDimStar(star: StarRecord): boolean {
  const kind = STAR_LOOK[star.star_type].kind
  return kind === 'dead' || kind === 'remnant' || kind === 'brown'
}

export function starLight(
  type: StarRecord['star_type'] | undefined,
  level: number
): Color {
  if (!type) return new Color(1, 1, 1).multiplyScalar(LIGHT_BASE)
  const look = STAR_LOOK[type]
  const brightness = level / PERCENT
  const scale =
    look.kind === 'dead' || look.kind === 'remnant' || look.kind === 'brown'
      ? DIM_LIGHT
      : look.kind === 'black'
        ? BLACK_LIGHT
        : LIGHT_BASE + LIGHT_BRIGHTNESS * brightness
  return tokenColor(look.lightToken).clone().multiplyScalar(scale)
}
