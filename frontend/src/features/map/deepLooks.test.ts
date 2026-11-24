import { describe, expect, it } from 'vitest'
import {
  deepPassageKindValues,
  deepPassageStateValues,
  undergroundStratumValues,
} from '@/api/generated/schema'
import {
  PASSAGE_KIND,
  PASSAGE_STATE,
  STRATUM,
} from '@/features/entity/environment/geologyLabels'
import {
  PASSAGE_GLYPH,
  PASSAGE_LOOK,
  type PassageLook,
  STRATUM_LOOK,
  type StratumLook,
} from './deepLooks'
import { LINE_STYLE, PASSAGE_LINE } from './mapLines'
import { LINE_LABEL } from './mapText'

function lookKey(look: StratumLook): string {
  return `${look.fill}|${look.glow}|${look.pattern}`
}

function passageKey(look: PassageLook): string {
  return `${look.token}|${look.width}|${look.dash.join(',')}`
}

describe('looks of the deep', () => {
  it('gives every stratum its own look and a label', () => {
    for (const stratum of undergroundStratumValues) {
      expect(STRATUM_LOOK[stratum]).toBeDefined()
      expect(STRATUM[stratum].label).not.toBe('')
    }
    const keys = undergroundStratumValues.map((stratum) =>
      lookKey(STRATUM_LOOK[stratum])
    )
    expect(new Set(keys).size).toBe(keys.length)
    const patterns = undergroundStratumValues.map(
      (stratum) => STRATUM_LOOK[stratum].pattern
    )
    expect(new Set(patterns).size).toBe(patterns.length)
  })

  it('gives every passage state its own stroke, line and label', () => {
    const keys = deepPassageStateValues.map((state) =>
      passageKey(PASSAGE_LOOK[state])
    )
    expect(new Set(keys).size).toBe(keys.length)
    const tokens = deepPassageStateValues.map(
      (state) => PASSAGE_LOOK[state].token
    )
    expect(new Set(tokens).size).toBe(tokens.length)
    for (const state of deepPassageStateValues) {
      const line = PASSAGE_LINE[state]
      expect(LINE_STYLE[line]).toBeDefined()
      expect(LINE_LABEL[line]).not.toBe('')
      expect(PASSAGE_STATE[state].label).not.toBe('')
    }
  })

  it('draws every kind of passage with its own glyph', () => {
    const glyphs = deepPassageKindValues.map((kind) => PASSAGE_GLYPH[kind])
    expect(new Set(glyphs).size).toBe(glyphs.length)
    for (const kind of deepPassageKindValues)
      expect(PASSAGE_KIND[kind].label).not.toBe('')
  })
})
