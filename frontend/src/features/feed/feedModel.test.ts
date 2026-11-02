import { type ServerEvent } from '@/realtime'
import { describe, expect, it } from 'vitest'
import {
  FEED_LINE_CAP,
  type FeedLine,
  appendLines,
  buildRows,
  matchesFilter,
  presentCategories,
  toFeedLine,
} from './feedModel'

const AT = '2026-01-01T12:00:00+00:00'

function event(
  id: number,
  kind: string,
  payload: Record<string, unknown>
): ServerEvent {
  return { id, kind, payload, at: AT } as unknown as ServerEvent
}

function note(id: number, feed: string): FeedLine {
  const line = toFeedLine(
    event(id, 'engine.note', {
      epoch: 2,
      phase: 'warfare',
      kind: 'world',
      text: `note ${id}`,
      feed,
    })
  )
  if (!line) throw new Error('expected a line')
  return line
}

describe('feed model', () => {
  it('maps events to actor lines with links', () => {
    const line = toFeedLine(
      event(1, 'son.turn_started', {
        epoch: 3,
        son_id: 7,
        son_name: 'Ithren',
        resumed: false,
      })
    )
    expect(line?.actor).toBe('gods')
    expect(line?.link).toEqual({ kind: 'son', id: '7', label: 'Ithren' })
    expect(line?.epoch).toBe(3)
  })

  it('skips quiet events and categorises world notes', () => {
    expect(
      toFeedLine(
        event(2, 'job.progress', { job_id: 'a', kind: 'epoch', progress: 0.5 })
      )
    ).toBeNull()
    expect(note(3, 'war').category).toBe('war')
  })

  it('appends without duplicates and caps the length', () => {
    const lines = Array.from({ length: FEED_LINE_CAP + 5 }, (_, index) =>
      note(index + 1, 'sky')
    )
    const merged = appendLines([], lines)
    expect(merged).toHaveLength(FEED_LINE_CAP)
    expect(appendLines(merged, [merged[0]])).toBe(merged)
  })

  it('filters by actor and category', () => {
    const war = note(1, 'war')
    expect(
      matchesFilter(war, { actor: 'world', categories: new Set(['war']) })
    ).toBe(true)
    expect(matchesFilter(war, { actor: 'gods', categories: new Set() })).toBe(
      false
    )
    expect(
      matchesFilter(war, { actor: 'all', categories: new Set(['sky']) })
    ).toBe(false)
    expect(presentCategories([war, note(2, 'sky')])).toEqual(['war', 'sky'])
  })

  it('groups long runs of one category behind a similar row', () => {
    const run = [1, 2, 3, 4, 5].map((id) => note(id, 'war'))
    const collapsed = buildRows(run, new Set())
    expect(collapsed.filter((row) => row.type === 'line')).toHaveLength(2)
    const group = collapsed.find((row) => row.type === 'group')
    expect(group?.type === 'group' && group.hidden).toHaveLength(3)
    const expanded = buildRows(run, new Set(['group-1']))
    expect(expanded.filter((row) => row.type === 'line')).toHaveLength(5)
  })
})
