import { describe, expect, it } from 'vitest'
import { validateWarsSearch } from './warsTabs'

describe('wars search', () => {
  it('keeps a known tab and a positive war id', () => {
    expect(validateWarsSearch({ tab: 'ended', war: '12' })).toEqual({
      tab: 'ended',
      war: 12,
    })
  })

  it('drops unknown tabs and invalid war ids', () => {
    expect(validateWarsSearch({ tab: 'nowhere', war: '-3' })).toEqual({})
    expect(validateWarsSearch({ war: 'abc' })).toEqual({})
  })
})
