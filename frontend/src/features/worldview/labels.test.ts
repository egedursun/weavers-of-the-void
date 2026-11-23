import { describe, expect, it } from 'vitest'
import {
  journeyIntentValues,
  settleModeValues,
  warTerrainValues,
} from '@/api/generated/schema'
import { JOURNEY_INTENT_LABEL } from '@/features/cosmos/model/labels'
import { SETTLES, WARS } from './labels'

describe('ways of settling, grounds of war and journey intents', () => {
  it('names and draws every way of settling', () => {
    expect(settleModeValues).toHaveLength(11)
    for (const mode of settleModeValues) {
      expect(SETTLES[mode].label).toBeTruthy()
      expect(SETTLES[mode].icon).toBeTruthy()
    }
  })

  it('names and draws every ground of war', () => {
    expect(warTerrainValues).toHaveLength(8)
    for (const ground of warTerrainValues) {
      expect(WARS[ground].label).toBeTruthy()
    }
  })

  it('names every journey intent', () => {
    expect(journeyIntentValues).toHaveLength(8)
    for (const intent of journeyIntentValues) {
      expect(JOURNEY_INTENT_LABEL[intent]).toBeTruthy()
    }
  })
})
