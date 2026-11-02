import { describe, expect, it } from 'vitest'
import { changesOf, hasChanges, initialDraft } from './languageEdit'
import { type LanguageNode } from './languageFamilies'

const NODE = {
  language: { id: 47, name: 'Old Velmoran', world_id: 3 },
  writing_system: 'alphabet',
  parent_language_id: null,
  words: 12,
  speakers: 2,
  sample_names: ['Velmora'],
  signature: { consonants: 'vlm', cluster: 'th', ending: 'ra', length_bias: 1 },
  alphabet: ['a', 'e', 'l', 'm', 'r', 'v'],
  cognates: [],
} as unknown as LanguageNode

describe('language edits', () => {
  it('sends nothing while the draft is untouched', () => {
    const change = changesOf(NODE, initialDraft(NODE))
    expect(hasChanges(change)).toBe(false)
    expect(change).toEqual({
      language_id: 47,
      clear_writing_system: false,
      clear_signature: false,
    })
  })

  it('clears the script and the signature on request', () => {
    const draft = {
      ...initialDraft(NODE),
      script: 'unwritten' as const,
      clearSignature: true,
    }
    const change = changesOf(NODE, draft)
    expect(change.clear_writing_system).toBe(true)
    expect(change.clear_signature).toBe(true)
    expect(change.signature).toBeUndefined()
  })

  it('keeps the length bias when the signature letters change', () => {
    const draft = { ...initialDraft(NODE), consonants: 'krs', ending: 'ek' }
    expect(changesOf(NODE, draft).signature).toEqual({
      consonants: 'krs',
      cluster: 'th',
      ending: 'ek',
      length_bias: 1,
    })
  })

  it('sends taught names line by line, or forgets them all', () => {
    const named = changesOf(NODE, {
      ...initialDraft(NODE),
      names: ' Ashkar \n\nOrrin ',
    })
    expect(named.sample_names).toEqual(['Ashkar', 'Orrin'])
    const forgotten = changesOf(NODE, {
      ...initialDraft(NODE),
      names: 'Ashkar',
      forgetNames: true,
    })
    expect(forgotten.sample_names).toEqual([])
  })

  it('sends a changed alphabet and a new script', () => {
    const change = changesOf(NODE, {
      ...initialDraft(NODE),
      alphabet: 'aeiouk',
      script: 'knot',
    })
    expect(change.alphabet).toBe('aeiouk')
    expect(change.writing_system).toBe('knot')
  })
})
