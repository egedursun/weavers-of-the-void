import { describe, expect, it } from 'vitest'
import {
  type LanguageNode,
  buildFamilies,
  relativesOf,
} from './languageFamilies'
import { validateLanguagesSearch } from './languagesSearch'

function node(id: number, parent: number | null): LanguageNode {
  return {
    language: { id, name: `Tongue ${id}` },
    writing_system: null,
    parent_language_id: parent,
    words: 0,
    speakers: 0,
    sample_names: [],
    cognates: [],
  } as unknown as LanguageNode
}

describe('language families', () => {
  const nodes = [
    node(1, null),
    node(2, 1),
    node(3, 2),
    node(4, null),
    node(5, 99),
  ]

  it('nests daughters under their mother and keeps loners apart', () => {
    const { families, loners } = buildFamilies(nodes)
    expect(families.map((family) => family.node.language.id)).toEqual([1])
    expect(families[0].children[0].children[0].node.language.id).toBe(3)
    expect(loners.map((item) => item.language.id)).toEqual([4, 5])
  })

  it('finds the mother and daughters of a language', () => {
    const { parent, daughters } = relativesOf(nodes, 2)
    expect(parent?.language.id).toBe(1)
    expect(daughters.map((item) => item.language.id)).toEqual([3])
  })

  it('validates the languages address', () => {
    expect(
      validateLanguagesSearch({ view: 'tree', language: '4', q: ' ' })
    ).toEqual({ view: 'tree', language: 4 })
  })
})
