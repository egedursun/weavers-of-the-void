import { describe, expect, it } from 'vitest'
import { type EpochStatistics } from './api'
import {
  humanKind,
  kindTone,
  kindWeight,
  strongestKind,
} from './chronicleKinds'
import { DELTA_FIELDS, DELTA_LABEL, deltaOf, sonFaithTotal } from './statDelta'

function stats(data: Record<string, unknown>): EpochStatistics {
  return { data } as unknown as EpochStatistics
}

describe('epoch snapshot comparison', () => {
  it('computes the difference of each metric between two epochs', () => {
    const before = stats({ population: 1000, wars: 3 })
    const after = stats({ population: 1450, wars: 1 })
    expect(deltaOf('population', after, before)).toEqual({
      field: 'population',
      label: 'Population',
      value: 450,
    })
    expect(deltaOf('wars', after, before).value).toBe(-2)
  })

  it('labels every compared metric', () => {
    for (const field of DELTA_FIELDS)
      expect(DELTA_LABEL[field].length).toBeGreaterThan(0)
  })

  it('sums the faith of all sons and tolerates a missing son table', () => {
    expect(
      sonFaithTotal(stats({ sons: { a: { faith: 10 }, b: { faith: 32 } } }))
    ).toBe(42)
    expect(sonFaithTotal(stats({}))).toBe(0)
  })
})

describe('chronicle kinds', () => {
  it('weights deaths above wars above births and falls back to creation', () => {
    expect(kindWeight('death')).toBeGreaterThan(kindWeight('war'))
    expect(kindWeight('war')).toBeGreaterThan(kindWeight('birth'))
    expect(strongestKind(['birth', 'death', 'trade'])).toBe('death')
    expect(strongestKind([])).toBe('creation')
  })

  it('tones destructive kinds and defaults the rest', () => {
    expect(kindTone('curse')).toBe('destructive')
    expect(kindTone('birth')).toBe('success')
    expect(kindTone('trade')).toBe('default')
  })

  it('shows a readable type name', () => {
    expect(humanKind('engine_raw')).toBe('Engine raw')
  })
})
