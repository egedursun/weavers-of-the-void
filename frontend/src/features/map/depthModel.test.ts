import { describe, expect, it } from 'vitest'
import { DEPTH_LAYERS, LAYER_MODES, depthReason } from './mapModel'

describe('layers at depth', () => {
  it('decides every layer for the world below', () => {
    expect(Object.keys(DEPTH_LAYERS).sort()).toEqual([...LAYER_MODES].sort())
  })

  it('keeps every layer at the surface and gives surface-only layers a reason below', () => {
    for (const mode of LAYER_MODES) expect(depthReason(mode, null)).toBeNull()
    expect(depthReason('soil', 'cavern_upper')).toBe(
      'Reads the soil and fields of the surface'
    )
    expect(depthReason('climate', 'cavern_upper')).toBe('Reads the sky')
    expect(depthReason('political', 'cavern_upper')).toBeNull()
    expect(depthReason('deep', 'cavern_upper')).toBeNull()
  })
})
