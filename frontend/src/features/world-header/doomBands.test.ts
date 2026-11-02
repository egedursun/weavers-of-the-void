import { describe, expect, it } from 'vitest'
import { bandRange, currentBand, doomBands } from './doomBands'

const BANDS = doomBands({ threshold: 100, firstPct: 50, secondPct: 80 })

describe('doom bands', () => {
  it('splits the clock at the rule points', () => {
    expect(BANDS.map((band) => band.from)).toEqual([0, 50, 80, 100])
    expect(bandRange(BANDS[0])).toBe('0 to 49')
    expect(bandRange(BANDS[3])).toBe('100 and above')
  })

  it('finds the band of a value', () => {
    expect(currentBand(BANDS, 0).key).toBe('calm')
    expect(currentBand(BANDS, 50).key).toBe('omen')
    expect(currentBand(BANDS, 99).key).toBe('warning')
    expect(currentBand(BANDS, 140).key).toBe('apocalypse')
  })

  it('never lets the second point fall below the first', () => {
    const odd = doomBands({ threshold: 10, firstPct: 90, secondPct: 20 })
    expect(odd[2].from).toBeGreaterThanOrEqual(odd[1].from)
  })
})
