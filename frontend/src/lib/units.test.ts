import { describe, expect, it } from 'vitest'
import { formatBytes, formatClock, formatDuration, plural } from './units'

describe('unit formatting', () => {
  it('formats durations from seconds to days', () => {
    expect(formatDuration(4.25)).toBe('4.3 s')
    expect(formatDuration(120)).toBe('2 min')
    expect(formatDuration(398)).toBe('6 min 38 s')
    expect(formatDuration(3600)).toBe('1 h')
    expect(formatDuration(9300)).toBe('2 h 35 min')
    expect(formatDuration(90_000)).toBe('1 d 1 h')
  })

  it('formats clocks, sizes and plurals', () => {
    expect(formatClock(65)).toBe('1:05')
    expect(formatBytes(2_097_152)).toBe('2 MB')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(plural(1, 'page')).toBe('1 page')
    expect(plural(3, 'page')).toBe('3 pages')
  })
})
