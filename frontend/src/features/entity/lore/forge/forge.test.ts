import { describe, expect, it } from 'vitest'
import {
  averageTruth,
  clampTruth,
  truthBar,
  truthWord,
} from '../rumours/rumourModel'
import {
  FORGE_FIELDS,
  forgeValues,
  initialDraft,
  isForgeKind,
  missingField,
} from './forgeModel'
import { KIND_CATALOG, paramsOf } from './kindModel'

describe('lore forge', () => {
  it('asks for the typed kind before anything is forged', () => {
    const fields = FORGE_FIELDS.item
    const draft = initialDraft(fields)
    expect(missingField(fields, draft)?.key).toBe('item_class')
    const ready = { ...draft, item_class: 'crown' }
    expect(missingField(fields, ready)).toBeNull()
    expect(forgeValues(fields, ready)).toEqual({
      item_class: 'crown',
      quality: 50,
    })
  })

  it('needs at least one tenet for a creed and knows which kinds it forges', () => {
    const fields = FORGE_FIELDS.ideology
    expect(missingField(fields, initialDraft(fields))?.key).toBe('tenets')
    expect(isForgeKind('knowledge')).toBe(true)
    expect(isForgeKind('mortal')).toBe(false)
  })

  it('summarises custom kinds from their parameters', () => {
    const params = paramsOf({ reach: 3, damage_type: 'cold' })
    expect(KIND_CATALOG.item_class.summary(params)).toEqual({ reach: 3 })
    expect(KIND_CATALOG.rite_effect.summary({ magnitude_pct: 150 })).toEqual({
      strength: 50,
    })
  })
})

describe('rumours', () => {
  it('reads how true a rumour runs', () => {
    expect(truthWord(90)).toBe('close to the truth')
    expect(truthWord(50)).toBe('half true')
    expect(truthBar(10)).toBe('destructive')
    expect(clampTruth(140)).toBe(100)
    expect(averageTruth([])).toBe(0)
  })
})
