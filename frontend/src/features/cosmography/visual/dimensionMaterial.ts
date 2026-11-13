import { type IUniform } from 'three'
import { unitHash } from '@/lib/hash'
import { uniform } from '@/features/cosmos/scene3d/materials'
import { DIMENSION_LOOK, DIMENSION_PATTERNS } from './dimensionLook'
import { type DimensionKind, type Palette } from './galaxyForm'

export type DimensionState = {
  id: number
  kind: DimensionKind
  veil: number
  stability: number
  magic: number
  time_factor: number
}

const SPIN = 0.09
const SPIN_MIN = 0.25
const SPIN_MAX = 4
const PERCENT = 100
const FLICKER = 0.6
const MAGIC_SPARKLE = 250
const SEED_SPAN = 40

export function dimensionUniforms(
  state: DimensionState,
  palette: Palette,
  tone: boolean
): Record<string, IUniform> {
  const look = DIMENSION_LOOK[state.kind]
  const steady = state.stability / PERCENT
  return {
    uCore: uniform(palette(look.core)),
    uBody: uniform(palette(look.body)),
    uEdge: uniform(palette(look.edge)),
    uRingColor: uniform(palette('--cosmos-copper')),
    uMode: uniform(DIMENSION_PATTERNS.indexOf(look.pattern)),
    uTime: uniform(unitHash(`dimension-time-${state.id}`) * SEED_SPAN),
    uSeed: uniform(unitHash(`dimension-seed-${state.id}`) * SEED_SPAN),
    uSpin: uniform(
      SPIN *
        Math.min(Math.max(state.time_factor, SPIN_MIN), SPIN_MAX) *
        (state.kind === 'time_reversed' ? -1 : 1)
    ),
    uTurb: uniform(Math.min(look.turbulence * (1.5 - steady * 0.5), 1)),
    uSparkle: uniform(
      Math.min(look.sparkle * (0.6 + state.magic / MAGIC_SPARKLE), 1)
    ),
    uHalo: uniform(look.halo),
    uVeil: uniform(state.veil),
    uFlicker: uniform((1 - steady) * FLICKER),
    uLight: uniform(1),
    uRing: uniform(0),
    uTone: uniform(tone ? 1 : 0),
  }
}
