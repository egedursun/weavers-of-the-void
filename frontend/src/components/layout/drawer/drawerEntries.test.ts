import { describe, expect, it } from 'vitest'
import { MAX_DRAWER_DEPTH } from '@/constants/ui'
import {
  parseDrawerStack,
  pushDrawerEntry,
  serializeDrawerStack,
  validateDrawerSearch,
} from './drawerEntries'
import { drawerSearchWith } from './useDrawerStack'

describe('drawer stack codec', () => {
  it('round-trips a stack of record pages', () => {
    const entries = [
      { kind: 'son' as const, id: '7' },
      { kind: 'entity' as const, id: '42' },
      { kind: 'help' as const },
    ]
    const raw = serializeDrawerStack(entries)
    expect(raw).toBe('son:7,entity:42,help')
    expect(parseDrawerStack(raw)).toEqual(entries)
  })

  it('drops unknown kinds, missing ids and ids on singleton pages', () => {
    expect(parseDrawerStack('dragon:1,son:,creator:5,entity:3')).toEqual([
      { kind: 'entity', id: '3' },
    ])
    expect(parseDrawerStack(12)).toEqual([])
    expect(parseDrawerStack('')).toEqual([])
  })

  it('keeps ids that contain the separator', () => {
    expect(parseDrawerStack('world-guide:a:b')).toEqual([
      { kind: 'world-guide', id: 'a:b' },
    ])
  })

  it('does not push the page that is already on top', () => {
    const entries = [{ kind: 'son' as const, id: '7' }]
    expect(pushDrawerEntry(entries, { kind: 'son', id: '7' })).toBe(entries)
    expect(pushDrawerEntry(entries, { kind: 'son', id: '8' })).toHaveLength(2)
  })

  it('caps the stack depth', () => {
    let entries = parseDrawerStack('')
    for (let index = 0; index < MAX_DRAWER_DEPTH + 3; index += 1) {
      entries = pushDrawerEntry(entries, { kind: 'entity', id: String(index) })
    }
    expect(entries).toHaveLength(MAX_DRAWER_DEPTH)
    expect(entries.at(-1)).toEqual({
      kind: 'entity',
      id: String(MAX_DRAWER_DEPTH + 2),
    })
  })

  it('normalises the search parameter', () => {
    expect(validateDrawerSearch({ drawer: 'son:1,bogus' })).toEqual({
      drawer: 'son:1',
    })
    expect(validateDrawerSearch({ drawer: 'bogus' })).toEqual({})
    expect(validateDrawerSearch({})).toEqual({})
  })

  it('removes the parameter when the stack empties', () => {
    expect(drawerSearchWith({ drawer: 'son:1' }, [])).toEqual({})
    expect(drawerSearchWith({}, [{ kind: 'help' }])).toEqual({ drawer: 'help' })
  })
})
