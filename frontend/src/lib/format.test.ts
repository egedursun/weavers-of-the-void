import { describe, expect, it } from 'vitest'
import {
  formatCompact,
  formatDecimal,
  formatInteger,
  formatNumber,
  formatPercent,
  formatTokens,
} from './format'

describe('number formatting', () => {
  it('uses the English locale for integers', () => {
    expect(formatInteger(1284000)).toBe('1,284,000')
    expect(formatInteger(2.7)).toBe('3')
  })

  it('rounds decimals instead of printing raw floats', () => {
    expect(formatDecimal(1.3440149226158604)).toBe('1.34')
    expect(formatDecimal(2)).toBe('2')
  })

  it('formats ratios as percentages and large numbers compactly', () => {
    expect(formatPercent(0.42)).toBe('42%')
    expect(formatCompact(1284000)).toBe('1.3M')
  })

  it('shows token counts with two decimals once they pass a thousand', () => {
    expect(formatTokens(9_040_000)).toBe('9.04M')
    expect(formatTokens(10_240_000)).toBe('10.24M')
    expect(formatTokens(105_480_000)).toBe('105.48M')
    expect(formatTokens(2_320_000_000)).toBe('2.32B')
    expect(formatTokens(12_500)).toBe('12.50K')
    expect(formatTokens(9_000_000)).toBe('9.00M')
    expect(formatTokens(842)).toBe('842')
  })

  it('dispatches on the requested format', () => {
    expect(formatNumber(0.5, 'percent')).toBe('50%')
    expect(formatNumber(12840)).toBe('12,840')
  })
})
