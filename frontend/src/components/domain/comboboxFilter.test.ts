import { describe, expect, it } from 'vitest'
import { filterOptions } from './comboboxFilter'

const OPTIONS = [
  { value: '1', label: 'Velmora', hint: 'Settlement' },
  { value: '2', label: 'Old Velm', hint: 'Region' },
  { value: '3', label: 'Ashreach', hint: 'Region' },
]

describe('record combobox filter', () => {
  it('puts names that start with the query first and caps the list', () => {
    expect(
      filterOptions(OPTIONS, 'velm', 10).map((option) => option.value)
    ).toEqual(['1', '2'])
    expect(
      filterOptions(OPTIONS, 'region', 10).map((option) => option.value)
    ).toEqual(['2', '3'])
    expect(filterOptions(OPTIONS, '', 2)).toHaveLength(2)
  })
})
