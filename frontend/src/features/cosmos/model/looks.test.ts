import theme from '@/styles/theme.css?raw'
import { describe, expect, it } from 'vitest'
import { starTypeValues, worldTypeValues } from '@/api/generated/schema'
import { STAR_TYPE_LABEL } from './labels'
import {
  COMPANION_TOKENS,
  METHOD_LOOK,
  STAR_KIND_CODE,
  STAR_LOOK,
  SURFACE_CODE,
  WORLD_BODY,
  WORLD_SEA,
} from './looks'

const defined = (token: string) => theme.includes(`${token}:`)

describe('cosmos looks', () => {
  it('gives every star type a look whose colours exist in the theme', () => {
    for (const type of starTypeValues) {
      const look = STAR_LOOK[type]
      expect(STAR_TYPE_LABEL[type]).toBeTruthy()
      expect(defined(look.token)).toBe(true)
      expect(defined(look.edgeToken)).toBe(true)
      expect(defined(look.lightToken)).toBe(true)
      expect(STAR_KIND_CODE[look.kind]).toBeGreaterThanOrEqual(0)
    }
    for (const token of COMPANION_TOKENS) expect(defined(token)).toBe(true)
    expect(STAR_LOOK.trinary.companions).toBe(2)
    expect(STAR_LOOK.binary.companions).toBe(1)
  })

  it('gives every world type a distinct, known surface', () => {
    for (const type of worldTypeValues)
      expect(SURFACE_CODE[WORLD_BODY[type].surface]).toBeGreaterThanOrEqual(0)
    const codes = Object.values(SURFACE_CODE)
    expect(new Set(codes).size).toBe(codes.length)
    const kinds = Object.values(STAR_KIND_CODE)
    expect(new Set(kinds).size).toBe(kinds.length)
  })

  it('draws no two world types alike', () => {
    const signatures = worldTypeValues.map((type) =>
      JSON.stringify([WORLD_BODY[type], WORLD_SEA[type] ?? null])
    )
    const twins = worldTypeValues.filter(
      (_, index) => signatures.indexOf(signatures[index]) !== index
    )
    expect(twins).toEqual([])
  })

  it('gives every travel method a colour in the theme', () => {
    for (const look of Object.values(METHOD_LOOK))
      expect(defined(look.token)).toBe(true)
  })
})
