import { describe, expect, it } from 'vitest'
import { generationsOf } from './api'
import { KIN_KINDS, SLOTS, SLOT_TYPES } from './labels'

describe('mortal kin and gear', () => {
  it('groups a family tree by generation, elders first', () => {
    const rows = generationsOf([
      {
        id: 3,
        name: 'Child',
        living: true,
        sex: 'female',
        parents: [1, 2],
        spouses: [],
        generation: 1,
      },
      {
        id: 1,
        name: 'Mother',
        living: true,
        sex: 'female',
        parents: [],
        spouses: [2],
        generation: 0,
      },
      {
        id: 4,
        name: 'Grandmother',
        living: false,
        sex: 'female',
        parents: [],
        spouses: [],
        generation: -1,
      },
      {
        id: 2,
        name: 'Father',
        living: false,
        sex: 'male',
        parents: [],
        spouses: [1],
        generation: 0,
      },
    ])
    expect(rows.map((row) => row.map((person) => person.id))).toEqual([
      [4],
      [1, 2],
      [3],
    ])
  })

  it('labels every kin bond and slot', () => {
    expect(Object.keys(KIN_KINDS)).toHaveLength(6)
    expect(Object.keys(SLOTS).sort()).toEqual(Object.keys(SLOT_TYPES).sort())
    expect(SLOT_TYPES.mount).toContain('beast')
  })
})
