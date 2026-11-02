import { describe, expect, it } from 'vitest'
import { type BondView } from '../api/types'
import { groupBonds } from './bondGroups'

function bond(id: number, kind: string, outgoing: boolean): BondView {
  return { id, kind, outgoing } as unknown as BondView
}

describe('bond grouping', () => {
  it('groups by direction and type and puts the largest group first', () => {
    const groups = groupBonds([
      bond(1, 'ally', true),
      bond(2, 'owes', true),
      bond(3, 'ally', true),
      bond(4, 'ally', false),
    ])
    expect(groups.map((group) => group.key)).toEqual([
      'out:ally',
      'out:owes',
      'in:ally',
    ])
    expect(groups[0]?.bonds.map((item) => item.id)).toEqual([1, 3])
  })

  it('hides the incoming containment bonds', () => {
    const groups = groupBonds([
      bond(1, 'inside', false),
      bond(2, 'inside', true),
    ])
    expect(groups.map((group) => group.key)).toEqual(['out:inside'])
  })
})
