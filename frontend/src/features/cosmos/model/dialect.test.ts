import { describe, expect, it } from 'vitest'
import {
  type Phonology,
  dialectRows,
  dialectSummary,
  syllableText,
} from './dialect'

const PHONOLOGY: Phonology = {
  vowels: ['a', 'o'],
  consonants: ['k', 'r'],
  forbidden_sounds: [],
  onsets: [],
  codas: [],
  syllable_patterns: ['CV'],
  preferred_endings: [],
  texture: 'hard',
  min_syllables: 1,
  max_syllables: 1,
  sample_names: [],
}

describe('dialect text', () => {
  it('summarises the phonology in plain words', () => {
    expect(dialectSummary(PHONOLOGY)).toBe('Hard names of 1 syllable.')
    expect(
      dialectSummary({
        ...PHONOLOGY,
        max_syllables: 3,
        preferred_endings: ['ak'],
        forbidden_sounds: ['z'],
      })
    ).toBe('Hard names of 1 to 3 syllables; often ending in -ak; never z.')
    expect(
      syllableText({ ...PHONOLOGY, min_syllables: 2, max_syllables: 2 })
    ).toBe('2 syllables')
  })

  it('leaves out empty sound lists', () => {
    expect(dialectRows(PHONOLOGY).map((row) => row.label)).toEqual([
      'Vowels',
      'Consonants',
      'Syllable shapes',
      'Length',
    ])
  })
})
