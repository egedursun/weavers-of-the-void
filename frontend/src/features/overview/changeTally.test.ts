import { describe, expect, it } from 'vitest'
import { type ChangesResponse, EMPTY_TALLY, addChanges } from './api'

const BASE: ChangesResponse = {
  full: false,
  version: 'v2',
  entities: [],
  removed_entity_ids: [],
  sons: [],
  removed_son_ids: [],
  new_chronicle_lines: 0,
  bonds_changed: false,
  cosmos_changed: false,
  worlds_changed: false,
  relations_changed: false,
  foreign_god_ids: [],
}

describe('change tally', () => {
  it('stays empty for a quiet digest', () => {
    expect(addChanges(EMPTY_TALLY, BASE)).toEqual(EMPTY_TALLY)
  })

  it('accumulates counts and sticky flags across digests', () => {
    const first = addChanges(EMPTY_TALLY, {
      ...BASE,
      removed_entity_ids: [1, 2],
      new_chronicle_lines: 3,
      bonds_changed: true,
    })
    const second = addChanges(first, {
      ...BASE,
      removed_son_ids: [4],
      new_chronicle_lines: 2,
    })
    expect(second.removedEntities).toBe(2)
    expect(second.sons).toBe(1)
    expect(second.chronicleLines).toBe(5)
    expect(second.bonds).toBe(true)
  })

  it('remembers that the world was rebuilt', () => {
    expect(addChanges(EMPTY_TALLY, { ...BASE, full: true }).rebuilt).toBe(true)
  })
})
