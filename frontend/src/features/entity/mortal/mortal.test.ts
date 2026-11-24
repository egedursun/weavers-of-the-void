import { describe, expect, it } from 'vitest'
import { sexKindValues } from '@/api/generated/schema'
import { KIN_KINDS, SEXES, SLOTS, SLOT_TYPES } from './labels'

describe('mortal kin and gear', () => {
  it('labels every kin bond and slot', () => {
    expect(Object.keys(KIN_KINDS)).toHaveLength(7)
    expect(Object.keys(SLOTS).sort()).toEqual(Object.keys(SLOT_TYPES).sort())
    expect(SLOT_TYPES.mount).toContain('beast')
  })

  it('labels every sex the world knows, so the god can set each one', () => {
    expect(Object.keys(SEXES).sort()).toEqual([...sexKindValues].sort())
  })
})
