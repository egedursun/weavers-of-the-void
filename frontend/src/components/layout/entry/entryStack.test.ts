import { describe, expect, it } from 'vitest'
import { MAX_ENTRY_DEPTH } from '@/constants/ui'
import {
  parseEntryStack,
  pushEntry,
  serializeEntryStack,
  validateEntrySearch,
} from './entryStack'
import { entrySearchWith } from './useEntryStack'

describe('drawer stack codec', () => {
  it('round-trips a stack of record pages', () => {
    const entries = [
      { kind: 'son' as const, id: '7' },
      { kind: 'entity' as const, id: '42' },
      { kind: 'help' as const },
    ]
    const raw = serializeEntryStack(entries)
    expect(raw).toBe('son:7,entity:42,help')
    expect(parseEntryStack(raw)).toEqual(entries)
  })

  it('drops unknown kinds, missing ids and ids on singleton pages', () => {
    expect(parseEntryStack('dragon:1,son:,creator:5,entity:3')).toEqual([
      { kind: 'entity', id: '3' },
    ])
    expect(parseEntryStack(12)).toEqual([])
    expect(parseEntryStack('')).toEqual([])
  })

  it('keeps ids that contain the separator', () => {
    expect(parseEntryStack('world-guide:a:b')).toEqual([
      { kind: 'world-guide', id: 'a:b' },
    ])
  })

  it('does not push the page that is already on top', () => {
    const entries = [{ kind: 'son' as const, id: '7' }]
    expect(pushEntry(entries, { kind: 'son', id: '7' })).toBe(entries)
    expect(pushEntry(entries, { kind: 'son', id: '8' })).toHaveLength(2)
  })

  it('caps the stack depth', () => {
    let entries = parseEntryStack('')
    for (let index = 0; index < MAX_ENTRY_DEPTH + 3; index += 1) {
      entries = pushEntry(entries, { kind: 'entity', id: String(index) })
    }
    expect(entries).toHaveLength(MAX_ENTRY_DEPTH)
    expect(entries.at(-1)).toEqual({
      kind: 'entity',
      id: String(MAX_ENTRY_DEPTH + 2),
    })
  })

  it('normalises the search parameter', () => {
    expect(validateEntrySearch({ entry: 'son:1,bogus' })).toEqual({
      entry: 'son:1',
    })
    expect(validateEntrySearch({ entry: 'bogus' })).toEqual({})
    expect(validateEntrySearch({})).toEqual({})
  })

  it('removes the parameter when the stack empties', () => {
    expect(entrySearchWith({ entry: 'son:1' }, [])).toEqual({})
    expect(entrySearchWith({}, [{ kind: 'help' }])).toEqual({ entry: 'help' })
  })
})
