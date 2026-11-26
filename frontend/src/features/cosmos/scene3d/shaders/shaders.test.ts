import { describe, expect, it } from 'vitest'
import * as visual from '@/features/cosmography/visual/shaders'
import * as effects from './effects'
import * as noise from './noise'
import * as planet from './planet'
import * as sky from './sky'
import * as star from './star'

const STEPPED_TIME = /\b(floor|ceil|round|trunc)\s*\(\s*(uTime|time|tt)\b/

const modules: Record<string, unknown>[] = [
  visual,
  effects,
  noise,
  planet,
  sky,
  star,
]
const sources = modules.flatMap((module) =>
  Object.entries(module).flatMap(([name, value]) =>
    typeof value === 'string' ? [{ name, source: value }] : []
  )
)

describe('scene shaders', () => {
  it('never step time, so nothing they draw strobes from frame to frame', () => {
    const stepped = sources.flatMap(({ name, source }) =>
      source
        .split('\n')
        .filter((line) => STEPPED_TIME.test(line))
        .map((line) => `${name}: ${line.trim()}`)
    )
    expect(stepped).toEqual([])
  })

  it('catches a stepped flicker like the old space fold route', () => {
    expect(
      STEPPED_TIME.test(
        'float fl = step(0.38, fract(sin(seg*12.9898 + floor(uTime*7.0)*3.17)*43758.5453));'
      )
    ).toBe(true)
  })
})
