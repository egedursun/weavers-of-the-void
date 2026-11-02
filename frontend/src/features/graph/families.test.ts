import { describe, expect, it } from 'vitest'
import {
  ALL_FAMILIES,
  FAMILIES,
  OTHER_FAMILY,
  familyOf,
  hollow,
  typeLabel,
} from './families'

describe('entity families', () => {
  it('gives every family a distinct shape and colour token', () => {
    const shapes = new Set(ALL_FAMILIES.map((family) => family.shape))
    const tokens = new Set(ALL_FAMILIES.map((family) => family.token))
    expect(shapes.size).toBe(ALL_FAMILIES.length)
    expect(tokens.size).toBe(ALL_FAMILIES.length)
  })

  it('places each type in exactly one family', () => {
    const seen = new Map<string, string>()
    for (const family of FAMILIES)
      for (const type of family.types) {
        expect(seen.has(type)).toBe(false)
        seen.set(type, family.key)
      }
  })

  it('maps known types to their family and unknown types to Other', () => {
    expect(familyOf('settlement').key).toBe('places')
    expect(familyOf('mortal').key).toBe('communities')
    expect(familyOf('son').key).toBe('gods')
    expect(familyOf('event').key).toBe('events')
    expect(familyOf('mystery')).toBe(OTHER_FAMILY)
  })

  it('draws only the living family hollow', () => {
    expect(hollow('ring')).toBe(true)
    expect(hollow('square')).toBe(false)
  })

  it('labels node kinds and entity types readably', () => {
    const labels = new Map([['settlement', 'Settlement']])
    expect(typeLabel('foreign_god', labels)).toBe('Foreign god')
    expect(typeLabel('settlement', labels)).toBe('Settlement')
    expect(typeLabel('natural_law', labels)).toBe('Natural law')
  })
})
